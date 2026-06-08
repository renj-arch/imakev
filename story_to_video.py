"""
Story-to-scene pipeline for YouTube narration videos.
Splits a story into logical scenes, generates sketches with visual variety.
"""
import os, re, json, hashlib, argparse, random
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
from src.narration_to_sketch import _describe_scene

CACHE_FILE = "output/.story_cache.json"

# Visual style rotation for variety across scenes
STYLES = [
    {"tag": "[Epic twilight] ", "mood": "epic", "bg_hint": "sunset", "particles": "stars", "zoom": 1.0},
    {"tag": "[Dramatic night] ", "mood": "dramatic", "bg_hint": "night", "particles": "stars", "zoom": 1.1},
    {"tag": "[Somber dawn] ", "mood": "somber", "bg_hint": "dawn", "particles": "mist", "zoom": 0.9},
    {"tag": "[Grand sunset] ", "mood": "epic", "bg_hint": "sunset", "particles": "sunbeams", "zoom": 1.0},
    {"tag": "[Mysterious moonlight] ", "mood": "mysterious", "bg_hint": "night", "particles": "fog", "zoom": 1.2},
    {"tag": "[Hopeful golden] ", "mood": "hopeful", "bg_hint": "sunset", "particles": "sunbeams", "zoom": 0.8},
    {"tag": "[Intense overcast] ", "mood": "dramatic", "bg_hint": "overcast", "particles": "ash", "zoom": 1.0},
    {"tag": "[Quiet evening] ", "mood": "peaceful", "bg_hint": "indoor", "particles": "none", "zoom": 1.0},
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


def split_scenes(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return paragraphs if paragraphs else [text.strip()]


def modify_scene_for_variety(scene: dict, style: dict, scene_idx: int, total: int) -> dict:
    """Apply visual variety modifications to a scene dict."""
    s = scene.copy()
    s["mood"] = style["mood"]

    # Adjust background colors based on style
    bg = s.get("bg", {})
    if style["bg_hint"] == "night":
        bg["type"] = "gradient"
        bg["colors"] = [[2, 2, 18], [8, 5, 25], [15, 10, 35]]
    elif style["bg_hint"] == "sunset":
        bg["type"] = "sunset"
        bg["colors"] = [[80, 40, 30], [180, 100, 60], [200, 160, 120]]
    elif style["bg_hint"] == "dawn":
        bg["type"] = "gradient"
        bg["colors"] = [[60, 50, 80], [120, 100, 140], [180, 170, 190]]
    elif style["bg_hint"] == "overcast":
        bg["type"] = "gradient"
        bg["colors"] = [[60, 60, 70], [80, 80, 90], [100, 100, 110]]
    elif style["bg_hint"] == "indoor":
        bg["type"] = "indoor"
        bg["colors"] = [[30, 25, 20], [50, 40, 35], [80, 70, 60]]

    s["bg"] = bg

    # Atmosphere
    atmos = s.get("atmosphere", {})
    if style["particles"] != "none":
        atmos["particles"] = style["particles"]
    s["atmosphere"] = atmos

    # Camera zoom effect: scale elements
    zoom = style.get("zoom", 1.0)
    if zoom != 1.0:
        for elem in s.get("elements", []):
            if "scale" in elem:
                elem["scale"] = round(elem["scale"] * zoom, 2)

    # Offset camera: shift x positions for variety
    offset_x = ((scene_idx % 3) - 1) * 0.08
    for elem in s.get("elements", []):
        if "x" in elem:
            elem["x"] = max(0.05, min(0.95, elem["x"] + offset_x))

    return s


def generate_scenes(
    text: str,
    width=720,
    height=1280,
    seed=42,
    output_dir="output/story_frames",
    add_subtitles=True,
    font_path=None,
):
    """Generate varied scene frames from a full story narration."""
    os.makedirs(output_dir, exist_ok=True)
    cache = load_cache()
    scenes = split_scenes(text)

    print(f"Split into {len(scenes)} scene(s):")
    for i, s in enumerate(scenes):
        short = s[:80] + ("..." if len(s) > 80 else "")
        print(f"  Scene {i+1}: {short}")

    frames = []
    for i, scene_text in enumerate(scenes):
        style = STYLES[i % len(STYLES)]
        modified_text = style["tag"] + scene_text

        cache_key = hashlib.md5(
            (modified_text + str(seed) + str(width) + str(height)).encode()
        ).hexdigest()
        cached = cache.get(cache_key)

        if cached and os.path.exists(cached):
            print(f"  [{i+1}/{len(scenes)}] CACHED -> {cached}")
            img = Image.open(cached).convert("RGB")
        else:
            short = modified_text[:60]
            print(f"  [{i+1}/{len(scenes)}] Generating ({style['mood']}/{style['bg_hint']})...")
            scene_desc = _describe_scene(modified_text)
            scene_desc = modify_scene_for_variety(scene_desc, style, i, len(scenes))
            gen = SketchGenerator(width, height, seed + i)
            img = gen.render_scene(scene_desc)

        if add_subtitles:
            img = add_text_overlay(img, scene_text, font_path)

        out_path = os.path.join(output_dir, f"scene_{i+1:03d}.png")
        img.save(out_path)
        frames.append((out_path, scene_text))
        print(f"    -> {out_path}")

    manifest = {
        "total_scenes": len(scenes),
        "width": width,
        "height": height,
        "fps": 24,
        "duration_per_scene_sec": 5,
        "scenes": [
            {
                "frame": f"scene_{i+1:03d}.png",
                "text": scenes[i],
                "style": STYLES[i % len(STYLES)]["mood"],
                "duration_frames": 5 * 24,
            }
            for i in range(len(scenes))
        ],
    }
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    print(f"Total: {len(scenes)} scenes -> {output_dir}/")

    return frames


def add_text_overlay(img: Image.Image, text: str, font_path=None) -> Image.Image:
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    bar_h = int(h * 0.12)
    draw.rectangle([0, h - bar_h, w, h], fill=(0, 0, 0, 140))

    font = None
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, int(bar_h * 0.35))
        except Exception:
            pass

    max_chars = 50
    lines = []
    for word in text.split():
        if not lines or len(lines[-1] + " " + word) > max_chars:
            lines.append(word)
        else:
            lines[-1] += " " + word

    line_h = int(bar_h * 0.32)
    start_y = h - bar_h + (bar_h - len(lines) * line_h) // 2
    for j, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        draw.text((tx, start_y + j * line_h), line, fill=(255, 255, 255, 230), font=font)
    return img


def assemble_video(output_dir="output/story_frames", output_video="output/story_video.mp4"):
    manifest_path = os.path.join(output_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print("No manifest found. Run with --generate first.")
        return
    manifest = json.load(open(manifest_path))
    w, h = manifest["width"], manifest["height"]
    fps = manifest.get("fps", 24)
    concat_path = os.path.join(output_dir, "concat.txt")
    with open(concat_path, "w") as f:
        for scene in manifest["scenes"]:
            frame_path = os.path.join(output_dir, scene["frame"]).replace("\\", "/")
            duration = scene.get("duration_frames", 120)
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
    parser = argparse.ArgumentParser(description="Generate story scene frames for YouTube")
    parser.add_argument("--text", "-t", type=str, help="Story narration text")
    parser.add_argument("--file", "-f", type=str, help="Read narration from file")
    parser.add_argument("--width", "-w", type=int, default=720)
    parser.add_argument("--height", "-H", type=int, default=1280)
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--output", "-o", type=str, default="output/story_frames")
    parser.add_argument("--no-subtitles", action="store_true")
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--video", type=str, default="output/story_video.mp4")
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
        text = input("Paste your story narration (Ctrl+Z then Enter to finish):\n")

    generate_scenes(
        text=text,
        width=args.width,
        height=args.height,
        seed=args.seed,
        output_dir=args.output,
        add_subtitles=not args.no_subtitles,
    )
