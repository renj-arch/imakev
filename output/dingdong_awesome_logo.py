"""Ding Dong & Think — awesome logo using SketchGenerator engine."""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from src.sketch_generator import SketchGenerator

W, H = 900, 520
gen = SketchGenerator(W, H, seed=42)
img = gen.create_canvas((25, 18, 50, 255))
draw = ImageDraw.Draw(img)

# ── Rich background gradient ──
for y in range(H):
    t = y / H
    if t < 0.5:
        # Dark purple → deep blue
        t2 = t * 2
        r = int(20 + 15 * t2)
        g = int(15 + 25 * t2)
        b = int(45 + 30 * t2)
    else:
        # Deep blue → warm dark
        t2 = (t - 0.5) * 2
        r = int(35 + 20 * t2)
        g = int(40 + 15 * t2)
        b = int(75 - 25 * t2)
    draw.line([(0, y), (W - 1, y)], fill=(r, g, b))

# ── Glow circles behind each figure ──
glow_positions = [(170, 230), (450, 230), (730, 240)]
glow_colors = [(50, 140, 255, 30), (255, 80, 160, 30), (255, 210, 50, 30)]
for (cx, cy), col in zip(glow_positions, glow_colors):
    for r in range(140, 40, -20):
        alpha = int(25 * (1 - r / 140))
        c = (col[0], col[1], col[2], max(5, alpha))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)

# Also stronger inner glow
for (cx, cy), col in zip(glow_positions, glow_colors):
    c = (col[0], col[1], col[2], 50)
    draw.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=c)

# ── Decorative diagonal lines ──
for i in range(3):
    y_base = 120 + i * 140
    draw.line([(0, y_base), (W, y_base + 30)], fill=(60, 50, 90, 60), width=1)

# ── Draw Ding (man) ──
gen.draw_human(draw, 170, 250, size=1.2, color=(40, 120, 220), skin_color=(230, 200, 175),
               gender="man", mood="peaceful", pose="standing")

# ── Draw Dong (woman) ──
gen.draw_human(draw, 450, 245, size=1.2, color=(200, 60, 140), skin_color=(235, 195, 175),
               gender="woman", mood="peaceful", pose="standing")

# ── Draw Think (child) ──
gen.draw_human(draw, 730, 260, size=0.9, color=(230, 180, 40), skin_color=(240, 210, 185),
               gender="neutral", mood="happy", pose="standing")

# ── Thought bubble above Think ──
bubble_center = (730, 140)
# Glow
for r in [48, 40, 32]:
    a = max(5, 60 - r * 1.2)
    draw.ellipse([bubble_center[0] - r, bubble_center[1] - r,
                  bubble_center[0] + r, bubble_center[1] + r],
                 fill=(255, 255, 255, int(a)))
# Main bubble
draw.ellipse([bubble_center[0] - 38, bubble_center[1] - 38,
              bubble_center[0] + 38, bubble_center[1] + 38],
             fill=(255, 255, 255, 230), outline=(220, 200, 255), width=2)
# Small connector bubbles
draw.ellipse([730 - 12, 170, 730 + 12, 194], fill=(255, 255, 255, 200), outline=(220, 200, 255), width=1)
draw.ellipse([730 - 7, 186, 730 + 7, 204], fill=(255, 255, 255, 160), outline=(220, 200, 255), width=1)

# Star inside bubble
star_cx, star_cy = 730, 140
# Draw a 5-point star
for angle_deg in range(0, 360, 72):
    rad1 = math.radians(angle_deg - 90)
    rad2 = math.radians(angle_deg + 36 - 90)
    x1 = star_cx + 14 * math.cos(rad1)
    y1 = star_cy + 14 * math.sin(rad1)
    x2 = star_cx + 6 * math.cos(rad2)
    y2 = star_cy + 6 * math.sin(rad2)
    draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 50), width=3)
# Connect back
for angle_deg in range(36, 396, 72):
    rad = math.radians(angle_deg - 90)
    x = star_cx + 6 * math.cos(rad)
    y = star_cy + 6 * math.sin(rad)
    rad_next = math.radians(angle_deg + 36 - 90)
    xn = star_cx + 14 * math.cos(rad_next)
    yn = star_cy + 14 * math.sin(rad_next)
    draw.line([(x, y), (xn, yn)], fill=(255, 200, 50), width=3)

# ── Names under figures ──
try:
    font_name = ImageFont.truetype("arialbd.ttf", 48) if os.name == "nt" else ImageFont.truetype("Arial Bold", 48)
except:
    font_name = ImageFont.truetype("arial.ttf", 48)

try:
    font_tag = ImageFont.truetype("arial.ttf", 18)
except:
    font_tag = ImageFont.load_default()

# DING
draw.text((170, 375), "DING", fill=(50, 140, 255), font=font_name, anchor="mm")
draw.text((171, 374), "DING", fill=(80, 180, 255, 120), font=font_name, anchor="mm")

# DONG
draw.text((450, 370), "DONG", fill=(230, 70, 150), font=font_name, anchor="mm")
draw.text((451, 369), "DONG", fill=(255, 120, 180, 120), font=font_name, anchor="mm")

# THINK
draw.text((730, 380), "THINK", fill=(255, 200, 50), font=font_name, anchor="mm")
draw.text((731, 379), "THINK", fill=(255, 220, 100, 120), font=font_name, anchor="mm")

# ── Bottom tagline ──
tagline_y = 460
# Decorative line
draw.line([(120, tagline_y - 10), (W - 120, tagline_y - 10)], fill=(80, 60, 120, 80), width=1)

try:
    font_tagline = ImageFont.truetype("arialbd.ttf", 36)
except:
    font_tagline = ImageFont.truetype("arial.ttf", 36)

# Tagline with glow
draw.text((W//2, tagline_y), "Ding Dong & Think", fill=(180, 170, 220), font=font_tagline, anchor="mm")
draw.text((W//2 + 1, tagline_y - 1), "Ding Dong & Think", fill=(220, 200, 255, 80), font=font_tagline, anchor="mm")

draw.line([(120, tagline_y + 10), (W - 120, tagline_y + 10)], fill=(80, 60, 120, 80), width=1)

# ── Subtitle ──
draw.text((W//2, tagline_y + 38), "— A Family Logo —", fill=(120, 110, 150, 180), font=font_tag, anchor="mm")

# ── Subtle decorative dots ──
for i in range(20):
    dx = 80 + i * 40
    dy = 55 + int(15 * math.sin(i * 0.8))
    draw.ellipse([dx - 1.5, dy - 1.5, dx + 1.5, dy + 1.5], fill=(100, 80, 140, 40))

# ── Save ──
output_path = os.path.join(os.path.dirname(__file__), "dingdong_logo_awesome.png")
img.save(output_path)
print(f"Logo saved to {output_path}")
img.show()
