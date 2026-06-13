"""Generate wildcat domestication story video -- YouTube-engaging content."""
import sys, os, subprocess, random
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
from src.narrative_to_scenes import narration_to_scenes
from src.painterly import painterly_postprocess

NARRATION = """Then another animal noticed the feast.
Wildcats.
They weren't interested in human friendship.
They came for the mice.
Humans didn't invite them.
The cats invited themselves."""

W, H = 1280, 720
FPS = 12
SECONDS_PER_SCENE = 2.0
FRAMES_PER_SCENE = int(FPS * SECONDS_PER_SCENE)

def add_night_glow(img, is_night):
    if not is_night:
        return img
    darken = Image.new("RGBA", img.size, (0, 0, 30, 100))
    img = Image.alpha_composite(img.convert("RGBA"), darken)
    return img

def add_fire_glow(img):
    w, h = img.size
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    cx, cy = w // 2, h - 20
    for r in range(300, 0, -15):
        alpha = max(0, int(40 * (1 - r / 300)))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 200, 100, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    return img

def add_text_overlay(frame, text, w=W, h=H):
    draw = ImageDraw.Draw(frame)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()
    text_x = w // 2
    text_y = h - 80
    for dx, dy in [(-2,-2), (-2,2), (2,-2), (2,2), (0,0)]:
        draw.text((text_x + dx, text_y + dy), text, font=font, fill=(0, 0, 0, 200), anchor="mb")
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 230), anchor="mb")
    return frame

def camera_crop(frame, zoom, target_x=0.5, target_y=0.4):
    w, h = frame.size
    new_w = int(w / zoom)
    new_h = int(h / zoom)
    cx = int(w * target_x)
    cy = int(h * target_y)
    left = max(0, cx - new_w // 2)
    top = max(0, cy - new_h // 2)
    right = min(w, left + new_w)
    bottom = min(h, top + new_h)
    if right - left < 10 or bottom - top < 10:
        return frame
    cropped = frame.crop((left, top, right, bottom))
    return cropped.resize((w, h), Image.LANCZOS)

def generate_ken_burns(scene, gen, num_frames):
    camera = scene.get("camera", {})
    zoom_target = camera.get("zoom_target", [0.5, 0.4])
    zoom_start = max(camera.get("zoom", 1.0) * 0.85, 0.6)
    zoom_end = camera.get("zoom", 1.0)
    is_night = scene.get("is_night", False)
    narration = scene.get("narration", "")

    frames = []
    for f_idx in range(num_frames):
        t = f_idx / num_frames
        zoom = zoom_start + (zoom_end - zoom_start) * t
        img = gen.render_scene(scene)
        img = camera_crop(img, zoom, zoom_target[0], zoom_target[1])
        if is_night:
            img = add_night_glow(img, True)
            if "feast" in narration.lower():
                img = add_fire_glow(img)
        img = painterly_postprocess(img, style="oil")
        add_text_overlay(img, narration, W, H)
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (0, 0, 0))
            bg.paste(img, mask=img.split()[3])
            img = bg
        frames.append(img)
    return frames

def main():
    scenes = narration_to_scenes(NARRATION)
    print("Composed %d scenes from narration" % len(scenes))
    for i, s in enumerate(scenes):
        types = [e['type'] for e in s.get('elements', [])]
        cam = s.get('camera', {})
        print("  %d. [%6s] %-40s -> %s" % (i+1, cam.get('shot','?'), s.get('narration','')[:40], ', '.join(types)))

    gen = SketchGenerator(W, H, seed=42)
    all_frames = []
    for scene in scenes:
        frames = generate_ken_burns(scene, gen, FRAMES_PER_SCENE)
        all_frames.extend(frames)
        print("  Rendered %d frames for: %s..." % (len(frames), scene.get('narration','')[:30]))

    out_dir = os.path.join(os.path.dirname(__file__), "wildcat_frames_seq")
    os.makedirs(out_dir, exist_ok=True)
    for idx, frame in enumerate(all_frames):
        frame.save(os.path.join(out_dir, "frame_%04d.png" % idx))
    print("Total frames: %d saved to %s" % (len(all_frames), out_dir))

    output_path = os.path.join(os.path.dirname(__file__), "wildcat_story.mp4")
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", os.path.join(out_dir, "frame_%04d.png").replace("\\", "/"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "22",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print("Video saved: %s (%.1f MB)" % (output_path, size_mb))

if __name__ == "__main__":
    main()
