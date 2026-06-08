"""
Story-to-scene pipeline for YouTube narration videos.
Splits a story into logical scenes, generates sketches, outputs frames.
"""
import os, re, json, hashlib, argparse
from PIL import Image, ImageDraw, ImageFont
from src.narration_to_sketch import sketch_from_narration

CACHE_FILE = "output/.story_cache.json"


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
    """Split a full narration into logical scene descriptions.
    
    Strategy:
    1. Split by paragraph breaks (double newline) -- each paragraph is a scene.
    2. If a paragraph has more than 3 sentences, keep as one scene.
    """
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return paragraphs if paragraphs else [text.strip()]


def generate_scenes(
    text: str,
    width=720,
    height=1280,
    seed=42,
    output_dir="output/story_frames",
    add_subtitles=True,
    font_path=None,
):
    """Generate scene frames from a full story narration."""
    os.makedirs(output_dir, exist_ok=True)
    cache = load_cache()
    scenes = split_scenes(text)

    print(f"Split into {len(scenes)} scene(s):")
    for i, s in enumerate(scenes):
        short = s[:80] + ("..." if len(s) > 80 else "")
        print(f"  Scene {i+1}: {short}")

    frames = []
    for i, scene_text in enumerate(scenes):
        cache_key = hashlib.md5(
            (scene_text + str(seed) + str(width) + str(height)).encode()
        ).hexdigest()
        cached = cache.get(cache_key)

        if cached and os.path.exists(cached):
            print(f"  [{i+1}/{len(scenes)}] CACHED -> {cached}")
            img = Image.open(cached).convert("RGB")
        else:
            short = scene_text[:60]
            print(f"  [{i+1}/{len(scenes)}] Generating: {short}...")
            img = sketch_from_narration(
                scene_text, width=width, height=height, seed=seed + i
            )
            out_path = os.path.join(output_dir, f"scene_{i+1:03d}.png")
            img.save(out_path)
            cache[cache_key] = out_path
            save_cache(cache)

        if add_subtitles:
            img = add_text_overlay(img, scene_text, font_path)

        out_path = os.path.join(output_dir, f"scene_{i+1:03d}.png")
        img.save(out_path)
        frames.append((out_path, scene_text))
        print(f"    -> {out_path}")

    # Save manifest for video assembly
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
    """Add subtitle text at the bottom of the frame."""
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
        draw.text(
            (tx, start_y + j * line_h), line, fill=(255, 255, 255, 230), font=font
        )

    return img


def assemble_video(output_dir="output/story_frames", output_video="output/story_video.mp4"):
    """Assemble scene frames into a video using ffmpeg."""
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
