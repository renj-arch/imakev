"""
Multi-voice narration-to-scene pipeline.
Parses scripts with 🎙️ speaker markers, generates varied frames per voice segment,
inserts child (Think) interjections and final acknowledgment.
"""
import os, re, json, hashlib, argparse
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
from src.narration_to_sketch import _describe_scene

CACHE_FILE = "output/.mv_cache.json"

# Voice configurations with personality roles
VOICES = {
    "Ding":  {"name": "Ding", "role": "Storykeeper", "color": (60, 140, 220), "icon": "~"},
    "Dong":  {"name": "Dong", "role": "Reflector", "color": (200, 100, 180), "icon": "~"},
    "Think": {"name": "Think", "role": "Curious", "color": (255, 200, 60), "icon": "?"},
}

# Mapping from script labels to voice keys
SPEAKER_MAP = {
    "Narrator": "Ding",
    "Voice 1":  "Ding",
    "Voice 2":  "Dong",
    "Voice 3":  "Dong",
    "Think":    "Think",
    "Child":    "Think",
    "Kid":      "Think",
}

# Child interjection templates (no family references — just a curious voice)
THINK_QUESTIONS = [
    "Why did the walls take so long to build?",
    "How did the cannons get so big?",
    "What happened to the people inside the city?",
    "Why didn't the army just go around the walls?",
    "How did they drag ships over land?",
    "What does it feel like when a city falls?",
    "Was the sultan scared too?",
    "How long is a thousand years?",
    "Why do people build walls if they can be broken?",
    "Did anyone escape?",
    "What's an empire?",
    "How do you know what happened so long ago?",
    "Who rebuilt the city after it fell?",
    "Could it happen to our city?",
    "Why do people fight over places?",
    "Was there a dragon?",
    "Did the king fight too?",
    "Where did all the treasure go?",
    "What is gunpowder?",
    "Why did the story end like that?",
    "Can I ask something?",
    "I have a question.",
    "Wait — I don't understand.",
    "But how?",
    "Tell me more about that part.",
    "Why is that important?",
    "What happened next?",
    "Do you think they were scared?",
    "Could someone have stopped it?",
    "I want to know more.",
]

# Visual style per voice
VOICE_STYLES = {
    "Ding":  {"border": (60, 140, 220), "bar_color": (10, 30, 60), "icon": "~"},
    "Dong":  {"border": (200, 100, 180), "bar_color": (50, 20, 40), "icon": "~"},
    "Think": {"border": (255, 200, 60), "bar_color": (50, 40, 10), "icon": "?"},
}

