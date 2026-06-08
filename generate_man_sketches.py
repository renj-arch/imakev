"""Generate all man pose sketches from draw_human()."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
from src.sketch_generator import SketchGenerator
import warnings
warnings.filterwarnings("ignore")

W, H = 400, 500
gen = SketchGenerator(W, H)

POSES = [
    "standing", "sitting_chair", "sitting_cross_legged", "meditating",
    "sitting_floor", "lying_back", "lying_side", "jogging", "running",
    "walking", "jumping", "kneeling", "bowing", "praying", "yoga_tree",
    "fighting_stance", "dancing", "bending", "squatting", "crawling",
    "climbing", "swimming", "stretching", "star_jump", "clapping",
    "carrying", "pushing", "pulling", "kicking", "punching", "sweeping",
    "phone_standing", "lying_stomach", "sleeping_fetal", "pushups", "situps",
    "hugging", "lying_reading", "pointing", "standing_arms_up",
    "arms_crossed", "standing_akimbo", "thinking", "waving", "cycling",
    "throwing", "kneeling_one", "kneeling_both", "yoga_warrior",
]

out_dir = os.path.join(os.path.dirname(__file__), "man_sketches")
os.makedirs(out_dir, exist_ok=True)

MOODS = ["peaceful", "hopeful", "sad", "angry", "dramatic"]
cols = 6
rows = (len(POSES) + cols - 1) // cols
grid_w = cols * W
grid_h = rows * H
grid = Image.new("RGBA", (grid_w, grid_h), (245, 240, 230, 255))

for i, pose in enumerate(POSES):
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    mood = "peaceful"
    gen.draw_human(draw, W // 2, H // 2 + 60, size=4.0,
                   color=(60, 80, 140), skin_color=(235, 200, 175),
                   gender="man", mood=mood, pose=pose)
    # Label
    lbl = f"{pose} ({mood})"
    draw.text((10, 10), lbl, fill=(60, 55, 50))
    grid.paste(canvas, ((i % cols) * W, (i // cols) * H))

opath = os.path.join(out_dir, "all_man_poses.png")
grid.save(opath)
print(f"Saved: {opath} ({len(POSES)} poses)")

# Also generate mood variations for key poses
key_poses = ["standing", "sitting_chair", "lying_back", "running", "kneeling", "dancing"]
for pose in key_poses:
    for mood in MOODS:
        canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        draw = ImageDraw.Draw(canvas)
        gen.draw_human(draw, W // 2, H // 2 + 60, size=4.0,
                       color=(60, 80, 140), skin_color=(235, 200, 175),
                       gender="man", mood=mood, pose=pose)
        lbl = f"{pose}_{mood}"
        draw.text((10, 10), lbl, fill=(60, 55, 50))
        canvas.save(os.path.join(out_dir, f"man_{pose}_{mood}.png"))

print(f"Mood variations saved to {out_dir}")
