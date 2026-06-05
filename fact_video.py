"""Fact-based Shorts video — cinematic, professional, zero API keys needed."""

import sys, subprocess, time, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, ImageClip, TextClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.engagement import hook_overlays, comment_prompt_overlay, subscribe_end_card, branding_overlays, get_audio_duration
from src.image_gen import gen_img
from src.cinematic import (
    apply_camera_move, enhance_frame, render_professional_caption,
    render_brand_overlay, generate_transition_frames,
)

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS

CURRENT_FACTS = []
CURRENT_NICHE = ""

BRAND = config.BRAND_NAME


def _generate_cinematic_frames(prompt: str, num_frames: int,
                                 move_type: str = "ken_burns_in") -> list[np.ndarray]:
    """Generate a cinematic frame sequence for a single prompt."""
    img = gen_img(prompt)
    if img is None:
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        for y in range(H):
            arr[y, :] = [int(20 + 40*(y/H)), int(10 + 20*(1-y/H)), int(40 + 60*(y/H))]
    else:
        arr = np.array(img)

    frames = []
    for i in range(num_frames):
        progress = i / max(num_frames - 1, 1)
        frame = apply_camera_move(arr, progress, move_type, W, H)
        frame = enhance_frame(frame, color_grade="dramatic", vignette=True)
        if BRAND:
            frame = render_brand_overlay(frame, BRAND)
        frames.append(frame)
    return frames


def main():
    global CURRENT_FACTS, CURRENT_NICHE

    print("=" * 50)
    print("  CINEMATIC FACTS")
    print("=" * 50)

    from src.facts import generate_fact_script
    fact_data = generate_fact_script()
    CURRENT_FACTS = fact_data["facts"]
    CURRENT_NICHE = fact_data["niche"]

    TITLE = fact_data["title"]
    FACTS = fact_data["facts"]
    PROMPTS = fact_data["image_prompts"][:len(FACTS)]
    HOOK = fact_data["hook"]

    temp_dir = config.TEMP_DIR / "fact_video"
    temp_dir.mkdir(exist_ok=True)

    print("\n[1/4] Voiceover...")
    tts_script = fact_data.get("tts_script", f"{HOOK} {' '.join(FACTS)}")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s | {len(FACTS)} facts")

    print("\n[2/4] Generating cinematic frames...")
    dur_per_fact = total_dur / max(len(FACTS), 1)
    frames_per_fact = max(8, int(dur_per_fact * FPS))
    move_types = ["ken_burns_in", "ken_burns_out", "pan_right", "pan_left", "dolly_in", "dolly_out"]

    all_frames = []
    for i, (fact, prompt) in enumerate(zip(FACTS, PROMPTS)):
        print(f"  Scene {i+1}/{len(FACTS)}: {fact[:40]}...")
        move = move_types[i % len(move_types)]
        scene_frames = _generate_cinematic_frames(prompt, frames_per_fact, move)

        text_overlay_frames = []
        for f in scene_frames:
            caption = f"#{i+1}"
            f_with_text = render_professional_caption(f, fact.upper(), font_size=36)
            text_overlay_frames.append(f_with_text)
        all_frames.extend(text_overlay_frames)

        if i < len(FACTS) - 1:
            next_prompt = PROMPTS[i + 1] if i + 1 < len(PROMPTS) else prompt
            next_img = gen_img(next_prompt)
            if next_img:
                next_arr = np.array(next_img)
                transition_frames = []
                for t in range(8):
                    p = t / 7
                    frame_a = apply_camera_move(scene_frames[-1], 1.0, move, W, H)
                    frame_b = apply_camera_move(next_arr, 0.0, move_types[(i+1) % len(move_types)], W, H)
                    blended = ((frame_a * (1 - p) + frame_b * p)).astype(np.uint8)
                    blended = enhance_frame(blended, color_grade="dramatic", vignette=True)
                    transition_frames.append(blended)
                all_frames.extend(transition_frames)

    total_frames = len(all_frames)
    print(f"  {total_frames} frames generated")

    print("\n[3/4] Assembling video...")
    frame_dur = total_dur / max(total_frames, 1)
    def make_frame(t):
        idx = min(int(t / frame_dur), total_frames - 1)
        return all_frames[idx]
    bg = VideoClip(make_frame, duration=total_dur)

    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(bg.duration)

    end_arr = np.zeros((H, W, 3), dtype=np.uint8)
    end_clip = subscribe_end_card(end_arr, 1.5)
    bg = concatenate_videoclips([bg, end_clip], method="compose")

    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)

    audio_clip = AudioFileClip(str(tts_path))
    video_dur = total_dur + 1.5
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print("\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:50]
    out = config.OUTPUT_DIR / f"cinematic_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H} | {FPS}fps")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")

    return out, fact_data


if __name__ == "__main__":
    main()
