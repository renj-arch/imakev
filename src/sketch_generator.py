"""LLM-driven sketch generator — creates detailed, full-color illustrations from
structured scene descriptions. Features rich procedural elements with gradient
fills, drop shadows, and atmospheric effects.

Handles any topic: landscapes, characters, objects, diagrams, abstract art.
Built from scratch — no hardcoded pirate/ship/etc. functions."""

import math, random, colorsys, re, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from typing import Optional
import config

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


class SketchGenerator:
    """Generate detailed, full-color illustrations from structured scene descriptions."""

    def __init__(self, width=W, height=H, seed=None):
        self.w = width
        self.h = height
        self.rng = random.Random(seed)

    # ── Color utilities ─────────────────────────────────────────

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _lerp_color(c1, c2, t):
        return tuple(int(a + (b-a)*t) for a, b in zip(c1, c2))

    def _harmonize(self, base_color, variation=30):
        return tuple(max(0, min(255, c + self.rng.randint(-variation, variation))) for c in base_color)

    def _with_alpha(self, color, alpha=255):
        return tuple(color[:3]) + (alpha,)

    def _tc(self, c, default=None):
        """Convert list/tuple color to tuple, safely."""
        if c is None: return default
        if isinstance(c, (list, tuple)):
            return tuple(c[:3])
        return c

    @staticmethod
    def _darken(c, amount=30):
        return tuple(max(0, v - amount) for v in c[:3])

    @staticmethod
    def _lighten(c, amount=30):
        return tuple(min(255, v + amount) for v in c[:3])

    # ── Canvas ──────────────────────────────────────────────────

    def create_canvas(self, bg_color=(255, 255, 255, 255)):
        img = Image.new("RGBA", (self.w, self.h), bg_color)
        return img

    # ── Drawing primitives (clean, no wobble) ───────────────────

    def draw_circle(self, draw, cx, cy, r, fill=None, stroke=None, stroke_width=2, opacity=255):
        if fill:
            c = fill if len(fill) == 4 else fill + (opacity,)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=c)
        if stroke:
            c = stroke if len(stroke) == 4 else stroke + (opacity,)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c, width=stroke_width)

    def draw_rect(self, draw, x, y, w, h, fill=None, stroke=None, stroke_width=2, rx=0, opacity=255):
        if fill:
            c = fill if len(fill) == 4 else fill + (opacity,)
            if rx > 0:
                draw.rounded_rectangle([x, y, x+w, y+h], radius=rx, fill=c)
            else:
                draw.rectangle([x, y, x+w, y+h], fill=c)
        if stroke:
            c = stroke if len(stroke) == 4 else stroke + (opacity,)
            if rx > 0:
                draw.rounded_rectangle([x, y, x+w, y+h], radius=rx, outline=c, width=stroke_width)
            else:
                draw.rectangle([x, y, x+w, y+h], outline=c, width=stroke_width)

    def draw_polygon(self, draw, points, fill=None, stroke=None, stroke_width=2, opacity=255):
        if fill:
            c = fill if len(fill) == 4 else fill + (opacity,)
            draw.polygon(points, fill=c)
        if stroke:
            c = stroke if len(stroke) == 4 else stroke + (opacity,)
            draw.polygon(points, outline=c, width=stroke_width)

    def draw_line(self, draw, x1, y1, x2, y2, color=(0, 0, 0), width=2, opacity=255):
        c = color if len(color) == 4 else color + (opacity,)
        draw.line([(x1, y1), (x2, y2)], fill=c, width=width)

    def draw_arc(self, draw, cx, cy, r, start_angle, end_angle, color=(0, 0, 0), width=2, opacity=255):
        c = color if len(color) == 4 else color + (opacity,)
        draw.arc([cx-r, cy-r, cx+r, cy+r], start_angle, end_angle, fill=c, width=width)

    def draw_text(self, draw, x, y, text, font_size=24, color=(0, 0, 0), align="left", opacity=255):
        try:
            font = ImageFont.truetype(config.get_font(), font_size)
        except:
            font = ImageFont.load_default()
        c = color if len(color) == 4 else color + (opacity,)
        if align == "center":
            bb = draw.textbbox((0, 0), text, font=font)
            x -= (bb[2] - bb[0]) // 2
        draw.text((x, y), text, font=font, fill=c)

    def draw_text_box(self, draw, x, y, text, font_size=24, text_color=(40, 35, 30),
                      bg_color=(255, 250, 240), border_color=(40, 35, 30), padding=12, rx=6):
        try:
            font = ImageFont.truetype(config.get_font(), font_size)
        except:
            font = ImageFont.load_default()
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        box_w, box_h = tw + padding*2, th + padding*2
        self.draw_rect(draw, x-box_w//2, y-box_h//2, box_w, box_h,
                       fill=bg_color, stroke=border_color, rx=rx)
        draw.text((x-tw//2, y-th//2), text, font=font, fill=text_color)

    # ── Advanced fills ──────────────────────────────────────────

    def fill_gradient_polygon(self, draw, points, color_top, color_bottom, stroke=None, stroke_width=1):
        """Fill polygon with vertical gradient from color_top to color_bottom."""
        if not points:
            return
        points = [(int(p[0]), int(p[1])) for p in points]
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        if max_y <= min_y:
            c = tuple(int((a+b)/2) for a,b in zip(color_top, color_bottom))
            draw.polygon(points, fill=c + (255,))
            return
        # Render scanline by scanline within the polygon
        for y in range(min_y, max_y + 1):
            t = (y - min_y) / (max_y - min_y)
            c = self._lerp_color(color_top, color_bottom, t)
            # Find x intersections at this scanline
            intersections = []
            n = len(points)
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    if y1 != y2:
                        x = int(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
                        intersections.append(x)
            if len(intersections) >= 2:
                intersections.sort()
                for i in range(0, len(intersections) - 1, 2):
                    draw.line([(intersections[i], y), (intersections[i+1], y)], fill=c + (255,))
        if stroke:
            draw.polygon(points, outline=stroke, width=stroke_width)

    def fill_gradient_rect(self, draw, x, y, w, h, color_top, color_bottom, vertical=True):
        """Fill rectangle with gradient."""
        x, y, w, h = int(x), int(y), int(w), int(h)
        if vertical:
            for row in range(h):
                t = row / max(h - 1, 1)
                c = self._lerp_color(color_top, color_bottom, t)
                draw.line([(x, y + row), (x + w - 1, y + row)], fill=c + (255,))
        else:
            for col in range(w):
                t = col / max(w - 1, 1)
                c = self._lerp_color(color_top, color_bottom, t)
                draw.line([(x + col, y), (x + col, y + h - 1)], fill=c + (255,))

    def draw_shadow(self, draw, points, offset=(4, 4), blur_radius=3, color=(0, 0, 0, 60)):
        """Draw a soft drop shadow behind a shape defined by points."""
        shadow_pts = [(int(x + offset[0]), int(y + offset[1])) for x, y in points]
        # Draw shadow on temp image for blur
        shadow_img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_img)
        s_draw.polygon(shadow_pts, fill=color)
        if blur_radius > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        draw.bitmap((0, 0), shadow_img)

    def draw_shadow_circle(self, draw, cx, cy, r, offset=(4, 4), blur_radius=3, color=(0, 0, 0, 60)):
        cx, cy, r = int(cx), int(cy), int(r)
        shadow_img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_img)
        s_draw.ellipse([cx-r+offset[0], cy-r+offset[1], cx+r+offset[0], cy+r+offset[1]], fill=color)
        if blur_radius > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        draw.bitmap((0, 0), shadow_img)

    # ── Background renderers ────────────────────────────────────

    def bg_gradient(self, draw, colors, direction="vertical"):
        if direction == "vertical":
            for y in range(self.h):
                t = y / self.h
                c = self._gradient_at(colors, t)
                draw.line([(0, y), (self.w, y)], fill=c)
        else:
            for x in range(self.w):
                t = x / self.w
                c = self._gradient_at(colors, t)
                draw.line([(x, 0), (x, self.h)], fill=c)

    def _gradient_at(self, colors, t):
        if len(colors) == 1:
            return colors[0][1]
        for i in range(len(colors)-1):
            p0, c0 = colors[i]
            p1, c1 = colors[i+1]
            if p0 <= t <= p1:
                lt = (t - p0) / (p1 - p0) if p1 > p0 else 0
                return self._lerp_color(c0, c1, lt)
        return colors[-1][1]

    # ── Procedural element generators ──────────────────────────

    def draw_mountains(self, draw, x, y, width, height, color, snow=True):
        """Draw detailed mountain range with shading, snow caps, and layered peaks."""
        c = tuple(color[:3])
        dark = self._darken(c, 30)
        light = self._lighten(c, 10)
        half_w = width // 2

        # ── Background peaks ──
        for i in range(3):
            bx = x + self.rng.randint(-half_w//2, half_w//2)
            by = y
            bh = height * self.rng.uniform(0.5, 0.75)
            bw = half_w * self.rng.uniform(0.5, 0.7)
            bp = [(bx - bw, by), (bx, by - bh), (bx + bw, by)]
            col = self._darken(c, 50 + i * 10)
            if i == 0:
                self.draw_shadow(draw, bp, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 50))
            self.fill_gradient_polygon(draw, bp, self._lighten(col, 10), self._darken(col, 20),
                                       stroke=self._darken(col, 30), stroke_width=1)

        # ── Main peak (shaded: left face darker, right face lighter) ──
        peak_x, peak_y = x, y - height
        mid_x = x - half_w // 3
        mid_y = y - height * 0.7

        # Left face (shadow side)
        left_face = [(x - half_w, y), (mid_x, mid_y), (peak_x, peak_y)]
        self.draw_shadow(draw, left_face, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 60))
        self.fill_gradient_polygon(draw, left_face, self._darken(c, 20), dark,
                                   stroke=self._darken(c, 40), stroke_width=1)

        # Right face (light side)
        right_face = [(peak_x, peak_y), (mid_x, mid_y), (x + half_w, y)]
        self.fill_gradient_polygon(draw, right_face, light, c,
                                   stroke=self._darken(c, 40), stroke_width=1)

        # ── Snow cap ──
        if snow:
            snow_h = height * 0.15
            snow_w = half_w * 0.35
            snow_pts = [(peak_x, peak_y),
                        (peak_x - snow_w * 0.8, peak_y + snow_h),
                        (peak_x - snow_w * 0.3, peak_y + snow_h * 0.5),
                        (peak_x + snow_w * 0.3, peak_y + snow_h * 0.5),
                        (peak_x + snow_w * 0.8, peak_y + snow_h)]
            self.draw_shadow(draw, snow_pts, offset=(1, 2), blur_radius=2, color=(0, 0, 0, 30))
            self.fill_gradient_polygon(draw, snow_pts, (255, 255, 255), (230, 235, 245),
                                       stroke=(200, 210, 220), stroke_width=1)

            # Snow streaks down the face
            for _ in range(3):
                sx = peak_x + self.rng.randint(-8, 8)
                sy = peak_y + snow_h
                sl = int(height * 0.12)
                self.draw_line(draw, sx, sy, sx + self.rng.randint(-3, 3), sy + sl,
                               color=(240, 245, 255, 150), width=self.rng.randint(1, 2))

        # ── Ridge detail lines ──
        for _ in range(4):
            rx = x - half_w + self.rng.randint(0, half_w * 2)
            ry1 = y - self.rng.randint(int(height * 0.2), int(height * 0.6))
            ry2 = y - self.rng.randint(int(height * 0.3), int(height * 0.7))
            if abs(rx - x) < half_w * 0.8:
                self.draw_line(draw, rx, ry1, rx + self.rng.randint(-10, 10), ry2,
                               color=self._darken(c, 40) + (80,), width=1)

    def draw_tree(self, draw, x, y, size=1.0, style="round", color=(50, 120, 50)):
        """Draw a detailed tree with bark, foliage clusters, and shadows."""
        s = size
        c = tuple(color[:3])
        dark_green = self._darken(c, 30)
        light_green = self._lighten(c, 20)
        trunk_h = 35 * s
        trunk_w = 7 * s

        # ── Shadow under tree ──
        shadow_r = 25 * s
        self.draw_shadow_circle(draw, x, y + 2, shadow_r, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 50))

        # ── Trunk with gradient ──
        self.fill_gradient_rect(draw, int(x-trunk_w//2), int(y-trunk_h), int(trunk_w), int(trunk_h),
                                (90, 65, 45), (60, 45, 35))

        # Trunk texture lines
        for _ in range(3):
            tx = x + self.rng.randint(-int(trunk_w//2), int(trunk_w//2))
            ty = y - self.rng.randint(0, int(trunk_h))
            self.draw_line(draw, tx, ty, tx, ty + self.rng.randint(5, 12),
                           color=(50, 35, 25, 100), width=1)

        # ── Foliage ──
        if style == "pine":
            # Layered triangular foliage
            layers = 4
            for i in range(layers):
                ly = y - trunk_h + i * (trunk_h // layers) * 0.9
                lw = (22 - i * 3.5) * s
                lh = (trunk_h // layers) * 1.0
                pts = [(x - lw, ly + lh), (x + lw, ly + lh), (x, ly)]
                shade = self._lerp_color(dark_green, light_green, i / layers)
                self.fill_gradient_polygon(draw, pts, shade, self._darken(shade, 15),
                                           stroke=self._darken(c, 40), stroke_width=1)
                # Snow on branches (winter effect)
                if self.rng.random() < 0.3:
                    sw = lw * 0.3
                    self.draw_arc(draw, x, ly, sw, 0, 180, color=(255, 255, 255, 120), width=int(2*s))

        elif style == "palm":
            # Trunk curve
            trunk_pts = [(x, y), (x, y - trunk_h)]
            self.draw_line(draw, x, y, x, y - trunk_h, color=(80, 55, 35), width=int(trunk_w))
            for a in [-70, -50, -30, -10, 10, 30, 50, 70]:
                rad = math.radians(a)
                fl = 30 * s
                fx = x + math.cos(rad) * fl
                fy = y - trunk_h + math.sin(rad) * fl * 0.3
                frond_pts = [(x, y - trunk_h)]
                for j in range(1, 8):
                    t = j / 8
                    fx2 = x + math.cos(rad + 0.4 * math.sin(t * math.pi)) * t * fl
                    fy2 = y - trunk_h + t * (fy - (y - trunk_h)) + abs(math.sin(t * math.pi * 2)) * 5 * s
                    frond_pts.append((fx2, fy2))
                for pi in range(len(frond_pts)-1):
                    self.draw_line(draw, frond_pts[pi][0], frond_pts[pi][1],
                                   frond_pts[pi+1][0], frond_pts[pi+1][1],
                                   color=(30, 80, 30, 180), width=int(2*s+1))

        else:
            # Round / deciduous — multiple foliage clusters
            canopy_center_y = y - trunk_h + 5 * s
            cluster_positions = [(0, 0), (8*s, -4*s), (-7*s, -3*s), (4*s, 6*s), (-5*s, 5*s),
                                 (10*s, 2*s), (-10*s, 1*s)]
            cr = 10 * s
            for ox, oy in cluster_positions:
                shade = self._harmonize(c, 25)
                if abs(ox) > 5*s or abs(oy) > 3*s:
                    shade = self._darken(shade, 10)
                # Bottom clusters slightly darker
                if oy > 0:
                    shade = self._darken(shade, 15)
                rr = cr * (0.7 + self.rng.random() * 0.4)
                self.draw_circle(draw, x+ox, canopy_center_y+oy, rr,
                                 fill=shade + (200,), stroke=self._darken(c, 30) + (100,), stroke_width=1)
            # Highlight clusters (lighter, smaller)
            for _ in range(3):
                hx = x + self.rng.randint(-int(8*s), int(8*s))
                hy = canopy_center_y + self.rng.randint(-int(6*s), int(4*s))
                hr = cr * self.rng.uniform(0.3, 0.5)
                self.draw_circle(draw, hx, hy, hr, fill=self._lighten(c, 50) + (120,))

            # Fallen leaves
            for _ in range(self.rng.randint(2, 5)):
                lx = x + self.rng.randint(-int(15*s), int(15*s))
                ly = y + self.rng.randint(0, int(5*s))
                self.draw_circle(draw, lx, ly, 2, fill=c + (150,))

    def draw_cloud(self, draw, x, y, size=1.0, color=(255, 255, 255)):
        """Draw a richly detailed cloud with shading."""
        c = tuple(color[:3])
        shadow_color = self._darken(c, 20)
        n_blobs = self.rng.randint(5, 8)
        blobs = []
        for _ in range(n_blobs):
            ox = self.rng.randint(-25, 25) * size
            oy = self.rng.randint(-10, 8) * size
            r = self.rng.randint(18, 40) * size
            blobs.append((ox, oy, r))

        # Sort by y position (draw back-to-front)
        blobs.sort(key=lambda b: b[1])

        # Draw shadow blobs
        for ox, oy, r in blobs:
            shade = self._harmonize(shadow_color, 5)
            self.draw_circle(draw, x+ox+2, y+oy+2, r, fill=shade + (100,))

        # Draw main blobs
        for i, (ox, oy, r) in enumerate(blobs):
            # Lighter at top, slightly darker at bottom
            is_top = oy < 0
            fc = self._lighten(c, 15) if is_top else self._darken(c, 5)
            self.draw_circle(draw, x+ox, y+oy, r, fill=fc + (200,),
                             stroke=self._darken(c, 15) + (80,), stroke_width=1)

        # Bottom flat highlight
        for ox, oy, r in blobs:
            if oy > 0:
                self.draw_arc(draw, x+ox, y+oy+r*0.3, r*0.7, 180, 360,
                              color=self._lighten(c, 30) + (60,), width=int(2*size+1))

    def draw_water(self, draw, x, y, w, h, color=(60, 120, 200)):
        """Draw water surface with reflections, waves, and depth."""
        c = tuple(color[:3])
        # Base water fill
        self.fill_gradient_rect(draw, x, y, w, h, self._lighten(c, 20), self._darken(c, 40))

        # Distant waves (small)
        for col in range(12):
            wx = x + col * (w // 12)
            for row in range(3):
                wy = y + row * 8
                wh = self.rng.randint(-3, 3)
                pts = [(wx, wy), (wx + w//24, wy + wh), (wx + w//12, wy)]
                shade = self._harmonize(self._lighten(c, 30), 10)
                self.draw_line(draw, pts[0][0], pts[0][1], pts[1][0], pts[1][1], color=shade, width=1, opacity=120)
                self.draw_line(draw, pts[1][0], pts[1][1], pts[2][0], pts[2][1], color=shade, width=1, opacity=120)

        # Near waves (bigger, more detail)
        for row in range(6):
            wy = y + h - row * (h // 6) - 5
            for col in range(8):
                wx = x + col * (w // 8)
                wave_h = self.rng.randint(-6, 6)
                pts = [(wx, wy), (wx + w//16, wy + wave_h), (wx + w//8, wy)]
                shade = self._harmonize(self._lighten(c, 15), 15)
                self.draw_line(draw, pts[0][0], pts[0][1], pts[1][0], pts[1][1], color=shade, width=1, opacity=160)
                self.draw_line(draw, pts[1][0], pts[1][1], pts[2][0], pts[2][1], color=shade, width=1, opacity=160)
                # Foam fleck
                if self.rng.random() < 0.3:
                    self.draw_circle(draw, wx + w//16, wy + wave_h, 1.5,
                                     fill=(255, 255, 255, self.rng.randint(80, 160)))

        # Horizontal reflection lines
        for _ in range(5):
            ry = y + self.rng.randint(5, h-5)
            rw = self.rng.randint(20, 60)
            rx = x + self.rng.randint(10, w-10-rw)
            self.draw_line(draw, rx, ry, rx+rw, ry, color=self._lighten(c, 40) + (100,), width=1)

        # Specular highlights
        for _ in range(6):
            hx = x + self.rng.randint(10, w-10)
            hy = y + self.rng.randint(5, h-5)
            self.draw_circle(draw, hx, hy, self.rng.uniform(1, 3),
                             fill=(255, 255, 255, self.rng.randint(40, 100)))

    def draw_human(self, draw, x, y, size=1.0, color=(80, 60, 120), skin_color=(235, 200, 175)):
        """Draw a detailed human figure with clothing, face features, and shading."""
        s = size
        skin = tuple(skin_color[:3])
        cloth = tuple(color[:3])

        # ── Shadow under feet ──
        self.draw_shadow_circle(draw, x, y + 22*s, 12*s, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 50))

        head_r = 11 * s
        neck_y = y - 38 * s

        # ── Legs with shading ──
        leg_color = self._darken(cloth, 20)
        for side, lx in [(-1, x-4*s), (1, x+4*s)]:
            leg_pts = [(lx, y+3*s), (lx + side*4*s, y+22*s),
                       (lx + side*3*s + 2, y+22*s), (lx+2, y+3*s)]
            self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 40))
            self.fill_gradient_polygon(draw, leg_pts, leg_color, self._darken(leg_color, 15),
                                       stroke=(40, 35, 30, 150), stroke_width=1)
            # Boot
            boot_pts = [(lx + side*4*s, y+20*s), (lx + side*6*s, y+24*s),
                       (lx + side*5*s, y+25*s), (lx + side*3*s, y+22*s)]
            self.draw_polygon(draw, boot_pts, fill=(45, 35, 30, 220), stroke=(30, 25, 20, 180), stroke_width=1)

        # ── Body (torso) ──
        torso_w = 10 * s
        torso_top = y - 28 * s
        torso_bot = y + 3 * s
        torso_pts = [(x - torso_w//2, torso_bot), (x - torso_w//2, torso_top),
                     (x + torso_w//2, torso_top), (x + torso_w//2, torso_bot)]
        self.draw_shadow(draw, torso_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 40))
        self.fill_gradient_rect(draw, x - torso_w//2, torso_top, torso_w, torso_bot - torso_top,
                                self._lighten(cloth, 10), self._darken(cloth, 20))

        # Belt
        belt_y = y - 5 * s
        self.draw_rect(draw, x - torso_w//2 - 1, belt_y, torso_w + 2, int(3*s),
                       fill=(50, 40, 30, 220))

        # ── Arms ──
        arm_color = self._darken(cloth, 10)
        for side in [-1, 1]:
            ax = x + side * (torso_w//2 + 1)
            # Upper arm
            self.draw_line(draw, x + side * 5*s, y - 22*s, x + side * 10*s, y - 8*s,
                           color=arm_color, width=int(3.5*s))
            if side == -1:
                # Hand / forearm
                hx = x - 10*s
                hy = y - 6*s
                self.draw_circle(draw, hx, hy, 3*s, fill=skin + (220,), stroke=(40, 35, 30, 180), stroke_width=1)
            else:
                # Arm resting
                self.draw_line(draw, x + 10*s, y - 8*s, x + 8*s, y + 3*s,
                               color=arm_color, width=int(3*s))
                self.draw_circle(draw, x + 8*s, y + 4*s, 3*s, fill=skin + (220,), stroke=(40, 35, 30, 180), stroke_width=1)

        # ── Head ──
        self.draw_shadow_circle(draw, x, neck_y + 2, head_r, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 40))
        # Head fill with gradient
        self.fill_gradient_polygon(draw,
            [(x - head_r, neck_y), (x + head_r, neck_y),
             (x + head_r, neck_y - head_r*2), (x - head_r, neck_y - head_r*2)],
            self._lighten(skin, 10), self._darken(skin, 15))
        self.draw_circle(draw, x, neck_y, head_r, fill=None,
                         stroke=(40, 35, 30, 180), stroke_width=2)

        # ── Hair ──
        hair_color = (50, 40, 30)
        self.draw_arc(draw, x, neck_y - head_r * 0.7, head_r * 0.85, 200, 340,
                      color=hair_color, width=int(4*s))
        self.draw_circle(draw, x, neck_y - head_r + 2, head_r * 0.7, fill=hair_color + (200,))

        # ── Face features ──
        # Eyes
        self.draw_circle(draw, x - 3.5*s, neck_y - 3*s, 1.8*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, x + 3.5*s, neck_y - 3*s, 1.8*s, fill=(30, 25, 20, 200))
        # Eye shine
        self.draw_circle(draw, x - 3*s, neck_y - 4*s, 0.7*s, fill=(255, 255, 255, 180))
        self.draw_circle(draw, x + 4*s, neck_y - 4*s, 0.7*s, fill=(255, 255, 255, 180))
        # Nose
        self.draw_line(draw, x, neck_y - 1.5*s, x, neck_y + 1.5*s, color=(40, 35, 30, 120), width=1)
        # Mouth
        self.draw_arc(draw, x, neck_y + 3*s, 3*s, 200, 340, color=(140, 80, 60, 180), width=int(s+1))
        # Eyebrows
        self.draw_line(draw, x - 5*s, neck_y - 6.5*s, x - 1.5*s, neck_y - 6*s,
                       color=hair_color + (150,), width=int(s+1))
        self.draw_line(draw, x + 5*s, neck_y - 6.5*s, x + 1.5*s, neck_y - 6*s,
                       color=hair_color + (150,), width=int(s+1))

    def draw_house(self, draw, x, y, size=1.0, color=(180, 150, 120), roof_color=(150, 50, 40)):
        """Draw a detailed house with texture, windows, door, and shadows."""
        s = size
        c = tuple(color[:3])
        rc = tuple(roof_color[:3])
        hw, hh = 35*s, 28*s

        # ── Shadow under house ──
        shadow_pts = [(x - hw//2 - 5, y), (x + hw//2 + 5, y),
                      (x + hw//2 + 5, y + 5), (x - hw//2 - 5, y + 5)]
        self.draw_shadow(draw, shadow_pts, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 50))

        # ── Walls with gradient ──
        self.fill_gradient_rect(draw, x - hw//2, y - hh, hw, hh,
                                self._lighten(c, 15), self._darken(c, 20))

        # Wall texture (brick lines)
        for brick_y in range(int(y - hh), int(y), 8):
            self.draw_line(draw, x - hw//2, brick_y, x + hw//2, brick_y,
                           color=self._darken(c, 15) + (50,), width=1)
            for brick_x in range(int(x - hw//2), int(x + hw//2), 12):
                self.draw_line(draw, brick_x, brick_y, brick_x, brick_y + 4,
                               color=self._darken(c, 15) + (40,), width=1)

        # ── Roof ──
        roof_h = 20*s
        roof_pts = [(x - hw//2 - 4, y - hh), (x, y - hh - roof_h), (x + hw//2 + 4, y - hh)]
        self.draw_shadow(draw, roof_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 50))
        self.fill_gradient_polygon(draw, roof_pts, self._lighten(rc, 15), self._darken(rc, 20),
                                   stroke=self._darken(rc, 30), stroke_width=2)
        # Roof tile lines
        for i in range(1, 6):
            t = i / 6
            rx1 = x - hw//2 - 4 + t * (x + hw//2 + 4 + hw//2 + 4) / 6
            rx2 = x + hw//2 + 4 - t * (x + hw//2 + 4 + hw//2 + 4) / 6
            ry = y - hh - t * roof_h
            self.draw_line(draw, rx1, ry, rx2, ry, color=self._darken(rc, 20) + (80,), width=1)

        # ── Door ──
        dw, dh = 8*s, 14*s
        door_color = (100, 65, 40)
        self.draw_rect(draw, x - dw//2, y - dh, dw, dh,
                       fill=door_color + (220,), stroke=(50, 35, 25, 180), stroke_width=2, rx=2)
        # Door knob
        self.draw_circle(draw, x + dw//2 - 3, y - dh//2, 1.5*s, fill=(180, 160, 100, 200))
        # Door panels (skip if too small)
        if dw > 6 and dh > 6:
            pw = max(1, dw//2 - 3)
            ph = max(1, dh//2 - 3)
            self.draw_rect(draw, x - dw//2 + 2, y - dh + 2, pw, ph,
                           stroke=(80, 50, 30, 100), stroke_width=1)
            self.draw_rect(draw, x + 2, y - dh + 2, pw, ph,
                           stroke=(80, 50, 30, 100), stroke_width=1)
            self.draw_rect(draw, x - dw//2 + 2, y - dh//2 + 1, pw, ph,
                           stroke=(80, 50, 30, 100), stroke_width=1)
            self.draw_rect(draw, x + 2, y - dh//2 + 1, pw, ph,
                           stroke=(80, 50, 30, 100), stroke_width=1)


        # ── Windows ──
        win_color = (255, 220, 100, 200)
        for win_side, wsign in [(-1, 1), (1, 1)]:
            wx = x + wsign * 11 * s
            ww, wh = 9*s, 9*s
            # Window frame shadow
            self.draw_shadow(draw,
                [(wx - ww//2, y - hh + wh//2), (wx + ww//2, y - hh + wh//2),
                 (wx + ww//2, y - hh - wh//2), (wx - ww//2, y - hh - wh//2)],
                offset=(2, 2), blur_radius=2, color=(0, 0, 0, 40))
            # Window pane
            self.draw_rect(draw, wx - ww//2, y - hh - wh//2, ww, wh,
                           fill=win_color, stroke=(60, 50, 40, 180), stroke_width=2, rx=1)
            # Cross dividers
            self.draw_line(draw, wx, y - hh - wh//2, wx, y - hh + wh//2,
                           color=(60, 50, 40, 150), width=1)
            self.draw_line(draw, wx - ww//2, y - hh, wx + ww//2, y - hh,
                           color=(60, 50, 40, 150), width=1)
            # Curtains
            self.draw_rect(draw, wx - ww//2, y - hh - wh//2, int(ww*0.3), wh,
                           fill=(200, 150, 120, 80))
            self.draw_rect(draw, wx + int(ww*0.4), y - hh - wh//2, int(ww*0.3), wh,
                           fill=(200, 150, 120, 80))

        # Chimney
        ch_x = x + hw//3
        ch_h = 12*s
        ch_w = 6*s
        self.fill_gradient_rect(draw, int(ch_x - ch_w//2), int(y - hh - roof_h - ch_h), int(ch_w), int(ch_h),
                                (130, 100, 80), (100, 75, 60))
        self.draw_rect(draw, int(ch_x - ch_w//2 - 1), int(y - hh - roof_h - ch_h), int(ch_w+2), int(2*s),
                       fill=(60, 50, 40, 200))
        # Smoke
        for _ in range(3):
            sm_x = ch_x + self.rng.randint(-5, 5)
            sm_y = y - hh - roof_h - ch_h - self.rng.randint(10, 25)
            sm_r = self.rng.randint(4, 8)
            self.draw_circle(draw, sm_x, sm_y, sm_r, fill=(200, 200, 200, self.rng.randint(30, 80)))

    def draw_hill(self, draw, x, y, width, height, color=(60, 120, 60)):
        """Draw a rolling hill with grass texture and shading."""
        c = tuple(color[:3])
        pts = [(x - width//2, y)]
        n_segments = 30
        for i in range(n_segments + 1):
            t = i / n_segments
            px = x - width//2 + t * width
            py = y - abs(math.sin(t * math.pi)) * height
            pts.append((px, py))
        pts.append((x + width//2, y))

        # Shadow
        self.draw_shadow(draw, pts, offset=(2, 3), blur_radius=4, color=(0, 0, 0, 40))

        # Hill fill with gradient (lighter at top, darker at bottom)
        self.fill_gradient_polygon(draw, pts, self._lighten(c, 20), self._darken(c, 15),
                                   stroke=self._darken(c, 20) + (100,), stroke_width=1)

        # Grass blades
        for _ in range(self.rng.randint(15, 30)):
            gx = x - width//2 + self.rng.randint(5, width-10)
            gy = y - abs(math.sin(((gx - (x - width//2)) / width) * math.pi)) * height
            gh = self.rng.randint(4, 10)
            gc = self._harmonize((50, 100, 40), 15)
            self.draw_line(draw, gx, gy, gx + self.rng.randint(-1, 1), gy - gh,
                            color=gc + (self.rng.randint(100, 180),), width=1)

    def draw_sun(self, draw, x, y, r=30, color=(255, 220, 50)):
        """Draw sun with glow effect and rays."""
        c = tuple(color[:3])

        # Outer glow (large, very transparent)
        for glow_r in [r * 3, r * 2.2, r * 1.6]:
            alpha = max(0, int(40 - glow_r * 0.5))
            self.draw_circle(draw, x, y, glow_r, fill=c + (alpha,))

        # Rays
        for a in range(0, 360, 15):
            rad = math.radians(a)
            self.draw_line(draw,
                x + math.cos(rad) * r * 1.05, y + math.sin(rad) * r * 1.05,
                x + math.cos(rad) * r * 1.8, y + math.sin(rad) * r * 1.8,
                color=self._lighten(c, 20) + (80,), width=2)

        # Sun body
        self.draw_shadow_circle(draw, x+2, y+2, r, offset=(2, 2), blur_radius=4, color=(0, 0, 0, 30))
        self.draw_circle(draw, x, y, r, fill=self._lighten(c, 30) + (200,))
        self.draw_circle(draw, x, y, r, fill=c + (180,))
        # Bright center
        self.draw_circle(draw, x, y, r * 0.6, fill=(255, 255, 255, 80))

    def draw_moon(self, draw, x, y, r=25):
        """Draw a glowing crescent moon."""
        # Outer glow
        for glow_r in [r * 2.5, r * 1.8, r * 1.3]:
            alpha = max(0, int(30 - glow_r * 0.3))
            self.draw_circle(draw, x, y, glow_r, fill=(200, 210, 255, alpha))

        # Moon body
        self.draw_circle(draw, x, y, r, fill=(250, 245, 230, 200))
        self.draw_circle(draw, x, y, r, fill=(240, 235, 210, 180),
                         stroke=(200, 195, 180, 150), stroke_width=1)

        # Crescent shadow
        self.draw_circle(draw, x + 6, y - 3, int(r * 0.8), fill=(20, 20, 50, 180))

        # Moon craters
        for _ in range(4):
            crx = x + self.rng.randint(-int(r*0.6), int(r*0.6))
            cry = y + self.rng.randint(-int(r*0.5), int(r*0.5))
            # Skip if inside crescent shadow area
            if math.sqrt((crx - x - 6)**2 + (cry - y + 3)**2) < r * 0.5:
                continue
            crr = self.rng.uniform(1.5, 3.5)
            self.draw_circle(draw, crx, cry, crr, fill=(210, 205, 190, 100))

    def draw_stars(self, draw, count=40):
        """Draw stars across the sky with varied sizes and brightness."""
        for _ in range(count):
            sx = self.rng.randint(0, self.w)
            sy = self.rng.randint(0, int(self.h * 0.6))
            sr = self.rng.uniform(0.5, 2.5)
            brightness = self.rng.randint(180, 255)
            twinkle = self.rng.randint(100, 200)
            self.draw_circle(draw, sx, sy, sr, fill=(brightness, brightness, brightness, twinkle))
            # Glow for brighter stars
            if sr > 1.5:
                self.draw_circle(draw, sx, sy, sr * 3, fill=(brightness, brightness, brightness, 20))

    def draw_ship(self, draw, x, y, s=1.0, hull_color=(80, 60, 40), sail_color=(220, 210, 190)):
        """Draw a detailed sailing ship with hull, masts, rigging, and sails."""
        hc = tuple(hull_color[:3])
        sc = tuple(sail_color[:3])
        hw, hh = 60*s, 14*s

        # ── Shadow on water ──
        self.draw_shadow_circle(draw, x, y + hh//2 + 5, hw//2, offset=(4, 4), blur_radius=6, color=(0, 0, 0, 50))
        # Water reflection
        for i in range(3):
            ry = y + hh//2 + 5 + i * 4
            rw = hw - i * 10
            self.draw_line(draw, x - rw//2, ry, x + rw//2, ry,
                           color=self._darken(hc, 20) + (60,), width=1)

        # ── Hull with planking ──
        hull_pts = [(x - hw//2, y + hh//2),
                    (x - hw//2 + 6*s, y - hh//2),
                    (x + hw//2 - 6*s, y - hh//2),
                    (x + hw//2, y + hh//2)]
        self.draw_shadow(draw, hull_pts, offset=(2, 3), blur_radius=4, color=(0, 0, 0, 50))
        self.fill_gradient_polygon(draw, hull_pts, self._lighten(hc, 10), self._darken(hc, 25),
                                   stroke=self._darken(hc, 40), stroke_width=2)

        # Hull plank lines
        for i in range(4):
            t = (i + 1) / 5
            ply = y + hh//2 - t * hh
            self.draw_line(draw, x - hw//2 + 4, ply, x + hw//2 - 2, ply,
                           color=self._darken(hc, 15) + (60,), width=1)

        # Hull stripe
        stripe_y = y - hh//4
        self.draw_line(draw, x - hw//2 + 4, stripe_y, x + hw//2 - 2, stripe_y,
                       color=(200, 180, 100, 150), width=int(2*s+1))

        # ── Bowsprit ──
        self.draw_line(draw, x + hw//2 - 2, y - hh//3, x + hw//2 + 20*s, y - hh//2 - 5*s,
                       color=(50, 40, 30), width=int(2*s))

        # ── Masts ──
        mast_color = (45, 35, 25)
        mast_positions = [(0, 1.0), (-12*s, 0.75), (14*s, 0.8)]
        for mx, mh_scale in mast_positions:
            mh = 40 * s * mh_scale
            self.draw_line(draw, x + mx, y - hh//2, x + mx, y - hh//2 - mh,
                           color=mast_color, width=int(2.5*s))

        # ── Sails ──
        # Main sail
        sail_pts = [(x, y - hh//2 - 5*s),
                    (x - 25*s, y - hh//2 - 18*s),
                    (x - 22*s, y - hh//2 - 20*s),
                    (x, y - hh//2 - 22*s),
                    (x + 22*s, y - hh//2 - 20*s),
                    (x + 25*s, y - hh//2 - 18*s)]
        self.draw_shadow(draw, sail_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 40))
        self.fill_gradient_polygon(draw, sail_pts, self._lighten(sc, 10), self._darken(sc, 15),
                                   stroke=self._darken(sc, 20) + (100,), stroke_width=1)
        # Sail billow lines
        for i in range(3):
            t = (i + 1) / 4
            sy = y - hh//2 - 5*s - t * 17*s
            cx = int(20 * math.sin(t * math.pi))
            self.draw_arc(draw, x, sy, 22*s - i * 3, 180, 360,
                          color=self._darken(sc, 15) + (60,), width=1)

        # Secondary sails
        for mx, ms, side in [(-12*s, 0.6, -1), (14*s, 0.65, 1)]:
            sail_top_y = y - hh//2 - 40*s * ms
            self.draw_polygon(draw,
                [(x + mx, y - hh//2 - 2*s),
                 (x + mx + side * 18*s * ms, y - hh//2 - 8*s - 14*s * ms),
                 (x + mx + side * 16*s * ms, y - hh//2 - 10*s - 14*s * ms),
                 (x + mx, y - hh//2 - 5*s - 35*s * ms + 5*s)],
                fill=self._lighten(sc, 5) + (200,),
                stroke=self._darken(sc, 15) + (100,), stroke_width=1)

        # ── Rigging lines ──
        self.draw_line(draw, x, y - hh//2 - 38*s, x + hw//2 + 18*s, y - hh//2 - 8*s,
                       color=(60, 50, 40, 100), width=1)
        self.draw_line(draw, x, y - hh//2 - 38*s, x - 15*s, y - hh//2 - 5*s,
                       color=(60, 50, 40, 100), width=1)
        # Ratlines
        for i in range(4):
            t = (i + 1) / 5
            ry = y - hh//2 - t * 35*s
            self.draw_line(draw, x - 8*s, ry, x + 8*s, ry,
                           color=(60, 50, 40, 60), width=1)

        # ── Flag ──
        flag_pts = [(x, y - hh//2 - 38*s),
                    (x + 16*s, y - hh//2 - 38*s - 8*s),
                    (x, y - hh//2 - 38*s + 4*s)]
        self.draw_polygon(draw, flag_pts, fill=(180, 40, 40, 220))

    def draw_building(self, draw, x, y, width, height, color=(120, 100, 80), window_color=(255, 220, 100)):
        """Draw a detailed building with windows, roof, and architectural details."""
        c = tuple(color[:3])
        wc = tuple(window_color[:3])
        bw = int(width)
        bh = int(height)

        # Shadow on ground
        shadow_pts = [(x - bw//2, y), (x + bw//2, y), (x + bw//2 + 10, y + 10), (x - bw//2 - 10, y + 10)]
        self.draw_shadow(draw, shadow_pts, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 50))

        # Building body
        self.fill_gradient_rect(draw, x - bw//2, y - bh, bw, bh,
                                self._lighten(c, 15), self._darken(c, 20))

        # Stone texture lines
        for stone_y in range(int(y - bh), int(y), 12):
            self.draw_line(draw, x - bw//2, stone_y, x + bw//2, stone_y,
                           color=self._darken(c, 10) + (40,), width=1)
            for stone_x in range(int(x - bw//2), int(x + bw//2), 15):
                self.draw_line(draw, stone_x, stone_y, stone_x, stone_y + 6,
                               color=self._darken(c, 10) + (30,), width=1)

        # Roof / battlements
        roof_h = int(bh * 0.08)
        self.draw_rect(draw, x - bw//2 - 4, y - bh - roof_h, bw + 8, roof_h,
                       fill=self._darken(c, 15) + (220,))
        for i in range(bw // 12 + 1):
            bx = x - bw//2 - 4 + i * 12
            self.draw_rect(draw, bx, y - bh - roof_h - 5, 5, 5, fill=self._darken(c, 15) + (200,))

        # Windows with glow
        n_cols = max(bw // 35, 2)
        n_rows = max(bh // 30, 2)
        win_w = bw // n_cols - 6
        win_h = bh // n_rows - 6
        for row in range(n_rows):
            for col in range(n_cols):
                wx = x - bw//2 + col * (bw // n_cols) + 3
                wy = y - bh + row * (bh // n_rows) + 3
                # Window glow
                self.draw_circle(draw, wx + win_w//2, wy + win_h//2, win_w,
                                 fill=wc + (40,))
                # Window frame
                self.draw_rect(draw, wx, wy, win_w, win_h,
                               fill=wc + (200,), stroke=(40, 35, 30, 180), stroke_width=1)
                # Window cross
                self.draw_line(draw, wx + win_w//2, wy, wx + win_w//2, wy + win_h,
                               color=(40, 35, 30, 120), width=1)
                self.draw_line(draw, wx, wy + win_h//2, wx + win_w, wy + win_h//2,
                               color=(40, 35, 30, 120), width=1)
                # Glass reflection
                self.draw_line(draw, wx + 2, wy + 2, wx + win_w//2 - 1, wy + win_h//2 - 1,
                               color=(255, 255, 255, 60), width=1)

        # Door
        door_w = bw // 4
        door_h = int(bh * 0.25)
        self.draw_rect(draw, x - door_w//2, y - door_h, door_w, door_h,
                       fill=(60, 50, 40, 220), stroke=(40, 35, 30, 180), stroke_width=2)
        # Door arch
        self.draw_arc(draw, x, y - door_h, door_w//2, 0, 180,
                      color=(40, 35, 30, 180), width=2)

    def draw_flag(self, draw, x, y, size=1.0, color=(200, 50, 50)):
        """Draw a flag on a pole."""
        s = size
        c = tuple(color[:3])
        pole_h = int(55 * s)
        fw = int(50 * s)
        fh = int(25 * s)

        # Pole shadow
        self.draw_shadow_circle(draw, x, y, 3*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 40))

        # Pole
        self.draw_line(draw, x, y, x, y - pole_h, color=(60, 50, 40), width=int(3*s))

        # Flag body (waving effect)
        flag_pts = [(x + 2, y - pole_h),
                    (x + 2 + fw, y - pole_h - 3*s),
                    (x + 2 + fw + 5*s, y - pole_h - s),
                    (x + 2 + fw, y - pole_h + fh - 3*s),
                    (x + 2, y - pole_h + fh)]
        self.draw_shadow(draw, flag_pts, offset=(1, 2), blur_radius=2, color=(0, 0, 0, 30))
        self.fill_gradient_polygon(draw, flag_pts, self._lighten(c, 15), self._darken(c, 15))

        # Fold lines
        for i in range(2):
            t = (i + 1) / 3
            fx = x + 2 + t * fw
            self.draw_line(draw, fx, y - pole_h - 2*s, fx, y - pole_h + fh - 2*s,
                           color=self._darken(c, 20) + (80,), width=1)

    def draw_cannon(self, draw, x, y, size=1.0, color=(60, 60, 60)):
        """Draw a cannon with carriage."""
        s = size
        c = tuple(color[:3])
        bl = int(50 * s)
        bw = int(8 * s)

        # Carriage
        carriage_color = (80, 60, 40)
        self.draw_rect(draw, x - bl//4, y, int(bl*0.6), int(10*s),
                       fill=carriage_color + (220,), stroke=(50, 40, 30, 180), stroke_width=2)
        # Wheels
        for wx in [x - bl//4 + 4, x + bl//4 - 4]:
            self.draw_circle(draw, wx, y + 12*s, 6*s, fill=(60, 50, 40, 220), stroke=(40, 35, 30, 180), stroke_width=2)

        # Barrel
        self.draw_shadow(draw,
            [(x - bl//2, y - 3*s), (x + bl//2, y - 3*s),
             (x + bl//2, y + 3*s), (x - bl//2, y + 3*s)],
            offset=(2, 2), blur_radius=2, color=(0, 0, 0, 40))
        self.fill_gradient_rect(draw, x - bl//2, y - 3*s, bl, int(6*s),
                                self._darken(c, 5), self._lighten(c, 10))
        # Barrel ring
        self.draw_rect(draw, x + bl//4 - 2, y - 4*s, int(4*s), int(8*s),
                       fill=self._darken(c, 20) + (220,))
        # Muzzle
        self.draw_rect(draw, x + bl//2 - 2, y - 5*s, int(4*s), int(10*s),
                       fill=(40, 40, 40, 220))

    def draw_grass(self, draw, count=40, y_range=None, color=(50, 100, 40)):
        """Draw grass blades across an area."""
        c = tuple(color[:3])
        if y_range is None:
            y_range = (int(self.h * 0.65), self.h)
        for _ in range(count):
            gx = self.rng.randint(10, self.w - 10)
            gy = self.rng.randint(y_range[0], y_range[1])
            gh = self.rng.randint(4, 12)
            gc = self._harmonize(c, 20)
            self.draw_line(draw, gx, gy, gx + self.rng.randint(-1, 1), gy - gh,
                           color=gc + (self.rng.randint(100, 180)), width=self.rng.randint(1, 2))

    def draw_path(self, draw, x1, y1, x2, y2, color=(140, 120, 100), width=20):
        """Draw a winding path."""
        c = tuple(color[:3])
        n_pts = 20
        pts = []
        for i in range(n_pts + 1):
            t = i / n_pts
            px = x1 + (x2 - x1) * t + math.sin(t * math.pi * 3) * 15
            py = y1 + (y2 - y1) * t
            pts.append((px, py))
        # Draw path segments with width
        for i in range(len(pts) - 1):
            self.draw_line(draw, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                           color=c + (150,), width=width)
        # Edge
        for i in range(len(pts) - 1):
            self.draw_line(draw, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                           color=self._darken(c, 20) + (80,), width=2)

    def draw_animal(self, draw, x, y, size=1.0, color=(100, 80, 60)):
        """Draw a simple four-legged animal."""
        s = size
        c = tuple(color[:3])
        body_w, body_h = 25*s, 12*s
        # Shadow
        self.draw_shadow_circle(draw, x, y + body_h//2 + 2, body_w//2, offset=(2, 2), blur_radius=4, color=(0, 0, 0, 40))
        # Body
        self.draw_rect(draw, x-body_w//2, y-body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=2, rx=4)
        # Legs
        leg_color = self._darken(c, 15)
        for lx in [x-body_w//3, x+body_w//3]:
            self.draw_line(draw, lx, y-body_h//2, lx-3*s, y+5*s, color=leg_color, width=int(2.5*s))
            self.draw_line(draw, lx+2*s, y-body_h//2, lx+4*s, y+5*s, color=leg_color, width=int(2.5*s))
        # Head
        head_r = 7*s
        hx = x + body_w//2 + head_r
        self.draw_circle(draw, hx, y-body_h+2*s, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=2)
        # Eye
        self.draw_circle(draw, hx+2*s, y-body_h, 1.5*s, fill=(30, 25, 20, 200))
        # Ear
        self.draw_circle(draw, hx-2*s, y-body_h-4*s, 3*s, fill=self._darken(c, 10) + (200,))
        # Tail
        tx = x - body_w//2 - 3*s
        self.draw_line(draw, tx, y-body_h+3*s, tx-5*s, y-body_h-5*s, color=self._darken(c, 10), width=int(2*s))

    def draw_bird(self, draw, x, y, size=1.0, color=(60, 50, 40)):
        """Draw a bird in flight or perched."""
        s = size
        c = tuple(color[:3])
        # Body
        body_r = 5*s
        self.draw_circle(draw, x, y, body_r, fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=1)
        # Head
        self.draw_circle(draw, x+5*s, y-2*s, 3*s, fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=1)
        # Beak
        self.draw_polygon(draw, [(x+7*s, y-2*s), (x+10*s, y-2*s), (x+8*s, y-s)],
                         fill=(200, 180, 100, 200), stroke=(150, 130, 60, 180), stroke_width=1)
        # Wing (as a curve)
        self.draw_arc(draw, x-3*s, y-3*s, 8*s, 200, 340, color=self._darken(c, 15), width=int(2*s))
        # Tail
        self.draw_line(draw, x-6*s, y, x-10*s, y-3*s, color=self._darken(c, 10), width=int(1.5*s))
        self.draw_line(draw, x-6*s, y, x-10*s, y+2*s, color=self._darken(c, 10), width=int(1.5*s))
        # Eye
        self.draw_circle(draw, x+6*s, y-3*s, 1*s, fill=(20, 20, 20, 200))

    def draw_fish(self, draw, x, y, size=1.0, color=(200, 180, 100)):
        """Draw a fish."""
        s = size
        c = tuple(color[:3])
        # Body (ellipse-like)
        body_len = 20*s
        body_h = 8*s
        self.draw_shadow_circle(draw, x, y, body_len//2, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        pts = []
        for i in range(13):
            a = math.radians(i * 30)
            rx = x + math.cos(a) * body_len/2 * (0.5 + 0.5*abs(math.sin(a)))
            ry = y + math.sin(a) * body_h/2
            pts.append((rx, ry))
        self.draw_polygon(draw, pts, fill=c + (200,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        # Tail fin
        self.draw_polygon(draw, [(x-body_len//2, y), (x-body_len//2-8*s, y-6*s), (x-body_len//2-8*s, y+6*s)],
                         fill=c + (200,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        # Dorsal fin
        self.draw_polygon(draw, [(x-3*s, y-body_h//2), (x+3*s, y-body_h//2), (x, y-body_h//2-5*s)],
                         fill=self._lighten(c, 10) + (180,))
        # Eye
        self.draw_circle(draw, x+body_len//3, y-1*s, 2*s, fill=(30, 25, 20, 200))
        # Mouth
        self.draw_circle(draw, x+body_len//2-1, y, 1*s, fill=(150, 130, 80, 180))

    # ── New element generators ──────────────────────────────────

    def draw_book(self, draw, x, y, size=1.0, color=(140, 100, 60)):
        s = size; c = tuple(color[:3])
        w, h = 16*s, 12*s
        self.draw_shadow_circle(draw, x, y+h//2, w//2, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_polygon(draw, [(x-w//2, y+h//2), (x-w//2, y-h//2), (x, y-h//2+2*s), (x, y+h//2-2*s)], fill=c+(220,), stroke=self._darken(c,20)+(180,))
        self.draw_polygon(draw, [(x, y-h//2+2*s), (x+w//2, y-h//2), (x+w//2, y+h//2), (x, y+h//2-2*s)], fill=self._lighten(c,15)+(220,), stroke=self._darken(c,20)+(180,))
        self.draw_line(draw, x, y-h//2+2*s, x, y+h//2-2*s, color=(60,50,40,150), width=1)

    def draw_scroll(self, draw, x, y, size=1.0, color=(220, 200, 170)):
        s = size; c = tuple(color[:3])
        w, h = 18*s, 14*s
        self.draw_shadow_circle(draw, x, y+h//2, w//2, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=c+(220,), stroke=self._darken(c,15)+(180,), stroke_width=1, rx=2)
        self.draw_rect(draw, x-w//2, y-h//2, w, 3*s, fill=self._darken(c,10)+(200,), stroke=self._darken(c,20)+(180,), stroke_width=1, rx=1)
        self.draw_rect(draw, x-w//2, y+h//2-3*s, w, 3*s, fill=self._darken(c,10)+(200,), stroke=self._darken(c,20)+(180,), stroke_width=1, rx=1)

    def draw_compass(self, draw, x, y, size=1.0, color=(180, 150, 80)):
        s = size; c = tuple(color[:3])
        r = 10*s
        self.draw_shadow_circle(draw, x, y, r, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_circle(draw, x, y, r, fill=(240,230,200,200), stroke=(120,100,80), stroke_width=2)
        # 4 points
        for angle, name, col in [(0,"N",(200,60,60)), (90,"E",(60,60,60)), (180,"S",(60,60,60)), (270,"W",(60,60,60))]:
            rad = math.radians(angle)
            px = x + math.cos(rad)*r*0.6
            py = y + math.sin(rad)*r*0.6
            self.draw_polygon(draw, [(x, y), (x+math.cos(rad+0.15)*r*0.4, y+math.sin(rad+0.15)*r*0.4), (px, py), (x+math.cos(rad-0.15)*r*0.4, y+math.sin(rad-0.15)*r*0.4)], fill=col+(200,))
            self.draw_text(draw, px, py-4*s if angle==0 else py+2*s if angle==180 else px+2*s, name, font_size=int(8*s), color=(40,35,30), align="center")

    def draw_globe(self, draw, x, y, size=1.0, color=(100, 150, 200)):
        s = size; c = tuple(color[:3])
        r = 10*s
        self.draw_shadow_circle(draw, x, y+r, r, offset=(3,2), blur_radius=4, color=(0,0,0,40))
        self.draw_circle(draw, x, y, r, fill=c+(200,), stroke=self._darken(c,20)+(180,), stroke_width=2)
        # Continents blobs
        for ox, oy in [(0.3,0.2), (-0.2,0.1), (0.1,-0.3), (-0.3,-0.1)]:
            self.draw_circle(draw, int(x+ox*r), int(y+oy*r), int(r*0.25), fill=(60,120,80,120))
        # Stand
        self.draw_rect(draw, x-2*s, y+r, 4*s, 6*s, fill=(80,70,60,200), stroke=(50,45,40), stroke_width=1)
        self.draw_rect(draw, x-5*s, y+6*s, 10*s, 2*s, fill=(80,70,60,200), stroke=(50,45,40), stroke_width=1)

    def draw_quill(self, draw, x, y, size=1.0, color=(220, 200, 180)):
        s = size; c = tuple(color[:3])
        self.draw_line(draw, x, y, x-3*s, y-15*s, color=c+(200,), width=int(2*s))
        self.draw_line(draw, x, y, x+2*s, y-14*s, color=c+(180,), width=int(1.5*s))
        self.draw_line(draw, x, y, x-1*s, y-16*s, color=(255,255,255,80), width=int(1*s))
        # Nib
        self.draw_polygon(draw, [(x-1*s, y), (x+1*s, y), (x, y+2*s)], fill=(60,50,40,200))

    def draw_lightbulb(self, draw, x, y, size=1.0, color=(255, 220, 50)):
        s = size; c = tuple(color[:3])
        r = 6*s
        self.draw_shadow_circle(draw, x, y, r, offset=(2,2), blur_radius=4, color=(0,0,0,30))
        # Bulb
        self.draw_circle(draw, x, y-r, r, fill=c+(200,), stroke=(180,150,30,180), stroke_width=2)
        # Glow
        self.draw_circle(draw, x, y-r, r*1.3, fill=(255,220,50,30))
        # Base
        self.draw_rect(draw, x-2*s, y-r, 4*s, 3*s, fill=(100,90,80,200), stroke=(60,55,50), stroke_width=1)

    def draw_fire(self, draw, x, y, size=1.0, color=(220, 120, 40)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y+2*s, 6*s, offset=(2,2), blur_radius=4, color=(0,0,0,30))
        # Flame layers
        for i, (r, col) in enumerate([(5*s, (255,200,50,120)), (4*s, c+(200,)), (2.5*s, (255,150,50,220)), (1.5*s, (255,200,80,200))]):
            pts = [(x, y-r)]
            for a in range(0, 360, 30):
                rr = r * (0.6 + 0.4*abs(math.sin(math.radians(a*1.5))))
                pts.append((x+math.cos(math.radians(a))*rr, y-math.sin(math.radians(a))*rr))
            self.draw_polygon(draw, pts, fill=col, stroke=None)
        # Logs
        self.draw_rect(draw, x-5*s, y+3*s, 3*s, 2*s, fill=(80,60,40,200), stroke=(50,40,30), stroke_width=1)
        self.draw_rect(draw, x+2*s, y+3*s, 3*s, 2*s, fill=(100,70,50,200), stroke=(50,40,30), stroke_width=1)

    def draw_clock(self, draw, x, y, size=1.0, color=(200, 190, 170)):
        s = size; c = tuple(color[:3])
        r = 8*s
        self.draw_shadow_circle(draw, x, y, r, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_circle(draw, x, y, r, fill=c+(220,), stroke=self._darken(c,20)+(180,), stroke_width=2)
        # Hour marks
        for a in range(0, 360, 30):
            rad = math.radians(a)
            self.draw_line(draw, x+math.cos(rad)*r*0.75, y+math.sin(rad)*r*0.75, x+math.cos(rad)*r*0.9, y+math.sin(rad)*r*0.9, color=(60,50,40), width=1)
        # Hands
        self.draw_line(draw, x, y, x+math.cos(math.radians(210))*r*0.5, y+math.sin(math.radians(210))*r*0.5, color=(40,35,30), width=int(2*s))
        self.draw_line(draw, x, y, x+math.cos(math.radians(60))*r*0.7, y+math.sin(math.radians(60))*r*0.7, color=(40,35,30), width=int(1.5*s))
        self.draw_circle(draw, x, y, 1.5*s, fill=(40,35,30,200))

    def draw_gear(self, draw, x, y, size=1.0, color=(160, 150, 140)):
        s = size; c = tuple(color[:3])
        r = 7*s
        self.draw_shadow_circle(draw, x, y, r, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        pts = []
        for i in range(24):
            a = math.radians(i * 15)
            rr = r * (1.0 if i % 2 == 0 else 0.7)
            pts.append((x + math.cos(a)*rr, y + math.sin(a)*rr))
        self.draw_polygon(draw, pts, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        self.draw_circle(draw, x, y, r*0.4, fill=(100,90,80,200))
        self.draw_circle(draw, x, y, r*0.15, fill=(40,35,30,200))

    def draw_skull(self, draw, x, y, size=1.0, color=(220, 210, 190)):
        s = size; c = tuple(color[:3])
        r = 5*s
        self.draw_shadow_circle(draw, x, y, r, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_circle(draw, x, y, r, fill=c+(220,), stroke=self._darken(c,20)+(150,), stroke_width=2)
        # Eyes
        self.draw_circle(draw, x-2*s, y-1*s, 1.5*s, fill=(30,25,20,200))
        self.draw_circle(draw, x+2*s, y-1*s, 1.5*s, fill=(30,25,20,200))
        # Nose
        self.draw_polygon(draw, [(x-0.5*s, y+1*s), (x+0.5*s, y+1*s), (x, y+2.5*s)], fill=(40,35,30,200))
        # Mouth
        for i in range(4):
            self.draw_line(draw, x-3*s+i*2*s, y+3*s, x-2*s+i*2*s, y+3*s, color=(40,35,30), width=1)

    def draw_crown(self, draw, x, y, size=1.0, color=(220, 180, 50)):
        s = size; c = tuple(color[:3])
        w, h = 12*s, 7*s
        self.draw_shadow_circle(draw, x, y+h//2, w//2, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_polygon(draw, [(x-w//2, y+h//2), (x-w//2, y), (x-w//3, y-h//2), (x, y-1*s), (x+w//3, y-h//2), (x+w//2, y), (x+w//2, y+h//2)], fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        self.draw_circle(draw, x-w//3, y-h//2, 1.5*s, fill=(255,50,50,200))
        self.draw_circle(draw, x, y-1*s, 1.5*s, fill=(50,150,255,200))
        self.draw_circle(draw, x+w//3, y-h//2, 1.5*s, fill=(50,200,50,200))

    def draw_key(self, draw, x, y, size=1.0, color=(180, 160, 100)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y, 4*s, offset=(2,2), blur_radius=2, color=(0,0,0,20))
        self.draw_circle(draw, x, y-4*s, 4*s, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=2)
        self.draw_line(draw, x, y, x, y+10*s, color=c+(200,), width=int(3*s))
        self.draw_line(draw, x, y+8*s, x+4*s, y+12*s, color=c+(200,), width=int(2*s))
        self.draw_line(draw, x, y+6*s, x-3*s, y+9*s, color=c+(200,), width=int(2*s))

    def draw_lamp(self, draw, x, y, size=1.0, color=(180, 160, 120)):
        s = size; c = tuple(color[:3])
        # Base
        self.draw_rect(draw, x-3*s, y+4*s, 6*s, 2*s, fill=c+(200,), stroke=self._darken(c,20), stroke_width=1)
        # Stem
        self.draw_line(draw, x, y+4*s, x, y-4*s, color=c, width=int(2*s))
        # Lamp body
        self.draw_polygon(draw, [(x-4*s, y-4*s), (x+4*s, y-4*s), (x+2*s, y+1*s), (x-2*s, y+1*s)], fill=c+(200,), stroke=self._darken(c,20), stroke_width=1)
        # Flame
        self.draw_circle(draw, x, y-5*s, 2*s, fill=(255,200,50,200))
        self.draw_circle(draw, x, y-5*s, 3*s, fill=(255,200,50,60))

    def draw_hand(self, draw, x, y, size=1.0, color=(235, 200, 175)):
        s = size; c = tuple(color[:3])
        # Palm
        self.draw_circle(draw, x, y, 3*s, fill=c+(220,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        # Fingers
        for dx, dy, a in [(-2.5*s, -3*s, 0.3), (-1*s, -4*s, 0), (1*s, -4*s, 0), (2.5*s, -3*s, -0.3)]:
            self.draw_line(draw, x+dx*0.5, y+dy*0.5, x+dx, y+dy, color=c+(200,), width=int(2*s))
        # Thumb
        self.draw_line(draw, x-2*s, y+1*s, x-4*s, y+3*s, color=c+(200,), width=int(2*s))

    def draw_eye(self, draw, x, y, size=1.0, color=(255, 250, 240)):
        s = size; c = tuple(color[:3])
        w, h = 8*s, 5*s
        self.draw_circle(draw, x, y, h//2, fill=c+(220,), stroke=(60,50,40), stroke_width=2)
        # Iris
        self.draw_circle(draw, x, y, h//3, fill=(80,120,180,200))
        # Pupil
        self.draw_circle(draw, x, y, 1.5*s, fill=(20,20,20,200))
        # Highlight
        self.draw_circle(draw, x+1*s, y-1*s, 0.8*s, fill=(255,255,255,150))

    def draw_cross(self, draw, x, y, size=1.0, color=(120, 80, 60)):
        s = size; c = tuple(color[:3])
        w, h = 3*s, 12*s
        self.draw_shadow_circle(draw, x, y+h//2, w//2, offset=(2,2), blur_radius=2, color=(0,0,0,20))
        self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        self.draw_rect(draw, x-w, y-h//4, w*2, h//3, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)

    def draw_coin(self, draw, x, y, size=1.0, color=(220, 190, 60)):
        s = size; c = tuple(color[:3])
        r = 4*s
        self.draw_circle(draw, x+1*s, y+1*s, r, fill=(0,0,0,30))
        self.draw_circle(draw, x, y, r, fill=c+(220,), stroke=self._darken(c,20)+(150,), stroke_width=2)
        self.draw_circle(draw, x, y, r*0.7, fill=self._lighten(c,10)+(150,))

    def draw_telescope(self, draw, x, y, size=1.0, color=(120, 80, 60)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y+2*s, 3*s, offset=(2,2), blur_radius=2, color=(0,0,0,20))
        # Tube
        self.draw_line(draw, x, y, x+8*s, y-4*s, color=c+(200,), width=int(3*s))
        self.draw_line(draw, x, y, x+8*s, y-4*s, color=self._lighten(c,10)+(150,), width=int(1*s))
        # Lens
        self.draw_circle(draw, x+9*s, y-5*s, 2*s, fill=(200,220,255,150), stroke=(60,60,80), stroke_width=1)

    def draw_question_mark(self, draw, x, y, size=1.0, color=(180, 60, 60)):
        s = size; c = tuple(color[:3])
        self.draw_text(draw, x, y, "?", font_size=int(30*s), color=c+(220,), align="center")

    def draw_printing_press(self, draw, x, y, size=1.0, color=(100, 80, 60)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y+5*s, 5*s, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        # Base
        self.draw_rect(draw, x-6*s, y+3*s, 12*s, 3*s, fill=c+(200,), stroke=self._darken(c,20), stroke_width=1)
        # Pillars
        self.draw_rect(draw, x-5*s, y-5*s, 2*s, 8*s, fill=self._darken(c,15)+(200,), stroke=self._darken(c,30), stroke_width=1)
        self.draw_rect(draw, x+3*s, y-5*s, 2*s, 8*s, fill=self._darken(c,15)+(200,), stroke=self._darken(c,30), stroke_width=1)
        # Top beam
        self.draw_rect(draw, x-6*s, y-6*s, 12*s, 2*s, fill=self._darken(c,10)+(200,), stroke=self._darken(c,20), stroke_width=1)
        # Screw
        self.draw_line(draw, x, y-6*s, x, y-9*s, color=(80,60,40), width=int(2*s))
        # Paper
        self.draw_rect(draw, x-3*s, y-1*s, 6*s, 4*s, fill=(240,235,220,200), stroke=(120,100,80), stroke_width=1)

    def draw_map(self, draw, x, y, size=1.0, color=(220, 200, 160)):
        s = size; c = tuple(color[:3])
        w, h = 16*s, 12*s
        self.draw_shadow_circle(draw, x, y+h//2, w//2, offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=c+(220,), stroke=self._darken(c,15)+(150,), stroke_width=2, rx=2)
        # Folds
        self.draw_line(draw, x-w//2, y, x+w//2, y, color=(180,165,130,100), width=1)
        self.draw_line(draw, x, y-h//2, x, y+h//2, color=(180,165,130,100), width=1)
        # Continent blobs
        for ox, oy in [(0.2,0.15), (-0.15,0.1), (0.05,-0.2)]:
            self.draw_circle(draw, int(x+ox*w), int(y+oy*h), int(2*s), fill=(120,160,100,80))

    # ── Main scene renderer ────────────────────────────────────

    def render_scene(self, desc: dict) -> Image.Image:
        """Render a full scene from a structured description dict."""
        self.desc = desc
        canvas = self.create_canvas((255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas, "RGBA")

        # ── Background ──
        bg = desc.get("bg", desc.get("background", {}))
        bg_type = bg.get("type", "gradient") if isinstance(bg, dict) else "gradient"

        if isinstance(bg, dict):
            self._render_background(draw, bg)

        # ── Atmosphere particles ──
        atmos = desc.get("atmosphere", {})
        if atmos.get("particles") == "stars" or bg_type == "night":
            self.draw_stars(draw, count=atmos.get("star_count", 60))

        # ── Elements ──
        for elem in desc.get("elements", []):
            self._render_element(draw, elem)

        # ── Post-processing ──
        canvas = self._post_process(canvas, desc.get("mood", ""), desc.get("style", {}))

        return canvas.convert("RGB")

    def _render_background(self, draw, bg: dict):
        """Render background from description."""
        bg_type = bg.get("type", "gradient")

        if bg_type == "gradient":
            colors = []
            for i, c in enumerate(bg.get("colors", [(200, 210, 230), (140, 160, 200)])):
                pos = i / max(len(bg.get("colors", [1, 2])) - 1, 1)
                colors.append((pos, self._tc(c, (200, 210, 230))))
            if len(colors) < 2:
                colors.append((1.0, self._tc(bg.get("colors", [(200, 210, 230)])[0], (200, 210, 230))))
            self.bg_gradient(draw, colors, bg.get("direction", "vertical"))

            # Ground
            if bg.get("ground_color"):
                horizon = bg.get("horizon", 0.6)
                gh = int(self.h * horizon)
                gc = self._tc(bg["ground_color"], (60, 90, 50))
                for y in range(gh, self.h):
                    t = (y - gh) / max(self.h - gh, 1)
                    r = int(gc[0] + t * 15)
                    g = int(gc[1] + t * 10)
                    b = int(gc[2] - t * 5)
                    draw.line([(0, y), (self.w, y)], fill=(r, g, b))

        elif bg_type == "night":
            colors = [(0, (5, 3, 20)), (0.4, (10, 8, 30)), (1, (30, 25, 60))]
            self.bg_gradient(draw, colors)
            if bg.get("ground_color"):
                horizon = bg.get("horizon", 0.6)
                gh = int(self.h * horizon)
                gc = self._tc(bg["ground_color"], (15, 20, 30))
                draw.rectangle([0, gh, self.w, self.h], fill=gc)

        elif bg_type == "ocean":
            colors = [(0, self._tc(bg.get("sky_color"), (180, 210, 240))),
                      (0.45, self._tc(bg.get("horizon_color"), (120, 170, 220))),
                      (0.5, self._tc(bg.get("horizon_color"), (100, 150, 200)))]
            self.bg_gradient(draw, colors)
            horizon = bg.get("horizon", 0.55)
            gh = int(self.h * horizon)
            water_color = self._tc(bg.get("water_color"), (30, 80, 160))
            for y in range(gh, self.h):
                t = (y - gh) / max(self.h - gh, 1)
                r = int(water_color[0] + t * 10)
                g = int(water_color[1] + t * 15)
                b = int(water_color[2] + t * 20)
                draw.line([(0, y), (self.w, y)], fill=(r, g, b))

            # Horizon haze
            haze_h = 8
            for i in range(haze_h):
                t = i / haze_h
                draw.line([(0, gh - haze_h + i), (self.w, gh - haze_h + i)],
                         fill=(200, 220, 240, int(30 * (1 - t))))

        elif bg_type == "indoor":
            colors = [(0, self._tc(bg.get("wall_color"), (220, 210, 190))),
                      (1, self._tc(bg.get("floor_color"), (180, 160, 140)))]
            self.bg_gradient(draw, colors)

        elif bg_type == "solid":
            c = self._tc(bg.get("color"), (245, 245, 240))
            draw.rectangle([0, 0, self.w, self.h], fill=c)

        elif bg_type == "sunset":
            colors = [(0, (220, 100, 70)), (0.2, (200, 120, 90)),
                      (0.4, (160, 80, 100)), (0.6, (80, 50, 80)),
                      (1, self._tc(bg.get("ground_color"), (40, 50, 30)))]
            self.bg_gradient(draw, colors)

    def _render_element(self, draw, elem: dict):
        """Render a single element from its description."""
        etype = elem.get("type", "").lower()
        x = int(elem.get("x", 0.5) * self.w)
        y = int(elem.get("y", 0.5) * self.h)
        s = elem.get("scale", elem.get("size", 1.0))

        # Colors
        fill = elem.get("fill", elem.get("fill_color", elem.get("color", None)))
        stroke = elem.get("stroke", elem.get("stroke_color", elem.get("line_color", None)))
        if fill and isinstance(fill, list): fill = tuple(fill)
        if stroke and isinstance(stroke, list): stroke = tuple(stroke)
        opacity = elem.get("opacity", 255)

        def _tc(c):
            if c is None: return None
            return tuple(c[:3]) if isinstance(c, (list, tuple)) else c

        fill = _tc(fill)
        stroke = _tc(stroke)

        if etype in ("mountain", "mountains"):
            w = int(elem.get("width", 0.3) * self.w)
            h = int(elem.get("height", 0.25) * self.h)
            c = fill or (100, 110, 140)
            self.draw_mountains(draw, x, y, w, h, tuple(c[:3]), snow=elem.get("snow", True))

        elif etype == "tree":
            style = elem.get("style", elem.get("tree_style", "round"))
            c = fill or (50, 120, 50)
            self.draw_tree(draw, x, y, s, style, c)

        elif etype == "cloud":
            c = fill or (255, 255, 255)
            self.draw_cloud(draw, x, y, s, c)

        elif etype == "water":
            w = int(elem.get("width", 0.8) * self.w)
            h = int(elem.get("height", 0.2) * self.h)
            c = fill or (60, 120, 200)
            self.draw_water(draw, x, y, w, h, c)

        elif etype in ("human", "person", "man", "woman", "figure"):
            c = fill or (80, 60, 120)
            skin = _tc(elem.get("skin_color", (235, 200, 175))) or (235, 200, 175)
            self.draw_human(draw, x, y, s, c, skin)

        elif etype == "house":
            c = fill or (180, 150, 120)
            roof = _tc(elem.get("roof_color", (150, 50, 40))) or (150, 50, 40)
            self.draw_house(draw, x, y, s, c, roof)

        elif etype == "hill":
            w = int(elem.get("width", 0.4) * self.w)
            h = int(elem.get("height", 0.15) * self.h)
            c = fill or (60, 120, 60)
            self.draw_hill(draw, x, y, w, h, c)

        elif etype == "sun":
            r = int(elem.get("radius", 30) * s)
            c = fill or (255, 220, 50)
            self.draw_sun(draw, x, y, max(r, 15), c)

        elif etype == "moon":
            r = int(elem.get("radius", 25) * s)
            self.draw_moon(draw, x, y, max(r, 15))

        elif etype == "star":
            r = elem.get("radius", elem.get("r", 2))
            c = fill or (255, 255, 200)
            self.draw_circle(draw, x, y, r, fill=c + (opacity,))
            if r > 1.5:
                self.draw_circle(draw, x, y, r * 3, fill=c + (20,))

        elif etype == "circle":
            r = int(elem.get("radius", 20) * (elem.get("r_scale", 1)))
            stroke_color = stroke or (40, 35, 30)
            fill_color = fill
            self.draw_circle(draw, x, y, max(r, 5), fill=fill_color, stroke=stroke_color,
                           stroke_width=elem.get("stroke_width", 2), opacity=opacity)

        elif etype == "rect" or etype == "rectangle":
            w = int(elem.get("width", 60) * (elem.get("w_scale", 1)))
            h = int(elem.get("height", 60) * (elem.get("h_scale", 1)))
            rx = elem.get("rx", 0)
            self.draw_rect(draw, x-w//2, y-h//2, w, h,
                          fill=fill, stroke=stroke or (40, 35, 30),
                          stroke_width=elem.get("stroke_width", 2), rx=rx, opacity=opacity)

        elif etype == "polygon":
            pts = elem.get("points", [])
            if pts:
                pxs = [(int(p[0]*self.w), int(p[1]*self.h)) for p in pts]
                self.draw_polygon(draw, pxs, fill=fill, stroke=stroke or (40, 35, 30),
                                stroke_width=elem.get("stroke_width", 2), opacity=opacity)

        elif etype == "line":
            x2 = elem.get("x2", 0.7)
            y2 = elem.get("y2", 0.7)
            if isinstance(x2, float) and x2 <= 1.0: x2 = int(x2 * self.w)
            if isinstance(y2, float) and y2 <= 1.0: y2 = int(y2 * self.h)
            self.draw_line(draw, x, y, int(x2), int(y2), color=stroke or (40, 35, 30),
                          width=elem.get("stroke_width", 2), opacity=opacity)

        elif etype == "text":
            text = elem.get("text", elem.get("label", ""))
            fs = elem.get("font_size", elem.get("size", 28))
            c = fill or (40, 35, 30)
            align = elem.get("align", "center")
            self.draw_text(draw, x, y, text, font_size=fs, color=c, align=align, opacity=opacity)

        elif etype == "label" or etype == "text_box":
            text = elem.get("text", elem.get("label", ""))
            fs = elem.get("font_size", elem.get("size", 20))
            tc = fill or (40, 35, 30)
            bc = _tc(elem.get("bg_color")) or (255, 250, 240)
            border = _tc(elem.get("border_color")) or _tc(stroke) or (40, 35, 30)
            self.draw_text_box(draw, x, y, text, font_size=fs, text_color=tc, bg_color=bc, border_color=border)

        elif etype == "arrow":
            x2 = elem.get("x2", 0.7)
            y2 = elem.get("y2", 0.7)
            if isinstance(x2, float) and x2 <= 1.0: x2 = int(x2 * self.w)
            if isinstance(y2, float) and y2 <= 1.0: y2 = int(y2 * self.h)
            c = stroke or (40, 35, 30)
            w = elem.get("stroke_width", 2)
            self.draw_line(draw, x, y, int(x2), int(y2), color=c, width=w, opacity=opacity)
            angle = math.atan2(int(y2)-y, int(x2)-x)
            hl = 12 * elem.get("head_scale", 1.0)
            ax = int(x2) - math.cos(angle) * hl
            ay = int(y2) - math.sin(angle) * hl
            self.draw_polygon(draw,
                [(int(x2), int(y2)),
                 (int(ax + math.sin(angle)*hl//2), int(ay - math.cos(angle)*hl//2)),
                 (int(ax - math.sin(angle)*hl//2), int(ay + math.cos(angle)*hl//2))],
                fill=c + (opacity,))

        elif etype == "x_mark":
            c = fill or (180, 40, 40)
            l = 12 * s
            self.draw_line(draw, x-l, y-l, x+l, y+l, color=c, width=int(3*s+1), opacity=opacity)
            self.draw_line(draw, x+l, y-l, x-l, y+l, color=c, width=int(3*s+1), opacity=opacity)

        elif etype == "ship":
            self.draw_ship(draw, x, y, s, fill or (80, 60, 40), _tc(elem.get("sail_color", (220, 210, 190))))

        elif etype == "building":
            bw = int(elem.get("width", 0.12) * self.w)
            bh = int(elem.get("height", 0.25) * self.h)
            c = fill or (120, 100, 80)
            wc = _tc(elem.get("window_color", (255, 220, 100))) or (255, 220, 100)
            self.draw_building(draw, x, y, bw, bh, c, wc)

        elif etype == "cannon":
            c = fill or (60, 60, 60)
            self.draw_cannon(draw, x, y, s, c)

        elif etype == "flag":
            c = fill or (200, 50, 50)
            self.draw_flag(draw, x, y, s, c)

        elif etype == "animal":
            c = fill or (100, 80, 60)
            self.draw_animal(draw, x, y, s, c)

        elif etype == "bird":
            c = fill or (60, 50, 40)
            self.draw_bird(draw, x, y, s, c)

        elif etype == "fish":
            c = fill or (200, 180, 100)
            self.draw_fish(draw, x, y, s, c)

        elif etype == "grass":
            count = elem.get("count", 40)
            c = fill or (50, 100, 40)
            y_range = elem.get("y_range", None)
            self.draw_grass(draw, count, y_range, c)

        elif etype == "path":
            x2 = elem.get("x2", 0.8)
            y2 = elem.get("y2", 1.0)
            if isinstance(x2, float) and x2 <= 1.0: x2 = int(x2 * self.w)
            if isinstance(y2, float) and y2 <= 1.0: y2 = int(y2 * self.h)
            c = fill or (140, 120, 100)
            w = elem.get("width", 20)
            self.draw_path(draw, x, y, int(x2), int(y2), c, w)

        elif etype == "book":
            self.draw_book(draw, x, y, s, fill or (140, 100, 60))
        elif etype == "scroll":
            self.draw_scroll(draw, x, y, s, fill or (220, 200, 170))
        elif etype == "compass":
            self.draw_compass(draw, x, y, s, fill or (180, 150, 80))
        elif etype == "globe":
            self.draw_globe(draw, x, y, s, fill or (100, 150, 200))
        elif etype == "quill":
            self.draw_quill(draw, x, y, s, fill or (220, 200, 180))
        elif etype == "lightbulb":
            self.draw_lightbulb(draw, x, y, s, fill or (255, 220, 50))
        elif etype == "fire":
            self.draw_fire(draw, x, y, s, fill or (220, 120, 40))
        elif etype == "clock":
            self.draw_clock(draw, x, y, s, fill or (200, 190, 170))
        elif etype == "gear":
            self.draw_gear(draw, x, y, s, fill or (160, 150, 140))
        elif etype == "skull":
            self.draw_skull(draw, x, y, s, fill or (220, 210, 190))
        elif etype == "crown":
            self.draw_crown(draw, x, y, s, fill or (220, 180, 50))
        elif etype == "key":
            self.draw_key(draw, x, y, s, fill or (180, 160, 100))
        elif etype == "lamp":
            self.draw_lamp(draw, x, y, s, fill or (180, 160, 120))
        elif etype == "hand":
            self.draw_hand(draw, x, y, s, fill or (235, 200, 175))
        elif etype == "eye":
            self.draw_eye(draw, x, y, s, fill or (255, 250, 240))
        elif etype == "cross":
            self.draw_cross(draw, x, y, s, fill or (120, 80, 60))
        elif etype == "coin":
            self.draw_coin(draw, x, y, s, fill or (220, 190, 60))
        elif etype == "telescope":
            self.draw_telescope(draw, x, y, s, fill or (120, 80, 60))
        elif etype == "question_mark":
            self.draw_question_mark(draw, x, y, s, fill or (180, 60, 60))
        elif etype == "printing_press":
            self.draw_printing_press(draw, x, y, s, fill or (100, 80, 60))
        elif etype == "map":
            self.draw_map(draw, x, y, s, fill or (220, 200, 160))

        else:
            # Unknown type — draw with label
            if fill:
                self.draw_circle(draw, x, y, 10*s, fill=fill + (180,))
            else:
                self.draw_circle(draw, x, y, 10*s, stroke=(40, 35, 30), stroke_width=2)
            label = elem.get("label", elem.get("text", etype))
            if label:
                self.draw_text(draw, x, y+15*s, label, font_size=14, color=(100, 90, 80), align="center")

    def _post_process(self, canvas: Image.Image, mood: str = "", style: dict = {}) -> Image.Image:
        """Apply final touches: rectangular vignette, grain, lighting."""
        grain_intensity = style.get("grain", 0.12)
        draw = ImageDraw.Draw(canvas, "RGBA")

        # ── Rectangular vignette (darkens edges, full-frame) ──
        vignette_strength = style.get("vignette", 0.4)
        if vignette_strength > 0:
            arr = np.array(canvas, dtype=np.float32)
            y_vals = np.arange(self.h, dtype=np.float32)
            x_vals = np.arange(self.w, dtype=np.float32)
            dy = np.abs(y_vals - self.h / 2)[:, None] / (self.h / 2)
            dx = np.abs(x_vals - self.w / 2)[None, :] / (self.w / 2)
            d = np.maximum(dx, dy)
            mask = 1.0 - np.clip((d - 0.3) / 0.7, 0, 1) * vignette_strength
            mask = np.clip(mask, 0, 1)
            arr[:, :, 0] *= mask
            arr[:, :, 1] *= mask
            arr[:, :, 2] *= mask
            canvas = Image.fromarray(arr.astype(np.uint8))

        # ── Paper grain ──
        if grain_intensity > 0:
            draw = ImageDraw.Draw(canvas, "RGBA")
            for _ in range(int(3000 * grain_intensity)):
                gx = self.rng.randint(0, self.w-1)
                gy = self.rng.randint(0, self.h-1)
                v = self.rng.randint(-6, 4)
                draw.point((gx, gy), fill=(v, v, v, 15))

        # ── Atmospheric haze ──
        if mood == "mysterious" or mood == "somber":
            fog_alpha = 25 if mood == "mysterious" else 40
            draw.rectangle([0, 0, self.w, self.h], fill=(200, 210, 220, fog_alpha))

        # Slight smoothing
        canvas = canvas.filter(ImageFilter.SMOOTH_MORE)

        return canvas


# ── Convenience function ──────────────────────────────────────

def generate_sketch(prompt: str, scene_desc: dict = None, width=W, height=H, seed=None) -> Image.Image:
    """Generate a sketch from a text prompt and optional structured description.

    If scene_desc is None, uses an LLM to generate one from the prompt.
    """
    gen = SketchGenerator(width, height, seed)

    if scene_desc is None:
        scene_desc = llm_generate_scene(prompt)

    return gen.render_scene(scene_desc)


def llm_generate_scene(prompt: str) -> dict:
    """Use LLM to generate a structured scene description from a text prompt.

    Returns a dict describing background, elements, mood, etc.
    """
    from src.script_generator import _generate

    system = """You are a visual artist and scene composer. You create beautiful, full-color illustrations.
You output ONLY valid JSON. You describe every visual detail with specific colors and positions."""

    user_prompt = f"""Create a beautiful full-color illustration for: "{prompt}"

Output a JSON scene description with this exact structure:
{{
  "bg": {{
    "type": "gradient|night|ocean|indoor|solid|sunset",
    "colors": [[R,G,B], [R,G,B], ...],
    "horizon": 0.0-1.0 or null,
    "ground_color": [R,G,B] or null
  }},
  "elements": [
    {{
      "type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|circle|rect|polygon|line|text|label|ship|building|cannon|flag|x_mark|arrow|grass|path",
      "x": 0.0-1.0,
      "y": 0.0-1.0,
      "scale": 0.5-2.0 or null,
      "fill": [R,G,B] or null,
      "stroke": [R,G,B] or null,
      "text": "text content" or null,
      "font_size": 14-60 or null,
      "width": 0.0-1.0 or null,
      "height": 0.0-1.0 or null,
      "radius": 0.0-1.0 or null,
      "label": "what this is" or null
    }}
  ],
  "atmosphere": {{
    "particles": "stars|rain|snow|none",
    "fog": true|false
  }},
  "mood": "peaceful|dramatic|somber|hopeful|epic|mysterious"
}}

RULES:
- Choose background type and colors that match the scene's mood and setting
- Place 3-8 elements to create a complete, beautiful composition
- Use rich, harmonious colors (provide exact [R,G,B] values)
- For text elements, use "text" type with "text" field and "font_size"
- For mountains: include "snow": true/false
- For trees: include "tree_style": "round|pine|palm"
- For ships: include "sail_color": [R,G,B]
- For buildings: include "window_color": [R,G,B]
- x,y coordinates are 0-1 on a portrait canvas (720x1280)

Respond with ONLY the JSON object, no other text."""

    fallback = {
        "bg": {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]},
        "elements": [
            {"type": "hill", "x": 0.3, "y": 0.7, "width": 0.5, "height": 0.15, "fill": [60, 120, 60]},
            {"type": "tree", "x": 0.3, "y": 0.72, "scale": 0.8, "tree_style": "round", "fill": [50, 120, 50]},
            {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 0.8},
            {"type": "text", "x": 0.5, "y": 0.08, "text": prompt.upper(), "font_size": 32},
        ],
        "atmosphere": {"particles": "none", "fog": False},
        "mood": "peaceful"
    }

    try:
        raw = _generate(user_prompt, temperature=0.8, max_tokens=3000, system=system)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        if "bg" in data or "elements" in data:
            return data
    except Exception as e:
        print(f"  LLM scene generation error: {e}")

    return fallback
