"""Generate Ding Dong & Think logo with character figures."""

import math
from PIL import Image, ImageDraw, ImageFont

W, H = 800, 500
img = Image.new("RGBA", (W, H), (20, 15, 35, 255))
draw = ImageDraw.Draw(img)

def _sc(c):
    return tuple(max(0, min(255, int(x))) for x in c)

def lerp_color(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))

# ── Background gradient ──
for y in range(H):
    t = y / H
    c = _sc(lerp_color((20, 15, 45), (45, 30, 70), t))
    draw.line([(0, y), (W - 1, y)], fill=c)

# ── Accent circles behind figures ──
accent_positions = [(140, 210), (400, 210), (660, 210)]
accent_colors = [(50, 140, 220, 60), (220, 80, 140, 60), (240, 190, 50, 60)]
for (cx, cy), col in zip(accent_positions, accent_colors):
    draw.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=col)

# ── Figure drawer ──
def draw_figure(d, cx, cy, scale, gender, color):
    """Draw a simple but expressive stick figure."""
    body_color = color
    head_r = int(18 * scale)
    # Head
    d.ellipse([cx - head_r, cy - 50 * scale - head_r,
               cx + head_r, cy - 50 * scale + head_r],
              fill=_sc(body_color), outline=_sc(lerp_color(body_color, (0, 0, 0), 0.3)), width=2)
    # Hair / hat detail
    if gender == "woman":
        # Hair
        hair_y = cy - 50 * scale - head_r + 2
        d.ellipse([cx - head_r - 2, hair_y - head_r // 3,
                   cx + head_r + 2, hair_y + head_r],
                  fill=_sc((180, 100, 60)), outline=None)
        # Re-draw face oval over hair
        d.ellipse([cx - head_r, cy - 50 * scale - head_r + 4,
                   cx + head_r, cy - 50 * scale + head_r],
                  fill=_sc(body_color), outline=_sc(lerp_color(body_color, (0, 0, 0), 0.3)), width=2)
        # Hair on sides
        d.arc([cx - head_r - 4, cy - 50 * scale - head_r + 4,
               cx + head_r + 4, cy - 50 * scale + head_r + 8],
              180, 360, fill=_sc((180, 100, 60)), width=3)
        # Dress triangle
        dress_top = cy + 20 * scale
        dress_bot = cy + 65 * scale
        d.polygon([cx - 25 * scale, dress_top, cx + 25 * scale, dress_top,
                   cx + 35 * scale, dress_bot, cx - 35 * scale, dress_bot],
                  fill=_sc(body_color), outline=_sc(lerp_color(body_color, (0, 0, 0), 0.3)), width=2)
        # Legs (from dress bottom)
        leg_top = dress_bot - 5 * scale
        leg_bot = leg_top + 30 * scale
        d.line([(cx - 15 * scale, leg_top), (cx - 20 * scale, leg_bot)],
               fill=_sc(body_color), width=max(3, int(3 * scale)))
        d.line([(cx + 15 * scale, leg_top), (cx + 20 * scale, leg_bot)],
               fill=_sc(body_color), width=max(3, int(3 * scale)))
    else:
        # Simple body
        body_top = cy - 30 * scale
        body_bot = cy + 40 * scale
        d.line([(cx, body_top), (cx, body_bot)],
               fill=_sc(body_color), width=max(3, int(3 * scale)))
        # Arms
        arm_y = cy
        d.line([(cx - 30 * scale, arm_y - 5 * scale), (cx + 30 * scale, arm_y + 5 * scale)],
               fill=_sc(body_color), width=max(2, int(2 * scale)))
        # Legs
        leg_top = body_bot
        leg_bot = leg_top + 30 * scale
        d.line([(cx, leg_top), (cx - 20 * scale, leg_bot)],
               fill=_sc(body_color), width=max(3, int(3 * scale)))
        d.line([(cx, leg_top), (cx + 20 * scale, leg_bot)],
               fill=_sc(body_color), width=max(3, int(3 * scale)))

    # Face (simple)
    face_y = cy - 50 * scale
    # Eyes
    eye_offset = int(6 * scale)
    eye_r = max(2, int(2 * scale))
    d.ellipse([cx - eye_offset - eye_r, face_y - eye_r - 2,
               cx - eye_offset + eye_r, face_y + eye_r - 2], fill=(255, 255, 255))
    d.ellipse([cx + eye_offset - eye_r, face_y - eye_r - 2,
               cx + eye_offset + eye_r, face_y + eye_r - 2], fill=(255, 255, 255))
    # Pupils
    pr = max(1, int(1.2 * scale))
    d.ellipse([cx - eye_offset - pr, face_y - pr - 1,
               cx - eye_offset + pr, face_y + pr - 1], fill=(30, 30, 30))
    d.ellipse([cx + eye_offset - pr, face_y - pr - 1,
               cx + eye_offset + pr, face_y + pr - 1], fill=(30, 30, 30))
    # Smile
    d.arc([cx - 8 * scale, face_y + 2 * scale,
           cx + 8 * scale, face_y + 10 * scale],
          0, 180, fill=(200, 100, 100), width=max(1, int(1.5 * scale)))

