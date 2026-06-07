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

    def draw_human(self, draw, x, y, size=1.0, color=(80, 60, 120), skin_color=(235, 200, 175), gender="neutral"):
        """Draw a human figure with distinct man/woman/child/neutral silhouettes."""
        s = size
        skin = tuple(skin_color[:3])
        cloth = tuple(color[:3])
        is_child = (gender == "child")
        is_woman = (gender == "woman")
        is_man = (gender == "man")
        is_neutral = (not is_child and not is_woman and not is_man)
        bs = s * (0.65 if is_child else 1.0)

        # ── Proportions ──
        head_r = (9.5 if is_child else 10 if is_woman else 11.5) * bs
        neck_y = y - (36 if is_child else 38) * bs
        body_h = (28 if is_child else 36) * bs
        torso_top = y - body_h

        # ── Shadow ──
        self.draw_shadow_circle(draw, x, y + 2*bs, head_r * 1.2, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 35))

        # ── Legs ──
        if is_woman:
            # Legs closer together
            leg_color = self._lighten(cloth, 10)
            for side, lx in [(-1, x-2*bs), (1, x+2*bs)]:
                leg_pts = [(lx, y+6*bs), (lx + side*2*bs, y+30*bs),
                           (lx + side*1*bs, y+32*bs), (lx-1, y+6*bs)]
                self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                self.fill_gradient_polygon(draw, leg_pts, leg_color, self._darken(leg_color, 15),
                                           stroke=(40, 35, 30, 150), stroke_width=1)
                # Heel hint
                self.draw_polygon(draw, [(lx + side*2*bs, y+30*bs), (lx + side*4*bs, y+32*bs),
                                        (lx + side*3*bs, y+33*bs), (lx + side*1*bs, y+31*bs)],
                                 fill=(45, 35, 30, 220))
        else:
            leg_color = self._darken(cloth, 20)
            spread = (5 if is_man else 4) * bs
            for side, lx in [(-1, x-spread), (1, x+spread)]:
                leg_len = (28 if is_child else 30) * bs
                leg_pts = [(lx, y+4*bs), (lx + side*4*bs, y+leg_len),
                           (lx + side*3*bs, y+leg_len+2*bs), (lx-1, y+4*bs)]
                self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                self.fill_gradient_polygon(draw, leg_pts, leg_color, self._darken(leg_color, 15),
                                           stroke=(40, 35, 30, 150), stroke_width=1)
                shoe = [(lx + side*4*bs, y+leg_len-2*bs), (lx + side*7*bs, y+leg_len+2*bs),
                        (lx + side*5*bs, y+leg_len+3*bs), (lx + side*2*bs, y+leg_len)]
                self.draw_polygon(draw, shoe, fill=(45, 35, 30, 220), stroke=(30, 25, 20, 180), stroke_width=1)

        # ── Torso ──
        if is_woman:
            # Hourglass: narrow waist, wider hips
            waist_w = 7 * bs
            hip_w = 14 * bs
            bust_y = torso_top + 6 * bs
            waist_y = y - 2 * bs
            hip_y = y + 6 * bs

            # Upper torso (ribcage to waist)
            torso_pts = [(x - waist_w//2, waist_y),
                         (x - waist_w//2, bust_y),
                         (x + waist_w//2, bust_y),
                         (x + waist_w//2, waist_y)]
            self.draw_shadow(draw, torso_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
            self.fill_gradient_polygon(draw, torso_pts, self._lighten(cloth, 10), cloth,
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            # Bust curve
            bust_c = self._lighten(cloth, 15)
            for side in [-1, 1]:
                self.draw_arc(draw, x + side * waist_w//2, bust_y + bs, waist_w//3, 0, 180,
                              color=bust_c, width=int(2*bs))
                self.draw_arc(draw, x + side * waist_w//2, bust_y, waist_w//3, 0, 180,
                              color=self._darken(cloth, 5) + (60,), width=1)

            # Dress / hips (waist to midthigh)
            dress_pts = [(x - waist_w//2, waist_y),
                         (x - hip_w//2, hip_y),
                         (x + hip_w//2, hip_y),
                         (x + waist_w//2, waist_y)]
            self.draw_shadow(draw, dress_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
            self.fill_gradient_polygon(draw, dress_pts, cloth, self._darken(cloth, 10),
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            # Dress hem detail
            hem_color = self._lighten(cloth, 20)
            self.draw_line(draw, x - hip_w//2, hip_y, x + hip_w//2, hip_y,
                          color=hem_color + (180,), width=2)

        elif is_man:
            # V-shape: broad chest, narrow waist
            chest_w = 14 * bs
            waist_w = 9 * bs
            chest_y = torso_top + 2 * bs
            waist_y = y

            for side in [-1, 1]:
                pts = [(x, chest_y),
                       (x + side * chest_w//2, chest_y + 2*bs),
                       (x + side * waist_w//2, waist_y),
                       (x, waist_y)]
                self.draw_shadow(draw, pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
                self.fill_gradient_polygon(draw, pts, self._lighten(cloth, 10), self._darken(cloth, 15),
                                           stroke=(40, 35, 30, 150), stroke_width=1)

            # Belt
            self.draw_rect(draw, x - waist_w//2 - 1, waist_y - 3*bs, waist_w + 2, int(3*bs),
                          fill=(50, 40, 30, 200))

        else:
            # Neutral / child: simple rectangle torso
            tw = (10 if is_neutral else 9) * bs
            torso_pts = [(x - tw//2, y), (x - tw//2, torso_top),
                         (x + tw//2, torso_top), (x + tw//2, y)]
            self.draw_shadow(draw, torso_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
            self.fill_gradient_rect(draw, x - tw//2, torso_top, tw, y - torso_top,
                                    self._lighten(cloth, 10), self._darken(cloth, 20))

        # ── Arms ──
        arm_color = self._darken(cloth, 10)
        if is_woman:
            # One arm on hip, one down
            for side in [-1, 1]:
                if side == -1:
                    # Arm on hip
                    pts = [(x + side * 6*bs, torso_top + 6*bs),
                           (x + side * 8*bs, torso_top + 14*bs),
                           (x + side * 4*bs, y + 4*bs)]
                else:
                    # Arm down
                    pts = [(x + side * 6*bs, torso_top + 6*bs),
                           (x + side * 8*bs, torso_top + 16*bs),
                           (x + side * 7*bs, y + 8*bs)]
                self.draw_line(draw, int(pts[0][0]), int(pts[0][1]), int(pts[1][0]), int(pts[1][1]),
                              color=arm_color, width=int(3*bs))
                self.draw_line(draw, int(pts[1][0]), int(pts[1][1]), int(pts[2][0]), int(pts[2][1]),
                              color=arm_color, width=int(2.5*bs))
                self.draw_circle(draw, int(pts[2][0]), int(pts[2][1]), 2*bs,
                                fill=skin + (220,), stroke=(40, 35, 30, 150), stroke_width=1)
        else:
            for side in [-1, 1]:
                shoulder_off = (7 if is_man else 5) * bs
                elbow_x = x + side * (shoulder_off + 3*bs)
                hand_x = elbow_x + side * 3*bs
                hand_y = y + (6 if is_child else 10) * bs
                pts = [(x + side * shoulder_off, torso_top + 4*bs),
                       (elbow_x, torso_top + 14*bs),
                       (hand_x, hand_y)]
                self.draw_line(draw, int(pts[0][0]), int(pts[0][1]), int(pts[1][0]), int(pts[1][1]),
                              color=arm_color, width=int(3.5*bs))
                self.draw_line(draw, int(pts[1][0]), int(pts[1][1]), int(pts[2][0]), int(pts[2][1]),
                              color=arm_color, width=int(3*bs))
                self.draw_circle(draw, int(pts[2][0]), int(pts[2][1]), 2.5*bs,
                                fill=skin + (220,), stroke=(40, 35, 30, 150), stroke_width=1)

        # ── Head ──
        self.draw_shadow_circle(draw, x, neck_y + 2, head_r, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        head_pts = [(x - head_r, neck_y), (x + head_r, neck_y),
                    (x + head_r, neck_y - head_r*2), (x - head_r, neck_y - head_r*2)]
        self.fill_gradient_polygon(draw, head_pts, self._lighten(skin, 10), self._darken(skin, 15))
        self.draw_circle(draw, x, neck_y, head_r, fill=None,
                         stroke=(40, 35, 30, 170), stroke_width=2)

        # ── Hair ──
        if is_woman:
            # Long flowing hair
            hair_c = (60, 30, 20)
            # Hair on top
            self.draw_circle(draw, x, neck_y - head_r + 1, head_r * 0.8, fill=hair_c + (220,))
            # Hair flowing down sides (multiple strands)
            for side in [-1, 1]:
                base_x = x + side * head_r * 0.85
                for strand in range(3):
                    offset = strand * 0.15 - 0.15
                    sx = base_x
                    ex = x + side * head_r * (0.7 + offset)
                    ey = neck_y + head_r * (0.8 + strand * 0.1)
                    self.draw_line(draw, sx, neck_y - head_r * 0.3, ex, ey,
                                   color=hair_c, width=int((3 - strand) * bs))

        elif is_man:
            # Short cropped hair
            hair_c = (40, 35, 25)
            self.draw_circle(draw, x, neck_y - head_r + 1, head_r * 0.78, fill=hair_c + (220,))
            self.draw_arc(draw, x, neck_y - head_r * 0.5, head_r * 0.8, 190, 350,
                          color=hair_c, width=int(3*bs))
        else:
            hair_c = (80, 60, 40) if is_child else (50, 40, 30)
            self.draw_circle(draw, x, neck_y - head_r + 2, head_r * 0.72, fill=hair_c + (200,))

        # ── Face features ──
        eye_r = (2.2 if is_child else 1.6) * bs
        eye_y = neck_y - (4 if is_child else 3) * bs
        eye_spread = (4 if is_child else 3.5) * bs

        # Eyes
        self.draw_circle(draw, x - eye_spread, eye_y, eye_r, fill=(30, 25, 20, 200))
        self.draw_circle(draw, x + eye_spread, eye_y, eye_r, fill=(30, 25, 20, 200))
        self.draw_circle(draw, x - eye_spread + 0.5*bs, eye_y - 0.5*bs, eye_r*0.4, fill=(255, 255, 255, 160))
        self.draw_circle(draw, x + eye_spread + 0.5*bs, eye_y - 0.5*bs, eye_r*0.4, fill=(255, 255, 255, 160))

        # Eyelashes (woman only)
        if is_woman:
            for side in [-1, 1]:
                lash_x = x + side * (eye_spread + eye_r + 1*bs)
                self.draw_line(draw, int(lash_x), int(eye_y - 2*bs), int(lash_x + side*1*bs), int(eye_y - 4*bs),
                              color=(30, 25, 20, 150), width=1)
                self.draw_line(draw, int(lash_x), int(eye_y - 1*bs), int(lash_x + side*1.5*bs), int(eye_y - 3*bs),
                              color=(30, 25, 20, 150), width=1)

        # Nose
        nose_len = (2 if is_child else 1.5) * bs
        self.draw_line(draw, x, eye_y + eye_r, x, eye_y + eye_r + nose_len,
                      color=(40, 35, 30, 120), width=1)

        # Mouth / smile
        if is_child:
            # Bigger smile
            self.draw_arc(draw, x, neck_y + 4*bs, 4*bs, 200, 340, color=(160, 80, 60, 180), width=2)
        elif is_woman:
            # Fuller lips
            lip_y = neck_y + (4 if is_child else 3) * bs
            self.draw_arc(draw, x, lip_y, 3*bs, 200, 340, color=(160, 80, 70, 200), width=int(bs+1))
        elif is_man:
            # Straight mouth
            self.draw_line(draw, x - 2*bs, neck_y + 3*bs, x + 2*bs, neck_y + 3*bs,
                          color=(100, 60, 50, 180), width=2)

        # Eyebrows (man only - stronger)
        if is_man:
            brow_c = (40, 35, 25, 160)
            self.draw_line(draw, x - 5*bs, neck_y - 6.5*bs, x - 1.5*bs, neck_y - 6*bs,
                          color=brow_c, width=int(bs+1))
            self.draw_line(draw, x + 5*bs, neck_y - 6.5*bs, x + 1.5*bs, neck_y - 6*bs,
                          color=brow_c, width=int(bs+1))

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
                           color=gc + (self.rng.randint(100, 180),), width=self.rng.randint(1, 2))

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

    def draw_flower(self, draw, x, y, size=1.0, color=(255, 100, 150)):
        """Draw a simple flower with stem and petals."""
        s = size; c = tuple(color[:3])
        # Stem
        self.draw_line(draw, x, y, x, y - 10*s, color=(40, 120, 40), width=int(2*s))
        # Leaf
        self.draw_arc(draw, x, y - 6*s, 4*s, 180, 360, color=(40, 120, 40), width=int(1.5*s))
        # Petals
        for a in range(0, 360, 45):
            rad = math.radians(a)
            self.draw_circle(draw, x + math.cos(rad) * 5*s, y - 10*s + math.sin(rad) * 5*s, 4*s,
                           fill=c + (200,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        # Center
        self.draw_circle(draw, x, y - 10*s, 3*s, fill=(255, 200, 50, 200))

    def draw_plant(self, draw, x, y, size=1.0, color=(50, 120, 50)):
        """Draw a simple small plant."""
        s = size; c = tuple(color[:3])
        # Stem
        self.draw_line(draw, x, y, x, y - 8*s, color=(60, 100, 40), width=int(2*s))
        # Leaves
        for side in [-1, 1]:
            self.draw_circle(draw, x + side * 5*s, y - 4*s, 4*s,
                           fill=c + (200,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        # Top leaf cluster
        self.draw_circle(draw, x, y - 8*s, 3*s, fill=self._lighten(c, 20) + (200,))

    def draw_fruit(self, draw, x, y, size=1.0, color=(255, 150, 50)):
        """Draw a simple fruit."""
        s = size; c = tuple(color[:3])
        r = 6 * s
        self.draw_shadow_circle(draw, x, y + 2, r, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        self.draw_circle(draw, x, y, r, fill=c + (220,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        # Highlight
        self.draw_circle(draw, x - r//3, y - r//3, r//3, fill=(255, 255, 255, 60))
        # Stem
        self.draw_line(draw, x, y - r, x + 2*s, y - r - 3*s, color=(60, 50, 40), width=int(1.5*s))

    def draw_cave(self, draw, x, y, size=1.0, color=(55, 45, 40)):
        """Draw a cave entrance with arch, stalactites, rocky texture, and dark interior."""
        s = size; c = tuple(color[:3])
        cave_w = int(35 * s)
        cave_h = int(28 * s)
        arch_h = int(18 * s)

        # Shadow behind cave
        self.draw_shadow_circle(draw, x, y + cave_h//2 - 4*s, cave_w//2 + int(4*s),
                                offset=(3, 3), blur_radius=6, color=(0, 0, 0, 60))

        # Cave arch: rocky arch shape using polygon (semi-circle with roughness)
        arch_pts = []
        for a in range(0, 190, 10):
            rad = math.radians(a - 5)
            rx = x + int(math.cos(rad) * cave_w // 2) + self.rng.randint(-2, 2)
            ry = y + int(math.sin(rad) * arch_h) + int(2*s) + self.rng.randint(-1, 1)
            arch_pts.append((rx, ry))
        if arch_pts:
            self.draw_polygon(draw, arch_pts,
                            fill=self._darken(c, 10) + (230,),
                            stroke=self._darken(c, 25) + (180,), stroke_width=2)

        # Dark interior
        interior_w = int(cave_w * 0.7)
        self.draw_circle(draw, x, y + int(2*s), interior_w // 2,
                        fill=(15, 12, 10, 250), stroke=(25, 20, 18, 200), stroke_width=1)
        # Deepest shadow inside
        self.draw_circle(draw, x, y + int(4*s), interior_w // 3,
                        fill=(5, 4, 3, 255))

        # Stalactites hanging from arch top
        stal_count = max(2, int(5 * s))
        for i in range(stal_count):
            sx = x + int((i / stal_count - 0.5) * cave_w * 1.2)
            stal_h = int((5 + self.rng.randint(0, 10)) * s)
            stal_w = int((2 + self.rng.randint(0, 3)) * s)
            self.draw_polygon(draw, [
                (sx - stal_w, y + int(3*s)),
                (sx, y + int(3*s) - stal_h),
                (sx + stal_w, y + int(3*s))
            ], fill=self._darken(c, 15) + (220,),
               stroke=self._darken(c, 30) + (150,), stroke_width=1)

        # Ground / floor inside cave
        floor_y = y + arch_h - int(2*s)
        self.draw_rect(draw, x - cave_w // 2, floor_y, cave_w, int(6*s),
                      fill=(25, 20, 18, 230), stroke=(40, 35, 30, 150), stroke_width=1)

        # Rock debris on floor
        for _ in range(max(2, int(4 * s))):
            rx = x + int((self.rng.random() - 0.5) * cave_w * 0.8)
            ry = floor_y + int(2 * s) + int(self.rng.random() * 3 * s)
            rr = int((2 + self.rng.random() * 4) * s)
            self.draw_circle(draw, rx, ry, rr,
                           fill=self._lighten(c, 5) + (200,),
                           stroke=self._darken(c, 15) + (150,), stroke_width=1)

        # Rocky texture on arch edges
        for _ in range(max(3, int(8 * s))):
            edge_angle = self.rng.uniform(0, 180)
            rad = math.radians(edge_angle)
            ex = x + int(math.cos(rad) * cave_w // 2 * 1.05)
            ey = y + int(math.sin(rad) * arch_h) + int(2*s)
            er = int((1.5 + self.rng.random() * 3) * s)
            self.draw_circle(draw, ex, ey, er,
                           fill=self._darken(c, 5) + (180,),
                           stroke=self._darken(c, 20) + (120,), stroke_width=1)

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
        r = 24*s
        self.draw_shadow_circle(draw, x, y+r, r, offset=(3,2), blur_radius=4, color=(0,0,0,40))
        self.draw_circle(draw, x, y, r, fill=c+(200,), stroke=self._darken(c,20)+(180,), stroke_width=2)
        # Continents blobs
        for ox, oy in [(0.3,0.2), (-0.2,0.1), (0.1,-0.3), (-0.3,-0.1)]:
            self.draw_circle(draw, int(x+ox*r), int(y+oy*r), int(r*0.25), fill=(60,120,80,120))
        # Latitude/longitude arcs
        self.draw_arc(draw, x, y, int(r*0.7), 180, 360, color=(255,255,255,40), width=1)
        self.draw_arc(draw, x, y, int(r*0.5), 0, 180, color=(255,255,255,30), width=1)
        # Stand
        self.draw_rect(draw, x-2*s, y+r, 4*s, int(6*s), fill=(80,70,60,200), stroke=(50,45,40,180), stroke_width=1)
        self.draw_rect(draw, x-5*s, y+r+int(6*s), int(10*s), int(3*s), fill=(80,70,60,200), stroke=(50,45,40,180), stroke_width=1)

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

    def draw_volcano(self, draw, x, y, size=1.0, color=(100, 80, 60)):
        """Draw a volcano with smoke plume."""
        s = size; c = tuple(color[:3])
        w, h = 20*s, 18*s
        # Mountain body
        pts = [(x-w//2, y+6*s), (x, y-h//2), (x+w//2, y+6*s)]
        self.draw_polygon(draw, pts, fill=c+(220,), stroke=self._darken(c,20)+(180,), stroke_width=2)
        # Crater
        self.draw_ellipse(draw, x-3*s, y-h//2, 6*s, 3*s, fill=(180,100,40,200), stroke=(120,60,30,180), stroke_width=1)
        # Lava glow
        self.draw_circle(draw, x, y-h//2+1*s, 4*s, fill=(255,150,50,60))
        # Smoke plume
        for i in range(5):
            sy = y - h//2 - i*5*s
            sr = 3*s + i*2*s
            alpha = max(30, 120 - i*20)
            self.draw_circle(draw, x+self.rng.randint(-3,3)*s, sy, sr, fill=(200,200,200,alpha))

    def draw_rainbow(self, draw, x, y, size=1.0, color=None):
        """Draw a rainbow arc."""
        s = size
        colors = [(255,50,50), (255,180,50), (255,255,80), (80,200,80), (80,120,255), (180,80,255)]
        r = 30*s
        for i, col in enumerate(colors):
            cr = r - i*3*s
            self.draw_arc(draw, x-cr, y-cr, cr*2, 0, 180, color=col+(180,), width=int(3*s))

    def draw_waterfall(self, draw, x, y, size=1.0, color=(100, 180, 255)):
        """Draw a cascading waterfall."""
        s = size; c = tuple(color[:3])
        w, h = 8*s, 30*s
        # Water column
        self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=c+(180,), stroke=(80,140,200,150), stroke_width=1, rx=2)
        # Foam lines
        for i in range(6):
            fy = y - h//2 + i*h//6
            self.draw_line(draw, x-w//2+2, fy, x+w//2-2, fy, color=(255,255,255,80), width=int(1.5*s))
        # Mist
        self.draw_circle(draw, x, y+h//2+4*s, 8*s, fill=(200,220,255,40))
        self.draw_circle(draw, x-3*s, y+h//2+6*s, 6*s, fill=(200,220,255,30))
        # Splash
        for i in range(3):
            dx = self.rng.randint(-6, 6)*s
            dy = self.rng.randint(2, 8)*s
            self.draw_circle(draw, x+dx, y+h//2+dy, 1.5*s, fill=(200,220,255,60))

    # ── Procedural element compositing ──────────────────────────

    def draw_composite(self, draw, parts, cx, cy, scale=1.0):
        """Render a list of composable parts (from elements_pro generators).
        Part types: c=circle, r=rect, e=ellipse, l=line, p=polygon, a=arc.
        Coordinates are relative to center (cx,cy) with scale factor.
        Scale 1.0 maps normalized generator values (~0.001-0.30) to ~0.3-60px."""
        for p in parts:
            t = p.get("t", p.get("type", ""))
            x = int(cx + p.get("x", 0) * scale)
            y = int(cy + p.get("y", 0) * scale)
            fill = tuple(p["f"]) if "f" in p else (200,200,200)
            stroke = tuple(p["s"]) if "s" in p and p["s"] else None
            sw = p.get("stroke_width", p.get("w_sw", 1))
            alpha = p.get("a", fill[3] if len(fill) > 3 else 255) if isinstance(fill, tuple) else 255

            if t == "c":
                r = max(int(p.get("r", 5) * scale), 1)
                self.draw_circle(draw, x, y, r, fill=fill, stroke=stroke, stroke_width=sw, opacity=alpha)
            elif t == "r":
                w = max(int(p.get("w", 10) * scale), 1)
                h = max(int(p.get("h", 10) * scale), 1)
                rx = p.get("rx", 0)
                self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=fill, stroke=stroke, stroke_width=sw, rx=rx, opacity=alpha)
            elif t == "e":
                w = max(int(p.get("w", 10) * scale), 1)
                h = max(int(p.get("h", 10) * scale), 1)
                self.draw_ellipse(draw, x, y, w, h, fill=fill, stroke=stroke, stroke_width=sw, opacity=alpha)
            elif t == "l":
                x1 = int(cx + p.get("x1", 0) * scale)
                y1 = int(cy + p.get("y1", 0) * scale)
                x2 = int(cx + p.get("x2", 0) * scale)
                y2 = int(cy + p.get("y2", 0) * scale)
                w = max(int(p.get("w", 2)), 1)  # line width is pixel value, don't scale
                self.draw_line(draw, x1, y1, x2, y2, color=fill, width=w, opacity=alpha)
            elif t == "p":
                pts = p.get("pts", [])
                if pts:
                    pxs = [(int(cx + pt[0] * scale), int(cy + pt[1] * scale)) for pt in pts]
                    self.draw_polygon(draw, pxs, fill=fill, stroke=stroke, stroke_width=sw, opacity=alpha)
            elif t == "a":
                r = max(int(p.get("r", 10) * scale), 1)
                start = p.get("start", 0)
                end = p.get("end", 360)
                w = max(int(p.get("w", 2)), 1)  # arc width is pixel value, don't scale
                self.draw_arc(draw, x, y, r, start, end, color=fill or (100,100,100), width=w)

    def draw_ellipse(self, draw, x, y, w, h, fill=None, stroke=None, stroke_width=1, opacity=255):
        """Draw an ellipse."""
        if fill:
            fc = tuple(fill[:3]) + (opacity,)
            draw.ellipse([x-w//2, y-h//2, x+w//2, y+h//2], fill=fc)
        if stroke:
            sc = tuple(stroke[:3]) + (opacity,)
            draw.ellipse([x-w//2, y-h//2, x+w//2, y+h//2], outline=sc, width=stroke_width)


    # ── Main scene renderer ────────────────────────────────────

    def render_scene(self, desc: dict) -> Image.Image:
        """Render a full scene from a structured description dict.
        Handles story scenes, diagrams, timelines, flowcharts, and maps generically."""
        self.desc = desc
        scene_type = desc.get("scene_type", "story")

        # Non-story types use clean informational backgrounds
        if scene_type == "diagram":
            base = (245, 242, 235)
        elif scene_type == "timeline":
            base = (250, 247, 240)
        elif scene_type == "flowchart":
            base = (248, 245, 238)
        elif scene_type == "map":
            base = (235, 240, 245)
        elif scene_type in ("bar_chart", "pie_chart", "line_graph", "data_viz"):
            base = (250, 248, 242)
        elif scene_type in ("cycle_diagram", "step_diagram"):
            base = (248, 246, 240)
        elif scene_type == "venn_diagram":
            base = (248, 245, 242)
        elif scene_type == "comparison":
            base = (250, 248, 245)
        else:
            base = None
        canvas = self.create_canvas(base + (255,) if base else (255, 255, 255, 255))

        draw = ImageDraw.Draw(canvas, "RGBA")

        if scene_type == "story":
            # ── Background ──
            bg = desc.get("bg", desc.get("background", {}))
            bg_type = bg.get("type", "gradient") if isinstance(bg, dict) else "gradient"

            if isinstance(bg, dict):
                self._render_background(draw, bg)

            # ── Atmosphere particles ──
            atmos = desc.get("atmosphere", {})
            if atmos.get("particles") == "stars" or bg_type == "night":
                self.draw_stars(draw, count=atmos.get("star_count", 60))

            # ── Landscape features (mountains, ground, trees, clouds) ──
            if isinstance(bg, dict):
                self._render_landscape(draw, bg)

        # ── Elements (all types) sorted by z_index ──
        sorted_elems = sorted(desc.get("elements", []), key=lambda e: e.get("z_index", 2))
        for elem in sorted_elems:
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
            colors = bg.get("colors", [])
            c = self._tc(colors[0] if colors else bg.get("color", None), (245, 245, 240))
            draw.rectangle([0, 0, self.w, self.h], fill=c)

        elif bg_type == "forest":
            sky = self._tc(bg.get("sky_color"), (180, 200, 180))
            horizon = bg.get("horizon", 0.5)

        elif bg_type == "sunset":
            colors = [(0, (220, 100, 70)), (0.2, (200, 120, 90)),
                      (0.4, (160, 80, 100)), (0.6, (80, 50, 80)),
                      (1, self._tc(bg.get("ground_color"), (40, 50, 30)))]
            self.bg_gradient(draw, colors)

        elif bg_type == "desert":
            colors = [(0, self._tc(bg.get("sky_color"), (220, 180, 120))),
                      (0.4, self._tc(bg.get("horizon_color"), (200, 155, 90))),
                      (0.5, (190, 140, 80))]
            self.bg_gradient(draw, colors)
            horizon = bg.get("horizon", 0.55)
            gh = int(self.h * horizon)
            sand_top = self._tc(bg.get("ground_color"), (200, 170, 120))
            sand_bot = self._tc(bg.get("ground_color"), (170, 140, 90))
            for y in range(gh, self.h):
                t = (y - gh) / max(self.h - gh, 1)
                r = int(sand_top[0] + t * (sand_bot[0] - sand_top[0]))
                g = int(sand_top[1] + t * (sand_bot[1] - sand_top[1]))
                b = int(sand_top[2] + t * (sand_bot[2] - sand_top[2]))
                draw.line([(0, y), (self.w, y)], fill=(r, g, b))
            # Heat shimmer at horizon
            for i in range(6):
                shimmer_y = gh - 3 + i
                shimmer_alpha = 30 - i * 4
                if shimmer_alpha > 0:
                    draw.line([(0, shimmer_y), (self.w, shimmer_y)], fill=(255, 220, 180, shimmer_alpha))

        elif bg_type == "sky":
            colors = [(0, self._tc(bg.get("colors", [(80, 150, 220)])[0], (80, 150, 220))),
                      (0.3, self._tc(bg.get("colors", [(120, 180, 235)])[1%len(bg.get("colors",[1]))], (120, 180, 235))),
                      (0.6, self._tc(bg.get("colors", [(180, 210, 245)])[min(2,len(bg.get("colors",[1,2,3]))-1)], (180, 210, 245))),
                      (1, self._tc(bg.get("colors", [(220, 235, 250)])[min(3,len(bg.get("colors",[1,2,3,4]))-1)], (220, 235, 250)))]
            self.bg_gradient(draw, colors)
            # Light clouds scattered across sky
            for i in range(4):
                cx = self.w * (0.15 + i * 0.2 + self.rng.random() * 0.08)
                cy = self.h * (0.1 + self.rng.random() * 0.25)
                cr = 30 + self.rng.random() * 40
                for j in range(3):
                    ox = self.rng.random() * cr * 0.8 - cr * 0.4
                    oy = self.rng.random() * cr * 0.3
                    alpha = 40 + self.rng.random() * 30
                    draw.ellipse([int(cx+ox-cr), int(cy+oy-cr//2), int(cx+ox+cr), int(cy+oy+cr//2)],
                                 fill=(255, 255, 255, int(alpha)))

    def _render_landscape(self, draw, bg: dict):
        """Draw landscape features (mountains, ground detail, vegetation) on top of background."""
        bg_type = bg.get("type", "gradient")
        colors = bg.get("colors", [])
        horizon = bg.get("horizon", 0.55)
        horizon_y = int(self.h * horizon)

        if bg_type in ("indoor", "solid", "ocean", "desert", "arctic", "sky"):
            return

        if len(colors) >= 2:
            sky_base = self._tc(colors[0], (100, 120, 180))
            ground_base = self._tc(colors[-1], (60, 80, 60))
        else:
            sky_base = (100, 120, 180)
            ground_base = (60, 80, 60)

        is_night = bg_type == "night"
        is_warm = bg_type == "sunset"

        # ── Mountains silhouette at horizon ──
        mtn_count = self.rng.randint(3, 5)
        far_color = (max(0, sky_base[0] - 20), max(0, sky_base[1] - 15), max(0, sky_base[2] - 10))
        for _ in range(mtn_count):
            mx = self.rng.randint(-50, self.w + 50)
            mh = self.rng.randint(40, 120)
            mw = self.rng.randint(80, 200)
            pts = [(mx - mw, horizon_y), (mx, horizon_y - mh), (mx + mw, horizon_y)]
            self.draw_polygon(draw, pts, fill=far_color + (180,),
                            stroke=self._darken(far_color, 10) + (120,), stroke_width=1)

        mtn_count2 = self.rng.randint(2, 4)
        near_color = self._darken(sky_base, 30)
        for _ in range(mtn_count2):
            mx = self.rng.randint(-30, self.w + 30)
            mh = self.rng.randint(60, 160)
            mw = self.rng.randint(100, 250)
            pts = [(mx - mw, horizon_y + 5), (mx, horizon_y - mh), (mx + mw, horizon_y + 5)]
            self.draw_polygon(draw, pts, fill=near_color + (200,),
                            stroke=self._darken(near_color, 15) + (140,), stroke_width=1)
            if not is_night and mh > 100 and self.rng.random() < 0.5:
                snow_h = mh * 0.2
                snow_pts = [(mx - mw * 0.15, horizon_y - mh + snow_h),
                           (mx, horizon_y - mh),
                           (mx + mw * 0.15, horizon_y - mh + snow_h)]
                self.draw_polygon(draw, snow_pts, fill=(230, 235, 245, 200),
                                stroke=(200, 210, 230, 150), stroke_width=1)

        # ── Ground texture (grass tufts) ──
        ground_h = self.h - horizon_y
        grass_color = self._lighten(ground_base, 10)
        for _ in range(self.rng.randint(10, 30)):
            gx = self.rng.randint(5, self.w - 5)
            gy = horizon_y + self.rng.randint(5, ground_h - 5)
            gh = self.rng.randint(4, 12)
            self.draw_line(draw, gx, gy, gx + self.rng.randint(-2, 2), gy - gh,
                         color=grass_color + (self.rng.randint(100, 180),), width=1)

        # ── Trees at horizon ──
        if bg_type in ("gradient", "forest", "sunset") and not is_night:
            tree_count = self.rng.randint(2, 4)
            for _ in range(tree_count):
                tx = self.rng.randint(30, self.w - 30)
                ty = horizon_y - self.rng.randint(5, 15)
                trunk_h = self.rng.randint(20, 35)
                trunk_w = self.rng.randint(3, 6)
                draw.rectangle([tx - trunk_w, ty - trunk_h, tx + trunk_w, ty],
                              fill=(50, 35, 20, 200))
                crown_r = self.rng.randint(15, 25)
                for i in range(2):
                    cy = ty - trunk_h - i * crown_r // 2
                    cr = crown_r - i * 5
                    if cr > 5:
                        draw.ellipse([tx - cr, cy - cr, tx + cr, cy + cr // 2],
                                    fill=(30 + self.rng.randint(0, 20), 60 + self.rng.randint(0, 30), 20 + self.rng.randint(0, 15), 200))

        # ── Clouds for daytime ──
        if not is_night and bg_type != "indoor":
            for _ in range(self.rng.randint(1, 3)):
                cx = self.rng.randint(0, self.w)
                cy = self.rng.randint(5, int(self.h * 0.25))
                cr = self.rng.randint(20, 40)
                cb = 200 + self.rng.randint(0, 40)
                for dx, dy in [(0, 0), (cr//2, cr//4), (-cr//3, cr//3), (cr//3, cr//3)]:
                    draw.ellipse([cx + dx - cr, cy + dy - cr//2, cx + dx + cr, cy + dy + cr//2],
                                fill=(cb, cb, cb, self.rng.randint(120, 200)))

    def draw_concept(self, draw, x, y, word, color=None, size=1.0):
        """Generate a unique meaningful visual for any concept word."""
        import math
        sw = max(10, int(35 * size))
        sh = max(10, int(35 * size))
        if color is None or not isinstance(color, (list, tuple)):
            clr = (160, 180, 200)
        else:
            clr = tuple(int(c) for c in color[:3])

        # Background shape based on first letter of word
        first = word[0].lower() if word else 'a'
        shape_idx = (ord(first) - 97) % 6 if first.isalpha() else 0

        # Draw background card
        card_w = max(40, len(word) * 9 + 12)
        card_h = 32
        self.draw_rect(draw, x - card_w//2, y - card_h//2, card_w, card_h,
                      fill=clr + (200,), rx=6)
        self.draw_rect(draw, x - card_w//2, y - card_h//2, card_w, card_h,
                      stroke=(40, 35, 30), stroke_width=1, rx=6)

        # Decorative shape inside card
        if shape_idx == 0:  # Circle
            self.draw_circle(draw, x, y - 2, sw * 0.15, fill=clr + (230,))
        elif shape_idx == 1:  # Diamond
            pts = [(x, y-2-int(sw*0.15)), (x+int(sw*0.15), y-2), (x, y-2+int(sw*0.15)), (x-int(sw*0.15), y-2)]
            self.draw_polygon(draw, pts, fill=clr + (230,))
        elif shape_idx == 2:  # Triangle
            pts = [(x, y-2-int(sw*0.15)), (x+int(sw*0.13), y-2+int(sw*0.1)), (x-int(sw*0.13), y-2+int(sw*0.1))]
            self.draw_polygon(draw, pts, fill=clr + (230,))
        elif shape_idx == 3:  # Star dot
            self.draw_circle(draw, x, y-2, 3, fill=(255, 255, 200, 230))
        elif shape_idx == 4:  # Small square
            self.draw_rect(draw, x-3, y-5, 6, 6, fill=clr + (230,), rx=1)
        else:  # Line
            self.draw_line(draw, x-8, y-2, x+8, y-2, color=clr + (200,), width=2)

        # Draw the word label below shape
        fs = max(10, min(16, int(22 / max(1, len(word) * 0.12))))
        self.draw_text(draw, x, y + int(card_h * 0.25), word, font_size=fs,
                      color=(40, 35, 30), align="center")

    def _render_element(self, draw, elem: dict):
        """Render a single element from its description."""
        etype = elem.get("type", "").lower()
        x = int(elem.get("x", 0.5) * self.w)
        y = int(elem.get("y", 0.5) * self.h)
        s = (elem.get("scale") or elem.get("size") or 1.0) * 5.0

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

        elif etype in ("human", "person", "figure", "people"):
            c = fill or (80, 60, 120)
            skin = _tc(elem.get("skin_color", (235, 200, 175))) or (235, 200, 175)
            self.draw_human(draw, x, y, s, c, skin, gender="neutral")
        elif etype == "man":
            c = fill or (70, 50, 100)
            skin = _tc(elem.get("skin_color", (235, 200, 175))) or (235, 200, 175)
            self.draw_human(draw, x, y, s, c, skin, gender="man")
        elif etype == "woman":
            c = fill or (140, 80, 120)
            skin = _tc(elem.get("skin_color", (230, 190, 170))) or (230, 190, 170)
            self.draw_human(draw, x, y, s, c, skin, gender="woman")
        elif etype == "child":
            c = fill or (100, 140, 180)
            skin = _tc(elem.get("skin_color", (240, 210, 190))) or (240, 210, 190)
            self.draw_human(draw, x, y, s * 0.65, c, skin, gender="child")

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

        elif etype == "arc":
            r = int(elem.get("radius", 40) * (elem.get("r_scale", 1)))
            start_angle = elem.get("start_angle", 0)
            end_angle = elem.get("end_angle", 90)
            c = stroke or (80, 70, 60)
            w = elem.get("stroke_width", 2)
            self.draw_arc(draw, x, y, max(r, 5), start_angle, end_angle, color=c, width=w, opacity=opacity)
            label = elem.get("label")
            if label:
                mid_angle = math.radians((start_angle + end_angle) / 2)
                lx = x + int(math.cos(mid_angle) * (r + 20))
                ly = y - int(math.sin(mid_angle) * (r + 20))
                self.draw_text(draw, lx, ly, label, font_size=elem.get("font_size", 18), color=c, align="center")

        elif etype == "ellipse":
            w = int(elem.get("width", 80) * (elem.get("w_scale", 1)))
            h = int(elem.get("height", 60) * (elem.get("h_scale", 1)))
            fill_color = fill
            stroke_color = stroke or (40, 35, 30)
            draw.ellipse([x - w // 2, y - h // 2, x + w // 2, y + h // 2],
                        fill=fill_color, outline=stroke_color, width=elem.get("stroke_width", 2))

        elif etype == "x_mark":
            c = fill or (180, 40, 40)
            l = 12 * s
            self.draw_line(draw, x-l, y-l, x+l, y+l, color=c, width=int(3*s+1), opacity=opacity)
            self.draw_line(draw, x+l, y-l, x-l, y+l, color=c, width=int(3*s+1), opacity=opacity)

        elif etype == "ship":
            self.draw_ship(draw, x, y, s, fill or (80, 60, 40), _tc(elem.get("sail_color", (220, 210, 190))))

        elif etype == "wave":
            self.draw_wave(draw, x, y, s, fill or (40, 100, 180))

        elif etype == "canoe":
            self.draw_canoe(draw, x, y, s, fill or (80, 55, 35))

        elif etype == "whale":
            self.draw_whale(draw, x, y, s, fill or (60, 70, 100))

        elif etype == "shark":
            self.draw_shark(draw, x, y, s, fill or (80, 85, 95))

        elif etype == "sea_serpent" or etype == "seaserpent":
            self.draw_sea_serpent(draw, x, y, s, fill or (40, 100, 60))

        elif etype == "totem" or etype == "monolith":
            self.draw_totem(draw, x, y, s, fill or (120, 105, 85))

        elif etype == "anchor":
            self.draw_anchor(draw, x, y, s, fill or (80, 75, 70))

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

        elif etype == "flower":
            c = fill or (255, 100, 150)
            self.draw_flower(draw, x, y, s, c)

        elif etype == "plant":
            c = fill or (50, 120, 50)
            self.draw_plant(draw, x, y, s, c)

        elif etype == "fruit":
            c = fill or (255, 150, 50)
            self.draw_fruit(draw, x, y, s, c)

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

        # ── Landscape / nature aliases ──
        elif etype in ("volcano", "eruption", "volcanic"):
            self.draw_volcano(draw, x, y, s, fill or (100, 80, 60))
        elif etype == "rainbow":
            self.draw_rainbow(draw, x, y, s, fill)
        elif etype in ("waterfall", "cascade", "falls"):
            self.draw_waterfall(draw, x, y, s, fill or (100, 180, 255))
        elif etype in ("cave", "cavern"):
            self.draw_cave(draw, x, y, s, (fill[:3] if fill else (55, 45, 40)))
        elif etype in ("cliff", "cliffs", "bluff", "bluffs"):
            self.draw_cliff(draw, x, y, s, fill or (100, 80, 60))

        elif etype in ("compass_rose", "wind_rose"):
            self.draw_compass_rose(draw, x, y, s, fill or (180, 160, 120))

        elif etype in ("shadow_figure", "silhouette", "shadow_man"):
            self.draw_shadow_figure(draw, x, y, s, fill or (20, 25, 30))

        elif etype in ("moon_path", "moonlight_path", "moon_reflection"):
            self.draw_moon_path(draw, x, y, s, fill or (200, 210, 230))

        elif etype == "jar":
            self.draw_jar(draw, x, y, s, fill or (200, 210, 220))

        elif etype == "shelf":
            self.draw_shelf(draw, x, y, s, fill or (120, 90, 60))

        elif etype in ("island", "isle"):
            r = 15*s
            self.draw_circle(draw, x, y, r, fill=(180,200,100,200), stroke=(100,140,60,180), stroke_width=2)
            self.draw_circle(draw, x-3*s, y-3*s, r*0.4, fill=(80,160,80,200))
            self.draw_ellipse(draw, x-r, y+2*s, r*2, r*0.3, fill=(180,200,220,150))

        # ── Animal aliases ──
        elif etype in ("elephant", "lion", "tiger", "bear", "wolf", "fox", "deer",
                       "horse", "zebra", "giraffe", "camel", "rhino", "hippo",
                       "dog", "cat", "monkey", "panda", "squirrel", "rabbit",
                       "dragon", "dinosaur", "snake", "lizard", "turtle", "frog",
                       "goat", "sheep", "cow", "pig", "rat", "mouse", "beaver",
                       "otter", "hedgehog", "bat", "kangaroo", "koala", "sloth",
                       "raccoon", "skunk", "moose", "elk", "bison", "buffalo",
                       "leopard", "panther", "jaguar", "cheetah", "hyena",
                       "unicorn", "griffin", "phoenix", "pegasus", "chimera",
                       "werewolf", "vampire", "zombie", "golem", "troll", "orc",
                       "centaur", "minotaur", "satyr", "fairy", "elf", "dwarf",
                       "giant", "ogre", "goblin", "gnome", "sprite", "nymph",
                       "beast", "monster", "creature", "animal"):
            self.draw_animal(draw, x, y, s, fill or (100, 80, 60))

        # ── Bird aliases ──
        elif etype in ("eagle", "hawk", "falcon", "vulture", "raven", "crow",
                       "owl", "parrot", "macaw", "cockatoo", "swan", "goose",
                       "duck", "heron", "crane", "stork", "flamingo", "peacock",
                       "penguin", "ostrich", "pigeon", "dove", "sparrow",
                       "robin", "bluebird", "cardinal", "hummingbird",
                       "woodpecker", "kingfisher", "seagull", "pelican",
                       "albatross", "magpie", "canary", "finch",
                       "chicken", "hen", "rooster", "cock", "chick", "quail",
                       "pheasant", "grouse", "partridge", "cuckoo",
                       "nightingale", "lark", "thrush", "blackbird", "starling",
                       "oriole", "tanager", "wren", "swift", "martin",
                       "warbler", "bunting", "meadowlark", "grackle",
                       "bird"):
            self.draw_bird(draw, x, y, s, fill or (60, 50, 40))

        # ── Fish / sea creature aliases ──
        elif etype in ("shark", "dolphin", "whale", "orca", "tuna", "salmon",
                       "trout", "bass", "goldfish", "koi", "clownfish",
                       "swordfish", "marlin", "ray", "eel", "octopus", "squid",
                       "jellyfish", "crab", "lobster", "shrimp", "seahorse",
                       "starfish", "coral", "anemone", "fish"):
            self.draw_fish(draw, x, y, s, fill or (200, 180, 100))

        # ── Tree / plant aliases ──
        elif etype in ("pine", "oak", "maple", "willow", "birch", "cedar",
                       "spruce", "fir", "redwood", "sequoia", "baobab",
                       "palm", "coconut", "bush", "shrub", "hedge",
                       "cactus", "succulent", "bamboo", "fern", "moss",
                       "vine", "ivy", "reed", "kelp", "seaweed"):
            style = "round"
            if etype in ("pine", "spruce", "fir", "redwood", "cedar"):
                style = "pine"
            elif etype in ("palm", "coconut"):
                style = "palm"
            self.draw_tree(draw, x, y, s, style, fill or (50, 120, 50))

        # ── Flower aliases ──
        elif etype in ("rose", "tulip", "daisy", "lotus", "lily", "orchid",
                       "sunflower", "poppy", "lavender", "violet", "iris",
                       "cherry_blossom", "blossom", "petal", "flower"):
            self.draw_flower(draw, x, y, s, fill or (255, 100, 150))

        # ── Fruit aliases ──
        elif etype in ("apple", "orange", "lemon", "lime", "cherry", "grape",
                       "berry", "strawberry", "blueberry", "raspberry",
                       "banana", "mango", "peach", "pear", "plum",
                       "watermelon", "melon", "pumpkin", "tomato", "fruit"):
            self.draw_fruit(draw, x, y, s, fill or (255, 150, 50))

        # ── Building / structure aliases ──
        elif etype in ("tower", "castle", "fortress", "palace", "temple",
                       "pyramid", "lighthouse", "windmill", "church",
                       "monument", "shrine", "tomb", "dome", "column",
                       "gate", "wall", "bridge", "ruin", "statue",
                       "barn", "stable", "silo", "well", "fountain",
                       "cabin", "hut", "shelter", "tent", "pavilion"):
            bw = int(elem.get("width", 0.12) * self.w)
            bh = int(elem.get("height", 0.25) * self.h)
            self.draw_building(draw, x, y, bw, bh, fill or (120, 100, 80),
                              window_color=_tc(elem.get("window_color", (255, 220, 100))) or (255, 220, 100))

        # ── Ship / boat aliases ──
        elif etype in ("boat", "sailboat", "vessel", "raft",
                        "kayak", "rowboat", "warship", "galleon"):
            self.draw_ship(draw, x, y, s, fill or (80, 60, 40),
                          _tc(elem.get("sail_color", (220, 210, 190))))

        elif etype in ("canoe", "dugout"):
            self.draw_canoe(draw, x, y, s, fill or (80, 55, 35))

        elif etype in ("shark",):
            self.draw_shark(draw, x, y, s, fill or (80, 85, 95))

        elif etype in ("whale", "orca"):
            self.draw_whale(draw, x, y, s, fill or (60, 70, 100))

        elif etype in ("sea_serpent", "seaserpent", "leviathan"):
            self.draw_sea_serpent(draw, x, y, s, fill or (40, 100, 60))

        # ── Weapon aliases ──
        elif etype in ("sword", "dagger", "knife", "blade", "spear",
                       "lance", "pike", "axe", "battleaxe", "hammer",
                       "mace", "club", "staff", "wand", "bow", "crossbow",
                       "arrow", "shield", "armor", "helmet"):
            # Use procedural object generator for weapons
            try:
                from src.procedural_engine import ProceduralEngine as _PE
                _pe = _PE()
                parts = _pe.generate(etype, size=s)
                if parts:
                    self.draw_composite(draw, parts, x, y, scale=s)
                else:
                    self.draw_rect(draw, x-10, y-5, 20, 10, fill=fill or (120,100,80))
            except:
                self.draw_rect(draw, x-10, y-5, 20, 10, fill=fill or (120,100,80))

        # ── Charts & diagrams ──
        elif etype == "bar_chart":
            data = elem.get("data", [])
            cw = elem.get("chart_w", 400)
            ch = elem.get("chart_h", 300)
            bc = fill or (70, 130, 180)
            ct = elem.get("chart_title", "")
            self.draw_bar_chart(draw, x, y, data, w=cw, h=ch, bar_color=bc, title=ct)

        elif etype == "pie_chart":
            data = elem.get("data", [])
            r = elem.get("radius", 120)
            self.draw_pie_chart(draw, x, y, data, radius=r)

        elif etype == "line_graph":
            data = elem.get("data", [])
            cw = elem.get("chart_w", 400)
            ch = elem.get("chart_h", 280)
            lc = fill or (200, 80, 60)
            self.draw_line_graph(draw, x, y, data, w=cw, h=ch, line_color=lc)

        elif etype == "cycle_diagram":
            steps = elem.get("steps", [])
            r = elem.get("radius", 130)
            self.draw_cycle_diagram(draw, x, y, steps, radius=r)

        elif etype == "venn_diagram":
            self.draw_venn_diagram(draw, x, y,
                                  left_label=elem.get("left_label", "A"),
                                  right_label=elem.get("right_label", "B"),
                                  common_label=elem.get("common_label", "Both"),
                                  r=elem.get("radius", 100))

        elif etype == "comparison":
            self.draw_comparison(draw, x, y,
                                left_title=elem.get("left_title", "Before"),
                                right_title=elem.get("right_title", "After"),
                                left_items=elem.get("left_items", []),
                                right_items=elem.get("right_items", []))

        elif etype == "step_diagram":
            steps = elem.get("steps", [])
            bw = elem.get("box_w", 160)
            bh = elem.get("box_h", 50)
            gap = elem.get("gap", 60)
            self.draw_step_diagram(draw, x, y, steps, box_w=bw, box_h=bh, gap=gap)

        # ── Abstract / concept elements ──
        elif etype == "atom":
            r = elem.get("radius", 50)
            self.draw_atom(draw, x, y, r=r, color=fill)
        elif etype == "dna":
            w = elem.get("width", 160)
            h = elem.get("height", 180)
            self.draw_dna(draw, x, y, w=w, h=h, color=fill)
        elif etype == "heart":
            s = elem.get("scale", 1.0)
            self.draw_heart(draw, x, y, s=int(40 * s), color=fill)
        elif etype == "infinity":
            s = elem.get("scale", 1.0)
            self.draw_infinity(draw, x, y, s=int(50 * s), color=fill)
        elif etype == "target":
            r = elem.get("radius", 50)
            self.draw_target(draw, x, y, r=r, color=fill)
        elif etype == "puzzle":
            s = elem.get("scale", 1.0)
            self.draw_puzzle(draw, x, y, s=int(40 * s), color=fill)
        elif etype == "scales":
            s = elem.get("scale", 1.0)
            self.draw_scales(draw, x, y, s=int(40 * s), color=fill)
        elif etype == "astronaut":
            s = elem.get("scale", 1.0)
            self.draw_astronaut(draw, x, y, s=int(30 * s), color=fill)
        elif etype == "spaceship":
            s = elem.get("scale", 1.0)
            self.draw_spaceship(draw, x, y, s=int(35 * s), color=fill)
        elif etype == "hourglass":
            s = elem.get("scale", 1.0)
            self.draw_hourglass(draw, x, y, s=int(35 * s), color=fill)
        elif etype == "treasure_chest":
            s = elem.get("scale", 1.0)
            self.draw_treasure_chest(draw, x, y, s=int(35 * s), color=fill)
        elif etype == "gravestone":
            s = elem.get("scale", 1.0)
            self.draw_gravestone(draw, x, y, s=int(30 * s), color=fill)
        elif etype == "hat":
            s = elem.get("scale", 1.0)
            self.draw_hat(draw, x, y, s=int(28 * s), color=fill)

        # ── New diagram types ──
        elif etype == "network_diagram":
            nodes = elem.get("nodes", [])
            edges = elem.get("edges", [])
            r = elem.get("radius", 30)
            self.draw_network_diagram(draw, x, y, nodes, edges, r=r)

        elif etype == "tree_diagram":
            levels = elem.get("levels", [])
            self.draw_tree_diagram(draw, x, y, levels)

        elif etype == "histogram":
            data = elem.get("data", [])
            cw = elem.get("chart_w", 400)
            ch = elem.get("chart_h", 280)
            self.draw_histogram(draw, x, y, data, w=cw, h=ch, color=fill)

        elif etype == "scatter_plot":
            points = elem.get("points", [])
            cw = elem.get("chart_w", 400)
            ch = elem.get("chart_h", 300)
            self.draw_scatter_plot(draw, x, y, points, w=cw, h=ch, color=fill)

        else:
            # Try procedural generator from elements_pro
            try:
                from src.elements_pro import PROCEDURAL_LIBRARY as _pro_lib
                if etype in _pro_lib:
                    rng = getattr(self, 'rng', __import__('random').Random())
                    parts = _pro_lib[etype](rng, fill or None, s)
                    # elements_pro generators produce normalized (~0.001-0.30) values
                    self.draw_composite(draw, parts, x, y, scale=1000)
                    return
            except Exception:
                pass
            # Try infinite procedural engine (generate() auto-scales to pixels)
            try:
                from src.procedural_engine import ProceduralEngine as _PE
                _pe = _PE(seed=getattr(self, 'rng', __import__('random').Random()).randint(0, 999999))
                _kwargs = {"size": 1.0}
                if fill is not None:
                    _kwargs["color"] = fill
                parts = _pe.generate(etype, **_kwargs)
                if parts:
                    self.draw_composite(draw, parts, x, y, scale=s)
                    return
            except Exception:
                pass
            # Unknown type — draw with concept card
            label = elem.get("label", elem.get("text", etype))
            self.draw_concept(draw, x, y, label, fill, s)

    # ── Chart renderers ────────────────────────────────────────

    def draw_bar_chart(self, draw, x, y, data, w=400, h=300, bar_color=None, title=None):
        """Draw a bar chart. data = [(label, value), ...], values 0-1."""
        if not data: return
        bc = bar_color or (70, 130, 180)
        bars = data
        n = len(bars)
        if n == 0: return
        chart_left = x - w // 2 + 60
        chart_bottom = y + h // 2 - 30
        chart_top = y - h // 2 + 30
        chart_right = x + w // 2 - 20
        bar_w = max(10, (chart_right - chart_left) // n * 0.6)
        gap = (chart_right - chart_left) / n
        if title:
            self.draw_text(draw, x, chart_top - 20, title, font_size=18, color=(60, 55, 50))
        self.draw_line(draw, chart_left, chart_bottom, chart_right, chart_bottom, color=(100, 95, 90), width=2)
        self.draw_line(draw, chart_left, chart_top, chart_left, chart_bottom, color=(100, 95, 90), width=2)
        for i, (label, val) in enumerate(bars):
            v = max(val, 0.02)
            bar_h = int((chart_bottom - chart_top) * v)
            bx = int(chart_left + gap * i + (gap - bar_w) / 2)
            by = chart_bottom - bar_h
            shade = tuple(int(c * (0.6 + 0.4 * (i / max(n - 1, 1)))) for c in bc)
            self.draw_rect(draw, bx, by, int(bar_w), bar_h, fill=shade + (220,), stroke=tuple(min(255, c + 30) for c in shade) + (200,), stroke_width=1)
            self.draw_text(draw, bx + bar_w // 2, chart_bottom + 12, str(label)[:8], font_size=11, color=(80, 75, 70), align="center")
            self.draw_text(draw, bx + bar_w // 2, by - 10, f"{int(val*100)}%", font_size=10, color=(60, 55, 50), align="center")

    def draw_pie_chart(self, draw, x, y, data, radius=120):
        """Draw a pie chart. data = [(label, value), ...], values sum to 1."""
        if not data: return
        pie_colors = [(70,130,180),(220,120,60),(60,160,80),(200,80,80),(160,120,200),(180,160,60),(140,80,140),(80,180,180)]
        total = sum(v for _, v in data)
        if total == 0: return
        start_angle = 90
        cx, cy = x, y + 10
        legend_x = x + radius + 40
        legend_y = y - radius
        for i, (label, val) in enumerate(data):
            frac = val / total
            end_angle = start_angle - frac * 360
            c = pie_colors[i % len(pie_colors)]
            self.draw_arc(draw, cx, cy, radius, end_angle, start_angle, color=c, width=radius)
            mid = math.radians((start_angle + end_angle) / 2)
            lx = int(cx + math.cos(mid) * radius * 0.6)
            ly = int(cy - math.sin(mid) * radius * 0.6)
            pct = int(frac * 100)
            if pct >= 8:
                self.draw_text(draw, lx, ly, f"{pct}%", font_size=12, color=(255, 255, 255, 200), align="center")
            start_angle = end_angle
            lx2 = legend_x
            ly2 = legend_y + i * 22
            self.draw_rect(draw, lx2, ly2, 12, 12, fill=c + (220,))
            self.draw_text(draw, lx2 + 18, ly2 + 6, str(label)[:18], font_size=12, color=(60, 55, 50), align="left")

    def draw_line_graph(self, draw, x, y, data, w=400, h=280, line_color=None):
        """Draw a line graph. data = [(label, val), ...], vals 0-1."""
        if len(data) < 2: return
        lc = line_color or (200, 80, 60)
        chart_left = x - w // 2 + 60
        chart_bottom = y + h // 2 - 30
        chart_top = y - h // 2 + 30
        chart_right = x + w // 2 - 30
        self.draw_line(draw, chart_left, chart_bottom, chart_right, chart_bottom, color=(100, 95, 90), width=2)
        self.draw_line(draw, chart_left, chart_top, chart_left, chart_bottom, color=(100, 95, 90), width=2)
        points = []
        for i, (label, val) in enumerate(data):
            px = chart_left + (chart_right - chart_left) * i / max(len(data) - 1, 1)
            py = chart_bottom - (chart_bottom - chart_top) * min(max(val, 0), 1)
            points.append((int(px), int(py)))
        for i in range(len(points) - 1):
            self.draw_line(draw, points[i][0], points[i][1], points[i+1][0], points[i+1][1], color=lc + (220,), width=3)
        for i, (px, py) in enumerate(points):
            self.draw_circle(draw, px, py, 4, fill=(255,255,255,230), stroke=lc + (220,), stroke_width=2)
            label = str(data[i][0])[:6]
            self.draw_text(draw, px, chart_bottom + 12, label, font_size=10, color=(80, 75, 70), align="center")
            val_str = f"{int(data[i][1]*100)}%"
            self.draw_text(draw, px, py - 14, val_str, font_size=10, color=(60, 55, 50), align="center")

    def draw_cycle_diagram(self, draw, x, y, steps, radius=130):
        """Draw a cycle diagram. steps = [label, ...]."""
        if not steps: return
        n = len(steps)
        for i in range(n):
            angle = math.radians(i * 360 / n - 90)
            nx = int(x + math.cos(angle) * radius)
            ny = int(y + math.sin(angle) * radius)
            r2 = 40
            shade = (70 + i * 25, 130 + i * 10, 180)
            self.draw_circle(draw, nx, ny, r2, fill=shade + (200,), stroke=(40, 40, 60) + (180,), stroke_width=2)
            self.draw_text(draw, nx, ny, steps[i], font_size=11, color=(255, 255, 255, 230), align="center")
            if i > 0:
                prev_angle = math.radians((i - 1) * 360 / n - 90)
                px = int(x + math.cos(prev_angle) * radius)
                py = int(y + math.sin(prev_angle) * radius)
                mid_a = math.radians((i - 0.5) * 360 / n - 90)
                mx = int(x + math.cos(mid_a) * radius * 0.5)
                my = int(y + math.sin(mid_a) * radius * 0.5)
                self.draw_line(draw, px, py, nx, ny, color=(120, 140, 180, 150), width=2)
                arr_angle = math.atan2(ny - py, nx - px)
                hl = 10
                ax = nx - math.cos(arr_angle) * hl
                ay = ny - math.sin(arr_angle) * hl
                self.draw_polygon(draw, [(nx, ny), (int(ax + math.sin(arr_angle)*hl//2), int(ay - math.cos(arr_angle)*hl//2)), (int(ax - math.sin(arr_angle)*hl//2), int(ay + math.cos(arr_angle)*hl//2))], fill=(120, 140, 180, 180))

    def draw_venn_diagram(self, draw, x, y, left_label="A", right_label="B", common_label="Both", r=100):
        """Draw a Venn diagram with two overlapping circles."""
        offset = r // 2
        self.draw_circle(draw, x - offset, y, r, fill=(70, 130, 180, 100), stroke=(40, 80, 120, 200), stroke_width=2)
        self.draw_circle(draw, x + offset, y, r, fill=(200, 80, 80, 100), stroke=(140, 50, 50, 200), stroke_width=2)
        self.draw_text(draw, x - offset - r // 2, y, str(left_label)[:10], font_size=16, color=(40, 80, 120), align="center")
        self.draw_text(draw, x + offset + r // 2, y, str(right_label)[:10], font_size=16, color=(140, 50, 50), align="center")
        self.draw_text(draw, x, y, str(common_label)[:10], font_size=14, color=(100, 60, 60), align="center")

    def draw_comparison(self, draw, x, y, left_title="Before", right_title="After", left_items=None, right_items=None):
        """Draw a two-column comparison layout."""
        if left_items is None: left_items = ["Item A", "Item B", "Item C"]
        if right_items is None: right_items = ["Item X", "Item Y", "Item Z"]
        col_w = 160
        cx1 = x - col_w // 2 - 100
        cx2 = x + col_w // 2 + 100
        cy = y - 60
        self.draw_text(draw, cx1, cy, str(left_title)[:15], font_size=18, color=(70, 130, 180), align="center")
        self.draw_text(draw, cx2, cy, str(right_title)[:15], font_size=18, color=(200, 80, 60), align="center")
        self.draw_line(draw, x, y - 40, x, y + 100, color=(150, 145, 140, 150), width=2)
        for i, item in enumerate(left_items):
            iy = cy + 40 + i * 28
            self.draw_circle(draw, cx1 - 40, iy, 4, fill=(70, 130, 180, 200))
            self.draw_text(draw, cx1 - 30, iy, str(item)[:15], font_size=13, color=(60, 55, 50), align="left")
        for i, item in enumerate(right_items):
            iy = cy + 40 + i * 28
            self.draw_circle(draw, cx2 - 40, iy, 4, fill=(200, 80, 80, 200))
            self.draw_text(draw, cx2 - 30, iy, str(item)[:15], font_size=13, color=(60, 55, 50), align="left")

    def draw_step_diagram(self, draw, x, y, steps, box_w=160, box_h=50, gap=60):
        """Draw numbered steps with connecting arrows. steps = [label, ...]."""
        n = len(steps)
        if n == 0: return
        total_w = n * box_w + (n - 1) * gap
        start_x = x - total_w // 2 + box_w // 2
        for i, label in enumerate(steps):
            sx = start_x + i * (box_w + gap)
            shade = (70 + i * 20, 130 + i * 10, 180)
            self.draw_rect(draw, sx - box_w // 2, y - box_h // 2, box_w, box_h, fill=shade + (210,), stroke=(40, 40, 60) + (180,), stroke_width=2, rx=6)
            self.draw_text(draw, sx - box_w // 2 + 8, y - box_h // 2 + 4, f"{i+1}.", font_size=12, color=(255, 255, 255, 200), align="left")
            self.draw_text(draw, sx + 4, y, str(label)[:18], font_size=12, color=(255, 255, 255, 230), align="left")
            if i < n - 1:
                ax1 = sx + box_w // 2
                ax2 = sx + box_w // 2 + gap
                ay = y
                self.draw_line(draw, ax1, ay, ax2, ay, color=(120, 140, 180, 180), width=2)
                hl = 10
                self.draw_polygon(draw, [(ax2, ay), (ax2 - hl, ay - hl//2), (ax2 - hl, ay + hl//2)], fill=(120, 140, 180, 200))

    # ── Abstract / concept renderers ──

    def draw_atom(self, draw, x, y, r=50, color=None):
        c = color or (80, 140, 200)
        self.draw_circle(draw, x, y, 12, fill=(255, 255, 255, 200), stroke=c + (200,), stroke_width=2)
        for angle in (0, 60, 120):
            a = math.radians(angle)
            ex = int(x + math.cos(a) * r)
            ey = int(y + math.sin(a) * r)
            self.draw_ellipse(draw, x, y, r * 2 * 0.7, 8, stroke=c + (150 + angle,), stroke_width=2)

    def draw_dna(self, draw, x, y, w=160, h=180, color=None):
        c = color or (60, 140, 200)
        steps = 12
        for i in range(steps):
            t = i / (steps - 1)
            yp = y - h // 2 + t * h
            x1 = x - w // 2
            x2 = x + w // 2
            phase = t * math.pi * 4
            lx = x1 + math.sin(phase) * w * 0.15
            rx = x2 + math.sin(phase + math.pi) * w * 0.15
            self.draw_circle(draw, int(lx), int(yp), 4, fill=c + (200,))
            self.draw_circle(draw, int(rx), int(yp), 4, fill=(200, 80, 80, 200))
            mid_x = (lx + rx) / 2
            self.draw_line(draw, int(lx), int(yp), int(mid_x), int(yp), color=(150, 150, 150, 150), width=2)
            self.draw_line(draw, int(mid_x), int(yp), int(rx), int(yp), color=(150, 150, 150, 150), width=2)
        self.draw_line(draw, x - w // 2, y - h // 2, x - w // 2, y + h // 2, color=c + (150,), width=2)
        self.draw_line(draw, x + w // 2, y - h // 2, x + w // 2, y + h // 2, color=(200, 80, 80, 150), width=2)

    def draw_heart(self, draw, x, y, s=40, color=None):
        c = color or (220, 60, 80)
        pts = []
        for a in range(0, 360, 5):
            rad = math.radians(a)
            hx = x + int(s * 16 * math.sin(rad) ** 3)
            hy = y + int(s * (-13 * math.cos(rad) + 5 * math.cos(2 * rad) + 2 * math.cos(3 * rad) + math.cos(4 * rad)))
            pts.append((hx, hy))
        if len(pts) >= 3:
            self.draw_polygon(draw, pts, fill=c + (220,), stroke=tuple(min(255, v + 20) for v in c) + (200,), stroke_width=2)

    def draw_infinity(self, draw, x, y, s=50, color=None):
        c = color or (100, 160, 200)
        pts = []
        for a in range(0, 720, 3):
            rad = math.radians(a)
            denom = 1 + math.sin(rad) ** 2
            ix = x + int(s * 30 * math.cos(rad) / denom)
            iy = y + int(s * 15 * math.sin(rad) * math.cos(rad) / denom)
            pts.append((ix, iy))
        for i in range(len(pts) - 1):
            self.draw_line(draw, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color=c + (200,), width=3)

    def draw_target(self, draw, x, y, r=50, color=None):
        c = color or (200, 60, 60)
        for i in range(4):
            cr = r - i * (r // 4)
            fill_c = ((255 - i * 40, 255 - i * 40, 255 - i * 40) if i % 2 == 0 else c) + (200,)
            self.draw_circle(draw, x, y, cr, fill=fill_c, stroke=(60, 60, 60, 150), stroke_width=1)
        self.draw_line(draw, x - r, y, x + r, y, color=(60, 60, 60, 120), width=1)
        self.draw_line(draw, x, y - r, x, y + r, color=(60, 60, 60, 120), width=1)

    def draw_puzzle(self, draw, x, y, s=40, color=None):
        c = color or (180, 140, 80)
        hw, hh = int(25 * s), int(25 * s)
        pts = [(x - hw, y - hh), (x + hw, y - hh), (x + hw, y - hh // 3),
               (x + hw // 2, y - hh // 3), (x + hw // 2, y - hh // 6),
               (x + hw, y - hh // 6), (x + hw, y + hh),
               (x - hw, y + hh)]
        self.draw_polygon(draw, pts, fill=c + (200,), stroke=self._darken(c, 30) + (180,), stroke_width=2)
        self.draw_circle(draw, x - hw // 2, y - hh // 2, 4, fill=c + (200,))

    def draw_scales(self, draw, x, y, s=40, color=None):
        c = color or (180, 160, 100)
        sw = int(30 * s)
        self.draw_line(draw, x, y - sw, x, y + sw, color=c + (200,), width=3)
        self.draw_line(draw, x - sw, y - sw // 2, x + sw, y - sw // 2, color=c + (200,), width=2)
        self.draw_arc(draw, x, y + sw, int(8 * s), 0, 360, color=c + (200,), width=2)
        self.draw_polygon(draw, [(x - sw, y - sw * 3 // 4), (x - sw // 2, y - sw // 2), (x - sw, y - sw // 4)], fill=c + (180,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        self.draw_polygon(draw, [(x + sw, y - sw * 3 // 4), (x + sw // 2, y - sw // 2), (x + sw, y - sw // 4)], fill=c + (180,), stroke=self._darken(c, 20) + (150,), stroke_width=1)

    def draw_astronaut(self, draw, x, y, s=30, color=None):
        c = color or (220, 220, 230)
        self.draw_circle(draw, x, y - int(15 * s), int(12 * s), fill=c + (200,), stroke=(160, 160, 170, 200), stroke_width=2)
        self.draw_rect(draw, x - int(8 * s), y - int(5 * s), int(16 * s), int(20 * s), fill=c + (200,), stroke=(160, 160, 170, 200), stroke_width=2, rx=3)
        self.draw_circle(draw, x - int(4 * s), y - int(17 * s), int(3 * s), fill=(100, 140, 200, 180))
        self.draw_circle(draw, x + int(4 * s), y - int(17 * s), int(3 * s), fill=(100, 140, 200, 180))
        self.draw_rect(draw, x - int(12 * s), y + int(15 * s), int(8 * s), int(8 * s), fill=c + (180,), stroke=(160, 160, 170, 150), stroke_width=1, rx=2)
        self.draw_rect(draw, x + int(4 * s), y + int(15 * s), int(8 * s), int(8 * s), fill=c + (180,), stroke=(160, 160, 170, 150), stroke_width=1, rx=2)

    def draw_spaceship(self, draw, x, y, s=35, color=None):
        c = color or (160, 180, 210)
        self.draw_ellipse(draw, x, y, int(30 * s), int(12 * s), fill=c + (200,), stroke=(120, 140, 180, 200), stroke_width=2)
        self.draw_ellipse(draw, x, y - int(4 * s), int(10 * s), int(6 * s), fill=(100, 160, 255, 150), stroke=(80, 120, 200, 150), stroke_width=1)
        self.draw_polygon(draw, [(x, y + int(8 * s)), (x - int(6 * s), y + int(18 * s)), (x + int(6 * s), y + int(18 * s))], fill=(200, 100, 60, 200))
        self.draw_polygon(draw, [(x - int(15 * s), y - int(2 * s)), (x - int(28 * s), y + int(6 * s)), (x - int(15 * s), y + int(4 * s))], fill=c + (180,))
        self.draw_polygon(draw, [(x + int(15 * s), y - int(2 * s)), (x + int(28 * s), y + int(6 * s)), (x + int(15 * s), y + int(4 * s))], fill=c + (180,))

    def draw_hourglass(self, draw, x, y, s=35, color=None):
        c = color or (180, 160, 120)
        hw, hh = int(18 * s), int(30 * s)
        self.draw_polygon(draw, [(x - hw, y - hh), (x + hw, y - hh), (x + hw, y - hh + int(4 * s)), (x - hw, y - hh + int(4 * s))], fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)
        self.draw_polygon(draw, [(x - hw, y + hh), (x + hw, y + hh), (x + hw, y + hh - int(4 * s)), (x - hw, y + hh - int(4 * s))], fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)
        self.draw_polygon(draw, [(x - hw, y - hh + int(4 * s)), (x, y), (x + hw, y - hh + int(4 * s))], fill=(220, 190, 130, 180), stroke=c + (150,), stroke_width=1)
        self.draw_polygon(draw, [(x - hw, y + hh - int(4 * s)), (x, y), (x + hw, y + hh - int(4 * s))], fill=(220, 190, 130, 180), stroke=c + (150,), stroke_width=1)
        self.draw_line(draw, x, y - int(2 * s), x, y + int(2 * s), color=(200, 180, 100, 200), width=2)

    def draw_treasure_chest(self, draw, x, y, s=35, color=None):
        c = color or (140, 90, 50)
        hw, hh = int(22 * s), int(16 * s)
        self.draw_rect(draw, x - hw, y, int(2 * hw), hh, fill=c + (200,), stroke=self._darken(c, 30) + (180,), stroke_width=2, rx=4)
        self.draw_rect(draw, x - hw + int(2 * s), y - hh // 2, int(2 * hw) - int(4 * s), hh // 2, fill=(200, 180, 80, 220), stroke=(180, 150, 50, 180), stroke_width=2, rx=3)
        self.draw_rect(draw, x - int(3 * s), y + int(4 * s), int(6 * s), int(4 * s), fill=(200, 180, 80, 200), stroke=(180, 150, 50, 180), stroke_width=1)

    def draw_gravestone(self, draw, x, y, s=30, color=None):
        c = color or (160, 150, 140)
        hw, hh = int(16 * s), int(28 * s)
        self.draw_rect(draw, x - hw, y - hh, int(2 * hw), hh, fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2, rx=int(8 * s))
        self.draw_text(draw, x, y - hh // 2, "RIP", font_size=14, color=(80, 75, 70, 200), align="center")
        self.draw_line(draw, x - hw, y, x - hw, y + int(8 * s), color=c + (200,), width=int(3 * s))
        self.draw_line(draw, x + hw, y, x + hw, y + int(8 * s), color=c + (200,), width=int(3 * s))

    def draw_hat(self, draw, x, y, s=28, color=None):
        c = color or (180, 160, 100)
        hw, hh = int(20 * s), int(10 * s)
        self.draw_arc(draw, x, y, hw, 0, 180, color=self._darken(c, 10) + (200,), width=int(4 * s))
        self.draw_rect(draw, x - hw // 2, y - hh, hw, hh, fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2, rx=int(2 * s))
        self.draw_circle(draw, x, y - hh // 2 - int(3 * s), int(4 * s), fill=c + (200,))

    # ── New diagram types ──

    def draw_network_diagram(self, draw, x, y, nodes, edges, r=30, w=400, h=350):
        """Draw a network graph. nodes = [label, ...], edges = [(i, j), ...]."""
        if not nodes: return
        n = len(nodes)
        positions = []
        for i in range(n):
            angle = math.radians(i * 360 / n - 90)
            nx = x + int(math.cos(angle) * w * 0.4)
            ny = y + int(math.sin(angle) * h * 0.4)
            positions.append((nx, ny))
        for i, j in edges:
            if i < len(positions) and j < len(positions):
                self.draw_line(draw, positions[i][0], positions[i][1], positions[j][0], positions[j][1], color=(140, 150, 170, 120), width=2)
        for i, (nx, ny) in enumerate(positions):
            shade = (70 + i * 20, 130 + i * 10, 180)
            self.draw_circle(draw, nx, ny, r, fill=shade + (200,), stroke=(40, 40, 60, 180), stroke_width=2)
            if i < len(nodes):
                self.draw_text(draw, nx, ny, str(nodes[i])[:6], font_size=11, color=(255, 255, 255, 230), align="center")

    def draw_tree_diagram(self, draw, x, y, levels, box_w=120, box_h=35, level_h=70):
        """Draw a tree/hierarchy. levels = [[label, ...], [label, ...], ...] (top to bottom)."""
        if not levels: return
        def _draw_level(level_items, cy, parent_centers=None):
            n = len(level_items)
            total_w = n * box_w + (n - 1) * 20
            start_x = x - total_w // 2 + box_w // 2
            centers = []
            for i, label in enumerate(level_items):
                cx = start_x + i * (box_w + 20)
                cy_pos = cy
                shade = (80 + cy // 2, 130, 180)
                self.draw_rect(draw, cx - box_w // 2, cy_pos - box_h // 2, box_w, box_h, fill=shade + (210,), stroke=(40, 40, 60, 180), stroke_width=2, rx=4)
                self.draw_text(draw, cx, cy_pos, str(label)[:16], font_size=12, color=(255, 255, 255, 230), align="center")
                centers.append(cx)
                if parent_centers and i < len(parent_centers):
                    px = parent_centers[i] if i < len(parent_centers) else parent_centers[-1]
                    py = cy_pos - level_h // 2
                    self.draw_line(draw, px, py, cx, cy_pos - box_h // 2, color=(140, 150, 170, 150), width=2)
            return centers
        cy = y - len(levels) * level_h // 2
        parents = None
        for level in levels:
            parents = _draw_level(level, cy, parents)
            cy += level_h

    def draw_histogram(self, draw, x, y, data, w=400, h=280, color=None):
        """Draw a histogram (bar chart + normal curve overlay). data = [(label, val), ...]."""
        if not data: return
        bc = color or (70, 130, 180)
        chart_left = x - w // 2 + 60
        chart_bottom = y + h // 2 - 30
        chart_top = y - h // 2 + 30
        chart_right = x + w // 2 - 30
        n = len(data)
        bar_w = max(8, (chart_right - chart_left) // n * 0.7)
        gap = (chart_right - chart_left) / n
        self.draw_line(draw, chart_left, chart_bottom, chart_right, chart_bottom, color=(100, 95, 90), width=2)
        self.draw_line(draw, chart_left, chart_top, chart_left, chart_bottom, color=(100, 95, 90), width=2)
        max_val = max((v for _, v in data), default=1)
        for i, (label, val) in enumerate(data):
            v = max(val / max_val, 0.02)
            bar_h = int((chart_bottom - chart_top) * v)
            bx = int(chart_left + gap * i + (gap - bar_w) / 2)
            by = chart_bottom - bar_h
            self.draw_rect(draw, bx, by, int(bar_w), bar_h, fill=bc + (160,), stroke=self._darken(bc, 20) + (120,), stroke_width=1)
            self.draw_text(draw, bx + bar_w // 2, chart_bottom + 10, str(label)[:5], font_size=10, color=(80, 75, 70), align="center")
        curve_pts = []
        for i in range(101):
            t = i / 100
            px = chart_left + (chart_right - chart_left) * t
            py = chart_bottom - (chart_bottom - chart_top) * (math.exp(-((t - 0.5) ** 2) * 10) * 0.95 + 0.02)
            curve_pts.append((int(px), int(py)))
        for i in range(len(curve_pts) - 1):
            self.draw_line(draw, curve_pts[i][0], curve_pts[i][1], curve_pts[i + 1][0], curve_pts[i + 1][1], color=(200, 80, 60, 200), width=2)

    def draw_scatter_plot(self, draw, x, y, points, w=400, h=300, color=None):
        """Draw a scatter plot. points = [(label, x_val, y_val), ...], values 0-1."""
        if not points: return
        pc = color or (70, 130, 180)
        chart_left = x - w // 2 + 60
        chart_bottom = y + h // 2 - 30
        chart_top = y - h // 2 + 30
        chart_right = x + w // 2 - 30
        self.draw_line(draw, chart_left, chart_bottom, chart_right, chart_bottom, color=(100, 95, 90), width=2)
        self.draw_line(draw, chart_left, chart_top, chart_left, chart_bottom, color=(100, 95, 90), width=2)
        scatter_colors = [(70, 130, 180), (200, 80, 60), (60, 160, 80), (180, 160, 60), (160, 120, 200)]
        for i, (label, xv, yv) in enumerate(points):
            px = int(chart_left + (chart_right - chart_left) * min(max(xv, 0), 1))
            py = int(chart_bottom - (chart_bottom - chart_top) * min(max(yv, 0), 1))
            sc = scatter_colors[i % len(scatter_colors)]
            self.draw_circle(draw, px, py, 5, fill=sc + (220,), stroke=self._darken(sc, 20) + (180,), stroke_width=1)
            self.draw_text(draw, px + 8, py - 6, str(label)[:6], font_size=10, color=(60, 55, 50), align="left")
        for i in range(11):
            gx = int(chart_left + (chart_right - chart_left) * i / 10)
            gy = int(chart_top + (chart_bottom - chart_top) * i / 10)
            self.draw_line(draw, gx, chart_bottom, gx, chart_bottom + 4, color=(100, 95, 90, 100), width=1)
            txt = f"{int(i*10)}%"
            self.draw_text(draw, gx, chart_bottom + 14, txt, font_size=9, color=(120, 115, 110), align="center")
            if i > 0:
                self.draw_line(draw, chart_left, gy, chart_left - 4, gy, color=(100, 95, 90, 100), width=1)

    def draw_wave(self, draw, x, y, size=1.0, color=(40, 100, 180), foam_color=(240, 245, 250)):
        """Draw a dramatic curling ocean wave with foam, spray, and depth."""
        s = max(size, 0.3)
        c = tuple(color[:3])
        fc = tuple(foam_color[:3])

        # Underwater swirl (deep mass)
        swirl_pts = []
        for a in range(0, 220, 6):
            rad = math.radians(a)
            rw = 70 * s * (1 - (a / 220) * 0.4)
            rx = x + math.cos(rad) * rw
            ry = y - math.sin(rad) * 45 * s + 5 * s - (a / 220) * 20 * s
            swirl_pts.append((rx, ry))
        dc = self._darken(c, 50)
        self.draw_polygon(draw, swirl_pts, fill=dc + (160,), stroke=dc + (200,), stroke_width=1)

        # Wave body (curling shape with more dramatic arc)
        pts = []
        for a in range(0, 200, 5):
            rad = math.radians(a)
            rx = x + math.cos(rad) * 65 * s
            ry = y - math.sin(rad) * 45 * s - (a / 200) * 35 * s
            pts.append((rx, ry))
        self.draw_polygon(draw, pts, fill=c + (190,), stroke=self._darken(c, 30) + (200,), stroke_width=2)

        # Wave curl (the barrel) with highlight
        for offset in (0, 3):
            curl_pts = []
            for a in range(180, 270, 5):
                rad = math.radians(a)
                rx = x + math.cos(rad) * (40 + offset) * s
                ry = y - math.sin(rad) * (28 + offset) * s + 12 * s
                curl_pts.append((rx, ry))
            if curl_pts:
                alpha = 140 if offset == 0 else 60
                clr = self._lighten(c, 40) if offset == 0 else (255, 255, 255)
                self.draw_polygon(draw, curl_pts, fill=clr + (alpha,), stroke=None, stroke_width=0)

        # Foam at crest (thick, layered)
        for layer in range(3):
            offset_y = layer * 3
            for i in range(10 + layer * 2):
                fx = x + self.rng.randint(-25, 25) * s
                fy = y - 42 * s + offset_y + self.rng.randint(-4, 4) * s
                fr = (self.rng.randint(4, 12) - layer * 2) * s
                fa = self.rng.randint(120 + layer * 30, 200 + layer * 10)
                self.draw_circle(draw, int(fx), int(fy), max(int(fr), 1), fill=fc + (fa,))

        # Spray droplets (fine mist)
        for i in range(20):
            sx = x + self.rng.randint(-35, 35) * s
            sy = y - 48 * s - self.rng.randint(0, 18) * s
            sr = self.rng.uniform(0.5, 3.0)
            sa = self.rng.randint(60, 180)
            self.draw_circle(draw, int(sx), int(sy), max(int(sr), 1), fill=(255, 255, 255, sa))

        # Water surface base with ripples
        for row in range(2):
            wy = int(y + 22 * s + row * 8 * s)
            self.draw_line(draw, int(x - 75 * s), wy, int(x + 75 * s), wy, color=self._darken(c, 10) + (80 + row * 40,), width=2)

        # Foam trail on surface
        for i in range(5):
            ftx = int(x + self.rng.randint(-60, -20) * s)
            fty = int(y + 22 * s + self.rng.randint(-2, 2) * s)
            ftw = int(self.rng.randint(6, 14) * s)
            self.draw_ellipse(draw, ftx, fty, ftw, int(2 * s), fill=fc + (self.rng.randint(60, 120),))

    def draw_canoe(self, draw, x, y, size=1.0, color=(80, 55, 35)):
        """Draw a primitive dugout canoe with paddlers."""
        s = size
        c = tuple(color[:3])

        # Canoe hull (elongated oval)
        hull_pts = []
        for a in range(180, 360, 10):
            rad = math.radians(a)
            rx = x + math.cos(rad) * 55 * s
            ry = y + math.sin(rad) * 12 * s
            hull_pts.append((rx, ry))
        self.draw_polygon(draw, hull_pts, fill=c + (200,), stroke=self._darken(c, 25) + (180,), stroke_width=2)

        # Interior hollow
        inner_pts = []
        for a in range(180, 360, 10):
            rad = math.radians(a)
            rx = x + math.cos(rad) * 45 * s
            ry = y + math.sin(rad) * 8 * s
            inner_pts.append((rx, ry))
        self.draw_polygon(draw, inner_pts, fill=self._darken(c, 20) + (150,))

        # Human paddler 1 (forward)
        self.draw_human(draw, int(x - 15 * s), int(y - 15 * s), size=s * 0.35, color=(60, 50, 80), skin_color=(230, 195, 170))

        # Paddle 1
        px1 = int(x - 25 * s)
        py1 = int(y - 20 * s)
        self.draw_line(draw, px1, py1, px1 - 20 * s, int(y + 15 * s), color=(160, 130, 80, 200), width=3)
        self.draw_ellipse(draw, px1 - 22 * s, int(y + 10 * s), 8 * s, 6 * s, fill=(160, 130, 80, 180))

        # Human paddler 2 (aft)
        self.draw_human(draw, int(x + 20 * s), int(y - 15 * s), size=s * 0.35, color=(70, 60, 50), skin_color=(220, 185, 160))

        # Paddle 2
        px2 = int(x + 30 * s)
        py2 = int(y - 20 * s)
        self.draw_line(draw, px2, py2, px2 + 20 * s, int(y + 15 * s), color=(160, 130, 80, 200), width=3)
        self.draw_ellipse(draw, px2 + 18 * s, int(y + 10 * s), 8 * s, 6 * s, fill=(160, 130, 80, 180))

    def draw_whale(self, draw, x, y, size=1.0, color=(60, 70, 100)):
        """Draw a breaching whale with water splash, barnacles, and detail."""
        s = max(size, 0.3)
        c = tuple(color[:3])

        # Belly (lighter underside)
        belly_pts = []
        for a in range(0, 140, 8):
            rad = math.radians(a)
            rw = 50 * s * (1 - (a / 180) * 0.3)
            rx = x + math.cos(rad) * rw
            ry = y + math.sin(rad) * 18 * s
            belly_pts.append((rx, ry))
        belly_c = self._lighten(c, 40)
        self.draw_polygon(draw, belly_pts, fill=belly_c + (180,), stroke=None, stroke_width=0)

        # Body (dorsal curve)
        body_pts = []
        for a in range(0, 180, 6):
            rad = math.radians(a)
            rw = 52 * s * (1 - (a / 180) * 0.3)
            rx = x + math.cos(rad) * rw
            ry = y - math.sin(rad) * 26 * s
            body_pts.append((rx, ry))
        self.draw_polygon(draw, body_pts, fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

        # Tail flukes (more dramatic spread)
        tail_x = int(x - 45 * s)
        tail_y = int(y - 5 * s)
        fluke_c = self._darken(c, 15)
        self.draw_polygon(draw, [
            (tail_x, tail_y),
            (tail_x - 18 * s, tail_y - 15 * s),
            (tail_x - 6 * s, tail_y - 4 * s),
        ], fill=fluke_c + (200,), stroke=self._darken(fluke_c, 20) + (180,), stroke_width=1)
        self.draw_polygon(draw, [
            (tail_x, tail_y),
            (tail_x - 18 * s, tail_y + 15 * s),
            (tail_x - 6 * s, tail_y + 4 * s),
        ], fill=fluke_c + (200,), stroke=self._darken(fluke_c, 20) + (180,), stroke_width=1)

        # Dorsal fin
        df_x = int(x - 15 * s)
        df_y = int(y - 24 * s)
        self.draw_polygon(draw, [(df_x, df_y), (df_x - 4 * s, df_y - 8 * s), (df_x + 2 * s, df_y)], fill=c + (200,), stroke=self._darken(c, 20) + (160,), stroke_width=1)

        # Pectoral fin
        pf_x = int(x + 20 * s)
        pf_y = int(y + 12 * s)
        self.draw_polygon(draw, [(pf_x, pf_y), (pf_x - 8 * s, pf_y + 10 * s), (pf_x + 4 * s, pf_y)], fill=self._darken(c, 10) + (180,), stroke=None, stroke_width=0)

        # Eye
        self.draw_circle(draw, int(x + 32 * s), int(y - 12 * s), 2, fill=(20, 25, 30, 220))
        # Eye highlight
        self.draw_circle(draw, int(x + 33 * s), int(y - 13 * s), 1, fill=(200, 210, 230, 150))

        # Blowhole spray (more dramatic)
        for i in range(8):
            bx = int(x + 12 * s + self.rng.randint(-6, 6) * s)
            by = int(y - 30 * s - self.rng.randint(0, 12) * s)
            br = self.rng.randint(2, 5)
            self.draw_circle(draw, bx, by, br, fill=(220, 235, 250, self.rng.randint(80, 180)))
        # Spray arcs
        for arc_i in range(2):
            spray_pts = []
            base_x = int(x + 10 * s + arc_i * 8 * s)
            base_y = int(y - 28 * s)
            for t in range(0, 6):
                tx = base_x + t * 4 * s
                ty = base_y - (6 - t) * 3 * s
                spray_pts.append((tx, ty))
            for i in range(len(spray_pts)-1):
                self.draw_line(draw, int(spray_pts[i][0]), int(spray_pts[i][1]),
                              int(spray_pts[i+1][0]), int(spray_pts[i+1][1]),
                              color=(220, 235, 250, 120), width=1)

        # Splash at waterline
        for i in range(10):
            spx = int(x + self.rng.randint(-40, 40) * s)
            spy = int(y + 22 * s + self.rng.randint(0, 6) * s)
            spw = self.rng.randint(4, 10) * s
            sph = 3 * s
            self.draw_ellipse(draw, spx, spy, spw, max(int(sph), 1), fill=(200, 225, 245, self.rng.randint(80, 160)))

        # Water trail behind tail
        for i in range(4):
            tx = int(tail_x - 25 * s - i * 8 * s)
            ty = int(tail_y + 20 * s + self.rng.randint(-3, 3) * s)
            tw = int(self.rng.randint(10, 18) * s)
            self.draw_ellipse(draw, tx, ty, tw, int(2 * s), fill=(200, 225, 245, self.rng.randint(40, 90)))

        # Barnacles on body
        for _ in range(4):
            bx = int(x + self.rng.randint(5, 25) * s * (1 if self.rng.random() < 0.5 else -1))
            by = int(y + self.rng.randint(-15, 15) * s)
            self.draw_circle(draw, bx, by, self.rng.randint(1, 2), fill=(140, 130, 110, self.rng.randint(100, 180)))

    def draw_shark(self, draw, x, y, size=1.0, color=(80, 85, 95)):
        """Draw a shark fin cutting through water, with submerged body hint."""
        s = size
        c = tuple(color[:3])

        # Dorsal fin
        fin_pts = []
        for a in range(30, 150, 8):
            rad = math.radians(a)
            rx = x + math.cos(rad) * 18 * s
            ry = y - math.sin(rad) * 20 * s
            fin_pts.append((rx, ry))
        self.draw_polygon(draw, fin_pts, fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

        # Water disturbance around fin
        for i in range(5):
            wx = int(x + self.rng.randint(-20, 20) * s)
            wy = int(y + self.rng.randint(-3, 3) * s)
            self.draw_ellipse(draw, wx, wy, self.rng.randint(8, 16) * s, 3 * s, fill=(180, 210, 240, self.rng.randint(60, 120)))

        # Submerged body hint (darker shape below surface)
        body_pts = []
        for a in range(0, 180, 10):
            rad = math.radians(a)
            rx = x + math.cos(rad) * 35 * s
            ry = y + math.sin(rad) * 10 * s + 5 * s
            body_pts.append((rx, ry))
        self.draw_polygon(draw, body_pts, fill=self._darken(c, 40) + (60,), stroke=None)

    def draw_sea_serpent(self, draw, x, y, size=1.0, color=(40, 100, 60), belly_color=(180, 200, 160)):
        """Draw a mythical sea serpent — coiled body rising from water."""
        s = size
        c = tuple(color[:3])
        bc = tuple(belly_color[:3])

        # Coils (body loops emerging from water)
        for i in range(3):
            coil_y = y - i * 20 * s
            coil_x = x + i * 8 * s
            self.draw_ellipse(draw, int(coil_x), int(coil_y), 25 * s - i * 3 * s, 16 * s - i * 2 * s, fill=c + (180,), stroke=self._darken(c, 20) + (160,), stroke_width=2)
            self.draw_ellipse(draw, int(coil_x + 2 * s), int(coil_y + 2 * s), 10 * s, 8 * s, fill=bc + (120,))

        # Neck rising
        neck_pts = [
            (x - 5 * s, y - 55 * s),
            (x + 5 * s, y - 65 * s),
            (x - 8 * s, y - 80 * s),
            (x + 12 * s, y - 85 * s),
            (x + 3 * s, y - 90 * s),
        ]
        self.draw_line(draw, neck_pts[0][0], neck_pts[0][1], neck_pts[-1][0], neck_pts[-1][1], color=c + (180,), width=8)
        for i in range(len(neck_pts) - 1):
            self.draw_line(draw, neck_pts[i][0], neck_pts[i][1], neck_pts[i+1][0], neck_pts[i+1][1], color=c + (200,), width=6)

        # Head
        head_pts = []
        for a in range(0, 360, 20):
            rad = math.radians(a)
            rx = neck_pts[-1][0] + math.cos(rad) * 12 * s
            ry = neck_pts[-1][1] + math.sin(rad) * 8 * s
            head_pts.append((rx, ry))
        self.draw_polygon(draw, head_pts, fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

        # Eyes (glowing)
        self.draw_circle(draw, int(neck_pts[-1][0] + 4 * s), int(neck_pts[-1][1] - 3 * s), 2, fill=(255, 200, 50, 220))
        self.draw_circle(draw, int(neck_pts[-1][0] + 4 * s), int(neck_pts[-1][1] - 3 * s), 4, fill=(200, 255, 100, 60))

        # Forked tongue
        tx = int(neck_pts[-1][0] + 14 * s)
        ty = int(neck_pts[-1][1] + 2 * s)
        self.draw_line(draw, int(neck_pts[-1][0] + 10 * s), int(neck_pts[-1][1] + 2 * s), tx + 8 * s, ty - 4 * s, color=(200, 80, 60, 200), width=2)
        self.draw_line(draw, int(neck_pts[-1][0] + 10 * s), int(neck_pts[-1][1] + 2 * s), tx + 8 * s, ty + 4 * s, color=(200, 80, 60, 200), width=2)

        # Water splash at base
        for i in range(6):
            spx = int(x + self.rng.randint(-20, 20) * s)
            spy = int(y + 10 * s + self.rng.randint(0, 5) * s)
            self.draw_ellipse(draw, spx, spy, self.rng.randint(5, 10) * s, 3 * s, fill=(200, 225, 245, self.rng.randint(80, 140)))

    def draw_totem(self, draw, x, y, size=1.0, color=(120, 105, 85)):
        """Draw an ancient standing stone / monolith / totem pole with carvings."""
        s = size
        c = tuple(color[:3])

        # Main pillar
        pw = 18 * s
        ph = 80 * s
        self.draw_rect(draw, int(x - pw), int(y - ph), int(pw * 2), int(ph), fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

        # Top cap (rounded)
        cap_pts = []
        for a in range(0, 180, 10):
            rad = math.radians(a)
            rx = x + math.cos(rad) * pw
            ry = y - ph + math.sin(rad) * 6 * s
            cap_pts.append((rx, ry))
        self.draw_polygon(draw, cap_pts, fill=self._lighten(c, 15) + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

        # Carving lines (weathering / ancient symbols)
        for i in range(3):
            cy = y - ph + 15 * s + i * 20 * s
            self.draw_line(draw, int(x - pw + 4 * s), int(cy), int(x + pw - 4 * s), int(cy), color=self._darken(c, 30) + (100,), width=1)
            # Circle carving
            self.draw_circle(draw, int(x), int(cy - 5 * s), int(4 * s), fill=None, stroke=self._darken(c, 30) + (80,), stroke_width=1)

        # Base moss/grass
        for i in range(5):
            gx = int(x + self.rng.randint(-int(pw), int(pw)))
            gy = int(y + self.rng.randint(-2, 2))
            self.draw_line(draw, gx, gy, gx + self.rng.randint(-3, 3), gy - self.rng.randint(4, 8), color=(50 + self.rng.randint(0, 30), 100 + self.rng.randint(0, 30), 40 + self.rng.randint(0, 20), 150), width=1)

    def draw_anchor(self, draw, x, y, size=1.0, color=(80, 75, 70)):
        """Draw a classic nautical anchor with rope."""
        s = size
        c = tuple(color[:3])

        # Main shaft
        self.draw_line(draw, int(x), int(y - 35 * s), int(x), int(y + 20 * s), color=c + (200,), width=4)

        # Crossbar
        self.draw_line(draw, int(x - 15 * s), int(y - 28 * s), int(x + 15 * s), int(y - 28 * s), color=c + (200,), width=3)

        # Ring at top
        self.draw_circle(draw, int(x), int(y - 38 * s), int(4 * s), fill=None, stroke=c + (200,), stroke_width=2)

        # Curved arms
        arm_pts = []
        for a in range(20, 160, 10):
            rad = math.radians(a)
            rx = x + math.cos(rad) * 22 * s
            ry = y + 20 * s - math.sin(rad) * 10 * s
            arm_pts.append((rx, ry))
        self.draw_line(draw, arm_pts[0][0], arm_pts[0][1], arm_pts[-1][0], arm_pts[-1][1], color=c + (200,), width=3)

        # Flukes (arrow tips at arm ends)
        fluke_size = 6 * s
        self.draw_polygon(draw, [
            (arm_pts[-1][0], arm_pts[-1][1]),
            (arm_pts[-1][0] + fluke_size, arm_pts[-1][1] - fluke_size),
            (arm_pts[-1][0] + fluke_size, arm_pts[-1][1] + fluke_size),
        ], fill=c + (200,))
        self.draw_polygon(draw, [
            (arm_pts[0][0], arm_pts[0][1]),
            (arm_pts[0][0] - fluke_size, arm_pts[0][1] - fluke_size),
            (arm_pts[0][0] - fluke_size, arm_pts[0][1] + fluke_size),
        ], fill=c + (200,))

        # Rope coiled on crossbar
        rope_color = (160, 140, 100)
        for i in range(3):
            rx = int(x - 12 * s + i * 12 * s)
            ry = int(y - 26 * s + i * 2 * s)
            self.draw_circle(draw, rx, ry, int(2 * s), fill=rope_color + (200,))

    def draw_cliff(self, draw, x, y, size=1.0, color=(100, 80, 60)):
        """Draw a dramatic sea cliff with jagged edges, grass top, and erosion lines."""
        s = max(size, 0.3)
        c = tuple(color[:3])
        w = int(120 * s)
        h = int(180 * s)
        left = int(x)
        top = int(y - h)

        # Cliff body (jagged polygon)
        cliff_pts = [(left, int(y))]
        segments = 10
        for i in range(segments + 1):
            t = i / segments
            cx = left + w * t + self.rng.randint(-8, 8) * s
            cy = top + h * (1 - t * 0.9) + self.rng.randint(-10, 10) * s * (1 - t)
            cliff_pts.append((cx, cy))
        cliff_pts.append((left + w, int(y)))
        self.draw_polygon(draw, cliff_pts, fill=c + (220,), stroke=self._darken(c, 25) + (200,), stroke_width=2)

        # Erosion lines / cracks
        for _ in range(5):
            ex1 = left + self.rng.randint(10, w - 10) * s
            ey1 = top + self.rng.randint(20, h - 30) * s
            ex2 = ex1 + self.rng.randint(-10, 10) * s
            ey2 = ey1 + self.rng.randint(15, 30) * s
            self.draw_line(draw, int(ex1), int(ey1), int(ex2), int(ey2),
                          color=self._darken(c, 30) + (120,), width=1)

        # Ledge highlights
        for _ in range(3):
            lx = left + self.rng.randint(5, w - 5) * s
            ly = top + self.rng.randint(40, h - 40) * s
            lw = self.rng.randint(8, 20) * s
            self.draw_line(draw, int(lx), int(ly), int(lx + lw), int(ly),
                          color=self._lighten(c, 30) + (80,), width=1)

        # Grass on top
        grass_c = (50, 90, 40)
        for _ in range(8):
            gx = left + self.rng.randint(5, w - 5) * s
            gy = top + self.rng.randint(-3, 3) * s
            gh = self.rng.randint(6, 14) * s
            self.draw_line(draw, int(gx), int(gy), int(gx + self.rng.randint(-3, 3) * s), int(gy - gh),
                          color=grass_c + (self.rng.randint(150, 210),), width=1)

        # Wave crash at cliff base
        foam_c = (240, 245, 250)
        for i in range(6):
            fx = left + self.rng.randint(5, w - 5) * s
            fy = int(y - self.rng.randint(0, 8) * s)
            fr = self.rng.randint(3, 8) * s
            self.draw_circle(draw, int(fx), int(fy), max(int(fr), 1),
                            fill=foam_c + (self.rng.randint(80, 160),))

    def draw_compass_rose(self, draw, x, y, size=1.0, color=(180, 160, 120)):
        """Draw a compass rose / wind rose for navigation charts."""
        s = max(size, 0.3)
        c = tuple(color[:3])

        # Outer ring
        outer_r = int(30 * s)
        inner_r = int(26 * s)
        draw.ellipse([x - outer_r, y - outer_r, x + outer_r, y + outer_r],
                     fill=None, outline=c + (200,), width=2)
        draw.ellipse([x - inner_r, y - inner_r, x + inner_r, y + inner_r],
                     fill=None, outline=c + (120,), width=1)

        # Cardinal points (N, S, E, W)
        directions = [(0, -1, "N", (200, 60, 60)), (0, 1, "S", c),
                      (1, 0, "E", c), (-1, 0, "W", c)]
        for dx, dy, label, lc in directions:
            tip = (int(x + dx * outer_r), int(y + dy * outer_r))
            base1 = (int(x + dx * 8 * s - dy * 8 * s), int(y + dy * 8 * s + dx * 8 * s))
            base2 = (int(x + dx * 8 * s + dy * 8 * s), int(y + dy * 8 * s - dx * 8 * s))
            self.draw_polygon(draw, [tip, base1, base2], fill=lc + (200,),
                            stroke=self._darken(lc, 20) + (180,), stroke_width=1)
            # Label
            lx = int(x + dx * (outer_r + 12))
            ly = int(y + dy * (outer_r + 12))
            draw.text((lx, ly), label, fill=c + (200,),
                     font=self._get_font(12 * s) if hasattr(self, '_get_font') else None,
                     anchor="mm")

        # Intercardinal points
        for dx, dy in [(0.707, -0.707), (0.707, 0.707), (-0.707, -0.707), (-0.707, 0.707)]:
            tip = (int(x + dx * outer_r), int(y + dy * outer_r))
            base1 = (int(x + dx * 5 * s - dy * 5 * s), int(y + dy * 5 * s + dx * 5 * s))
            base2 = (int(x + dx * 5 * s + dy * 5 * s), int(y + dy * 5 * s - dx * 5 * s))
            self.draw_polygon(draw, [tip, base1, base2], fill=self._lighten(c, 30) + (160,), stroke=None, stroke_width=0)

        # Center dot
        self.draw_circle(draw, x, y, 3, fill=c + (220,))

    def draw_shadow_figure(self, draw, x, y, size=1.0, color=(20, 25, 30)):
        """Draw a dramatic silhouette/shadow figure - backlit, mysterious."""
        s = max(size, 0.3)
        c = tuple(color[:3])

        # Head
        head_r = int(8 * s)
        self.draw_circle(draw, x, int(y - 40 * s), head_r, fill=c + (220,))

        # Body
        body_pts = [
            (x - 12 * s, int(y - 32 * s)),
            (x + 12 * s, int(y - 32 * s)),
            (x + 14 * s, int(y)),
            (x - 14 * s, int(y)),
        ]
        self.draw_polygon(draw, body_pts, fill=c + (220,), stroke=None, stroke_width=0)

        # Arms (dramatic outstretched pose)
        # Left arm
        arm_pts = [(x - 10 * s, int(y - 26 * s)),
                   (x - 28 * s, int(y - 32 * s)),
                   (x - 32 * s, int(y - 28 * s))]
        self.draw_polygon(draw, arm_pts, fill=c + (220,), stroke=None, stroke_width=0)
        # Right arm
        arm_pts2 = [(x + 10 * s, int(y - 26 * s)),
                    (x + 28 * s, int(y - 32 * s)),
                    (x + 32 * s, int(y - 28 * s))]
        self.draw_polygon(draw, arm_pts2, fill=c + (220,), stroke=None, stroke_width=0)

        # Legs
        leg_len = 20 * s
        self.draw_polygon(draw, [
            (x - 6 * s, int(y)),
            (x + 2 * s, int(y)),
            (x + 4 * s, int(y + leg_len)),
            (x - 8 * s, int(y + leg_len)),
        ], fill=c + (220,), stroke=None, stroke_width=0)
        self.draw_polygon(draw, [
            (x - 2 * s, int(y)),
            (x + 6 * s, int(y)),
            (x + 8 * s, int(y + leg_len)),
            (x - 4 * s, int(y + leg_len)),
        ], fill=c + (220,), stroke=None, stroke_width=0)

        # Rim light (subtle glow on one side)
        glow_pts = [(x + 12 * s, int(y - 28 * s)),
                    (x + 14 * s, int(y - 20 * s)),
                    (x + 12 * s, int(y))]
        self.draw_polygon(draw, glow_pts, fill=(255, 220, 150, 40), stroke=None, stroke_width=0)

    def draw_moon_path(self, draw, x, y, size=1.0, color=(200, 210, 230)):
        """Draw moonlight reflection path on water - shimmering, ethereal."""
        s = max(size, 0.3)
        c = tuple(color[:3])
        path_width = int(40 * s)
        path_height = int(100 * s)
        left = int(x - path_width // 2)

        # Layered shimmer columns
        for col in range(7):
            cx = left + col * (path_width // 7)
            base_alpha = 100 - col * 10
            for row in range(12):
                ry = int(y + row * (path_height // 12))
                rw = self.rng.randint(3, 8) * s
                ra = self.rng.randint(max(0, base_alpha - 40), base_alpha)
                self.draw_ellipse(draw, int(cx - rw // 2), ry, int(rw), max(int(2 * s), 1),
                                fill=self._lighten(c, self.rng.randint(0, 20)) + (ra,))

        # Bright center path
        for row in range(10):
            cy = int(y + row * (path_height // 10))
            cw = self.rng.randint(6, 14) * s
            ca = self.rng.randint(100, 200) - row * 5
            if ca > 30:
                self.draw_ellipse(draw, int(x - cw // 2), cy, int(cw), max(int(2 * s), 1),
                                fill=(255, 255, 250, max(ca, 20)))

    def draw_jar(self, draw, x, y, size=1.0, color=(200, 210, 220)):
        """Draw a glass jar with warm inner glow."""
        s = max(size * 25, 15)
        neck_w = s * 0.3
        neck_h = s * 0.2
        body_w = s * 0.8
        body_h = s * 0.9
        cx = x
        cy = y
        base = tuple(min(c + 40, 255) for c in color[:3])
        glow = tuple(min(c + 80, 255) for c in color[:3])

        # Inner glow (warm light inside)
        self.draw_ellipse(draw, cx - body_w * 0.3, cy - body_h * 0.8,
                         body_w * 0.6, body_h * 0.6,
                         fill=glow + (60,))

        # Jar body (semi-transparent glass)
        body_points = [
            (cx - neck_w * 0.5, cy - body_h * 0.3),
            (cx - body_w * 0.5, cy - body_h * 0.1),
            (cx - body_w * 0.5, cy + body_h * 0.4),
            (cx - body_w * 0.3, cy + body_h * 0.5),
            (cx + body_w * 0.3, cy + body_h * 0.5),
            (cx + body_w * 0.5, cy + body_h * 0.4),
            (cx + body_w * 0.5, cy - body_h * 0.1),
            (cx + neck_w * 0.5, cy - body_h * 0.3),
        ]
        self.draw_polygon(draw, body_points, fill=color[:3] + (80,), stroke=(255, 255, 255, 60), stroke_width=1)

        # Neck
        neck_points = [
            (cx - neck_w * 0.4, cy - body_h * 0.3),
            (cx - neck_w * 0.6, cy - body_h * 0.45),
            (cx - neck_w * 0.5, cy - body_h * 0.55),
            (cx + neck_w * 0.5, cy - body_h * 0.55),
            (cx + neck_w * 0.6, cy - body_h * 0.45),
            (cx + neck_w * 0.4, cy - body_h * 0.3),
        ]
        self.draw_polygon(draw, neck_points, fill=color[:3] + (60,), stroke=(255, 255, 255, 40), stroke_width=1)

        # Lid
        self.draw_rect(draw, cx - neck_w * 0.5, cy - body_h * 0.55,
                      neck_w, neck_h * 0.3,
                      fill=(160, 140, 100, 180))

        # Glass highlight
        self.draw_ellipse(draw, cx - body_w * 0.35, cy - body_h * 0.2,
                         body_w * 0.12, body_h * 0.3,
                         fill=(255, 255, 255, 30))

    def draw_shelf(self, draw, x, y, size=1.0, color=(120, 90, 60)):
        """Draw a wooden shelf."""
        s = max(size * 40, 20)
        w = s * 1.2
        h = s * 0.12
        cx = x
        cy = y
        base = tuple(color[:3])

        # Shelf top (lighter)
        self.draw_rect(draw, cx - w / 2, cy - h / 2, w, h * 0.6,
                      fill=self._lighten(base, 20))

        # Shelf front (darker)
        self.draw_rect(draw, cx - w / 2, cy, w, h * 0.5,
                      fill=self._darken(base, 30))

        # Shadow below
        self.draw_rect(draw, cx - w / 2 + 4, cy + h * 0.3, w - 8, h * 0.2,
                      fill=(0, 0, 0, 30))

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
      "type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|circle|rect|polygon|line|text|label|ship|building|cannon|flag|x_mark|arrow|grass|path|bird|animal|fish|flower|fire|cave|volcano|wave|canoe|whale|shark|sea_serpent|totem|anchor|compass|globe|cliff|compass_rose|shadow_figure|moon_path",
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
