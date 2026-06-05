"""Narration-synced fact video — word-timestamp-aligned captions + per-phrase visuals."""

import sys, time, random, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, ImageClip, TextClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.engagement import hook_overlays, comment_prompt_overlay, subscribe_end_card, branding_overlays
from src.image_gen import gen_img
from src.cinematic import apply_camera_move, enhance_frame, render_brand_overlay
from src.text_to_speech import generate_tts_with_timestamps

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
BRAND = config.BRAND_NAME


def extract_phrases(fact: str, max_phrases: int = 3) -> list[str]:
    """Split a fact into visual phrases for separate imagery."""
    import re
    normalized = fact.replace("\u2014", " ").replace("\u2013", " ").replace("  ", " ")
    for sep in [",", " but ", " and ", " because ", " while ", " which ", " that "]:
        parts = [p.strip().strip(".,!?;:'\"") for p in normalized.split(sep) if len(p.strip()) > 8]
        if len(parts) >= 2:
            return [p for p in parts[:max_phrases] if p]
    words = normalized.split()
    if len(words) > 6:
        mid = len(words) // 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]
    return [fact]


def find_fact_word_range(fact: str, full_text: str, words: list[dict]) -> tuple[int, int]:
    """Find start/end word index for a fact using word-sequence matching (ignores punctuation/case)."""
    import re
    fact_parts = [re.sub(r"[^\w\s'-]", "", w).lower().strip() for w in fact.split()]
    fact_parts = [w for w in fact_parts if w]
    all_parts = [re.sub(r"[^\w\s'-]", "", w["text"]).lower().strip() for w in words]
    for start in range(len(all_parts)):
        match = True
        for j, fw in enumerate(fact_parts):
            if start + j >= len(all_parts) or all_parts[start + j] != fw:
                match = False
                break
        if match:
            return start, start + len(fact_parts) - 1
    return 0, len(words) - 1