STYLES = [
    {"tag": "[Epic twilight] ", "mood": "epic", "bg_hint": "sunset", "zoom": 1.0},
    {"tag": "[Dramatic night] ", "mood": "dramatic", "bg_hint": "night", "zoom": 1.1},
    {"tag": "[Somber dawn] ", "mood": "somber", "bg_hint": "dawn", "zoom": 0.9},
    {"tag": "[Grand sunset] ", "mood": "epic", "bg_hint": "sunset", "zoom": 1.0},
    {"tag": "[Mysterious moonlight] ", "mood": "mysterious", "bg_hint": "night", "zoom": 1.2},
    {"tag": "[Hopeful golden] ", "mood": "hopeful", "bg_hint": "sunset", "zoom": 0.8},
    {"tag": "[Intense overcast] ", "mood": "dramatic", "bg_hint": "overcast", "zoom": 1.0},
    {"tag": "[Quiet evening] ", "mood": "peaceful", "bg_hint": "indoor", "zoom": 1.0},
]


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs("output", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def parse_script(text: str) -> list[dict]:
    """Parse 🎙️ VoiceName: format into segments."""
    segments = []
    # Normalize line endings
    text = text.replace("\r\n", "\n")
    # Split by 🎙️ markers
    pattern = r'🎙️\s*([^:\n]+):\s*\n'
    parts = re.split(pattern, text)
    # parts[0] is anything before first marker (usually empty)
    # then alternating: speaker, text, speaker, text, ...
    for i in range(1, len(parts), 2):
        if i + 1 >= len(parts):
            break
        raw_speaker = parts[i].strip()
        raw_text = parts[i + 1].strip()
        if not raw_text:
            continue
        # Map speaker label to voice key
        voice_key = SPEAKER_MAP.get(raw_speaker, raw_speaker)
        if voice_key not in VOICES:
            voice_key = "Ding"  # fallback
        segments.append({"voice": voice_key, "speaker": raw_speaker, "text": raw_text})
    return segments


def insert_child_interjections(segments: list[dict], density=0.4) -> list[dict]:
    """Insert Think child question segments scattered through narration."""
    result = []
    q_idx = 0
    narration_count = sum(1 for s in segments if s["voice"] in ("Ding", "Dong"))
    insert_every = max(1, int(1 / density)) if narration_count > 0 else 999

    seg_count = 0
    for seg in segments:
        result.append(seg)
        if seg["voice"] in ("Ding", "Dong"):
            seg_count += 1
            if seg_count % insert_every == 0:
                q = THINK_QUESTIONS[q_idx % len(THINK_QUESTIONS)]
                q_idx += 1
                result.append({"voice": "Think", "speaker": "Think",
                              "text": q, "auto_inserted": True})
    return result


def child_acknowledgment(segments: list[dict]) -> list[dict]:
    """Append child acknowledgment at the end."""
    ack_text = (
        "I liked the story.\n"
        "I didn't understand all of it.\n"
        "But I think I understood the end."
    )
    segments.append({"voice": "Think", "speaker": "Think", "text": ack_text,
                    "auto_inserted": True})
    # Short child outro
    outro = (
        "Will our walls hold?\n"
        "...I hope so."
    )
    segments.append({"voice": "Think", "speaker": "Think", "text": outro,
                    "auto_inserted": True})
    return segments


def generate_multi_voice(
    script_text: str,
    width=720,
    height=1280,
    seed=42,
    output_dir="output/mv_frames",
    font_path=None,
    child_density=0.4,
    add_child=True,
):
    """Generate scene frames from a multi-voice script."""
    os.makedirs(output_dir, exist_ok=True)
    cache = load_cache()

    # Parse and expand script
    segments = parse_script(script_text)
    if not segments:
        print("No segments parsed from script.")
        return []

    if add_child:
        segments = insert_child_interjections(segments, child_density)
        segments = child_acknowledgment(segments)

    print(f"Generated {len(segments)} segments:")
    for i, seg in enumerate(segments):
        short = seg["text"][:60].replace("\n", " ")
        icon = VOICES.get(seg["voice"], {}).get("icon", "")
        tag = seg.get("auto_inserted", False) and " [auto]" or ""
        print(f"  [{i+1}] {seg['voice']}: {short}...{tag}")

    frames = []
    for i, seg in enumerate(segments):
        voice = seg["voice"]
        voice_info = VOICES.get(voice, VOICES["Ding"])
        style = STYLES[i % len(STYLES)]

        # Use segment text as the scene narration
        scene_text = seg["text"]
        modified_text = style["tag"] + scene_text

        cache_key = hashlib.md5(
            (modified_text + str(seed) + str(width) + str(height)).encode()
        ).hexdigest()
        cached = cache.get(cache_key)

        if cached and os.path.exists(cached):
            print(f"  [{i+1}/{len(segments)}] CACHED -> {cached}")
            img = Image.open(cached).convert("RGB")
        else:
            print(f"  [{i+1}/{len(segments)}] {voice} ({style['mood']})...")
            scene_desc = _describe_scene(modified_text)
            # Apply style
            bg = scene_desc.get("bg", {})
            if style["bg_hint"] == "night":
                bg["colors"] = [[2, 2, 18], [8, 5, 25], [15, 10, 35]]
            elif style["bg_hint"] == "sunset":
                bg["colors"] = [[80, 40, 30], [180, 100, 60], [200, 160, 120]]
            elif style["bg_hint"] == "dawn":
                bg["colors"] = [[60, 50, 80], [120, 100, 140], [180, 170, 190]]
            elif style["bg_hint"] == "overcast":
                bg["colors"] = [[60, 60, 70], [80, 80, 90], [100, 100, 110]]
            elif style["bg_hint"] == "indoor":
                bg["colors"] = [[30, 25, 20], [50, 40, 35], [80, 70, 60]]
            scene_desc["mood"] = style["mood"]
            scene_desc["bg"] = bg

            gen = SketchGenerator(width, height, seed + i)
            img = gen.render_scene(scene_desc)

        # Add voice-specific overlay
        img = add_voice_overlay(img, seg["voice"], seg["text"], font_path)

        out_path = os.path.join(output_dir, f"seg_{i+1:03d}.png")
        img.save(out_path)
        frames.append((out_path, seg))
        print(f"    -> {out_path}")

    # Save manifest
    manifest = {
        "total_segments": len(segments),
        "width": width,
        "height": height,
        "fps": 24,
        "segments": [
            {
                "frame": f"seg_{i+1:03d}.png",
                "voice": seg["voice"],
                "speaker": seg["speaker"],
                "text": seg["text"],
                "auto_inserted": seg.get("auto_inserted", False),
                "duration_frames": 5 * 24,
            }
            for i, seg in enumerate(segments)
        ],
    }
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    print(f"Total: {len(segments)} segments -> {output_dir}/")

    return frames


def add_voice_overlay(img: Image.Image, voice_key: str, text: str,
                      font_path=None) -> Image.Image:
    """Add subtitle bar with voice indicator and colored border."""
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    vstyle = VOICE_STYLES.get(voice_key, VOICE_STYLES["Ding"])
    voice_info = VOICES.get(voice_key, VOICES["Ding"])
    icon = voice_info["icon"]
    # Top voice indicator bar
    bar_h = int(h * 0.05)
    draw.rectangle([0, 0, w, bar_h], fill=vstyle["bar_color"] + (200,))
    # Voice name + role
    label = f"{icon} {voice_key} ({voice_info['role']})"
    font = None
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, int(bar_h * 0.55))
        except Exception:
            pass
    draw.text((12, 2), label, fill=(255, 255, 255, 230), font=font)

    # Colored left border strip
    strip_w = int(w * 0.015)
    draw.rectangle([0, 0, strip_w, h], fill=vstyle["border"] + (180,))

    # Bottom subtitle bar
    sub_h = int(h * 0.13)
    draw.rectangle([0, h - sub_h, w, h], fill=(0, 0, 0, 160))

    # Split text into lines
    max_chars = 55
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        for word in words:
            if not lines or len(lines[-1] + " " + word) > max_chars:
                lines.append(word)
            else:
                lines[-1] += " " + word
        lines.append("")  # paragraph break
    lines = [l for l in lines if l]  # remove trailing empty

    line_h = int(sub_h * 0.28)
    start_y = h - sub_h + (sub_h - len(lines) * line_h) // 2
    for j, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        draw.text((tx, start_y + j * line_h), line, fill=(255, 255, 255, 230), font=font)

    return img


