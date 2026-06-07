"""Sketch-story video: script → hand-drawn illustrations + text → TTS → video with word-sync."""

import sys, re, time, random, json, math, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip, ImageClip, TextClip,
)
import config
from src.text_to_speech import generate_tts_with_timestamps
from src.engagement import subscribe_end_card

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS

# ─── Script parser ─────────────────────────────────────────────

def parse_script(text: str) -> list[dict]:
    """Split script into scenes: each has a title and narration lines."""
    scenes = []
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    current_title = ""
    current_narration = []

    for line in lines:
        line_stripped = line.strip("[]*# ")
        if line.startswith("[") and line.endswith("]"):
            if current_narration:
                scenes.append({
                    "title": current_title,
                    "narration": " ".join(current_narration),
                })
            current_title = line_stripped
            current_narration = []
        elif line.startswith("#"):
            continue
        else:
            removed_brackets = re.sub(r'\[.*?\]', '', line).strip()
            if removed_brackets:
                current_narration.append(removed_brackets)

    if current_narration:
        scenes.append({
            "title": current_title,
            "narration": " ".join(current_narration),
        })

    return scenes

# ─── Scene image generator ──────────────────────────────────────

def _get_font(size=36):
    try:
        return ImageFont.truetype(config.get_font(), size)
    except:
        return ImageFont.load_default()

def generate_scene_image(title: str, narration: str, scene_idx: int) -> Image.Image:
    """Generate a full-color procedural illustration with title text embedded."""
    from src.narration_to_sketch import sketch_from_narration

    # Generate scene from narration (uses SceneComposer offline, no API needed)
    prompt = f"{title}: {narration}"
    img = sketch_from_narration(prompt, width=W, height=H, seed=scene_idx)

    # Convert to RGBA for overlay
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # ── Scene number badge ──
    badge_size = 44
    badge_text = f"{scene_idx:02d}"
    bf = _get_font(badge_size)
    badge_x, badge_y = 30, 30
    bb = draw.textbbox((0, 0), badge_text, font=bf)
    bw, bh = bb[2]-bb[0]+20, bb[3]-bb[1]+10
    draw.rounded_rectangle([badge_x, badge_y, badge_x+bw, badge_y+bh], radius=8, fill=(0,0,0,160))
    draw.text((badge_x+10, badge_y+5), badge_text, font=bf, fill=(255,255,255,220))

    # ── Title card at top ──
    title_font = _get_font(42)
    title_lines = []
    current = ""
    for w in title.split():
        test = (current + " " + w).strip()
        tb = draw.textbbox((0, 0), test, font=title_font)
        if tb[2]-tb[0] > W - 120:
            title_lines.append(current)
            current = w
        else:
            current = test
    title_lines.append(current)

    # Title background pill
    all_title = " / ".join(title_lines)
    tb = draw.textbbox((0, 0), all_title, font=title_font)
    pill_w = tb[2]-tb[0] + 60
    pill_h = len(title_lines) * 55 + 30
    pill_x = (W - pill_w) // 2
    pill_y = 80
    draw.rounded_rectangle([pill_x, pill_y, pill_x+pill_w, pill_y+pill_h], radius=12, fill=(0,0,0,140))

    for i, line in enumerate(title_lines):
        tb = draw.textbbox((0, 0), line, font=title_font)
        tx = (W - (tb[2]-tb[0])) // 2
        ty = pill_y + 15 + i * 55
        draw.text((tx+1, ty+1), line, font=title_font, fill=(0,0,0,160))
        draw.text((tx, ty), line, font=title_font, fill=(255,255,255,230))

    # ── Key quote overlay at bottom ──
    sentences = [s.strip() for s in narration.split(".") if len(s.strip()) > 15]
    if sentences:
        quote = sentences[-1] if len(sentences) > 1 else sentences[0]
        if len(quote) > 60:
            quote = quote[:57] + "..."
        qf = _get_font(26)
        qb = draw.textbbox((0, 0), quote, font=qf)
        qw = qb[2]-qb[0] + 40
        qh = qb[3]-qb[1] + 20
        qx = (W - qw) // 2
        qy = H - 100
        draw.rounded_rectangle([qx, qy, qx+qw, qy+qh], radius=10, fill=(0,0,0,120))
        draw.text((qx+20, qy+10), quote, font=qf, fill=(255,255,255,200))

    return img.convert("RGB")

