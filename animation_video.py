"""AI Animation video — procedural frame-by-frame animation (no API key needed)."""

import sys, subprocess, time, random
from pathlib import Path
import numpy as np
from moviepy import (
    VideoClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
    CompositeVideoClip,
)
import config
from src.animation_gen import generate_animation_script
from src.engagement import (
    hook_overlays,
    comment_prompt_overlay,
    subscribe_end_card,
    branding_overlays,
    get_audio_duration,
)
from src.procedural_anim import animate_scene

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


def main():
    print("=" * 50)
    print("  AI ANIMATION GENERATOR")
    print("=" * 50)

    user_prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not user_prompt:
        print("  No prompt provided — auto-generating one...")
        try:
            from src.script_generator import _generate
            raw = _generate(
                "Suggest a single visually interesting subject for an AI animation video. "
                "Examples: 'a cat exploring a neon city', 'a dragon flying over mountains', "
                "'a jellyfish glowing in the deep ocean'. Return ONLY the subject, 3-10 words.",
                temperature=0.9, max_tokens=30,
                system="You suggest creative subjects for AI animation.",
            )
            user_prompt = raw.strip().strip('"').strip("'") if raw else ""
        except Exception:
            user_prompt = ""
        if not user_prompt:
            user_prompt = random.choice([
                "a duck swimming in a pond",
                "a cat exploring a neon city",
                "a dragon flying over mountains",
                "a jellyfish glowing in the deep ocean",
                "a fox in an enchanted forest",
                "a hummingbird drinking nectar",
            ])
        print(f"  Auto-generated prompt: {user_prompt}")

    data = generate_animation_script(user_prompt)
    SUBJECT = data["subject"]
    narration = data["narration"]

    temp_dir = config.TEMP_DIR / "animation"
    temp_dir.mkdir(exist_ok=True)

    print(f"\n[1/4] Voiceover: {SUBJECT}")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", narration, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)],
        capture_output=True, text=True, timeout=120, check=True,
    )
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s")

    print(f"\n[2/4] Generating {int(total_dur * 12)} animation frames...")
    frame_arrays = animate_scene(
        prompt=user_prompt, w=W, h=H,
        num_frames=int(total_dur * 12), fps=12,
    )

    print(f"\n[3/4] Composing video...")
    frame_dur = total_dur / max(len(frame_arrays), 1)

    def make_frame(t):
        idx = min(int(t / frame_dur), len(frame_arrays) - 1)
        return frame_arrays[idx]

    anim_clip = VideoClip(make_frame, duration=total_dur)

    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(total_dur)

    end_clip = subscribe_end_card(np.zeros((H, W, 3), dtype=np.uint8), 1.2)

    bg = concatenate_videoclips([anim_clip, end_clip], method="compose")
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)

    audio_clip = AudioFileClip(str(tts_path))
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_dur).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print("\n[4/4] Rendering...")
    safe_title = SUBJECT.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:50]
    out = config.OUTPUT_DIR / f"animation_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1 - t0:.0f}s: {out}")
    return out, data


if __name__ == "__main__":
    main()