def assemble_video(output_dir="output/mv_frames", output_video="output/mv_video.mp4"):
    manifest_path = os.path.join(output_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print("No manifest found. Run with --generate first.")
        return
    manifest = json.load(open(manifest_path))
    w, h = manifest["width"], manifest["height"]
    fps = manifest.get("fps", 24)
    concat_path = os.path.join(output_dir, "concat.txt")
    with open(concat_path, "w") as f:
        for seg in manifest["segments"]:
            frame_path = os.path.join(output_dir, seg["frame"]).replace("\\", "/")
            duration = seg.get("duration_frames", 120)
            f.write(f"file '{frame_path}'\n")
            f.write(f"duration {duration/fps:.2f}\n")
    cmd = (
        f'ffmpeg -y -f concat -safe 0 -i "{concat_path}" '
        f'-c:v libx264 -pix_fmt yuv420p -r {fps} '
        f'-vf "scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2" '
        f'"{output_video}"'
    )
    print(f"Running: {cmd}")
    ret = os.system(cmd)
    if ret == 0:
        print(f"Video saved: {output_video}")
    else:
        print("Video assembly failed. Install ffmpeg or run manually.")
        print(f"Command: {cmd}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-voice narration scene generator")
    parser.add_argument("--text", "-t", type=str, help="Narration script text")
    parser.add_argument("--file", "-f", type=str, help="Read script from file")
    parser.add_argument("--width", "-w", type=int, default=720)
    parser.add_argument("--height", "-H", type=int, default=1280)
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--output", "-o", type=str, default="output/mv_frames")
    parser.add_argument("--no-child", action="store_true",
                       help="Skip child interjections and acknowledgment")
    parser.add_argument("--child-density", type=float, default=0.4,
                       help="How often child questions appear (0-1)")
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--video", type=str, default="output/mv_video.mp4")
    args = parser.parse_args()

    if args.assemble:
        assemble_video(args.output, args.video)
        exit(0)

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = input("Paste your multi-voice script (Ctrl+Z then Enter to finish):\n")

    generate_multi_voice(
        script_text=text,
        width=args.width,
        height=args.height,
        seed=args.seed,
        output_dir=args.output,
        add_child=not args.no_child,
        child_density=args.child_density,
    )