# ─── Caption rendering ─────────────────────────────────────────

def render_captions(frame: np.ndarray, all_words: list[dict], word_start: int, word_end: int, current_word_idx: int) -> np.ndarray:
    """Draw word-level captions at bottom with highlight on current word."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    font = _get_font(38)
    hl_font = _get_font(44)

    bar_h = 120
    overlay = Image.new("RGBA", (W, bar_h), (0, 0, 0, 180))
    img.paste(overlay, (0, H - bar_h - 20), overlay)

    words_to_show = []
    for wi in range(word_start, min(word_end + 1, len(all_words))):
        words_to_show.append(all_words[wi]["text"])

    y = H - bar_h + 25
    x = 30
    max_x = W - 30
    line_y = y

    for i, w in enumerate(words_to_show):
        wi_global = word_start + i
        is_current = (wi_global == current_word_idx and current_word_idx >= 0)
        f = hl_font if is_current else font
        color = (255, 220, 80) if is_current else (255, 255, 255)
        display = " " + w + " "
        bb = draw.textbbox((0, 0), display, font=f)
        ww = bb[2] - bb[0]
        if x + ww > max_x:
            x = 30
            line_y += 52
        if is_current:
            pill_pad = 6
            draw.rounded_rectangle(
                [x - pill_pad, line_y - 4, x + ww + pill_pad, line_y + 44],
                radius=6, fill=(200, 80, 60, 180),
            )
        draw.text((x, line_y), display, font=f, fill=color)
        x += ww

    return np.array(img)

# ─── Main video builder ────────────────────────────────────────

def build_story_video(scenes: list[dict], output_path: str):
    print(f"\n{'='*55}")
    print(f"  SKETCH STORY VIDEO — {len(scenes)} scenes")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "story_video"
    temp_dir.mkdir(exist_ok=True)

    # Step 1: Generate scene images with text overlays
    print(f"\n[1/4] Drawing {len(scenes)} full-color illustration scenes with text...")
    scene_images = []
    for i, scene in enumerate(scenes):
        print(f"  Scene {i+1}: {scene['title'][:40]}")
        img = generate_scene_image(scene["title"], scene["narration"], i + 1)
        scene_images.append(np.array(img))

    # Step 2: Generate TTS with word timestamps
    print(f"\n[2/4] Generating narration TTS...")
    full_script = " ".join(s["narration"] for s in scenes)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_script, tts_path)
    total_dur = words[-1]["end"] if words else 5.0
    print(f"  {total_dur:.1f}s | {len(words)} words | {len(scenes)} scenes")

    # Step 3: Build timeline
    print(f"\n[3/4] Building scene timeline...")
    timeline = []
    global_word_idx = 0
    for i, scene in enumerate(scenes):
        scene_words = scene["narration"].split()
        w_start = global_word_idx
        w_end = w_start + len(scene_words) - 1
        if w_end >= len(words):
            w_end = len(words) - 1
        s_start = words[w_start]["start"]
        s_end = words[w_end]["end"]
        timeline.append({
            "image": scene_images[i],
            "start": s_start,
            "end": s_end,
            "word_start": w_start,
            "word_end": w_end,
        })
        global_word_idx = w_end + 1

    # Step 4: Render video
    print(f"\n[4/4] Rendering video ({W}x{H} @ {FPS}fps)...")

    TITLE_DUR = 2.0
    END_DUR = 2.0
    video_dur = total_dur + TITLE_DUR + END_DUR
    bg_blank = np.full((H, W, 3), 248, dtype=np.uint8)

    # Pre-render title page
    title_page = Image.new("RGB", (W, H), (252, 250, 245))
    tdraw = ImageDraw.Draw(title_page)
    tf = _get_font(56)
    sf = _get_font(28)
    title = scenes[0]["title"] if scenes else "Story"
    lines = []
    current = ""
    for w in title.split():
        test = (current + " " + w).strip()
        tb = tdraw.textbbox((0, 0), test, font=tf)
        if tb[2]-tb[0] > W - 100:
            lines.append(current)
            current = w
        else:
            current = test
    lines.append(current)
    y = H // 2 - 80
    for line in lines:
        tb = tdraw.textbbox((0, 0), line, font=tf)
        tdraw.text(((W-(tb[2]-tb[0]))//2, y), line, font=tf, fill=(30, 25, 20))
        y += 75
    sub = "A HAND-DRAWN STORY"
    tb = tdraw.textbbox((0, 0), sub, font=sf)
    tdraw.text(((W-(tb[2]-tb[0]))//2, H-200), sub, font=sf, fill=(150, 140, 130))
    title_arr = np.array(title_page)

    # Transition cache
    TRANSITION_DUR = 0.5
    trans_cache = {}
    for i in range(len(scene_images) - 1):
        frames = []
        nf = int(TRANSITION_DUR * FPS)
        for fi in range(nf):
            t = fi / nf
            ease = t * t * (3 - 2 * t)
            blended = ((1 - ease) * scene_images[i].astype(np.float32) + ease * scene_images[i+1].astype(np.float32)).astype(np.uint8)
            frames.append(blended)
        trans_cache[i] = frames

    def make_frame(t):
        if t < TITLE_DUR:
            p = t / TITLE_DUR
            alpha = int(255 * (p * p * (3 - 2 * p)))
            if alpha < 255:
                return ((bg_blank.astype(np.float32) * (255 - alpha) + title_arr.astype(np.float32) * alpha) / 255).astype(np.uint8)
            return title_arr

        t_rel = t - TITLE_DUR

        if t_rel > total_dur:
            return bg_blank

        # Find active scene
        active = None
        active_idx = -1
        for i, s in enumerate(timeline):
            if s["start"] <= t_rel < s["end"]:
                active = s
                active_idx = i
                break

        if active is None:
            for i, s in reversed(list(enumerate(timeline))):
                if t_rel >= s["end"]:
                    active = s
                    active_idx = i
                    break

        if active is None:
            return bg_blank

        # Transition blend
        base = active["image"]
        if active_idx < len(timeline) - 1:
            next_start = timeline[active_idx + 1]["start"]
            if next_start is not None and abs(next_start - active["end"]) < 0.05:
                trans_t = t_rel - active["end"]
                if 0 <= trans_t < TRANSITION_DUR and active_idx in trans_cache:
                    cached = trans_cache[active_idx]
                    fi = min(int(trans_t * FPS), len(cached) - 1)
                    base = cached[fi]

        # Word sync
        current_word_idx = -1
        for wi in range(active["word_start"], min(active["word_end"] + 1, len(words))):
            if words[wi]["start"] <= t_rel:
                current_word_idx = wi
            else:
                break

        return render_captions(base, words, active["word_start"], active["word_end"], current_word_idx)

    bg_clip = VideoClip(make_frame, duration=video_dur)

    # Audio
    audio = AudioFileClip(str(tts_path))
    if video_dur > audio.duration + TITLE_DUR:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio.duration - TITLE_DUR).with_volume_scaled(0)
        audio = concatenate_audioclips([audio, silence])

    # Background music
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.04)
        final_audio = CompositeAudioClip([audio, music])
    else:
        final_audio = audio

    # End card
    end_card = subscribe_end_card(np.full((H, W, 3), 240, dtype=np.uint8), END_DUR)
    end_card = end_card.with_start(total_dur + TITLE_DUR)

    final = CompositeVideoClip([bg_clip, end_card], size=config.SHORTS_SIZE)
    final = final.with_audio(final_audio)

    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    print(f"\n  ✓ Done in {time.time()-t0:.0f}s: {output_path}")
    print(f"  Size: {os.path.getsize(output_path):,} bytes")
    return output_path

def main():
    script_path = sys.argv[1] if len(sys.argv) > 1 else None
    if script_path and os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            text = f.read()
    elif script_path:
        text = script_path
    else:
        # Built-in pirate script
        text = """[Opening Hook]

