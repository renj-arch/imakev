"""Explainer video - Script > Piper TTS > Animation > FFmpeg > MP4.
Completely free, local, no APIs needed."""

import sys, subprocess, time, os, json, random
from pathlib import Path
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, VideoFileClip,
    concatenate_videoclips, CompositeAudioClip, CompositeVideoClip,
)
import config
from src.explainer_anim import generate_explainer_frames
from src.piper_tts import generate_speech
from src.engagement import get_audio_duration, subscribe_end_card, hook_overlays, branding_overlays, comment_prompt_overlay

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS

FALLBACK_TOPICS = {
    "how": ["Here is how it works", "This is the basic idea", "Let me explain the details", "Here is something interesting", "Now you understand better"],
    "what": ["Here is what you need to know", "This is the key point", "Here is another important fact", "This might surprise you", "Now you know the truth"],
    "why": ["Here is why this happens", "The reason is simple", "Here is another reason", "This explains a lot", "Now it all makes sense"],
    "default": ["Here is an interesting fact", "This is how it works", "Here is another detail", "This is worth knowing", "Now you understand"],
}

GENERIC_DESCRIPTORS = ["interesting", "fascinating", "amazing", "incredible", "cool", "surprising", "fun", "clever"]

def main():
    print("=" * 50)
    print("  EXPLAINER - Script > Piper TTS > Animation > MP4")
    print("  Completely free, local, no APIs")
    print("=" * 50)

    user_topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    topic = user_topic or random.choice(list(FALLBACK_TOPICS.keys())).capitalize() + " things work"
    points = None
    if user_topic:
        try:
            from src.script_generator import _generate
            raw = _generate(
                f"Write 5 short, interesting bullet points explaining '{user_topic}'. "
                f"Each point: 5-10 words, simple, clear. Number them 1-5.",
                temperature=0.5, max_tokens=400,
                system="You write clear educational bullet points.",
            )
            if raw:
                lines = [l.strip().lstrip("12345.) ") for l in raw.split("\n") if l.strip() and l.strip()[0].isdigit()]
                points = [l for l in lines if len(l) > 10][:5]
        except Exception:
            pass
    if not points:
        words = topic.lower().split()
        key = "default"
        for w in words:
            if w in FALLBACK_TOPICS:
                key = w
                break
        templates = FALLBACK_TOPICS[key]
        adj = random.choice(GENERIC_DESCRIPTORS)
        points = [f"{topic} is {adj}"]
        points += [f"{t} about {topic}" for t in templates[1:]]

    print(f"\n[Script] {topic}")
    narration = f"{topic}. " + " ".join(points)
    print(f"  {len(points)} points, {len(narration.split())} words")

    temp_dir = config.TEMP_DIR / "explainer"
    temp_dir.mkdir(exist_ok=True)

    print(f"\n[Piper TTS] Generating speech...")
    tts_path = temp_dir / "narration.wav"
    if not generate_speech(narration, tts_path):
        print("  Piper failed, falling back to edge-tts...")
        subprocess.run(
            [sys.executable, "-m", "edge_tts", "--text", narration, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path.with_suffix(".mp3"))],
            capture_output=True, timeout=120,
        )
        tts_path = tts_path.with_suffix(".mp3")
    total_dur = get_audio_duration(str(tts_path))
    dur_per_point = max(3.0, total_dur / max(len(points), 1))
    print(f"  {total_dur:.1f}s audio")

    print(f"\n[Animation] Generating explainer frames...")
    t0 = time.time()
    frame_arrays = generate_explainer_frames(
        title=topic,
        points=points,
        duration_per_point=dur_per_point,
        intro_duration=2.0,
        outro_duration=2.0,
    )
    total_frames = len(frame_arrays)
    elapsed = time.time() - t0
    print(f"  {total_frames} frames in {elapsed:.1f}s")

    if total_frames / FPS < total_dur:
        pad = int((total_dur - total_frames / FPS) * FPS)
        if pad > 0:
            frame_arrays.extend([frame_arrays[-1]] * min(pad, FPS * 3))
            total_frames = len(frame_arrays)

    frame_dur = total_dur / max(total_frames, 1)

    def make_frame(t):
        return frame_arrays[min(int(t / frame_dur), total_frames - 1)]

    bg = VideoClip(make_frame, duration=total_dur)

    print(f"\n[Composition] Adding overlays + audio...")
    end_clip = subscribe_end_card(np.zeros((H, W, 3), dtype=np.uint8), 1.5)
    bg = concatenate_videoclips([bg, end_clip], method="compose")

    audio_clip = AudioFileClip(str(tts_path))
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_dur).with_volume_scaled(0.06)
        final = CompositeVideoClip([bg], size=config.SHORTS_SIZE).with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = CompositeVideoClip([bg], size=config.SHORTS_SIZE).with_audio(audio_clip)

    print(f"\n[Rendering] FFmpeg...")
    safe = topic.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:40]
    out = config.OUTPUT_DIR / f"explainer_{safe}.mp4"
    out.unlink(missing_ok=True)
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", logger=None)
    final.close()
    print(f"\n  DONE in {time.time()-t0:.0f}s: {out}")
    return out

if __name__ == "__main__":
    main()
