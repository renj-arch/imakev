"""Generate cow sketches from draw_cow()."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
from src.sketch_generator import SketchGenerator
import warnings
warnings.filterwarnings("ignore")

W, H = 500, 400
gen = SketchGenerator(W, H)

out_dir = os.path.join(os.path.dirname(__file__), "cow_sketches")
os.makedirs(out_dir, exist_ok=True)

# 1. Default cow
canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
draw = ImageDraw.Draw(canvas)
gen.draw_cow(draw, W // 2, H // 2 + 40, size=5.0)
canvas.save(os.path.join(out_dir, "cow_default.png"))

# 2. Color variations
colors = [
    ((240, 230, 220), "cream"),
    ((200, 180, 160), "brown"),
    ((220, 200, 200), "pinkish"),
    ((50, 50, 50), "dark"),
    ((80, 120, 80), "greenish"),
]
for c_tuple, name in colors:
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    gen.draw_cow(draw, W // 2, H // 2 + 40, size=5.0, color=c_tuple)
    canvas.save(os.path.join(out_dir, f"cow_{name}.png"))

# 3. Size variations
for sz, label in [(2.0, "small"), (4.0, "medium"), (7.0, "large")]:
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    gen.draw_cow(draw, W // 2, H // 2 + 40, size=sz)
    canvas.save(os.path.join(out_dir, f"cow_{label}.png"))

# 4. Scene: cow in field
canvas = Image.new("RGBA", (W, H), (180, 210, 240, 255))
draw = ImageDraw.Draw(canvas)
gen.fill_gradient_rect(draw, 0, 0, W, H, (180, 210, 240), (100, 160, 200))
# Ground
gen.fill_gradient_rect(draw, 0, H // 2, W, H // 2, (80, 160, 80), (50, 120, 50))
# Grass patches
for gx in range(0, W, 40):
    gen.draw_circle(draw, gx + 10, H // 2 + 20, 8, fill=(60, 140, 60))

# Sun
gen.draw_circle(draw, W - 60, 60, 25, fill=(255, 230, 80, 220))

# Cloud
gen.draw_cloud(draw, 120, 60, 2.5, (255, 255, 255, 200))

# Cow
gen.draw_cow(draw, W // 2, H // 2 + 60, size=4.5, color=(240, 230, 220))

canvas.save(os.path.join(out_dir, "cow_field_scene.png"))

# 5. Grid with all color+size combos
import math
variants = [(c_tuple, name, sz) for c_tuple, name in colors for sz in [3.0, 5.0]]
cols = len(colors)
rows = 2
gw, gh = 250, 200
grid = Image.new("RGBA", (cols * gw, rows * gh), (245, 240, 230, 255))
for idx, (c_tuple, name, sz) in enumerate(variants):
    cx = idx % cols
    cy = idx // cols
    cell = Image.new("RGBA", (gw, gh), (255, 255, 255, 0))
    d = ImageDraw.Draw(cell)
    gen.draw_cow(d, gw // 2, gh // 2 + 20, size=sz * 0.6, color=c_tuple)
    d.text((5, 5), f"{name} x{sz:.1f}", fill=(60, 55, 50))
    grid.paste(cell, (cx * gw, cy * gh))

grid.save(os.path.join(out_dir, "cow_variants_grid.png"))

print(f"All cow sketches saved to {out_dir}")