Picture a pirate. A ragged man with a wooden leg, a parrot on his shoulder, and a chest overflowing with gold. He swings across ships shouting Arrr while searching for buried treasure on a tropical island. It sounds exciting. But almost none of it was true. The real life of a pirate was far stranger and far harsher.

[Why Become a Pirate]

Imagine it is the year 1715. You are a young sailor. Every day you work on a merchant ship. The food is rotten. The captain beats crew members for small mistakes. Your pay is delayed for months sometimes years. Then one day a pirate ship appears on the horizon. The merchant crew surrenders. And instead of forcing you to stay the pirates offer you a choice. Join them. For many sailors becoming a pirate was about escaping a worse life.

[Pirate Democracy]

Surprisingly pirate ships were often more democratic than many countries of their time. Captains were not absolute rulers. Crew members could vote. If a captain became cruel or incompetent the crew could remove him. Treasure was divided according to agreed shares. Even compensation existed. Lose an arm in battle and you might receive extra payment. A floating workplace where common sailors had a voice.

[Life at Sea]

Do not imagine endless parties. Most pirate days were incredibly boring. Weeks could pass without spotting a target. The sun burned relentlessly. Fresh water became stale. Food spoiled quickly. Meals often consisted of hard biscuits crawling with insects. Rats shared the ship. Storms could appear without warning. Every creak of the ship reminded sailors how fragile their world was.