def draw_child(d, cx, cy, scale, color):
    """Draw a child figure (shorter, bigger head proportion)."""
    body_color = color
    head_r = int(20 * scale)
    # Head (bigger proportion)
    d.ellipse([cx - head_r, cy - 45 * scale - head_r,
               cx + head_r, cy - 45 * scale + head_r],
              fill=_sc(body_color), outline=_sc(lerp_color(body_color, (0, 0, 0), 0.3)), width=2)
    # Body (shorter)
    body_top = cy - 25 * scale
    body_bot = cy + 25 * scale
    d.line([(cx, body_top), (cx, body_bot)],
           fill=_sc(body_color), width=max(3, int(3 * scale)))
    # Arms up (excited)
    d.line([(cx - 25 * scale, cy - 5 * scale), (cx, cy - 15 * scale)],
           fill=_sc(body_color), width=max(2, int(2 * scale)))
    d.line([(cx + 25 * scale, cy - 5 * scale), (cx, cy - 15 * scale)],
           fill=_sc(body_color), width=max(2, int(2 * scale)))
    # Legs
    leg_top = body_bot
    leg_bot = leg_top + 20 * scale
    d.line([(cx, leg_top), (cx - 15 * scale, leg_bot)],
           fill=_sc(body_color), width=max(3, int(3 * scale)))
    d.line([(cx, leg_top), (cx + 15 * scale, leg_bot)],
           fill=_sc(body_color), width=max(3, int(3 * scale)))

    # Face
    face_y = cy - 45 * scale
    eye_offset = int(7 * scale)
    eye_r = max(2, int(2.5 * scale))
    d.ellipse([cx - eye_offset - eye_r, face_y - eye_r,
               cx - eye_offset + eye_r, face_y + eye_r], fill=(255, 255, 255))
    d.ellipse([cx + eye_offset - eye_r, face_y - eye_r,
               cx + eye_offset + eye_r, face_y + eye_r], fill=(255, 255, 255))
    pr = max(1, int(1.5 * scale))
    d.ellipse([cx - eye_offset - pr, face_y - pr + 1,
               cx - eye_offset + pr, face_y + pr + 1], fill=(30, 30, 30))
    d.ellipse([cx + eye_offset - pr, face_y - pr + 1,
               cx + eye_offset + pr, face_y + pr + 1], fill=(30, 30, 30))
    # Big smile
    d.arc([cx - 10 * scale, face_y + 3 * scale,
           cx + 10 * scale, face_y + 12 * scale],
          0, 180, fill=(220, 120, 100), width=max(1, int(2 * scale)))

# ── Draw figures ──
# DING (man) - blue
draw_figure(draw, 140, 270, 1.0, "man", (60, 140, 220))
# DONG (woman) - pink/red
draw_figure(draw, 400, 270, 1.0, "woman", (210, 80, 140))
# THINK (child) - yellow/orange, smaller
draw_child(draw, 660, 290, 0.85, (240, 180, 50))

# ── Thought bubble for Think ──
bubble_cx, bubble_cy = 660, 170
bubble_r = 35
# Bubble circles
draw.ellipse([bubble_cx - bubble_r, bubble_cy - bubble_r,
              bubble_cx + bubble_r, bubble_cy + bubble_r],
             fill=(255, 255, 255, 220), outline=(200, 200, 220), width=2)
# Small bubbles leading to head
draw.ellipse([bubble_cx - 10, bubble_cy + bubble_r - 5,
              bubble_cx + 10, bubble_cy + bubble_r + 25],
             fill=(255, 255, 255, 200), outline=(200, 200, 220), width=1)
draw.ellipse([bubble_cx - 6, bubble_cy + bubble_r + 18,
              bubble_cx + 6, bubble_cy + bubble_r + 36],
             fill=(255, 255, 255, 180), outline=(200, 200, 220), width=1)
# Lightbulb symbol inside bubble
lb_cx, lb_cy = bubble_cx, bubble_cy
# Bulb circle
draw.ellipse([lb_cx - 10, lb_cy - 5, lb_cx + 10, lb_cy + 12],
             fill=(255, 200, 50), outline=(200, 160, 30), width=1)
# Base
draw.polygon([(lb_cx - 5, lb_cy + 12), (lb_cx + 5, lb_cy + 12),
              (lb_cx + 3, lb_cy + 18), (lb_cx - 3, lb_cy + 18)],
             fill=(180, 180, 190))
# Rays
for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
    rad = math.radians(angle)
    sx = lb_cx + 10 * math.cos(rad)
    sy = lb_cy - 2 + 10 * math.sin(rad)
    ex = lb_cx + 16 * math.cos(rad)
    ey = lb_cy - 2 + 16 * math.sin(rad)
    draw.line([(sx, sy), (ex, ey)], fill=(255, 200, 50), width=2)

# ── Names under figures ──
try:
    font_large = ImageFont.truetype("arial.ttf", 52)
    font_med = ImageFont.truetype("arial.ttf", 36)
    font_small = ImageFont.truetype("arial.ttf", 20)
except:
    font_large = ImageFont.load_default()
    font_med = font_large
    font_small = font_large

# DING
draw.text((140, 370), "DING", fill=(60, 140, 220), font=font_large, anchor="mm")
# DONG
draw.text((400, 370), "DONG", fill=(210, 80, 140), font=font_large, anchor="mm")
# THINK
draw.text((660, 380), "THINK", fill=(240, 180, 50), font=font_med, anchor="mm")

# ── Tagline at bottom ──
tagline_y = 440
# Decorated line
draw.line([(150, tagline_y - 8), (W - 150, tagline_y - 8)], fill=(100, 80, 140, 100), width=1)
draw.text((W // 2, tagline_y), "Ding Dong & Think", fill=(200, 190, 220),
          font=font_large, anchor="mm")
draw.line([(150, tagline_y + 8), (W - 150, tagline_y + 8)], fill=(100, 80, 140, 100), width=1)

# ── Subtle subtitle ──
draw.text((W // 2, tagline_y + 35), "— A Family Logo —", fill=(140, 130, 170, 180),
          font=font_small, anchor="mm")

# ── Save ──
output_path = r"C:\Users\Renjith\Desktop\icode (2)\imakev\output\dingdong_logo.png"
img.save(output_path)
img.show()
print(f"Logo saved to {output_path}")
