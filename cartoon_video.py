"""Cartoon mode — Tom & Jerry style slapstick animation generated from a story description.
Uses the storyboard animator (pure PIL, no API, no GPU) with cartoon characters
(cat, mouse) and slapstick actions (chase, squish, bonk, flatten, trick)."""

import sys, subprocess, time, random, re, os
from pathlib import Path
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, concatenate_videoclips,
    CompositeAudioClip, CompositeVideoClip,
)
import config
from src.engagement import (
    hook_overlays, comment_prompt_overlay, subscribe_end_card,
    branding_overlays, get_audio_duration,
)
from src.storyboard_anim import generate_storyboard_frames

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS

CARTOON_STYLE_TEMPLATES = [
    "Tom and Jerry style cartoon, a {action} scene where {story}",
    "Classic slapstick cartoon comedy, {description}",
    "Vintage cartoon cat and mouse chase, {description}",
]

FALLBACK_STORIES = [
    "A mischievous mouse sneaks a piece of cheese from the kitchen. "
    "The cat chases the mouse around the house. "
    "The mouse tricks the cat into running into a wall, squishing him flat. "
    "The cat gets bonked on the head by a falling frying pan. "
    "The mouse giggles and eats the cheese while the cat shakes his head, dazed.",

    "A lazy orange cat is napping in the sun. "
    "A tiny mouse tiptoes past carrying a giant piece of cheese. "
    "The cat wakes up and chases the mouse through the living room. "
    "The mouse hides behind a vase and the cat crashes into it. "
    "The mouse dances on the cat's head while he's dizzy.",
]


def _generate_cartoon_story(user_story: str) -> list[str]:
    """Generate a multi-scene cartoon story. Uses LLM if available, else fallback."""
    if not user_story:
        return random.choice(FALLBACK_STORIES).split(". ")
    
    try:
        from src.script_generator import _generate
        raw = _generate(
            f"Break this cartoon story into 4-6 short scene descriptions for a silent slapstick "
            f"cartoon with a cat and mouse. Each scene should describe a visual action. "
            f"Use words like: chases, squishes, bonks, flattens, tricks. "
            f"Story: {user_story}\n\n"
            f"Return each scene on a separate line, starting with 'Scene: '. "
            f"Example:\n"
            f"Scene: The cat chases the mouse through the kitchen\n"
            f"Scene: The mouse hides and the cat bonks into the wall\n"
            f"Scene: The mouse squishes the cat with a frying pan\n"
            f"Scene: The cat shakes his head while the mouse dances",
            temperature=0.8, max_tokens=300,
            system="You write short visual scene descriptions for a silent Tom & Jerry style cartoon with a cat and a mouse.",
        )
        if raw:
            scenes = []
            for line in raw.strip().split("\n"):
                line = line.strip()
                if line.lower().startswith("scene"):
                    scenes.append(re.sub(r'^Scene[:\s]*', '', line, flags=re.IGNORECASE))
            if len(scenes) >= 3:
                return scenes
    except Exception as e:
        print(f"  LLM unavailable ({e}), using fallback")

    return random.choice(FALLBACK_STORIES).split(". ")


def main():
    print("=" * 55)
    print("  CARTOON MODE — Tom & Jerry Style Slapstick")
    print("=" * 55)

    user_story = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not user_story:
        print("  No story provided — auto-generating one...")
    else:
        print(f"  Story: {user_story}")

    print("[1/4] Generating cartoon story...")
    scenes = _generate_cartoon_story(user_story)
    for i, s in enumerate(scenes):
        print(f"  Scene {i+1}: {s}")

    full_prompt = ". ".join(scenes)
    print(f"\n  Full prompt: {full_prompt}")

    print("\n[2/4] Generating voiceover...")
    tts_text = f"Watch as our cartoon cat and mouse get into all sorts of silly trouble. "
    tts_text += ". ".join(scenes) + ". Isn't that hilarious?"
    tts_path = config.TEMP_DIR / "cartoon_narration.mp3"
    try:
        subprocess.run(
            [sys.executable, "-m", "edge_tts", "--text", tts_text,
             "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)],
            capture_output=True, text=True, timeout=120, check=True,
        )
    except Exception:
        print("  TTS failed, using fallback audio duration")
        tts_path = None
    total_dur = get_audio_duration(str(tts_path)) if tts_path and tts_path.exists() else 15.0
    print(f"  Duration: {total_dur:.1f}s")

    print("\n[3/4] Rendering cartoon frames...")
    frame_arrays = generate_storyboard_frames(prompt=full_prompt, w=W, h=H, fps=FPS)
    total_frames = len(frame_arrays)
    print(f"  {total_frames} frames = {total_frames / FPS:.1f}s @ {FPS}fps")

    if total_dur > total_frames / FPS and total_frames > 0:
        pad_needed = int((total_dur - total_frames / FPS) * FPS)
        if pad_needed > 0:
            frame_arrays.extend([frame_arrays[-1]] * min(pad_needed, FPS * 3))
            total_frames = len(frame_arrays)
            print(f"  Padded to {total_frames} frames ({total_frames / FPS:.1f}s)")

    if total_frames == 0:
        print("  ERROR: No frames generated!")
        return None, None

    frame_dur = total_dur / max(total_frames, 1)
    def make_frame(t):
        return frame_arrays[min(int(t / frame_dur), total_frames - 1)]

    bg = VideoClip(make_frame, duration=total_dur)

    print("\n[4/4] Assembling final video...")
    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(total_dur)

    end_clip = subscribe_end_card(np.zeros((H, W, 3), dtype=np.uint8), 1.2)
    bg = concatenate_videoclips([bg, end_clip], method="compose")
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)

    if tts_path and tts_path.exists():
        audio_clip = AudioFileClip(str(tts_path))
        music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
        if music_paths:
            music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_dur).with_volume_scaled(0.08)
            final = final.with_audio(CompositeAudioClip([audio_clip, music]))
        else:
            final = final.with_audio(audio_clip)

    safe_title = "cartoon_cat_and_mouse"
    out = config.OUTPUT_DIR / f"{safe_title}_{int(time.time())}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur:.1f}s | {W}x{H} | {total_frames} frames")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-crf", "18", "-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1 - t0:.0f}s: {out}")
    return out, {"title": "Cartoon Cat and Mouse", "scenes": scenes}


if __name__ == "__main__":
    main()