[The Truth About Treasure]

Forget giant treasure chests filled with gold. Most pirate loot was surprisingly ordinary. Sugar. Tobacco. Cloth. Spices. Tools. Anything valuable enough to sell. The famous buried treasure stories are mostly myths. Pirates wanted money they could spend immediately. Burying wealth made little sense when you might be dead within months.

[The Constant Fear]

Pirate life was extremely dangerous. Governments across Europe hunted pirates relentlessly. Naval warships patrolled the seas. Captured pirates faced brutal punishment. Many were hanged in public. Their bodies displayed near harbors as warnings. Every sail on the horizon could be an opportunity or the beginning of your execution.

[The Golden Age Ends]

For a brief moment pirates ruled parts of the Atlantic Ocean. Names like Blackbeard became legendary. But governments adapted. Navies grew stronger. Trade routes became better protected. By the 1720s the Golden Age of Piracy was collapsing. The era that inspired countless stories was ending.

[Ending]

The real pirate life was not a carefree adventure. It was a gamble. Freedom in exchange for danger. Democracy mixed with violence. Hope mixed with hunger. Many pirates never found riches. Many never returned home. Yet for thousands of sailors trapped in a brutal world piracy offered something precious. A chance to choose their own fate. And perhaps that is why centuries later we are still fascinated by them."""
    scenes = parse_script(text)
    print(f"Parsed {len(scenes)} scenes:")
    for i, s in enumerate(scenes):
        print(f"  {i+1}. {s['title'][:50]}")

    safe = re.sub(r'[^\w]+', '_', scenes[0]["title"].lower())[:30] if scenes else "story"
    out = config.OUTPUT_DIR / f"story_{safe}.mp4"
    build_story_video(scenes, out)

if __name__ == "__main__":
    main()