def make_title_card(img: Image.Image, title: str) -> np.ndarray:
    img = img.copy()
    draw = ImageDraw.Draw(img)
    overlay = Image.new("RGBA", (W, int(H * 0.3)), (0, 0, 0, 160))
    img.paste(overlay, (0, H - int(H * 0.3)), overlay)
    try:
        font = ImageFont.truetype(config.get_font(), 44)
    except:
        font = ImageFont.load_default()
    bb = draw.textbbox((0, 0), title.upper(), font=font)
    draw.text(((W - (bb[2] - bb[0])) // 2, H - 220), title.upper(), font=font, fill=(255, 255, 255))
    try:
        font2 = ImageFont.truetype(config.get_font(), 28)
    except:
        font2 = ImageFont.load_default()
    bb2 = draw.textbbox((0, 0), "SWIPE FOR MORE", font=font2)
    draw.text(((W - (bb2[2] - bb2[0])) // 2, H - 120), "SWIPE FOR MORE", font=font2, fill=(255, 200, 0))
    return np.array(img)


def render_captions(frame: np.ndarray, fact_words: list[str], spoken_idx: int) -> np.ndarray:
    """Overlay words spoken so far, highlighting current word."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(config.get_font(), 50)
        font_hl = ImageFont.truetype(config.get_font(), 54)
    except:
        font = font_hl = ImageFont.load_default()

    bar_h = 140
    overlay = Image.new("RGBA", (W, bar_h), (0, 0, 0, 170))
    img.paste(overlay, (0, H - bar_h - 20), overlay)

    y = H - bar_h + 15
    x = 25
    max_x = W - 25
    current = ""
    line_y = y

    for i, w in enumerate(fact_words):
        is_current = (i == spoken_idx)
        f = font_hl if is_current else font
        color = (255, 220, 80) if is_current else (255, 255, 255)
        if i > spoken_idx:
            break
        if i == spoken_idx:
            display_w = " " + w + " "
        else:
            display_w = " " + w
        bb = draw.textbbox((0, 0), display_w, font=f)
        word_w = bb[2] - bb[0]
        if x + word_w > max_x:
            x = 25
            line_y += 60
        draw.text((x, line_y), display_w, font=f, fill=color)
        x += word_w

    return np.array(img)


def main():
    print("=" * 50)
    print("  FACTS VIDEO — narration-synced")
    print("=" * 50)

    from src.facts import generate_fact_script
    fact_data = generate_fact_script()
    TITLE = fact_data["title"]
    FACTS = fact_data["facts"]
    HOOK = fact_data["hook"]
    NICHE = fact_data.get("niche", "")

    temp_dir = config.TEMP_DIR / "fact_video"
    temp_dir.mkdir(exist_ok=True)

    tts_script = fact_data.get("tts_script", f"{HOOK} {' '.join(FACTS)}")

    print("\n[1/5] Generating TTS with word timestamps...")
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(tts_script, tts_path)
    total_dur = words[-1]["end"] if words else 5.0
    print(f"  {total_dur:.1f}s | {len(words)} words | {len(FACTS)} facts")

    print("\n[2/5] Extracting per-fact word ranges and phrases...")
    fact_infos = []
    phrase_visuals = []
    for i, fact in enumerate(FACTS):
        w_start, w_end = find_fact_word_range(fact, tts_script, words)
        fact_start = words[w_start]["start"]
        fact_end = words[w_end]["end"]
        phrases = extract_phrases(fact, max_phrases=3)
        seg_dur = (fact_end - fact_start) / max(len(phrases), 1)
        segments = []
        for pi, phrase in enumerate(phrases):
            seg_start = fact_start + pi * seg_dur
            seg_end = seg_start + seg_dur if pi < len(phrases) - 1 else fact_end
            segments.append({"phrase": phrase, "start": seg_start, "end": seg_end, "image": None})
        fact_infos.append({
            "fact": fact,
            "word_start": w_start,
            "word_end": w_end,
            "start": fact_start,
            "end": fact_end,
            "segments": segments,
            "phrases": phrases,
        })
        phrase_visuals.append(segments)

    print(f"\n[3/5] Generating {sum(len(s) for s in phrase_visuals)} images for phrases...")
    for fi, fact_info in enumerate(fact_infos):
        for si, seg in enumerate(fact_info["segments"]):
            cached = temp_dir / f"p_{fi}_{si}.png"
            phrase = seg["phrase"]
            prompt = f"{phrase}, cinematic, atmospheric lighting, vertical, highly detailed, moody"
            if cached.exists() and cached.stat().st_size > 50000:
                img = Image.open(cached)
            else:
                print(f"  Fact {fi+1}/{len(FACTS)} phrase {si+1}: {phrase[:50]}...", end=" ", flush=True)
                img = gen_img(prompt)
                if img:
                    img.save(cached)
                    print("OK")
                else:
                    print("fallback")
                    from src.image_gen import _generate_scene
                    img = _generate_scene(W, H, prompt)
            seg["image"] = np.array(img.resize((W, H), Image.LANCZOS)) if img else None

        first_good = None
        for seg in fact_info["segments"]:
            if seg["image"] is not None:
                first_good = seg["image"]
                break
        if first_good is None:
            from src.image_gen import _generate_scene
            fallback = _generate_scene(W, H, f"abstract {fact_info['fact']}")
            fallback_arr = np.array(fallback.resize((W, H), Image.LANCZOS))
            for seg in fact_info["segments"]:
                if seg["image"] is None:
                    seg["image"] = fallback_arr
            fact_infos[fi]["title_image"] = fallback_arr
        else:
            fact_infos[fi]["title_image"] = first_good

    print("\n[4/5] Building timeline and rendering frames...")
    title_img_arr = make_title_card(
        Image.fromarray(fact_infos[0]["title_image"]) if fact_infos[0]["title_image"] is not None else Image.new("RGB", (W, H), (20, 20, 40)),
        TITLE
    )

    move_types = ["ken_burns_in", "ken_burns_out", "pan_right", "pan_left", "dolly_in", "dolly_out"]

    def make_frame(t):
        # Title card: 0.8s
        if t < 0.8:
            progress = t / 0.8
            f = apply_camera_move(title_img_arr, progress, "ken_burns_in", W, H)
            f = enhance_frame(f, color_grade="dramatic", vignette=True)
            if BRAND:
                f = render_brand_overlay(f, BRAND)
            return f

        # End card: last 1.5s
        if t > total_dur:
            end_t = (t - total_dur) / 1.5
            black = np.zeros((H, W, 3), dtype=np.uint8)
            from src.cinematic import crossfade
            f = crossfade(black, black, min(end_t * 2, 1))
            return f

        # Find active fact — fill gaps with last known fact
        active_fact = None
        active_seg = None
        active_fact_idx = -1
        for fi, fi_data in enumerate(fact_infos):
            if fi_data["start"] <= t < fi_data["end"]:
                active_fact = fi_data
                active_fact_idx = fi
                for seg in fi_data["segments"]:
                    if seg["start"] <= t < seg["end"]:
                        active_seg = seg
                        break
                if active_seg is None:
                    active_seg = fi_data["segments"][-1]
                break
            elif t < fi_data["start"]:
                break

        # Fill gap before first fact with black
        if active_fact is None:
            for fi, fi_data in reversed(list(enumerate(fact_infos))):
                if t > fi_data["end"]:
                    active_fact = fi_data
                    active_fact_idx = fi
                    active_seg = fi_data["segments"][-1]
                    break

        if active_fact is None or active_seg is None:
            return np.zeros((H, W, 3), dtype=np.uint8)

        img_arr = active_seg["image"]
        if img_arr is None:
            img_arr = active_fact["title_image"]

        seg_progress = (t - active_seg["start"]) / max(active_seg["end"] - active_seg["start"], 0.1)
        move = move_types[(active_fact_idx * 3 + active_fact["segments"].index(active_seg)) % len(move_types)]
        f = apply_camera_move(img_arr, min(seg_progress, 1), move, W, H)
        f = enhance_frame(f, color_grade="dramatic", vignette=True)
        if BRAND:
            f = render_brand_overlay(f, BRAND)

        # Caption: show words of this fact spoken so far
        fact_words = active_fact["fact"].split()
        spoken_idx = -1
        for wi in range(active_fact["word_start"], min(active_fact["word_end"] + 1, len(words))):
            if words[wi]["start"] <= t:
                spoken_idx = wi - active_fact["word_start"]
            else:
                break
        if spoken_idx >= 0:
            f = render_captions(f, fact_words, spoken_idx)

        return f

    video_dur = total_dur + 1.5
    bg_clip = VideoClip(make_frame, duration=video_dur)

    audio_clip = AudioFileClip(str(tts_path))
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])

    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(bg_clip.duration)

    # End card overlay
    end_arr = np.zeros((H, W, 3), dtype=np.uint8)
    end_card = subscribe_end_card(end_arr, 1.5).with_start(total_dur)
    overlays.append(end_card)

    final = CompositeVideoClip([bg_clip] + overlays, size=config.SHORTS_SIZE)

    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print(f"\n[5/5] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:50]
    out = config.OUTPUT_DIR / f"facts_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H} | {FPS}fps | {len(words)} word-timed segments")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")

    return out, fact_data


if __name__ == "__main__":
    main()
