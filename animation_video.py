"""AI Animation video — Seedance API for realistic AI video, storyboard fallback."""

import sys, subprocess, time, random, os
from pathlib import Path
import numpy as np
from moviepy import (
    VideoClip,
    AudioFileClip,
    VideoFileClip,
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
from src.video_api import generate_video as gen_video_api
from src.photo_video import generate_photorealistic_frames, generate_via_space_video, generate_via_svd_img2vid, _gradio_image

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS


def main():
    print("=" * 50)
    print("  AI STORYBOARD ANIMATOR")
    print("=" * 50)

    user_prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not user_prompt:
        print("  No prompt provided — auto-generating one...")
        try:
            from src.script_generator import _generate
            raw = _generate(
                "Suggest a short visual story for an animated video. "
                "Examples: 'A clever monkey opens a banana delivery service in the jungle', "
                "'A curious fox discovers a glowing mushroom in an enchanted forest', "
                "'A dragon teaches baby dragons how to fly over mountain peaks'. "
                "Return ONLY the story, 10-20 words.",
                temperature=0.9, max_tokens=40,
                system="You suggest short visual stories for AI animation.",
            )
            user_prompt = raw.strip().strip('"').strip("'") if raw else ""
        except Exception:
            user_prompt = ""
        if not user_prompt:
            user_prompt = random.choice([
                "a duck swimming in a pond under cherry blossoms",
                "a cat exploring a neon city at midnight",
                "a dragon flying over misty mountains",
                "a clever monkey riding a bicycle through the jungle",
                "an elephant splashing water in a river at sunset",
                "a parrot soaring through rainbow clouds",
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

    print(f"\n[2/4] Generating video...")
    total_frames = 0
    bg = None

    # Try 1: Video API (Seedance with key)
    video_path = temp_dir / "ai_video.mp4"
    if gen_video_api(user_prompt, video_path, duration=min(5, int(total_dur))):
        vid = VideoFileClip(str(video_path))
        total_frames = int(vid.fps * vid.duration)
        if vid.duration < total_dur:
            clips = [vid] * (int(total_dur // vid.duration) + 1)
            vid = concatenate_videoclips(clips, method="compose").with_duration(total_dur)
        else:
            vid = vid.with_duration(total_dur)
        bg = vid
        print("  Using Seedance AI video")

    # Try 2: Gradio Space text-to-video (free, no key)
    if bg is None:
        print("  Trying Gradio Space T2V...")
        if generate_via_space_video(user_prompt, video_path, duration=min(5, int(total_dur))):
            try:
                vid = VideoFileClip(str(video_path))
                total_frames = int(vid.fps * vid.duration)
                if vid.duration < total_dur:
                    clips = [vid] * (int(total_dur // vid.duration) + 1)
                    vid = concatenate_videoclips(clips, method="compose").with_duration(total_dur)
                else:
                    vid = vid.with_duration(total_dur)
                bg = vid
                print("  Using Gradio Space AI video")
            except Exception:
                bg = None

    # Try 3: SVD Image-to-Video (generate SD image + animate via Stable Video Diffusion)
    if bg is None:
        print("  Trying SVD image-to-video...")
        if generate_via_svd_img2vid(user_prompt, video_path, duration=min(4, int(total_dur))):
            try:
                vid = VideoFileClip(str(video_path))
                total_frames = int(vid.fps * vid.duration)
                if vid.duration < total_dur:
                    clips = [vid] * (int(total_dur // vid.duration) + 1)
                    vid = concatenate_videoclips(clips, method="compose").with_duration(total_dur)
                else:
                    vid = vid.with_duration(total_dur)
                bg = vid
                print("  Using SVD image-to-video")
            except Exception:
                bg = None

    # Try 4: Photorealistic frames via HF Inference (realistic images + motion)
    if bg is None:
        print("  Trying photorealistic frames...")
        num_frames_needed = int(total_dur * FPS)
        frames = generate_photorealistic_frames(
            user_prompt, w=W, h=H, num_frames=num_frames_needed, fps=FPS,
        )
        if frames:
            total_frames = len(frames)
            print(f"  {total_frames} photorealistic frames")
            frame_dur = total_dur / max(total_frames, 1)
            def make_photo_frame(t):
                return frames[min(int(t / frame_dur), total_frames - 1)]
            bg = VideoClip(make_photo_frame, duration=total_dur)
            print("  Using photorealistic frames")

    # Fallback: Storyboard animator
    if bg is None:
        print("  Using storyboard fallback")
        from src.storyboard_anim import generate_storyboard_frames
        frame_arrays = generate_storyboard_frames(prompt=user_prompt, w=W, h=H, fps=FPS)
        total_frames = len(frame_arrays)
        print(f"  {total_frames} storyboard frames = {total_frames / FPS:.1f}s @ {FPS}fps")

        if total_dur > total_frames / FPS:
            pad_needed = int((total_dur - total_frames / FPS) * FPS)
            if pad_needed > 0 and total_frames > 0:
                frame_arrays.extend([frame_arrays[-1]] * min(pad_needed, FPS * 3))
                total_frames = len(frame_arrays)

        frame_dur = total_dur / max(total_frames, 1)
        def make_frame(t):
            return frame_arrays[min(int(t / frame_dur), total_frames - 1)]
        bg = VideoClip(make_frame, duration=total_dur)

    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(total_dur)

    end_clip = subscribe_end_card(np.zeros((H, W, 3), dtype=np.uint8), 1.2)

    bg = concatenate_videoclips([bg, end_clip], method="compose")
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
    out = config.OUTPUT_DIR / f"storyboard_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur:.1f}s | {W}x{H} | {total_frames} frames")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1 - t0:.0f}s: {out}")
    return out, data


if __name__ == "__main__":
    main()
