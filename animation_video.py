"""AI Animation video — realistic AI video via HuggingFace T2V, AI image Ken Burns fallback."""

import sys, subprocess, time, random, os, threading
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
from src.photo_video import generate_hf_text_to_video, generate_ai_image_video, generate_stock_photo_video, generate_photorealistic_frames, generate_coverr_video, generate_hf_space_video
from src.motion_video import generate_motion_video

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS


def _run_with_timeout(fn, args=(), kwargs=None, timeout=60):
    """Run a function with a timeout. Returns (result, error) or raises TimeoutError."""
    if kwargs is None:
        kwargs = {}
    result = [None]
    error = [None]
    done = threading.Event()

    def worker():
        try:
            result[0] = fn(*args, **kwargs)
        except Exception as e:
            error[0] = e
        finally:
            done.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    if not done.wait(timeout=timeout):
        return None, TimeoutError(f"Timed out after {timeout}s")
    if error[0]:
        return None, error[0]
    return result[0], None


def main():
    print("=" * 50)
    print("  AI ANIMATION — Text-to-Video")
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
    bg = None
    video_path = temp_dir / "ai_video.mp4"

    # Try 0: HF Space T2V (free, real AI video via Gradio Spaces)
    print("  Trying HF Space T2V (Gradio Space API)...")
    result, err = _run_with_timeout(
        generate_hf_space_video,
        args=(user_prompt, video_path),
        kwargs={"num_frames": min(32, max(4, int(total_dur * 8))), "num_inference_steps": 25, "timeout": 600},
        timeout=660,
    )
    if result:
        try:
            vid = VideoFileClip(str(video_path))
            total_frames = int(vid.fps * vid.duration)
            if vid.duration < total_dur:
                clips = [vid] * (int(total_dur // vid.duration) + 1)
                vid = concatenate_videoclips(clips, method="compose").with_duration(total_dur)
            else:
                vid = vid.with_duration(total_dur)
            bg = vid
            print("  Using HF Space AI video")
        except Exception as e:
            print(f"  HF Space video load failed: {e}")
            bg = None
    else:
        print(f"  HF Space T2V unavailable ({err or 'no result'})")

    # Try 1: Procedural motion video (works for ANY prompt, no APIs)
    print("  Trying procedural motion video...")
    num_frames_needed = int(total_dur * FPS)
    result, err = _run_with_timeout(
        generate_motion_video,
        args=(user_prompt, W, H, num_frames_needed, FPS),
        timeout=90,
    )
    frames = result if err is None else None
    if frames:
        total_frames = len(frames)
        print(f"  {total_frames} motion frames")
        frame_dur = total_dur / max(total_frames, 1)
        def make_motion_frame(t):
            return frames[min(int(t / frame_dur), total_frames - 1)]
        bg = VideoClip(make_motion_frame, duration=total_dur)
        print("  Using procedural motion video")
    else:
        print(f"  Motion video unavailable ({err or 'no result'})")

    # Try 2: Coverr stock video (free, no API key, real video clips)
    if bg is None:
        print("  Trying Coverr stock video...")
        result, err = _run_with_timeout(
            generate_coverr_video,
            args=(user_prompt, video_path),
            timeout=30,
        )
        if result:
            try:
                vid = VideoFileClip(str(video_path))
                if vid.duration < total_dur:
                    clips = [vid] * (int(total_dur // vid.duration) + 1)
                    vid = concatenate_videoclips(clips, method="compose").with_duration(total_dur)
                else:
                    vid = vid.with_duration(total_dur)
                bg = vid
                print("  Using Coverr stock video")
            except Exception as e:
                print(f"  Coverr video load failed: {e}")
                bg = None
        else:
            print(f"  Coverr unavailable ({err or 'no result'})")

    # Try 3: HF text-to-video (requires HF_TOKEN or free tier)
    if bg is None:
        print("  Trying HF text-to-video...")
        result, err = _run_with_timeout(
            generate_hf_text_to_video,
            args=(user_prompt, video_path),
            kwargs={"duration": min(5, int(total_dur))},
            timeout=120,
        )
        if result:
            try:
                vid = VideoFileClip(str(video_path))
                total_frames = int(vid.fps * vid.duration)
                if vid.duration < total_dur:
                    clips = [vid] * (int(total_dur // vid.duration) + 1)
                    vid = concatenate_videoclips(clips, method="compose").with_duration(total_dur)
                else:
                    vid = vid.with_duration(total_dur)
                bg = vid
                print("  Using HF T2V AI video")
            except Exception as e:
                print(f"  HF video load failed: {e}")
                bg = None
        else:
            print(f"  HF T2V unavailable ({err or 'no result'})")

    # Try 3: Pollinations.ai image Ken Burns (free, no API key)
    if bg is None:
        print("  Trying AI image Ken Burns...")
        num_frames_needed = int(total_dur * FPS)
        result, err = _run_with_timeout(
            generate_ai_image_video,
            args=(user_prompt, W, H, num_frames_needed, FPS),
            timeout=90,
        )
        frames = result if err is None else None
        if frames:
            total_frames = len(frames)
            print(f"  {total_frames} AI image frames")
            frame_dur = total_dur / max(total_frames, 1)
            def make_ai_frame(t):
                return frames[min(int(t / frame_dur), total_frames - 1)]
            bg = VideoClip(make_ai_frame, duration=total_dur)
            print("  Using AI image slideshow")

    # Try 4: Stock photo Ken Burns (free, no keys, reliable)
    if bg is None:
        print("  Trying stock photo Ken Burns...")
        num_frames_needed = int(total_dur * FPS)
        result, err = _run_with_timeout(
            generate_stock_photo_video,
            args=(user_prompt, W, H, num_frames_needed, FPS),
            timeout=30,
        )
        frames = result if err is None else None
        if frames:
            total_frames = len(frames)
            print(f"  {total_frames} stock photo frames")
            frame_dur = total_dur / max(total_frames, 1)
            def make_stock_frame(t):
                return frames[min(int(t / frame_dur), total_frames - 1)]
            bg = VideoClip(make_stock_frame, duration=total_dur)
            print("  Using stock photo slideshow")

    # Fallback: Storyboard animator (always works)
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
