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


SKETCH_TECHNIQUES = {
    "pencil": {
        "stroke": (20, 18, 15),        # dark pencil — bolder outlines
        "stroke_width": 2,
        "fill_t": 0.35,                # how much to lighten fills
        "paper_tint": (250, 245, 235),
        "noise": 35,
        "blur_sigma": 0.4,
        "edge_strength": 0.5,
        "grain": 0.07,
        "label": "Pencil Sketch",
    },
    "pen": {
        "stroke": (15, 12, 10),        # dark ink
        "stroke_width": 3,
        "fill_t": 0.45,
        "paper_tint": (255, 250, 240),
        "noise": 15,
        "blur_sigma": 0.1,
        "edge_strength": 0.7,
        "grain": 0.02,
        "label": "Pen & Ink",
    },
    "charcoal": {
        "stroke": (25, 22, 25),        # dark, slightly warm
        "stroke_width": 4,
        "fill_t": 0.50,
        "paper_tint": (235, 225, 210),
        "noise": 50,
        "blur_sigma": 0.8,
        "edge_strength": 0.6,
        "grain": 0.10,
        "label": "Charcoal",
    },
    "watercolor": {
        "stroke": (55, 50, 60),        # soft edges
        "stroke_width": 1,
        "fill_t": 0.20,
        "paper_tint": (252, 248, 240),
        "noise": 20,
        "blur_sigma": 1.2,
        "edge_strength": 0.2,
        "grain": 0.05,
        "label": "Watercolor",
    },
    "comic": {
        "stroke": (10, 10, 10),        # bold black
        "stroke_width": 5,
        "fill_t": 0.15,
        "paper_tint": (255, 255, 255),
        "noise": 5,
        "blur_sigma": 0.0,
        "edge_strength": 0.9,
        "grain": 0.0,
        "label": "Comic",
    },
}


class SketchGenerator:
    """Generate detailed, full-color illustrations from structured scene descriptions."""

    def __init__(self, width=W, height=H, seed=None, hand_drawn=True):
        self.w = width
        self.h = height
        self.rng = random.Random(seed)
        self.hand_drawn = hand_drawn

        # Resolve sketch technique
        if isinstance(hand_drawn, str):
            self.technique = SKETCH_TECHNIQUES.get(hand_drawn, SKETCH_TECHNIQUES["pencil"])
        elif hand_drawn:
            self.technique = SKETCH_TECHNIQUES["pencil"]
        else:
            self.technique = None

        self.paper_color = tuple(self.technique["paper_tint"]) if self.technique else (255, 255, 255)
        self._clean_canvas = None

    def get_clean_canvas(self):
        """Return the pre-_post_process canvas, or None if not yet rendered."""
        return self._clean_canvas

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

    def _sketchify_fill(self, fill):
        """Lighten/desaturate fill colors for hand-drawn sketch appearance."""
        if fill is None or self.technique is None: return fill
        if isinstance(fill, int): return fill
        try:
            c = tuple(fill[:3])
            t = self.technique["fill_t"]
            paper = self.paper_color
            return tuple(int(a + (b - a) * t) for a, b in zip(c, paper))
        except (TypeError, IndexError):
            return fill
        return c

    @staticmethod
    def _darken(c, amount=30):
        return tuple(max(0, v - amount) for v in c[:3])

    # ── Sketch rendering helpers ─────────────────────────────────

    def _hatch_fill(self, draw, polygon, color=(20, 18, 15), density=1.5, angle=45):
        if not polygon or len(polygon) < 3:
            return
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        min_x, max_x = int(min(xs)), int(max(xs))
        min_y, max_y = int(min(ys)), int(max(ys))
        rad = math.radians(angle)
        spacing = density * 3
        diag = max(max_x - min_x, max_y - min_y)
        for i in range(int(diag / spacing) + 2):
            off = i * spacing
            hx1 = min_x + off * math.cos(rad)
            hy1 = min_y + off * math.sin(rad)
            hx2 = min_x + off * math.cos(rad) + diag * math.sin(rad)
            hy2 = min_y + off * math.sin(rad) + diag * math.cos(rad)
            c = tuple(color[:3]) + (80,)
            draw.line([(hx1, hy1), (hx2, hy2)], fill=c, width=1)

    def _wobble_points(self, pts, amount=2.0, freq=5):
        result = []
        for i, (x, y) in enumerate(pts):
            t = i / max(len(pts) - 1, 1)
            wobble_x = amount * math.sin(t * freq * math.pi * 2 + self.rng.random() * 0.5)
            wobble_y = amount * math.cos(t * freq * math.pi * 2 + self.rng.random() * 0.5)
            result.append((x + wobble_x, y + wobble_y))
        return result

    def _sample_ellipse_pts(self, cx, cy, rx, ry, n=20):
        pts = []
        for i in range(n + 1):
            a = 2 * math.pi * i / n
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        return pts

    def _sketch_line(self, draw, x1, y1, x2, y2, color, width, passes=2):
        steps = max(6, int(math.sqrt((x2-x1)**2 + (y2-y1)**2) / 3))
        base_pts = []
        for i in range(steps + 1):
            t = i / steps
            base_pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
        for p in range(passes):
            pts = self._wobble_points(base_pts, amount=1.0 + p * 0.5, freq=4 + p * 2)
            w = max(1, width + self.rng.randint(-1, 1))
            alpha = max(40, 200 - p * 50)
            c = tuple(color[:3]) + (alpha,)
            for i in range(len(pts) - 1):
                draw.line([pts[i], pts[i+1]], fill=c, width=w)

    def _sketch_ellipse(self, draw, cx, cy, rx, ry, fill=None, stroke=None, stroke_width=2):
        pts = self._sample_ellipse_pts(cx, cy, rx, ry, n=24)
        if fill:
            hatch_angle = self.rng.choice([30, 45, 60])
            self._hatch_fill(draw, pts, color=fill, density=1.2, angle=hatch_angle)
        if stroke or not fill:
            line_color = stroke or (20, 18, 15)
            for p in range(2):
                wobbled = self._wobble_points(pts, amount=1.0 + p, freq=4)
                w = max(1, stroke_width + self.rng.randint(-1, 1))
                alpha = 180 - p * 50
                c = tuple(line_color[:3]) + (alpha,)
                for i in range(len(wobbled) - 1):
                    draw.line([wobbled[i], wobbled[i+1]], fill=c, width=w)

    def _sketch_rect(self, draw, x, y, w, h, fill=None, stroke=None, stroke_width=2, rx=0):
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        if fill:
            hatch_angle = self.rng.choice([30, 45, 60])
            self._hatch_fill(draw, pts, color=fill, density=1.2, angle=hatch_angle)
        if stroke or not fill:
            line_color = stroke or (20, 18, 15)
            for p in range(2):
                wobbled = self._wobble_points(pts, amount=1.0 + p, freq=4)
                w = max(1, stroke_width + self.rng.randint(-1, 1))
                alpha = 180 - p * 50
                c = tuple(line_color[:3]) + (alpha,)
                for i in range(len(wobbled)):
                    j = (i + 1) % len(wobbled)
                    draw.line([wobbled[i], wobbled[j]], fill=c, width=w)

    def _sketch_polygon(self, draw, points, fill=None, stroke=None, stroke_width=2):
        if fill:
            hatch_angle = self.rng.choice([30, 45, 60])
            self._hatch_fill(draw, points, color=fill, density=1.2, angle=hatch_angle)
        if stroke or not fill:
            line_color = stroke or (20, 18, 15)
            for p in range(2):
                wobbled = self._wobble_points(points, amount=1.0 + p, freq=4)
                w = max(1, stroke_width + self.rng.randint(-1, 1))
                alpha = 180 - p * 50
                c = tuple(line_color[:3]) + (alpha,)
                for i in range(len(wobbled)):
                    j = (i + 1) % len(wobbled)
                    draw.line([wobbled[i], wobbled[j]], fill=c, width=w)

    def _sketch_circle(self, draw, cx, cy, r, fill=None, stroke=None, stroke_width=2):
        self._sketch_ellipse(draw, cx, cy, r, r, fill=fill, stroke=stroke, stroke_width=stroke_width)

    def _sketch_arc(self, draw, cx, cy, r, start_angle, end_angle, color=(0, 0, 0), width=2):
        n = max(8, int(r * 0.3))
        pts = []
        start_r = math.radians(start_angle)
        end_r = math.radians(end_angle)
        if end_r <= start_r:
            end_r += 2 * math.pi
        for i in range(n + 1):
            a = start_r + (end_r - start_r) * i / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for p in range(2):
            wobbled = self._wobble_points(pts, amount=0.8 + p * 0.3, freq=5)
            w = max(1, width + self.rng.randint(-1, 1))
            alpha = 180 - p * 50
            c = tuple(color[:3]) + (alpha,)
            for i in range(len(wobbled) - 1):
                draw.line([wobbled[i], wobbled[i+1]], fill=c, width=w)

    @staticmethod
    def _lighten(c, amount=30):
        return tuple(min(255, v + amount) for v in c[:3])

    # ── Canvas ──────────────────────────────────────────────────

    def create_canvas(self, bg_color=(255, 255, 255, 255)):
        img = Image.new("RGBA", (self.w, self.h), bg_color)
        return img

    # ── Drawing primitives (clean, no wobble) ───────────────────

    def draw_circle(self, draw, cx, cy, r, fill=None, stroke=None, stroke_width=2, opacity=255):
        if self.hand_drawn and self.technique:
            self._sketch_circle(draw, cx, cy, r, fill=fill, stroke=stroke or self.technique["stroke"], stroke_width=stroke_width)
            return
        if fill:
            c = fill if len(fill) == 4 else fill + (opacity,)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=c)
        if stroke:
            c = stroke if len(stroke) == 4 else stroke + (opacity,)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c, width=stroke_width)

    def draw_rect(self, draw, x, y, w, h, fill=None, stroke=None, stroke_width=2, rx=0, opacity=255):
        if self.hand_drawn and self.technique:
            self._sketch_rect(draw, x, y, w, h, fill=fill, stroke=stroke or self.technique["stroke"], stroke_width=stroke_width, rx=rx)
            return
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
        if self.hand_drawn and self.technique:
            self._sketch_polygon(draw, points, fill=fill, stroke=stroke or self.technique["stroke"], stroke_width=stroke_width)
            return
        if fill:
            c = fill if len(fill) == 4 else fill + (opacity,)
            draw.polygon(points, fill=c)
        if stroke:
            c = stroke if len(stroke) == 4 else stroke + (opacity,)
            draw.polygon(points, outline=c, width=stroke_width)

    def draw_line(self, draw, x1, y1, x2, y2, color=(0, 0, 0), width=2, opacity=255):
        if self.hand_drawn and self.technique:
            self._sketch_line(draw, x1, y1, x2, y2, color or self.technique["stroke"], width, passes=2)
            return
        c = color if len(color) == 4 else color + (opacity,)
        draw.line([(x1, y1), (x2, y2)], fill=c, width=width)

    def draw_arc(self, draw, cx, cy, r, start_angle, end_angle, color=(0, 0, 0), width=2, opacity=255):
        if self.hand_drawn and self.technique:
            self._sketch_arc(draw, cx, cy, r, start_angle, end_angle, color=color or self.technique["stroke"], width=width)
            return
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

    def draw_human(self, draw, x, y, size=1.0, color=(80, 60, 120), skin_color=(235, 200, 175), gender="neutral", mood="peaceful", pose="standing"):
        """Draw a human figure with distinct man/woman/child/neutral silhouettes and facial expressions."""
        s = size
        skin = tuple(skin_color[:3])
        cloth = tuple(color[:3])
        is_child = (gender == "child")
        is_woman = (gender == "woman")
        is_man = (gender == "man")
        is_neutral = (not is_child and not is_woman and not is_man)
        bs = s * (0.65 if is_child else 1.0)

        # ── Pose offsets ──
        POSE_OFFSETS = {
            "standing": {"y": 0},
            "sitting_chair": {"y": 10, "leg_l": {"knee_dx": -1, "knee_dy": 5, "foot_dx": -2, "foot_dy": 8}, "leg_r": {"knee_dx": 1, "knee_dy": 5, "foot_dx": 2, "foot_dy": 8}},
            "sitting_cross_legged": {"y": 10, "leg_l": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 0}, "leg_r": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 0}},
            "meditating": {"y": 10, "leg_l": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 0}, "leg_r": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 0}},
            "sitting_floor": {"y": 10, "leg_l": {"knee_dx": -1, "knee_dy": 5, "foot_dx": -2, "foot_dy": 8}, "leg_r": {"knee_dx": 1, "knee_dy": 5, "foot_dx": 2, "foot_dy": 8}},
            "lying_back": {"y": 8, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}},
            "lying_side": {"y": 8, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}},
            "jogging": {"y": 0, "leg_l": {"knee_dx": -4, "knee_dy": -1, "foot_dx": -6, "foot_dy": 0}, "leg_r": {"knee_dx": -2, "knee_dy": -1, "foot_dx": -3, "foot_dy": 0}},
            "running": {"y": -2, "leg_l": {"knee_dx": -6, "knee_dy": -2, "foot_dx": -8, "foot_dy": -1}, "leg_r": {"knee_dx": -3, "knee_dy": -2, "foot_dx": -5, "foot_dy": -1}},
            "walking": {"y": 0, "leg_l": {"knee_dx": -2, "knee_dy": 0, "foot_dx": -3, "foot_dy": 0}, "leg_r": {"knee_dx": -1, "knee_dy": 0, "foot_dx": -1, "foot_dy": 0}},
            "jumping": {"y": -5, "leg_l": {"knee_dx": 0, "knee_dy": -3, "foot_dx": 0, "foot_dy": -4}, "leg_r": {"knee_dx": 0, "knee_dy": -3, "foot_dx": 0, "foot_dy": -4}},
            "kneeling": {"y": 8, "leg_l": {"knee_dx": -1, "knee_dy": 3, "foot_dx": -1, "foot_dy": 4}, "leg_r": {"knee_dx": 1, "knee_dy": 3, "foot_dx": 1, "foot_dy": 4}},
            "bowing": {"y": 2, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": 0}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": 0}},
            "praying": {"y": 0, "leg_l": {}, "leg_r": {}},
            "yoga_tree": {"y": 0, "leg_l": {}, "leg_r": {"foot_dx": 0, "foot_dy": -4}},
            "fighting_stance": {"y": 0, "leg_l": {"knee_dx": -3, "knee_dy": 0, "foot_dx": -4, "foot_dy": 0}, "leg_r": {"knee_dx": -1, "knee_dy": 0, "foot_dx": -2, "foot_dy": 0}},
            "dancing": {"y": -3, "leg_l": {"knee_dx": -5, "knee_dy": -2, "foot_dx": -7, "foot_dy": -3}, "leg_r": {"knee_dx": -2, "knee_dy": -2, "foot_dx": -3, "foot_dy": -3}},
            "bending": {"y": 2, "leg_l": {}, "leg_r": {}},
            "squatting": {"y": 12, "leg_l": {"knee_dx": -1, "knee_dy": 6, "foot_dx": -1, "foot_dy": 8}, "leg_r": {"knee_dx": 1, "knee_dy": 6, "foot_dx": 1, "foot_dy": 8}},
            "crawling": {"y": 10, "leg_l": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 4}, "leg_r": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 4}},
            "climbing": {"y": -4, "leg_l": {"knee_dx": -3, "knee_dy": -5, "foot_dx": -5, "foot_dy": -7}, "leg_r": {"knee_dx": -1, "knee_dy": -3, "foot_dx": -2, "foot_dy": -5}},
            "swimming": {"y": 6, "leg_l": {"knee_dx": -2, "knee_dy": -1, "foot_dx": -4, "foot_dy": -2}, "leg_r": {"knee_dx": 2, "knee_dy": -1, "foot_dx": 4, "foot_dy": -2}},
            "stretching": {"y": -4, "leg_l": {}, "leg_r": {}},
            "star_jump": {"y": -5, "leg_l": {"knee_dx": -3, "knee_dy": -3, "foot_dx": -5, "foot_dy": -4}, "leg_r": {"knee_dx": 3, "knee_dy": -3, "foot_dx": 5, "foot_dy": -4}},
            "clapping": {"y": 0, "leg_l": {}, "leg_r": {}},
            "carrying": {"y": 0, "leg_l": {}, "leg_r": {}},
            "pushing": {"y": 0, "leg_l": {"knee_dx": -3, "knee_dy": 0, "foot_dx": -4, "foot_dy": 0}, "leg_r": {"knee_dx": -1, "knee_dy": 0, "foot_dx": -1, "foot_dy": 0}},
            "pulling": {"y": 0, "leg_l": {"knee_dx": -1, "knee_dy": 0, "foot_dx": -1, "foot_dy": 0}, "leg_r": {"knee_dx": -3, "knee_dy": 0, "foot_dx": -4, "foot_dy": 0}},
            "kicking": {"y": 0, "leg_l": {"knee_dx": -2, "knee_dy": 0, "foot_dx": -3, "foot_dy": 0}, "leg_r": {"foot_dx": 6, "foot_dy": -3}},
            "punching": {"y": 0, "leg_l": {"knee_dx": -2, "knee_dy": 0, "foot_dx": -3, "foot_dy": 0}, "leg_r": {"knee_dx": 1, "knee_dy": 0, "foot_dx": 2, "foot_dy": 0}},
            "sweeping": {"y": 2, "leg_l": {"knee_dx": -2, "knee_dy": 0, "foot_dx": -3, "foot_dy": 0}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 1, "foot_dy": 0}},
            "phone_standing": {"y": 0, "leg_l": {}, "leg_r": {}},
            "lying_stomach": {"y": 8, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}},
            "sleeping_fetal": {"y": 8, "leg_l": {"knee_dx": -2, "knee_dy": 2, "foot_dx": -3, "foot_dy": 3}, "leg_r": {"knee_dx": 2, "knee_dy": 2, "foot_dx": 3, "foot_dy": 3}},
            "pushups": {"y": 8, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": 0}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": 0}},
            "situps": {"y": 6, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": 0}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": 0}},
            "hugging": {"y": 0, "leg_l": {}, "leg_r": {}},
            "lying_reading": {"y": 6, "leg_l": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}, "leg_r": {"knee_dx": 0, "knee_dy": 0, "foot_dx": 0, "foot_dy": -2}},
            "pointing": {"y": 0, "leg_l": {}, "leg_r": {}},
            "standing_arms_up": {"y": 0, "leg_l": {}, "leg_r": {}},
            "arms_crossed": {"y": 0, "leg_l": {}, "leg_r": {}},
            "standing_akimbo": {"y": 0, "leg_l": {}, "leg_r": {}},
            "thinking": {"y": 0, "leg_l": {}, "leg_r": {}},
            "waving": {"y": 0, "leg_l": {}, "leg_r": {}},
            "cycling": {"y": 5, "leg_l": {"knee_dx": 3, "knee_dy": 2, "foot_dx": 5, "foot_dy": 4}, "leg_r": {"knee_dx": -3, "knee_dy": 2, "foot_dx": -5, "foot_dy": 4}},
            "throwing": {"y": 0, "leg_l": {"knee_dx": -1, "knee_dy": 0, "foot_dx": -2, "foot_dy": 0}, "leg_r": {}},
            "kneeling_one": {"y": 8, "leg_l": {"knee_dx": 0, "knee_dy": 3, "foot_dx": 0, "foot_dy": 4}, "leg_r": {"knee_dx": 2, "knee_dy": 4, "foot_dx": 3, "foot_dy": 5}},
            "kneeling_both": {"y": 10, "leg_l": {"knee_dx": 0, "knee_dy": 4, "foot_dx": 0, "foot_dy": 5}, "leg_r": {"knee_dx": 0, "knee_dy": 4, "foot_dx": 0, "foot_dy": 5}},
            "yoga_warrior": {"y": 0, "leg_l": {"foot_dx": -8, "foot_dy": 0}, "leg_r": {"foot_dx": 6, "foot_dy": 0}},
        }
        PO = POSE_OFFSETS.get(pose, POSE_OFFSETS["standing"])
        po_l = PO.get("leg_l", {})
        po_r = PO.get("leg_r", {})
        pose_y = PO.get("y", 0) * bs
        has_pose_arms = pose not in ("standing",) and "arm" in str(PO.keys())

        # ── Pose classification ──
        BENT_LEG_POSES = {"kneeling", "kneeling_one", "kneeling_both", "sitting_chair",
                          "sitting_cross_legged", "sitting_floor", "sitting_phone",
                          "meditating", "praying", "bowing", "squatting",
                          "hugging", "arms_crossed", "bending"}
        HORIZONTAL_POSES = {"lying_back", "lying_side", "lying_stomach", "sleeping_fetal",
                            "lying_reading", "crawling", "pushups", "situps"}

        # ── Proportions ──
        head_r = (9.5 if is_child else 10 if is_woman else 11.5) * bs
        neck_y = y - (36 if is_child else 38) * bs
        body_h = (28 if is_child else 36) * bs
        torso_top = y - body_h

        # ── Mood-based pose modifiers ──
        m = mood.lower()
        arms_up = m in ("hopeful", "happy", "surprised", "shocked")
        arms_crossed = m in ("epic", "determined")
        arms_limp = m in ("sad", "somber")
        arms_tense = m in ("angry", "dramatic", "furious")
        head_tilt = -2*bs if m in ("sad", "somber") else 0
        body_shift_y = 3*bs if m in ("sad", "somber") else (-2*bs if m in ("hopeful", "happy") else 0)

        # Shift entire figure up/down for mood + pose
        y = y + body_shift_y + pose_y
        neck_y = neck_y + body_shift_y + pose_y
        torso_top = torso_top + body_shift_y + pose_y

        # ── Horizontal pose (lying, crawling, pushups, etc.) ──
        if pose in HORIZONTAL_POSES:
            body_len = 36 * bs
            body_h = 14 * bs
            hx = x - body_len // 2 - head_r
            hy = y - body_h // 2
            es = (4 if is_child else 3.5) * bs

            # Bed/mattress behind sleeping/lying poses
            if pose in ("sleeping_fetal", "lying_back", "lying_side", "lying_stomach", "lying_reading"):
                bed_top = y - body_h * 1.5
                bed_bot = y + body_h * 1.5
                bed_left = x - body_len // 2 - head_r - 8 * bs
                bed_right = x + body_len // 2 + head_r + 8 * bs
                bed_w = bed_right - bed_left
                bed_h = bed_bot - bed_top
                # Mattress shadow
                self.draw_rect(draw, bed_left, bed_top, bed_w, bed_h,
                              fill=(0, 0, 0, 25), rx=int(3*bs))
                # Mattress body
                self.draw_rect(draw, bed_left, bed_top, bed_w, bed_h,
                              fill=(200, 190, 180, 200), stroke=(140, 130, 120), stroke_width=1, rx=int(3*bs))
                # Pillow at head (left)
                pillow_w = 12 * bs
                pillow_h = 8 * bs
                self.draw_rect(draw, bed_left + 2 * bs, bed_top + 2 * bs, pillow_w, pillow_h,
                              fill=(255, 250, 240, 220), stroke=(200, 190, 180), stroke_width=1, rx=int(bs))

            # Shadow under horizontal body
            self.draw_shadow(draw, [(x - body_len // 2 - head_r - 2, y + body_h // 2),
                                    (x + body_len // 2 + head_r + 2, y + body_h // 2 - 2),
                                    (x + 18 * bs, y + body_h // 2 + 5),
                                    (x - body_len // 2 - head_r - 2, y + body_h // 2 + 5)],
                             offset=(2, 2), blur_radius=3, color=(0, 0, 0, 35))

            # Body torso
            bp = [(x - body_len // 2, y - body_h // 2), (x - body_len // 2, y + body_h // 2),
                  (x + body_len // 2, y + body_h // 2), (x + body_len // 2, y - body_h // 2)]
            self.draw_shadow(draw, bp, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 30))
            self.fill_gradient_polygon(draw, bp, self._lighten(cloth, 10), self._darken(cloth, 15),
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            lc = self._darken(cloth, 20)
            if pose in ("crawling", "pushups"):
                # Legs extend left (behind)
                for leg_off in [-3 * bs, 3 * bs]:
                    leg_pts = [(x - body_len // 2, y + leg_off),
                               (x - body_len // 2 - 14 * bs, y + leg_off + 3 * bs),
                               (x - body_len // 2 - 12 * bs, y + leg_off + 6 * bs),
                               (x - body_len // 2, y + leg_off + 3 * bs)]
                    self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, leg_pts, lc, self._darken(lc, 15),
                                               stroke=(40, 35, 30, 150), stroke_width=1)
                if pose == "crawling":
                    # Arms forward (hands on ground)
                    ac = self._darken(cloth, 10)
                    for side in [-1, 1]:
                        sx = x + body_len // 6
                        sy = y + side * body_h // 3
                        ex = sx + 14 * bs
                        ey = sy - side * 4 * bs
                        self.draw_line(draw, sx, sy, ex, ey, color=ac, width=int(3 * bs))
                        self.draw_circle(draw, ex, ey, 2.5 * bs, fill=skin + (220,),
                                        stroke=(40, 35, 30, 150), stroke_width=1)
            elif pose == "sleeping_fetal":
                # Curled up: knees pulled to chest, legs drawn to left
                for leg_off in [-2 * bs, 2 * bs]:
                    leg_pts = [(x - body_len // 4, y + leg_off),
                               (x - body_len // 4 - 8 * bs, y + leg_off + 6 * bs),
                               (x - body_len // 4 - 6 * bs, y + leg_off + 8 * bs),
                               (x - body_len // 4, y + leg_off + 3 * bs)]
                    self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, leg_pts, lc, self._darken(lc, 15),
                                               stroke=(40, 35, 30, 150), stroke_width=1)
                # Arms wrapped around knees
                ac = self._darken(cloth, 10)
                for side in [-1, 1]:
                    sx = x - body_len // 8
                    sy = y + side * body_h // 4
                    ex = sx - 4 * bs
                    ey = sy - side * 6 * bs
                    self.draw_line(draw, sx, sy, ex, ey, color=ac, width=int(2.5 * bs))
            else:
                # Legs extend right from torso
                for leg_off in [-3 * bs, 3 * bs]:
                    leg_pts = [(x + body_len // 2, y + leg_off),
                               (x + body_len // 2 + 14 * bs, y + leg_off + 3 * bs),
                               (x + body_len // 2 + 12 * bs, y + leg_off + 6 * bs),
                               (x + body_len // 2, y + leg_off + 3 * bs)]
                    self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, leg_pts, lc, self._darken(lc, 15),
                                               stroke=(40, 35, 30, 150), stroke_width=1)
                # Arms at sides
                ac = self._darken(cloth, 10)
                for side in [-1, 1]:
                    sx = x - body_len // 6
                    sy = y + side * body_h // 3
                    ex = sx + 8 * bs
                    ey = sy + side * 8 * bs
                    self.draw_line(draw, sx, sy, ex, ey, color=ac, width=int(2.5 * bs))
                    self.draw_circle(draw, ex, ey, 2 * bs, fill=skin + (220,),
                                    stroke=(40, 35, 30, 150), stroke_width=1)

            # Head
            self.draw_shadow_circle(draw, hx, hy + 2, head_r, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
            self.draw_circle(draw, hx, hy, head_r, fill=skin,
                             stroke=(40, 35, 30, 170), stroke_width=2)
            hair_c = (60, 30, 20) if is_woman else ((40, 35, 25) if is_man else (50, 40, 30))
            self.draw_circle(draw, hx, hy - head_r + 1, head_r * 0.75, fill=hair_c + (220,))

            # Simple face
            eye_r = 1.6 * bs
            if pose in ("lying_side", "lying_stomach", "crawling", "pushups", "sleeping_fetal", "lying_reading"):
                # Closed eyes
                self.draw_arc(draw, hx - es, hy - 2 * bs, eye_r, 0, 180, color=(30, 25, 20, 200), width=int(bs + 1))
                self.draw_arc(draw, hx + es, hy - 2 * bs, eye_r, 0, 180, color=(30, 25, 20, 200), width=int(bs + 1))
            else:
                self.draw_circle(draw, hx - es, hy - 2 * bs, eye_r, fill=(30, 25, 20, 200))
                self.draw_circle(draw, hx + es, hy - 2 * bs, eye_r, fill=(30, 25, 20, 200))
            self.draw_line(draw, hx, hy + bs, hx, hy + 3 * bs, color=(40, 35, 30, 120), width=1)
            self.draw_arc(draw, hx, hy + 4 * bs, 3 * bs, 20, 160, color=(160, 80, 60, 200), width=int(bs + 1.5))

            return

        # ── Chair for sitting_chair pose (draw behind figure) ──
        if pose == "sitting_chair":
            chair_color = (120, 90, 60)
            back_w = 3 * bs
            back_top = y - 28 * bs
            seat_y = y - 2 * bs
            seat_h = 3 * bs
            seat_w = 14 * bs
            ground_y = y + 18 * bs

            # Shadow under chair
            self.draw_rect(draw, x - seat_w, ground_y, seat_w * 2, 3,
                          fill=(0, 0, 0, 30))

            # Back rest
            back_c = self._darken(chair_color, 10)
            back_x = x - back_w // 2
            self.draw_shadow(draw, [(back_x, back_top), (back_x + back_w, back_top),
                                    (back_x + back_w, seat_y), (back_x, seat_y)],
                             offset=(2, 2), blur_radius=2, color=(0, 0, 0, 30))
            self.fill_gradient_polygon(draw, [(back_x, back_top), (back_x + back_w, back_top),
                                              (back_x + back_w, seat_y), (back_x, seat_y)],
                                       self._lighten(chair_color, 10), back_c,
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            # Seat
            seat_left = x - seat_w // 2
            self.draw_shadow(draw, [(seat_left, seat_y), (seat_left + seat_w, seat_y),
                                    (seat_left + seat_w, seat_y + seat_h), (seat_left, seat_y + seat_h)],
                             offset=(2, 2), blur_radius=2, color=(0, 0, 0, 30))
            self.fill_gradient_polygon(draw, [(seat_left, seat_y), (seat_left + seat_w, seat_y),
                                              (seat_left + seat_w, seat_y + seat_h),
                                              (seat_left, seat_y + seat_h)],
                                       self._lighten(chair_color, 15), self._darken(chair_color, 20),
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            # Legs
            leg_c = self._darken(chair_color, 20)
            for lx in [seat_left + 1, seat_left + seat_w - 2]:
                self.draw_line(draw, lx, seat_y + seat_h, lx, ground_y, color=leg_c, width=int(1.5 * bs))

        # ── Shadow ──
        self.draw_shadow_circle(draw, x, y + 2*bs, head_r * 1.2, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 35))

        # ── Legs ──
        leg_spread_extra = 2*bs if arms_tense else 0

        # ── Bent-leg poses (kneeling, sitting, meditating, etc.) ──
        if pose in BENT_LEG_POSES:
            leg_color = self._lighten(cloth, 10) if is_woman else self._darken(cloth, 20)

            if pose == "sitting_chair":
                # Sitting on chair: thighs go forward/down, shins hang straight down
                bl_spread = (6 if is_child else 7) * bs
                knee_y = y + 12 * bs
                foot_y = y + 24 * bs
                for side, lx in [(-1, x - bl_spread), (1, x + bl_spread)]:
                    # Thigh (hip → knee, outward and down)
                    knee_x = lx + side * 4 * bs
                    t_pts = [(lx, y - 2 * bs), (knee_x, knee_y),
                             (knee_x - side * 3 * bs, knee_y - 1), (lx - 1, y - 2 * bs)]
                    self.draw_shadow(draw, t_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, t_pts, leg_color, self._darken(leg_color, 15),
                                               stroke=(40, 35, 30, 150), stroke_width=1)

                    # Shin (knee → foot, straight down)
                    shin_w = 4 * bs
                    s_pts = [(knee_x - shin_w // 2, knee_y), (knee_x + shin_w // 2, knee_y),
                             (knee_x + shin_w // 2, foot_y), (knee_x - shin_w // 2, foot_y)]
                    self.draw_shadow(draw, s_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, s_pts, self._darken(leg_color, 10), self._darken(leg_color, 20),
                                               stroke=(40, 35, 30, 150), stroke_width=1)

                    # Shoe
                    shoe = [(knee_x - shin_w // 2 - 1, foot_y), (knee_x + shin_w // 2 + 1, foot_y),
                            (knee_x + shin_w // 2 + 2, foot_y + 2 * bs), (knee_x - shin_w // 2 - 2, foot_y + 2 * bs)]
                    self.draw_polygon(draw, shoe, fill=(45, 35, 30, 220), stroke=(30, 25, 20, 180), stroke_width=1)

                # Arms: hands on lap (resting pose)
                ac = self._darken(cloth, 10)
                for side in [-1, 1]:
                    sx = x + side * 4 * bs
                    sy = y + 4 * bs
                    ex = x + side * 2 * bs
                    ey = y + 8 * bs
                    self.draw_line(draw, sx, sy, ex, ey, color=ac, width=int(2.5 * bs))
            else:
                leg_color = self._lighten(cloth, 10) if is_woman else self._darken(cloth, 20)
                bl_spread = (4 if is_child else 5) * bs
                for side, lx in [(-1, x - bl_spread), (1, x + bl_spread)]:
                    knee_x = lx + side * 8 * bs
                    knee_y = y + 20 * bs
                    foot_x = lx + side * 2 * bs
                    foot_y = knee_y + 3 * bs

                    # Thigh (hip → knee)
                    t_pts = [(lx, y + 4 * bs), (knee_x, knee_y),
                             (knee_x - side * 4 * bs, knee_y - 1), (lx - 1, y + 4 * bs)]
                    self.draw_shadow(draw, t_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, t_pts, leg_color, self._darken(leg_color, 15),
                                               stroke=(40, 35, 30, 150), stroke_width=1)

                    # Shin (knee → foot, tucks back toward center)
                    s_pts = [(knee_x, knee_y), (foot_x, foot_y),
                             (foot_x - side * 2 * bs, foot_y - 1), (knee_x - side * 4 * bs, knee_y - 1)]
                    self.draw_shadow(draw, s_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                    self.fill_gradient_polygon(draw, s_pts, leg_color, self._darken(leg_color, 15),
                                               stroke=(40, 35, 30, 150), stroke_width=1)

                    # Shoe pointing inward (toward center)
                    shoe = [(foot_x, foot_y), (foot_x - side * 4 * bs, foot_y + 2 * bs),
                            (foot_x - side * 3 * bs, foot_y + 3 * bs), (foot_x + side * bs, foot_y)]
                    self.draw_polygon(draw, shoe, fill=(45, 35, 30, 220), stroke=(30, 25, 20, 180), stroke_width=1)

        elif is_woman:
            leg_color = self._lighten(cloth, 10)
            spread = 2 + leg_spread_extra // (3*bs)
            for side, lx in [(-1, x-(2+spread)*bs), (1, x+(2+spread)*bs)]:
                po = po_l if side == -1 else po_r
                kdx = po.get("knee_dx", 0) * bs
                kdy = po.get("knee_dy", 0) * bs
                fdx = po.get("foot_dx", 0) * bs
                fdy = po.get("foot_dy", 0) * bs
                leg_pts = [(lx, y+6*bs), (lx + side*2*bs + kdx, y+30*bs + kdy),
                           (lx + side*1*bs + fdx, y+32*bs + fdy), (lx-1, y+6*bs)]
                self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                self.fill_gradient_polygon(draw, leg_pts, leg_color, self._darken(leg_color, 15),
                                           stroke=(40, 35, 30, 150), stroke_width=1)
                self.draw_polygon(draw, [(lx + side*2*bs + kdx, y+30*bs + kdy), (lx + side*4*bs + fdx, y+32*bs + fdy),
                                        (lx + side*3*bs + fdx, y+33*bs + fdy), (lx + side*1*bs + kdx, y+31*bs + kdy)],
                                 fill=(45, 35, 30, 220))
        else:
            leg_color = self._darken(cloth, 20)
            spread = (5 if is_man else 4) * bs + leg_spread_extra
            for side, lx in [(-1, x-spread), (1, x+spread)]:
                po = po_l if side == -1 else po_r
                kdx = po.get("knee_dx", 0) * bs
                kdy = po.get("knee_dy", 0) * bs
                fdx = po.get("foot_dx", 0) * bs
                fdy = po.get("foot_dy", 0) * bs
                leg_len = (28 if is_child else 30) * bs
                leg_pts = [(lx, y+4*bs), (lx + side*4*bs + kdx, y+leg_len + kdy),
                           (lx + side*3*bs + fdx, y+leg_len+2*bs + fdy), (lx-1, y+4*bs)]
                self.draw_shadow(draw, leg_pts, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 25))
                self.fill_gradient_polygon(draw, leg_pts, leg_color, self._darken(leg_color, 15),
                                           stroke=(40, 35, 30, 150), stroke_width=1)
                shoe = [(lx + side*4*bs + kdx, y+leg_len-2*bs + kdy), (lx + side*7*bs + fdx, y+leg_len+2*bs + fdy),
                        (lx + side*5*bs + fdx, y+leg_len+3*bs + fdy), (lx + side*2*bs + kdx, y+leg_len + kdy)]
                self.draw_polygon(draw, shoe, fill=(45, 35, 30, 220), stroke=(30, 25, 20, 180), stroke_width=1)

        # ── Torso ──
        if is_woman:
            waist_w = 7 * bs
            hip_w = 14 * bs
            bust_y = torso_top + 6 * bs
            waist_y = y - 2 * bs
            hip_y = y + 6 * bs

            torso_pts = [(x - waist_w//2, waist_y),
                         (x - waist_w//2, bust_y),
                         (x + waist_w//2, bust_y),
                         (x + waist_w//2, waist_y)]
            self.draw_shadow(draw, torso_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
            self.fill_gradient_polygon(draw, torso_pts, self._lighten(cloth, 10), cloth,
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            bust_c = self._lighten(cloth, 15)
            for side in [-1, 1]:
                self.draw_arc(draw, x + side * waist_w//2, bust_y + bs, waist_w//3, 0, 180,
                              color=bust_c, width=int(2*bs))
                self.draw_arc(draw, x + side * waist_w//2, bust_y, waist_w//3, 0, 180,
                              color=self._darken(cloth, 5) + (60,), width=1)

            dress_pts = [(x - waist_w//2, waist_y),
                         (x - hip_w//2, hip_y),
                         (x + hip_w//2, hip_y),
                         (x + waist_w//2, waist_y)]
            self.draw_shadow(draw, dress_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
            self.fill_gradient_polygon(draw, dress_pts, cloth, self._darken(cloth, 10),
                                       stroke=(40, 35, 30, 150), stroke_width=1)

            hem_color = self._lighten(cloth, 20)
            self.draw_line(draw, x - hip_w//2, hip_y, x + hip_w//2, hip_y,
                          color=hem_color + (180,), width=2)

        elif is_man:
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

            self.draw_rect(draw, x - waist_w//2 - 1, waist_y - 3*bs, waist_w + 2, int(3*bs),
                          fill=(50, 40, 30, 200))

        else:
            tw = (10 if is_neutral else 9) * bs
            torso_pts = [(x - tw//2, y), (x - tw//2, torso_top),
                         (x + tw//2, torso_top), (x + tw//2, y)]
            self.draw_shadow(draw, torso_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
            self.fill_gradient_rect(draw, x - tw//2, torso_top, tw, y - torso_top,
                                    self._lighten(cloth, 10), self._darken(cloth, 20))

        # ── Arms (mood-aware pose) ──
        arm_color = self._darken(cloth, 10)
        sh_off = (7 if is_man else 5) * bs
        
        # ── Pose-specific arm overrides ──
        # Format: for each arm key "l"/"r", {"el": (dx, dy), "ha": (dx, dy)}
        # dx positive = away from body center (right for right arm, left for left arm)
        # dy positive = down from shoulder (shoulder_y = torso_top + 4*s)
        # Full arm length ~36*bs from shoulder to relaxed hand
        ARM_POSES = {
            "standing": None,
            "jogging": {"l": {"el": (5, 6), "ha": (4, 12)}, "r": {"el": (5, 6), "ha": (4, 12)}},
            "running": {"l": {"el": (7, 4), "ha": (6, 8)}, "r": {"el": (7, 4), "ha": (6, 8)}},
            "walking": {"l": {"el": (3, 8), "ha": (3, 16)}, "r": {"el": (3, 8), "ha": (3, 16)}},
            "jumping": {"l": {"el": (3, -6), "ha": (5, -16)}, "r": {"el": (3, -6), "ha": (5, -16)}},
            "star_jump": {"l": {"el": (8, -4), "ha": (14, -10)}, "r": {"el": (8, -4), "ha": (14, -10)}},
            "dancing": {"l": {"el": (10, -2), "ha": (14, 4)}, "r": {"el": (10, -2), "ha": (14, 4)}},
            "praying": {"l": {"el": (2, 2), "ha": (0, -2)}, "r": {"el": (2, 2), "ha": (0, -2)}},
            "clapping": {"l": {"el": (3, 5), "ha": (0, 1)}, "r": {"el": (3, 5), "ha": (0, 1)}},
            "pointing": {"l": {"el": (4, 10), "ha": (6, 20)}, "r": {"el": (12, 2), "ha": (20, 0)}},
            "waving": {"l": {"el": (4, 10), "ha": (6, 20)}, "r": {"el": (5, -10), "ha": (8, -20)}},
            "thinking": {"l": {"el": (4, 10), "ha": (6, 20)}, "r": {"el": (1, -2), "ha": (0, -6)}},
            "standing_arms_up": {"l": {"el": (3, -10), "ha": (5, -22)}, "r": {"el": (3, -10), "ha": (5, -22)}},
            "arms_crossed": {"l": {"el": (4, 8), "ha": (1, 4)}, "r": {"el": (4, 8), "ha": (1, 4)}},
            "standing_akimbo": {"l": {"el": (4, 2), "ha": (2, 4)}, "r": {"el": (4, 2), "ha": (2, 4)}},  # hands on hips
            "bowing": {"l": {"el": (3, 12), "ha": (4, 22)}, "r": {"el": (3, 12), "ha": (4, 22)}},  # arms hanging forward
            "carrying": {"l": {"el": (6, 4), "ha": (8, 8)}, "r": {"el": (6, 4), "ha": (8, 8)}},
            "pushing": {"l": {"el": (4, 8), "ha": (6, 16)}, "r": {"el": (10, 2), "ha": (18, 0)}},
            "pulling": {"l": {"el": (4, 8), "ha": (2, 12)}, "r": {"el": (8, 4), "ha": (10, 6)}},
            "sweeping": {"l": {"el": (5, 10), "ha": (8, 20)}, "r": {"el": (10, 4), "ha": (16, 8)}},
            "cooking": {"l": {"el": (5, 10), "ha": (8, 20)}, "r": {"el": (8, 2), "ha": (14, 0)}},
            "phone_standing": {"l": {"el": (5, 10), "ha": (8, 20)}, "r": {"el": (2, -4), "ha": (1, -8)}},
            "hugging": {"l": {"el": (3, 4), "ha": (0, 2)}, "r": {"el": (3, 4), "ha": (0, 2)}},  # arms wrapped around self
            "crawling": {"l": {"el": (6, 8), "ha": (8, 14)}, "r": {"el": (6, 8), "ha": (8, 14)}},
            "climbing": {"l": {"el": (5, -4), "ha": (7, -10)}, "r": {"el": (8, -6), "ha": (12, -12)}},
            "swimming": {"l": {"el": (8, 6), "ha": (14, 10)}, "r": {"el": (8, 6), "ha": (14, 10)}},
            "sitting_chair": {"l": {"el": (2, 6), "ha": (1, 12)}, "r": {"el": (2, 6), "ha": (1, 12)}},  # hands in lap
            "sitting_cross_legged": {"l": {"el": (3, 6), "ha": (2, 14)}, "r": {"el": (3, 6), "ha": (2, 14)}},  # hands on knees
            "sitting_floor": {"l": {"el": (5, 8), "ha": (6, 16)}, "r": {"el": (5, 8), "ha": (6, 16)}},  # hands behind on floor
            "lying_back": {"l": {"el": (5, 4), "ha": (7, 8)}, "r": {"el": (5, 4), "ha": (7, 8)}},
            "lying_side": {"l": {"el": (5, 3), "ha": (6, 6)}, "r": {"el": (4, 3), "ha": (3, 6)}},
            "lying_stomach": {"l": {"el": (4, 6), "ha": (5, 12)}, "r": {"el": (4, 6), "ha": (5, 12)}},
            "sleeping_fetal": {"l": {"el": (3, 6), "ha": (2, 10)}, "r": {"el": (3, 6), "ha": (2, 10)}},
            "pushups": {"l": {"el": (5, 8), "ha": (4, 14)}, "r": {"el": (5, 8), "ha": (4, 14)}},
            "situps": {"l": {"el": (4, 6), "ha": (3, 12)}, "r": {"el": (4, 6), "ha": (3, 12)}},
            "lying_reading": {"l": {"el": (5, 3), "ha": (6, 6)}, "r": {"el": (3, 1), "ha": (2, 2)}},
            "squatting": {"l": {"el": (3, 2), "ha": (4, 0)}, "r": {"el": (3, 2), "ha": (4, 0)}},  # arms forward for balance
            "kneeling": {"l": {"el": (2, 4), "ha": (1, 8)}, "r": {"el": (2, 4), "ha": (1, 8)}},  # hands on thighs
            "kneeling_one": {"l": {"el": (2, 4), "ha": (1, 8)}, "r": {"el": (3, 3), "ha": (2, 5)}},  # one hand on raised knee
            "kneeling_both": {"l": {"el": (2, 2), "ha": (0, 0)}, "r": {"el": (2, 2), "ha": (0, 0)}},  # hands clasped
            "bending": {"l": {"el": (2, 14), "ha": (1, 24)}, "r": {"el": (2, 14), "ha": (1, 24)}},  # reaching toward ground
            "stretching": {"l": {"el": (3, -8), "ha": (4, -18)}, "r": {"el": (4, 4), "ha": (3, 8)}},  # one arm up, one on hip
            "yoga_warrior": {"l": {"el": (10, 0), "ha": (18, 0)}, "r": {"el": (10, 0), "ha": (18, 0)}},  # arms out wide
            "cycling": {"l": {"el": (5, 4), "ha": (4, 8)}, "r": {"el": (5, 4), "ha": (4, 8)}},  # hands on handlebars
            "reading_standing": {"l": {"el": (3, 5), "ha": (2, 8)}, "r": {"el": (3, 5), "ha": (2, 8)}},  # holding book
            "reading_sitting": {"l": {"el": (3, 5), "ha": (2, 8)}, "r": {"el": (3, 5), "ha": (2, 8)}},  # holding book
            "sitting_phone": {"l": {"el": (5, 10), "ha": (6, 20)}, "r": {"el": (2, 2), "ha": (1, 0)}},
        }
        pose_arms = ARM_POSES.get(pose, None)
        
        def _draw_arm_segment(sx, sy, ex, ey, hx, hy):
            self.draw_line(draw, int(sx), int(sy), int(ex), int(ey),
                          color=arm_color, width=int(3*bs))
            self.draw_line(draw, int(ex), int(ey), int(hx), int(hy),
                          color=arm_color, width=int(2.5*bs))
            self.draw_circle(draw, int(hx), int(hy), 2.5*bs,
                            fill=skin + (220,), stroke=(40, 35, 30, 150), stroke_width=1)
        
        if pose_arms is not None and pose != "standing":
            # Draw pose-specific arms instead of mood-based
            for sdir, key in [(-1, "l"), (1, "r")]:
                pa = pose_arms.get(key, {})
                sx = x + sdir * sh_off
                sy = torso_top + 4*bs + body_shift_y
                ex = sx + pa.get("el", (4, 10))[0] * bs * sdir
                ey = sy + pa.get("el", (4, 10))[1] * bs
                hx = sx + pa.get("ha", (6, 20))[0] * bs * sdir
                hy = sy + pa.get("ha", (6, 20))[1] * bs
                _draw_arm_segment(sx, sy, ex, ey, hx, hy)
        elif arms_up:
            # Arms raised above head
            for side in [-1, 1]:
                shoulder = (x + side * sh_off, torso_top + 4*bs + body_shift_y)
                elbow = (x + side * sh_off * 1.3, torso_top - 8*bs)
                hand = (x + side * sh_off * 0.8, torso_top - 16*bs)
                self.draw_line(draw, int(shoulder[0]), int(shoulder[1]), int(elbow[0]), int(elbow[1]),
                              color=arm_color, width=int(3*bs))
                self.draw_line(draw, int(elbow[0]), int(elbow[1]), int(hand[0]), int(hand[1]),
                              color=arm_color, width=int(2.5*bs))
                self.draw_circle(draw, int(hand[0]), int(hand[1]), 2.5*bs,
                                fill=skin + (220,), stroke=(40, 35, 30, 150), stroke_width=1)
        elif arms_crossed:
            # Arms crossed on chest
            for side in [-1, 1]:
                shoulder = (x + side * sh_off, torso_top + 4*bs + body_shift_y)
                elbow = (x + side * sh_off * 0.3, torso_top + 12*bs)
                hand = (x + side * sh_off * 0.5, torso_top + 6*bs)
                self.draw_line(draw, int(shoulder[0]), int(shoulder[1]), int(elbow[0]), int(elbow[1]),
                              color=arm_color, width=int(3.5*bs))
                self.draw_line(draw, int(elbow[0]), int(elbow[1]), int(hand[0]), int(hand[1]),
                              color=arm_color, width=int(3*bs))
        elif arms_limp:
            # Arms hanging limp (sad)
            for side in [-1, 1]:
                shoulder = (x + side * sh_off, torso_top + 4*bs + body_shift_y)
                elbow = (x + side * sh_off * 1.1, torso_top + 18*bs)
                hand = (x + side * sh_off * 1.3, y + 16*bs)
                self.draw_line(draw, int(shoulder[0]), int(shoulder[1]), int(elbow[0]), int(elbow[1]),
                              color=arm_color, width=int(3*bs))
                self.draw_line(draw, int(elbow[0]), int(elbow[1]), int(hand[0]), int(hand[1]),
                              color=arm_color, width=int(2.5*bs))
                self.draw_circle(draw, int(hand[0]), int(hand[1]), 2*bs,
                                fill=skin + (220,), stroke=(40, 35, 30, 150), stroke_width=1)
        elif arms_tense:
            # Tense fists at sides (angry)
            for side in [-1, 1]:
                shoulder = (x + side * sh_off, torso_top + 4*bs + body_shift_y)
                elbow = (x + side * sh_off * 1.2, torso_top + 16*bs)
                hand = (x + side * sh_off * 0.8, y + 8*bs)
                self.draw_line(draw, int(shoulder[0]), int(shoulder[1]), int(elbow[0]), int(elbow[1]),
                              color=arm_color, width=int(4*bs), opacity=220)
                self.draw_line(draw, int(elbow[0]), int(elbow[1]), int(hand[0]), int(hand[1]),
                              color=arm_color, width=int(3.5*bs))
                self.draw_circle(draw, int(hand[0]), int(hand[1]), 3*bs,
                                fill=(40, 35, 30, 220), stroke=(30, 25, 20, 180), stroke_width=1)
        else:
            # Default relaxed arms at sides
            if is_woman:
                for side in [-1, 1]:
                    if side == -1:
                        pts = [(x + side * 6*bs, torso_top + 6*bs),
                               (x + side * 8*bs, torso_top + 14*bs),
                               (x + side * 4*bs, y + 4*bs)]
                    else:
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
                    elbow_x = x + side * (sh_off + 3*bs)
                    hand_x = elbow_x + side * 3*bs
                    hand_y = y + (6 if is_child else 10) * bs
                    pts = [(x + side * sh_off, torso_top + 4*bs),
                           (elbow_x, torso_top + 14*bs),
                           (hand_x, hand_y)]
                    self.draw_line(draw, int(pts[0][0]), int(pts[0][1]), int(pts[1][0]), int(pts[1][1]),
                                  color=arm_color, width=int(3.5*bs))
                    self.draw_line(draw, int(pts[1][0]), int(pts[1][1]), int(pts[2][0]), int(pts[2][1]),
                                  color=arm_color, width=int(3*bs))
                    self.draw_circle(draw, int(pts[2][0]), int(pts[2][1]), 2.5*bs,
                                    fill=skin + (220,), stroke=(40, 35, 30, 150), stroke_width=1)

        # ── Head (with mood tilt) ──
        hx = x + head_tilt
        hy = neck_y
        self.draw_shadow_circle(draw, hx, hy + 2, head_r, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        head_pts = [(hx - head_r, hy), (hx + head_r, hy),
                    (hx + head_r, hy - head_r*2), (hx - head_r, hy - head_r*2)]
        self.fill_gradient_polygon(draw, head_pts, self._lighten(skin, 10), self._darken(skin, 15))
        self.draw_circle(draw, hx, hy, head_r, fill=None,
                         stroke=(40, 35, 30, 170), stroke_width=2)

        # ── Hair ──
        if is_woman:
            hair_c = (60, 30, 20)
            self.draw_circle(draw, hx, hy - head_r + 1, head_r * 0.8, fill=hair_c + (220,))
            for side in [-1, 1]:
                base_x = hx + side * head_r * 0.85
                for strand in range(3):
                    offset = strand * 0.15 - 0.15
                    sx = base_x
                    ex = hx + side * head_r * (0.7 + offset)
                    ey = hy + head_r * (0.8 + strand * 0.1)
                    self.draw_line(draw, sx, hy - head_r * 0.3, ex, ey,
                                   color=hair_c, width=int((3 - strand) * bs))
        elif is_man:
            hair_c = (40, 35, 25)
            self.draw_circle(draw, hx, hy - head_r + 1, head_r * 0.78, fill=hair_c + (220,))
            self.draw_arc(draw, hx, hy - head_r * 0.5, head_r * 0.8, 190, 350,
                          color=hair_c, width=int(3*bs))
        else:
            hair_c = (80, 60, 40) if is_child else (50, 40, 30)
            self.draw_circle(draw, hx, hy - head_r + 2, head_r * 0.72, fill=hair_c + (200,))

        # ── Face features (mood-aware, head-tilted) ──
        eye_r = (2.2 if is_child else 1.6) * bs
        face_tilt_y = bs * 2 if m in ("hopeful", "happy") else (-bs * 2 if m in ("sad", "somber") else 0)
        fx, fy = hx, hy  # Use tilted head position
        eye_y = fy - (4 if is_child else 3) * bs + face_tilt_y
        eye_spread = (4 if is_child else 3.5) * bs

        # Eyes (mood varies shape)
        if m in ("sad", "somber"):
            for side in [-1, 1]:
                self.draw_arc(draw, fx + side * eye_spread, eye_y, eye_r, 200, 340,
                              color=(30, 25, 20, 200), width=int(bs+1))
        elif m in ("angry", "dramatic", "furious"):
            for side in [-1, 1]:
                ex = fx + side * eye_spread
                self.draw_line(draw, int(ex - eye_r), int(eye_y + bs), int(ex + eye_r), int(eye_y),
                              color=(30, 25, 20, 200), width=int(bs+1))
        elif m in ("epic", "determined"):
            for side in [-1, 1]:
                self.draw_circle(draw, fx + side * eye_spread, eye_y, eye_r * 1.2,
                                fill=(30, 25, 20, 200))
                self.draw_circle(draw, fx + side * eye_spread + bs, eye_y - bs, eye_r * 0.4,
                                fill=(255, 255, 255, 180))
        else:
            self.draw_circle(draw, fx - eye_spread, eye_y, eye_r, fill=(30, 25, 20, 200))
            self.draw_circle(draw, fx + eye_spread, eye_y, eye_r, fill=(30, 25, 20, 200))
            self.draw_circle(draw, fx - eye_spread + 0.5*bs, eye_y - 0.5*bs, eye_r*0.4, fill=(255, 255, 255, 160))
            self.draw_circle(draw, fx + eye_spread + 0.5*bs, eye_y - 0.5*bs, eye_r*0.4, fill=(255, 255, 255, 160))

        # Eyebrows (mood-aware)
        brow_y = fy - (7 if is_child else 6.5) * bs + face_tilt_y
        brow_w = (4 if is_child else 3.5) * bs
        brow_c = (40, 35, 25, 160)
        if m in ("sad", "somber"):
            for side in [-1, 1]:
                bx = fx + side * brow_w
                self.draw_line(draw, int(bx), int(brow_y + bs), int(fx), int(brow_y),
                              color=brow_c, width=int(bs+1))
        elif m in ("angry", "dramatic", "furious"):
            for side in [-1, 1]:
                bx = fx + side * brow_w
                self.draw_line(draw, int(bx), int(brow_y), int(fx), int(brow_y + bs),
                              color=brow_c, width=int(bs+1.5))
        elif m in ("surprised", "shocked"):
            for side in [-1, 1]:
                self.draw_arc(draw, fx + side * brow_w * 0.5, brow_y - bs, brow_w, 0, 180,
                              color=brow_c, width=int(bs+1))
        elif m in ("hopeful", "happy"):
            for side in [-1, 1]:
                bx = fx + side * brow_w
                self.draw_line(draw, int(bx), int(brow_y - bs*0.5), int(fx), int(brow_y - bs*0.5),
                              color=(40, 35, 25, 120), width=int(bs+0.5))
        else:
            for side in [-1, 1]:
                bx = fx + side * brow_w
                self.draw_line(draw, int(bx), int(brow_y), int(fx + side * bs*0.5), int(brow_y),
                              color=brow_c, width=int(bs+1))

        # Nose
        nose_len = (2 if is_child else 1.5) * bs
        self.draw_line(draw, fx, eye_y + eye_r, fx, eye_y + eye_r + nose_len,
                      color=(40, 35, 30, 120), width=1)

        # Mouth (mood-aware)
        lip_y = fy + (4 if is_child else 3) * bs + face_tilt_y
        if m in ("happy", "hopeful"):
            self.draw_arc(draw, fx, lip_y, (4 if is_child else 3) * bs, 20, 160,
                          color=(160, 80, 60, 200), width=int(bs+1.5))
            if not is_man:
                self.draw_arc(draw, fx, lip_y, (4 if is_child else 3) * bs, 20, 160,
                              color=(180, 100, 80, 120), width=int(bs*0.5))
        elif m in ("sad", "somber"):
            self.draw_arc(draw, fx, lip_y, (3 if is_child else 2.5) * bs, 200, 340,
                          color=(120, 70, 60, 200), width=int(bs+1.5))
        elif m in ("angry", "dramatic", "furious"):
            self.draw_line(draw, int(fx - (3 if is_child else 2.5) * bs), int(lip_y),
                          int(fx + (3 if is_child else 2.5) * bs), int(lip_y),
                          color=(100, 50, 40, 220), width=int(bs+2))
            self.draw_line(draw, int(fx - bs), int(lip_y - bs), int(fx + bs), int(lip_y - bs),
                          color=(220, 210, 190, 200), width=int(bs))
        elif m in ("surprised", "shocked"):
            self.draw_circle(draw, fx, lip_y + bs, (2 if is_child else 1.5) * bs,
                            fill=(40, 30, 25, 220))
        elif m in ("epic", "determined"):
            self.draw_line(draw, int(fx - (3 if is_child else 2.5) * bs), int(lip_y),
                          int(fx + (3 if is_child else 2.5) * bs), int(lip_y),
                          color=(100, 60, 50, 200), width=int(bs+1.5))
        else:
            if is_child:
                self.draw_arc(draw, fx, fy + 4*bs, 4*bs, 20, 160, color=(160, 80, 60, 180), width=2)
            elif is_woman:
                self.draw_arc(draw, fx, lip_y, 3*bs, 20, 160, color=(160, 80, 70, 200), width=int(bs+1))
            else:
                self.draw_line(draw, int(fx - 2*bs), int(lip_y), int(fx + 2*bs), int(lip_y),
                              color=(100, 60, 50, 180), width=int(bs+1))

        # ── Phone for phone poses ──
        if pose in ("phone_standing", "sitting_phone"):
            sh_off_phone = (7 if is_man else 5) * bs
            sx = x + 1 * sh_off_phone
            sy = torso_top + 4*bs + body_shift_y
            if pose == "phone_standing":
                hx = sx + 1 * bs
                hy = sy - 8 * bs
            else:
                hx = sx + 1 * bs
                hy = sy
            phone_w = 4 * max(bs, 0.8)
            phone_h = 7 * max(bs, 0.8)
            phone_pts = [(hx - phone_w // 2, hy - phone_h // 2),
                         (hx + phone_w // 2, hy - phone_h // 2),
                         (hx + phone_w // 2, hy + phone_h // 2),
                         (hx - phone_w // 2, hy + phone_h // 2)]
            self.draw_shadow(draw, phone_pts, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 35))
            self.fill_gradient_polygon(draw, phone_pts, (200, 220, 240), (180, 200, 220),
                                       stroke=(60, 60, 60, 180), stroke_width=1)

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

    def _draw_ash_particles(self, draw, count=80):
        """Draw ash/soot particles drifting down — dark, varied sizes."""
        for _ in range(count):
            ax = self.rng.randint(0, self.w)
            ay = self.rng.randint(0, self.h)
            ar = self.rng.uniform(1, 4)
            shade = self.rng.randint(20, 80)
            alpha = self.rng.randint(30, 120)
            self.draw_circle(draw, ax, ay, ar, fill=(shade, shade, shade, alpha))

    def _draw_mist(self, draw):
        """Draw low-lying mist over the ground."""
        for _ in range(30):
            mx = self.rng.randint(0, self.w)
            my = self.rng.randint(int(self.h * 0.45), self.h)
            mw = self.rng.randint(60, 200)
            mh = self.rng.randint(15, 40)
            alpha = self.rng.randint(15, 45)
            self.draw_ellipse(draw, mx, my, mw, mh, fill=(200, 210, 220, alpha))

    def _draw_sunbeams(self, draw):
        """Draw warm sunbeams slanting down."""
        for _ in range(8):
            bx = self.rng.randint(0, self.w)
            beam_w = self.rng.randint(20, 60)
            beam_h = self.rng.randint(self.h // 3, self.h)
            alpha = self.rng.randint(8, 20)
            x1 = bx - beam_w // 2
            y1 = 0
            x2 = bx + beam_w // 2
            y2 = beam_h
            draw.polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
                         fill=(255, 240, 200, alpha))

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

    def draw_canoe(self, draw, x, y, size=1.0, color=(80, 60, 40)):
        """Draw a narrow canoe."""
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(30*s), int(6*s)
        hull = [(x-w//2, y+h//2), (x-w//2+4*s, y-h//2), (x+w//2-4*s, y-h//2), (x+w//2, y+h//2)]
        self.draw_polygon(draw, hull, fill=c+(200,), stroke=self._darken(c,30)+(180,), stroke_width=1)
        # Seat
        self.draw_line(draw, x-3*s, y, x+3*s, y, color=self._darken(c,20)+(150,), width=int(2*s))
        # Paddle
        self.draw_line(draw, x+w//2-2*s, y-h//2, x+w//2+8*s, y-h//2+6*s, color=(200,180,140,180), width=int(1.5*s))
        self.draw_ellipse(draw, x+w//2+7*s, y-h//2+5*s, 4*s, 2*s, fill=(200,180,140,180))

    def draw_kayak(self, draw, x, y, size=1.0, color=(60, 80, 120)):
        """Draw a kayak (closed deck, pointed ends)."""
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(28*s), int(5*s)
        hull = [(x-w//2, y+h//3), (x-w//2+2*s, y-h//2), (x+w//2-2*s, y-h//2), (x+w//2, y+h//3)]
        self.draw_polygon(draw, hull, fill=c+(200,), stroke=self._darken(c,25)+(180,), stroke_width=1)
        # Cockpit
        self.draw_ellipse(draw, x, y-h//4, 5*s, 3*s, fill=(30,30,40,180))
        # Paddle (double-bladed)
        self.draw_line(draw, x-w//2-6*s, y-h//2-2*s, x+w//2+6*s, y-h//2-2*s, color=(200,180,140,180), width=int(1.5*s))
        self.draw_ellipse(draw, x-w//2-7*s, y-h//2-3*s, 3*s, 2*s, fill=(200,180,140,180))
        self.draw_ellipse(draw, x+w//2+5*s, y-h//2-3*s, 3*s, 2*s, fill=(200,180,140,180))

    def draw_raft(self, draw, x, y, size=1.0, color=(100, 80, 50)):
        """Draw a log raft."""
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(24*s), int(8*s)
        # Logs
        for i in range(5):
            ly = y - h//2 + i * int(2*s)
            self.draw_rect(draw, x-w//2, ly, w, int(1.8*s), fill=self._lighten(c,i*10)+(200,),
                          stroke=self._darken(c,20)+(160,), stroke_width=1, rx=int(0.9*s))
        # Cross beams
        self.draw_rect(draw, x-w//2+2*s, y-h//2, int(2.5*s), h, fill=(60,50,40,200), stroke=(40,35,30,150), stroke_width=1)
        self.draw_rect(draw, x+w//2-5*s, y-h//2, int(2.5*s), h, fill=(60,50,40,200), stroke=(40,35,30,150), stroke_width=1)
        # Pole
        self.draw_line(draw, x, y-h//2, x, y-h//2-int(14*s), color=(140,120,80,180), width=int(2*s))

    def draw_pirate_ship(self, draw, x, y, size=1.0, color=(60, 40, 30)):
        """Draw a pirate ship with skull flag."""
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(50*s), int(12*s)
        hull = [(x-w//2, y+h//2), (x-w//2+4*s, y-h//2), (x+w//2-4*s, y-h//2), (x+w//2, y+h//2)]
        self.draw_polygon(draw, hull, fill=c+(200,), stroke=self._darken(c,30)+(180,), stroke_width=1)
        # Masts
        for mx, mh in [(0, 30), (-10*s, 22), (12*s, 24)]:
            self.draw_line(draw, x+mx, y-h//2, x+mx, y-h//2-int(mh*s), color=(40,30,20,200), width=int(2.5*s))
        # Sails
        for mx, mw, mh, side in [(0, 18*s, 12*s, 1), (-10*s, 12*s, 10*s, -1), (12*s, 14*s, 11*s, 1)]:
            pts = [(x+mx, y-h//2-int(mh)), (x+mx+side*mw, y-h//2-int(mh*0.3)),
                   (x+mx+side*int(mw*0.8), y-h//2), (x+mx, y-h//2+2*s)]
            self.draw_polygon(draw, pts, fill=(200,190,170,200), stroke=(160,150,130,150), stroke_width=1)
        # Pirate flag (skull)
        self.draw_rect(draw, x+2*s, y-h//2-int(32*s), 12*s, 8*s, fill=(15,15,15,220), stroke=(0,0,0,200), stroke_width=1)
        # Skull on flag
        self.draw_circle(draw, x+8*s, y-h//2-int(29*s), 2*s, fill=(220,220,220,200))
        # Crossbones
        self.draw_line(draw, x+5*s, y-h//2-int(26*s), x+11*s, y-h//2-int(23*s), color=(220,220,220,160), width=1)
        self.draw_line(draw, x+11*s, y-h//2-int(26*s), x+5*s, y-h//2-int(23*s), color=(220,220,220,160), width=1)

    def draw_galleon(self, draw, x, y, size=1.0, color=(70, 50, 35)):
        """Draw a large galleon with multiple decks and sails."""
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(60*s), int(16*s)
        # Hull
        hull = [(x-w//2, y+h//2), (x-w//2+3*s, y-h//2), (x+w//2-3*s, y-h//2), (x+w//2, y+h//2)]
        self.draw_polygon(draw, hull, fill=c+(200,), stroke=self._darken(c,30)+(180,), stroke_width=2)
        # Decks (castle structures)
        for dx, dw, dh in [(x-w//2+2*s, 18*s, 8*s), (x+w//2-22*s, 18*s, 8*s)]:
            self.draw_rect(draw, dx, y-h//2-dh, dw, dh, fill=self._lighten(c,10)+(200,),
                          stroke=self._darken(c,20)+(150,), stroke_width=1)
        # Masts
        for mx, mh in [(0, 36), (-12*s, 28), (14*s, 30)]:
            self.draw_line(draw, x+mx, y-h//2, x+mx, y-h//2-int(mh*s), color=(40,30,20,200), width=int(2.5*s))
        # Square sails
        for mx, mw, my in [(0, 22*s, 10*s), (-12*s, 18*s, 8*s), (14*s, 20*s, 9*s)]:
            for i in range(3):
                sy = y-h//2-int(my) + i*5*s
                self.draw_polygon(draw,
                    [(x+mx-mw//2, sy), (x+mx+mw//2, sy),
                     (x+mx+int(mw*0.9), sy+4*s), (x+mx-int(mw*0.9), sy+4*s)],
                    fill=(210,200,180,180), stroke=(170,160,140,120), stroke_width=1)

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

    def draw_windmill(self, draw, x, y, size=1.0, color=(150, 130, 110)):
        """Draw a windmill with tower and blades."""
        s = max(size, 0.3)
        c = tuple(color[:3])
        tw = int(20 * s)   # tower width at base
        th = int(40 * s)   # tower height
        tw_top = int(12 * s)  # tower width at top
        # Tower (trapezoid)
        tower_pts = [(x - tw//2, y), (x + tw//2, y),
                     (x + tw_top//2, y - th), (x - tw_top//2, y - th)]
        self.draw_shadow(draw, tower_pts, offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
        self.fill_gradient_polygon(draw, tower_pts, self._lighten(c, 10), self._darken(c, 20),
                                   stroke=(40, 35, 30, 150), stroke_width=1)
        # Tower windows
        win_w = int(3 * s)
        for wy in [y - th + int(8 * s), y - th + int(18 * s), y - th + int(28 * s)]:
            self.draw_rect(draw, x - win_w//2, wy, win_w, int(4 * s),
                          fill=(200, 200, 220, 200), stroke=(40, 35, 30, 150), stroke_width=1)
        # Conical roof
        roof_h = int(8 * s)
        roof_pts = [(x - tw_top//2 - int(2 * s), y - th),
                    (x + tw_top//2 + int(2 * s), y - th),
                    (x, y - th - roof_h)]
        self.draw_polygon(draw, roof_pts, fill=(120, 60, 40, 220),
                         stroke=(40, 35, 30, 150), stroke_width=1)
        # Blades (4 rotating arms)
        blade_c = (180, 180, 190)
        blade_len = int(18 * s)
        blade_w = int(3 * s)
        cx, cy = x, y - th - roof_h // 2
        draw.ellipse([cx - int(1.5 * s), cy - int(1.5 * s),
                     cx + int(1.5 * s), cy + int(1.5 * s)],
                    fill=(200, 200, 200), outline=(40, 35, 30), width=1)
        for angle in [0, 45, 90, 135]:
            rad = math.radians(angle)
            ex = cx + int(blade_len * math.cos(rad))
            ey = cy + int(blade_len * math.sin(rad))
            draw.line([(cx, cy), (ex, ey)], fill=blade_c, width=blade_w)
            # Blade sail (rectangle at end of each arm)
            sail_w = int(5 * s)
            sail_h = int(8 * s)
            sx = ex - int(sail_w * math.cos(rad)) // 2
            sy = ey - int(sail_h * math.sin(rad)) // 2
            draw.ellipse([sx - sail_w // 2, sy - sail_h // 2,
                         sx + sail_w // 2, sy + sail_h // 2],
                        fill=(220, 220, 230, 180), outline=(40, 35, 30, 100), width=1)

    def draw_factory(self, draw, x, y, width, height, color=(120, 100, 85), window_color=(200, 180, 100)):
        c = tuple(color[:3])
        wc = tuple(window_color[:3])
        bw = int(width)
        bh = int(height)

        smokestack_w = max(bw // 8, 4)
        smokestack_h = int(bh * 0.4)
        for sx in [x - bw//4, x + bw//4]:
            self.draw_rect(draw, sx - smokestack_w//2, y - bh - smokestack_h, smokestack_w, smokestack_h,
                           fill=self._darken(c, 15) + (220,))
            self.draw_rect(draw, sx - smokestack_w//2 - 2, y - bh - smokestack_h - 3, smokestack_w + 4, 4,
                           fill=self._darken(c, 25) + (200,))
            self.draw_circle(draw, sx, y - bh - smokestack_h - 5, 4, fill=(200, 200, 200, 100))
            self.draw_circle(draw, sx, y - bh - smokestack_h - 5, 2, fill=(150, 150, 150, 60))

        self.fill_gradient_rect(draw, x - bw//2, y - bh, bw, bh,
                                self._lighten(c, 15), self._darken(c, 20))

        n_cols = max(bw // 30, 3)
        n_rows = max(bh // 25, 3)
        win_w = bw // n_cols - 4
        win_h = bh // n_rows - 4
        for row in range(n_rows):
            for col in range(n_cols):
                wx = x - bw//2 + col * (bw // n_cols) + 2
                wy = y - bh + row * (bh // n_rows) + 2
                self.draw_rect(draw, wx, wy, win_w, win_h,
                               fill=wc + (180,), stroke=(40, 35, 30, 150), stroke_width=1)

        door_w = bw // 4
        door_h = int(bh * 0.2)
        self.draw_rect(draw, x - door_w//2, y - door_h, door_w, door_h,
                       fill=(60, 50, 40, 220), stroke=(40, 35, 30, 180), stroke_width=2)

    def draw_shop(self, draw, x, y, width, height, color=(180, 150, 120), window_color=(255, 240, 200)):
        c = tuple(color[:3])
        wc = tuple(window_color[:3])
        bw = int(width)
        bh = int(height)

        self.fill_gradient_rect(draw, x - bw//2, y - bh, bw, bh,
                                self._lighten(c, 15), self._darken(c, 20))

        awning_h = int(bh * 0.15)
        stripe_colors = [(200, 80, 80), (220, 200, 180)]
        stripe_w = bw // 8
        for si in range(8):
            sc = stripe_colors[si % 2]
            sx = x - bw//2 + si * stripe_w
            self.draw_polygon(draw, [(sx, y - bh), (sx + stripe_w, y - bh),
                                     (sx + stripe_w + 4, y - bh + awning_h),
                                     (sx - 4, y - bh + awning_h)],
                              fill=sc + (220,), stroke=(40, 35, 30, 100), stroke_width=1)
            self.draw_line(draw, sx + stripe_w//2, y - bh, sx + stripe_w//2 + 2, y - bh + awning_h,
                           color=(40, 35, 30, 60), width=1)

        display_h = int(bh * 0.35)
        display_y = y - bh + awning_h
        self.draw_rect(draw, x - bw//2 + 4, display_y, bw - 8, display_h,
                       fill=wc + (200,), stroke=(40, 35, 30, 150), stroke_width=2)
        self.draw_line(draw, x, display_y, x, display_y + display_h,
                       color=(40, 35, 30, 80), width=1)
        self.draw_line(draw, x - bw//4 + 4, display_y, x - bw//4 + 4, display_y + display_h,
                       color=(40, 35, 30, 60), width=1)
        self.draw_line(draw, x + bw//4 - 4, display_y, x + bw//4 - 4, display_y + display_h,
                       color=(40, 35, 30, 60), width=1)
        self.draw_circle(draw, x, display_y + display_h//2, 3,
                         fill=(255, 255, 200, 60))

        door_w = bw // 5
        door_h = int(bh * 0.3)
        door_x = x - bw//2 + (bw - door_w) // 2
        self.draw_rect(draw, door_x, y - door_h, door_w, door_h,
                       fill=(60, 50, 40, 220), stroke=(40, 35, 30, 180), stroke_width=2)
        self.draw_circle(draw, door_x + door_w - 4, y - door_h//2, 2,
                         fill=(200, 180, 100, 200))

        sign_w = bw // 3
        sign_h = int(bh * 0.06)
        self.draw_rect(draw, x - sign_w//2, y - bh - sign_h - 4, sign_w, sign_h,
                       fill=(60, 50, 40, 200))

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

    def draw_wall(self, draw, x, y, size=1.0, color=(140, 120, 100)):
        """Draw a stone wall with battlements."""
        s = size
        c = tuple(color[:3])
        w = int(40 * s)
        h = int(24 * s)
        # Main wall body
        self.draw_shadow(draw,
            [(x - w//2, y - h), (x + w//2, y - h),
             (x + w//2, y), (x - w//2, y)],
            offset=(2, 2), blur_radius=3, color=(0, 0, 0, 40))
        self.fill_gradient_rect(draw, x - w//2, y - h, w, h,
                                self._darken(c, 10), self._lighten(c, 15))
        # Battlements
        batt_count = 6
        batt_w = w // batt_count
        for i in range(batt_count):
            bx = x - w//2 + i * batt_w
            if i % 2 == 0:
                self.draw_rect(draw, bx, y - h - int(8*s), batt_w, int(8*s),
                               fill=c+(200,), stroke=self._darken(c, 20)+(150,), stroke_width=1)
        # Stone lines
        for row in range(4):
            ry = y - h + row * (h // 4)
            self.draw_line(draw, x - w//2, ry, x + w//2, ry,
                           color=self._darken(c, 15)+(80,), width=1)
        # Vertical mortar lines
        for i in range(1, batt_count):
            lx = x - w//2 + i * batt_w
            self.draw_line(draw, lx, y - h, lx, y,
                           color=self._darken(c, 15)+(80,), width=1)

    def draw_tent(self, draw, x, y, size=1.0, color=(160, 140, 100)):
        """Draw a tent with pole and opening."""
        s = size
        c = tuple(color[:3])
        w = int(32 * s)
        h = int(28 * s)
        # Shadow
        self.draw_polygon(draw,
            [(x - w//2 + 2, y + 2), (x + w//2 + 2, y + 2),
             (x + 2, y - h + 2)],
            fill=(0, 0, 0, 30))
        # Tent body (triangle)
        self.draw_polygon(draw,
            [(x - w//2, y), (x + w//2, y), (x, y - h)],
            fill=c+(210,), stroke=self._darken(c, 20)+(150,), stroke_width=2)
        # Pole
        self.draw_line(draw, x, y - h, x, y - h - int(6*s),
                       color=(80, 60, 40, 200), width=2)
        # Opening
        open_w = int(10 * s)
        open_h = int(14 * s)
        self.draw_polygon(draw,
            [(x - open_w//2, y), (x + open_w//2, y),
             (x, y - open_h)],
            fill=self._darken(c, 30)+(150,), stroke=self._darken(c, 20)+(100,), stroke_width=1)
        # Tent lines (fabric seams)
        self.draw_line(draw, x - w//4, y - h//2, x + w//4, y - h//2,
                       color=self._darken(c, 10)+(80,), width=1)
        self.draw_line(draw, x, y - h, x, y, color=self._darken(c, 10)+(60,), width=1)

    def draw_chain(self, draw, x, y, size=1.0, color=(100, 90, 80)):
        """Draw a chain with visible links."""
        s = size
        c = tuple(color[:3])
        n_links = 5
        link_w = int(10 * s)
        link_h = int(16 * s)
        gap = int(8 * s)
        total_w = n_links * (link_w + gap)
        start_x = x - total_w // 2
        for i in range(n_links):
            lx = start_x + i * (link_w + gap)
            # Outer oval
            self.draw_circle(draw, lx, y, link_h//2,
                           fill=(0,0,0,30))
            self.draw_rect(draw, lx - link_w//2, y - link_h//2, link_w, link_h,
                          fill=self._lighten(c, 10)+(200,),
                          stroke=self._darken(c, 20)+(150,), stroke_width=2, rx=link_w//2)
            # Inner hole
            self.draw_rect(draw, lx - link_w//4, y - link_h//4, link_w//2, link_h//2,
                          fill=(30, 30, 40, 180),
                          rx=link_w//4)

    def draw_tower(self, draw, x, y, size=1.0, color=(130, 110, 90)):
        """Draw a stone tower with battlements and windows."""
        s = size
        c = tuple(color[:3])
        w = int(24 * s)
        h = int(40 * s)
        # Shadow
        self.draw_shadow(draw,
            [(x - w//2, y - h), (x + w//2, y - h),
             (x + w//2, y), (x - w//2, y)],
            offset=(2, 2), blur_radius=3, color=(0, 0, 0, 40))
        # Tower body
        self.fill_gradient_rect(draw, x - w//2, y - h, w, h,
                                self._darken(c, 10), self._lighten(c, 15))
        # Battlements
        batt_count = 4
        batt_w = w // batt_count
        for i in range(batt_count):
            bx = x - w//2 + i * batt_w
            if i % 2 == 0:
                self.draw_rect(draw, bx, y - h - int(6*s), batt_w, int(6*s),
                               fill=c+(200,), stroke=self._darken(c, 20)+(150,), stroke_width=1)
        # Door
        door_w = int(8 * s)
        door_h = int(10 * s)
        self.draw_rect(draw, x - door_w//2, y - door_h, door_w, door_h,
                      fill=self._darken(c, 30)+(180,), stroke=self._darken(c, 20)+(120,), stroke_width=1)
        # Windows
        for wy in [y - h + int(14*s), y - h + int(24*s)]:
            self.draw_rect(draw, x - int(3*s), wy - int(4*s), int(6*s), int(8*s),
                          fill=(180, 190, 200, 150), stroke=(60, 50, 40, 100), stroke_width=1)
        # Stone lines
        for row in range(5):
            ry = y - h + row * (h // 5)
            self.draw_line(draw, x - w//2, ry, x + w//2, ry,
                           color=self._darken(c, 15)+(60,), width=1)

    def draw_fortress(self, draw, x, y, size=1.0, color=(120, 100, 80)):
        """Draw a fortress/castle with keep, towers and walls."""
        s = size
        c = tuple(color[:3])
        # Central keep
        kw, kh = int(24*s), int(32*s)
        # Side towers
        tw, th = int(14*s), int(22*s)
        # Walls connecting
        wall_h = int(12*s)
        # Shadow
        self.draw_shadow(draw,
            [(x - kw//2 - tw, y), (x + kw//2 + tw, y),
             (x + kw//2 + tw, y - th - 4), (x - kw//2 - tw, y - th - 4)],
            offset=(2, 3), blur_radius=4, color=(0, 0, 0, 50))
        # Left tower
        ltx = x - kw//2 - tw//2
        self.fill_gradient_rect(draw, ltx - tw//2, y - th, tw, th,
                                self._darken(c, 10), self._lighten(c, 15))
        # Right tower
        rtx = x + kw//2 + tw//2
        self.fill_gradient_rect(draw, rtx - tw//2, y - th, tw, th,
                                self._darken(c, 10), self._lighten(c, 15))
        # Connecting walls
        self.draw_rect(draw, x - kw//2, y - wall_h, kw, wall_h,
                      fill=c+(200,), stroke=self._darken(c, 20)+(150,), stroke_width=1)
        self.draw_rect(draw, ltx + tw//2, y - wall_h, kw//2 - tw//2, wall_h,
                      fill=c+(180,))
        self.draw_rect(draw, rtx - tw//2 - kw//2 + tw//2, y - wall_h, kw//2 - tw//2, wall_h,
                      fill=c+(180,))
        # Central keep
        self.fill_gradient_rect(draw, x - kw//2, y - kh, kw, kh,
                                self._darken(c, 15), self._lighten(c, 10))
        # Keep battlements
        for i in range(4):
            bx = x - kw//2 + i * (kw // 4)
            if i % 2 == 0:
                self.draw_rect(draw, bx, y - kh - int(5*s), kw//4, int(5*s),
                               fill=c+(200,), stroke=self._darken(c, 20)+(150,), stroke_width=1)
        # Tower battlements
        for tlx in [ltx, rtx]:
            for i in range(3):
                bx = tlx - tw//2 + i * (tw // 3)
                if i % 2 == 0:
                    self.draw_rect(draw, bx, y - th - int(4*s), tw//3, int(4*s),
                                   fill=c+(200,), stroke=self._darken(c, 20)+(150,), stroke_width=1)
        # Gate
        self.draw_rect(draw, x - int(6*s), y - int(10*s), int(12*s), int(10*s),
                      fill=self._darken(c, 30)+(180,), stroke=(60, 50, 40, 150), stroke_width=2, rx=2)
        # Gate arch (arc above door)
        self.draw_arc(draw, x, y - int(10*s), int(6*s), 180, 0,
                      color=(60, 50, 40, 150), width=2)
        # Windows on keep
        for wy in [y - kh + int(10*s), y - kh + int(18*s)]:
            self.draw_rect(draw, x - int(3*s), wy - int(4*s), int(6*s), int(8*s),
                          fill=(180, 190, 200, 150), stroke=(50, 40, 30, 100), stroke_width=1)
        # Flags on towers
        for fx, fy in [(ltx, y - th - int(4*s)), (rtx, y - th - int(4*s)), (x, y - kh - int(5*s))]:
            self.draw_line(draw, fx, fy, fx, fy - int(6*s),
                          color=(80, 60, 40, 200), width=2)
            self.draw_polygon(draw,
                [(fx, fy - int(6*s)), (fx + int(6*s), fy - int(3*s)), (fx, fy)],
                fill=(180, 40, 40, 200))

    def draw_soldier(self, draw, x, y, size=1.0, color=(140, 60, 60)):
        """Draw a medieval soldier with armor, shield and spear."""
        s = size
        c = tuple(color[:3])
        ss = max(int(12 * s), 6)  # base unit

        # Shield (left arm)
        shx = x - int(5 * s)
        shy = y - int(8 * s)
        self.draw_ellipse(draw, shx - int(4*s), shy - int(6*s), int(8*s), int(12*s),
                         fill=(140, 120, 100, 220), stroke=(80, 60, 40, 180), stroke_width=2)
        # Shield emblem (cross)
        self.draw_line(draw, shx, shy - int(4*s), shx, shy + int(4*s),
                      color=(180, 50, 50, 200), width=int(2*s))
        self.draw_line(draw, shx - int(3*s), shy, shx + int(3*s), shy,
                      color=(180, 50, 50, 200), width=int(2*s))

        # Body (tunic / breastplate)
        bw, bh = int(10*s), int(14*s)
        self.draw_rect(draw, x - bw//2, y - bh, bw, bh,
                      fill=c+(210,), stroke=self._darken(c, 20)+(150,), stroke_width=2)
        # Belt
        self.draw_rect(draw, x - bw//2, y - int(5*s), bw, int(2*s),
                      fill=(60, 40, 30, 200), stroke=(40, 30, 20, 150), stroke_width=1)
        # Legs
        leg_w = int(3*s)
        leg_h = int(8*s)
        for lx in [x - int(2.5*s), x + int(2.5*s)]:
            self.draw_rect(draw, lx - leg_w//2, y - int(1*s), leg_w, leg_h,
                          fill=(70, 50, 80, 200), stroke=(50, 35, 60, 150), stroke_width=1)
        # Boots
        for bx in [x - int(2.5*s), x + int(2.5*s)]:
            self.draw_rect(draw, bx - int(2*s), y + int(7*s), int(4*s), int(2*s),
                          fill=(40, 30, 25, 200))

        # Head / Helmet
        hr = int(5*s)
        # Face
        self.draw_circle(draw, x, y - bh - int(2*s), hr,
                        fill=(220, 190, 165, 200), stroke=self._darken(c, 20)+(150,), stroke_width=1)
        # Helmet
        self.draw_arc(draw, x, y - bh - int(2*s), int(6*s), 180, 0,
                     color=(80, 75, 70, 180), width=int(3*s))
        # Helmet crest/plume
        crest_col = (200, 50, 50, 200)
        self.draw_polygon(draw,
            [(x - int(2*s), y - bh - int(9*s)), (x + int(2*s), y - bh - int(9*s)),
             (x, y - bh - int(14*s))],
            fill=crest_col, stroke=(120, 30, 30, 150), stroke_width=1)

        # Spear (right hand)
        spx = x + int(6*s)
        self.draw_line(draw, spx, y - bh - int(6*s), spx, y + int(12*s),
                      color=(100, 85, 60, 200), width=int(2*s))
        # Spear head
        self.draw_polygon(draw,
            [(spx - int(2*s), y - bh - int(6*s)), (spx + int(2*s), y - bh - int(6*s)),
             (spx, y - bh - int(12*s))],
            fill=(180, 180, 190, 200))

    def draw_alien(self, draw, x, y, size=1.0, color=(80, 200, 120)):
        """Draw a classic alien with large head and eyes."""
        s = size
        c = tuple(color[:3])
        # Head
        head_r = int(10 * s)
        self.draw_ellipse(draw, x - head_r, y - head_r*2, head_r*2, head_r*2,
                         fill=c+(200,), stroke=self._darken(c, 20)+(150,), stroke_width=2)
        # Eyes (large black)
        eye_off = int(3*s)
        for ex in [x - eye_off, x + eye_off]:
            self.draw_circle(draw, ex, y - int(2*s), int(3*s),
                           fill=(10, 10, 10, 230))
            self.draw_circle(draw, ex - 1, y - int(3*s), 1,
                           fill=(255, 255, 255, 200))
        # Body (smaller)
        bw, bh = int(8*s), int(10*s)
        self.draw_rect(draw, x - bw//2, y, bw, bh,
                      fill=c+(180,), stroke=self._darken(c, 20)+(120,), stroke_width=1)
        # Arms
        for dx in [-1, 1]:
            self.draw_line(draw, x + dx*bw//2, y + int(2*s),
                          x + dx*bw//2 + dx*int(5*s), y + int(5*s),
                          color=c+(150,), width=int(2*s))
        # Legs
        for dx in [-1, 1]:
            self.draw_line(draw, x + dx*int(2*s), y + bh,
                          x + dx*int(3*s), y + bh + int(6*s),
                          color=c+(150,), width=int(2*s))

    def draw_artifact(self, draw, x, y, size=1.0, color=(100, 255, 200)):
        """Draw a glowing ancient artifact."""
        s = size
        c = tuple(color[:3])
        # Glow
        glow_r = int(16 * s)
        self.draw_circle(draw, x, y - int(4*s), glow_r,
                        fill=c+(60,))
        self.draw_circle(draw, x, y - int(4*s), int(glow_r*0.6),
                        fill=c+(100,))
        # Gem/core
        self.draw_polygon(draw,
            [(x, y - int(12*s)), (x + int(6*s), y - int(4*s)),
             (x, y + int(4*s)), (x - int(6*s), y - int(4*s))],
            fill=self._lighten(c, 20)+(220,), stroke=self._darken(c, 20)+(150,), stroke_width=2)
        # Pedestal
        pw = int(12*s)
        self.draw_rect(draw, x - pw//2, y + int(4*s), pw, int(3*s),
                      fill=(120, 100, 80, 200), stroke=(80, 60, 40, 150), stroke_width=1)
        self.draw_rect(draw, x - int(pw*0.7), y + int(7*s), int(pw*0.7*2), int(2*s),
                      fill=(100, 80, 60, 200))

    def draw_candle(self, draw, x, y, size=1.0, color=(255, 220, 180)):
        """Draw a candle with flame."""
        s = size
        c = tuple(color[:3])
        # Candle body
        cw, ch = int(6*s), int(16*s)
        self.draw_rect(draw, x - cw//2, y - ch, cw, ch,
                      fill=c+(210,), stroke=self._darken(c, 15)+(150,), stroke_width=1)
        # Wax drips
        for dx in [-1, 1]:
            self.draw_circle(draw, x + dx*cw//2, y - ch + int(3*s), int(1.5*s),
                           fill=c+(180,))
        # Wick
        self.draw_line(draw, x, y - ch, x, y - ch - int(2*s),
                      color=(40, 30, 20, 200), width=1)
        # Flame (teardrop)
        flame_c = (255, 200, 50, 220)
        self.draw_polygon(draw,
            [(x, y - ch - int(10*s)), (x + int(3*s), y - ch - int(3*s)),
             (x, y - ch), (x - int(3*s), y - ch - int(3*s))],
            fill=flame_c)
        # Inner flame
        self.draw_circle(draw, x, y - ch - int(5*s), int(2*s),
                        fill=(255, 255, 200, 200))

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
        self.draw_shadow_circle(draw, x, y + 3, 14*s, offset=(2, 2), blur_radius=4, color=(0, 0, 0, 35))

        body_w, body_h = 26*s, 14*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

        head_r = 6*s
        hx = x + body_w//2 + 2*s
        hy = y - body_h + 3*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 20) + (180,), stroke_width=2)

        self.draw_circle(draw, hx + 2*s, hy - 1*s, 1.3*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 3*s, hy + 4*s, 2*s, fill=(40, 35, 30, 200))
        self.draw_circle(draw, hx + 4*s, hy - 4*s, 2.5*s, fill=self._darken(c, 10) + (200,))

        leg_color = self._darken(c, 15)
        for lx in [-7*s, 4*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * 2*s, y - 4*s, x + lx + side * 2*s, y + 8*s,
                              color=leg_color, width=int(2.5*s))

        tx = x - body_w//2 - 3*s
        self.draw_line(draw, tx, y - body_h + 4*s, tx - 5*s, y - body_h - 4*s,
                      color=self._darken(c, 10), width=int(2*s))

    def draw_crocodile(self, draw, x, y, size=1.0, color=(60, 130, 50)):
        """Draw a crocodile — long body, snout, tail, bumpy back."""
        s = size
        c = tuple(color[:3])
        # Shadow
        self.draw_shadow_circle(draw, x, y + 3, 16*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        # Tail (curved)
        tail_pts = [(x - 18*s, y - 3*s), (x - 28*s, y - 8*s), (x - 30*s, y - 6*s),
                    (x - 28*s, y - 4*s), (x - 18*s, y - 1*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (220,),
                          stroke=self._darken(c, 20) + (180,), stroke_width=1)
        # Body
        body_pts = [(x - 18*s, y - 3*s), (x + 12*s, y - 5*s), (x + 14*s, y),
                    (x + 12*s, y + 2*s), (x - 18*s, y + 1*s)]
        self.draw_polygon(draw, body_pts, fill=c + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)
        # Bumpy back (scutes)
        for bx in range(int(x - 15*s), int(x + 10*s), 4):
            bh = 2*s if (bx - x) % 8 < 4 else 3*s
            self.draw_polygon(draw, [(bx, y - 4*s), (bx + 2*s, y - 4*s - bh), (bx + 4*s, y - 4*s)],
                              fill=self._darken(c, 20) + (200,))
        # Legs (short)
        leg_color = self._darken(c, 15)
        for lx, lsign in [(-12*s, -1), (8*s, -1), (-6*s, 1), (10*s, 1)]:
            self.draw_line(draw, x + lx, y + 1*s, x + lx + lsign*2*s, y + 4*s,
                           color=leg_color, width=int(2*s))
        # Head (long snout)
        head_pts = [(x + 12*s, y - 5*s), (x + 24*s, y - 6*s), (x + 28*s, y - 4*s),
                    (x + 26*s, y - 1*s), (x + 12*s, y + 2*s)]
        self.draw_polygon(draw, head_pts, fill=self._lighten(c, 10) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)
        # Eye ridge
        self.draw_circle(draw, x + 14*s, y - 6*s, 3*s, fill=self._lighten(c, 15) + (220,),
                         stroke=self._darken(c, 15) + (180,), stroke_width=1)
        # Eye
        self.draw_circle(draw, x + 14*s, y - 6*s, 1.5*s, fill=(200, 180, 60, 220))
        # Teeth (small triangles in jaw)
        for tx2 in range(int(x + 18*s), int(x + 26*s), 3):
            self.draw_polygon(draw, [(tx2, y - 1*s), (tx2 + 1*s, y + 1*s), (tx2 + 2*s, y - 1*s)],
                              fill=(240, 240, 230, 200))
        # Nostril
        self.draw_circle(draw, x + 27*s, y - 4*s, 1*s, fill=(30, 30, 30, 180))

    def draw_dinosaur(self, draw, x, y, size=1.0, color=(80, 100, 60)):
        """Draw a sauropod dinosaur — large body, long neck, tail, four legs."""
        s = size
        c = tuple(color[:3])
        # Shadow
        self.draw_shadow_circle(draw, x, y + 4, 18*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 30))
        # Tail
        tail_pts = [(x - 16*s, y - 4*s), (x - 26*s, y - 12*s), (x - 28*s, y - 10*s),
                    (x - 24*s, y - 6*s), (x - 16*s, y - 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (220,),
                          stroke=self._darken(c, 20) + (180,), stroke_width=1)
        # Body
        body_pts = [(x - 14*s, y - 4*s), (x - 2*s, y - 14*s), (x + 6*s, y - 14*s),
                    (x + 12*s, y - 6*s), (x + 10*s, y), (x - 14*s, y - 1*s)]
        self.draw_polygon(draw, body_pts, fill=c + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)
        # Neck (long, curved up)
        neck_pts = [(x + 6*s, y - 14*s), (x + 12*s, y - 22*s), (x + 10*s, y - 28*s),
                    (x + 6*s, y - 28*s), (x + 4*s, y - 22*s), (x + 2*s, y - 14*s)]
        self.draw_polygon(draw, neck_pts, fill=self._lighten(c, 5) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)
        # Head (small)
        head_pts = [(x + 10*s, y - 28*s), (x + 18*s, y - 30*s), (x + 20*s, y - 28*s),
                    (x + 18*s, y - 26*s), (x + 6*s, y - 26*s)]
        self.draw_polygon(draw, head_pts, fill=self._lighten(c, 10) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)
        # Eye
        self.draw_circle(draw, x + 12*s, y - 29*s, 1.5*s, fill=(200, 180, 60, 220))
        # Legs (thick, column-like)
        leg_color = self._darken(c, 15)
        for lx in [-10*s, -2*s, 2*s, 8*s]:
            lw = 3*s
            self.draw_rect(draw, x + lx - lw//2, y, lw, 5*s,
                          fill=leg_color + (220,), stroke=self._darken(leg_color, 15) + (180,), stroke_width=1)
        # Toes
        for lx in [-10*s, -2*s, 2*s, 8*s]:
            for tx3 in range(-1, 2):
                self.draw_circle(draw, x + lx + tx3*1.5*s, y + 5*s, 1*s, fill=(180, 170, 150, 200))

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

    def draw_horse(self, draw, x, y, size=1.0, color=(140, 100, 70)):
        """Draw a horse in side profile."""
        s = size
        c = tuple(color[:3])
        # Shadow
        self.draw_shadow_circle(draw, x, y + 4, 24*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        # Tail (flowing back and down)
        tail_pts = [(x - 20*s, y - 6*s), (x - 30*s, y - 4*s), (x - 34*s, y),
                    (x - 32*s, y + 6*s), (x - 28*s, y + 4*s), (x - 18*s, y - 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (210,),
                          stroke=self._darken(c, 20) + (160,), stroke_width=1)
        # Tail hair strands
        for strand in range(3):
            sx = x - 30*s + strand * 2*s
            self.draw_line(draw, sx, y - 2*s, sx - 4*s, y + 8*s,
                          color=self._darken(c, 20), width=int(1.5*s))

        # Body (large oval)
        body_cx, body_cy = x - 4*s, y - 12*s
        body_w, body_h = 32*s, 16*s
        self.draw_ellipse(draw, body_cx - body_w//2, body_cy - body_h//2, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Neck (curved up and forward)
        neck_pts = [(x + 8*s, y - 14*s), (x + 14*s, y - 26*s), (x + 12*s, y - 32*s),
                    (x + 8*s, y - 32*s), (x + 4*s, y - 26*s), (x + 2*s, y - 14*s)]
        self.draw_polygon(draw, neck_pts, fill=self._lighten(c, 5) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)

        # Mane (along top of neck)
        mane_c = self._darken(c, 25)
        for mi in range(6):
            ny = y - (16 + mi * 3) * s
            nx = x + (2 + mi * 2) * s
            self.draw_line(draw, nx - 2*s, ny, nx + 2*s, ny - 2*s,
                          color=mane_c, width=int(2*s))

        # Head (long snout)
        head_pts = [(x + 12*s, y - 32*s), (x + 24*s, y - 34*s), (x + 28*s, y - 32*s),
                    (x + 26*s, y - 28*s), (x + 20*s, y - 26*s), (x + 8*s, y - 28*s)]
        self.draw_polygon(draw, head_pts, fill=self._lighten(c, 10) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)

        # Ears (two small pointed triangles)
        for ex_offset in [12*s, 14*s]:
            ear_pts = [(x + ex_offset, y - 32*s),
                       (x + ex_offset + 1*s, y - 36*s),
                       (x + ex_offset + 3*s, y - 32*s)]
            self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 15) + (220,),
                              stroke=self._darken(c, 15) + (180,), stroke_width=1)

        # Eye
        self.draw_circle(draw, x + 16*s, y - 31*s, 1.5*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, x + 16*s, y - 31*s, 0.6*s, fill=(255, 255, 255, 160))

        # Nostril
        self.draw_circle(draw, x + 26*s, y - 30*s, 1*s, fill=(40, 35, 30, 180))

        # Mouth line
        self.draw_line(draw, x + 24*s, y - 28*s, x + 28*s, y - 29*s,
                      color=self._darken(c, 20), width=1)

        # Legs (four long slender legs with hooves)
        leg_c = self._darken(c, 15)
        hoof_c = (60, 55, 50)
        leg_positions = [(-12*s, 1), (-6*s, 1), (4*s, -1), (10*s, -1)]
        for lx, direction in leg_positions:
            # Upper leg
            self.draw_line(draw, x + lx, y - 4*s, x + lx + direction * 2*s, y + 4*s,
                          color=leg_c, width=int(2.5*s))
            # Lower leg
            self.draw_line(draw, x + lx + direction * 2*s, y + 4*s,
                          x + lx + direction * 3*s, y + 12*s,
                          color=leg_c, width=int(2*s))
            # Hoof
            self.draw_polygon(draw,
                             [(x + lx + direction * 2*s - 2*s, y + 12*s),
                              (x + lx + direction * 3*s + 2*s, y + 12*s),
                              (x + lx + direction * 3*s, y + 14*s),
                              (x + lx + direction * 2*s - s, y + 14*s)],
                             fill=hoof_c + (220,), stroke=(40, 35, 30, 150), stroke_width=1)

        # Knee joints
        for lx, direction in leg_positions:
            self.draw_circle(draw, x + lx + direction * 2*s, y + 4*s, 1.5*s,
                            fill=self._lighten(leg_c, 10) + (200,),
                            stroke=leg_c + (180,), stroke_width=1)

    def draw_elephant(self, draw, x, y, size=1.0, color=(130, 130, 140)):
        """Draw an African elephant — huge ear, curved trunk, tusks, thick legs."""
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 4, 24*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        # Body (large rounded ellipse)
        body_w, body_h = 36*s, 22*s
        self.draw_ellipse(draw, x, y - body_h//2 - 2*s, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Head (domed forehead, overlapping body)
        head_r = 11*s
        hx = x + 14*s
        hy = y - 16*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Huge fan-shaped ear (signature elephant feature)
        ear_c = self._darken(c, 8)
        ear_pts = [(hx + 4*s, hy - 6*s), (hx - 2*s, hy - 14*s), (hx - 6*s, hy - 10*s),
                   (hx - 8*s, hy - 2*s), (hx - 6*s, hy + 6*s), (hx + 2*s, hy + 4*s)]
        self.draw_polygon(draw, ear_pts, fill=ear_c + (200,),
                          stroke=self._darken(c, 20) + (160,), stroke_width=1)

        # Trunk (S-curve)
        trunk_pts = [(hx + 8*s, hy + 2*s), (hx + 14*s, hy - 2*s), (hx + 16*s, hy + 4*s),
                     (hx + 14*s, hy + 12*s), (hx + 10*s, hy + 16*s), (hx + 6*s, hy + 14*s)]
        self.draw_polygon(draw, trunk_pts, fill=self._lighten(c, 8) + (220,),
                          stroke=self._darken(c, 10) + (160,), stroke_width=1)
        # Trunk wrinkle lines
        for wy in range(4):
            wy2 = hy + 4*s + wy * 3*s
            wx1 = hx + 12*s - wy * s
            wx2 = hx + 15*s - wy * s
            self.draw_line(draw, wx1, wy2, wx2, wy2, color=self._darken(c, 15) + (100,), width=1)

        # Tusk (curving upward)
        tusk_color = (245, 240, 230)
        tusk_pts = [(hx + 10*s, hy + 4*s), (hx + 14*s, hy + 5*s), (hx + 13*s, hy + 1*s)]
        self.draw_polygon(draw, tusk_pts, fill=tusk_color + (220,),
                          stroke=(160, 150, 130, 150), stroke_width=1)

        # Eye
        self.draw_circle(draw, hx + 6*s, hy - 3*s, 1.8*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 6*s, hy - 3*s, 0.6*s, fill=(255, 255, 255, 150))

        # Tail
        tx = x - 18*s
        tail_pts = [(tx, y - 8*s), (tx - 8*s, y - 6*s), (tx - 6*s, y + 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (200,))
        self.draw_line(draw, tx - 6*s, y + 2*s, tx - 8*s, y + 6*s,
                      color=self._darken(c, 20), width=int(2*s))

        # Legs (thick columns)
        leg_c = self._darken(c, 15)
        for lx in [-10*s, -2*s, 4*s, 12*s]:
            self.draw_rect(draw, x + lx - 3*s, y - 4*s, 6*s, 10*s,
                          fill=leg_c + (220,), stroke=self._darken(leg_c, 10) + (160,), stroke_width=1)
            self.draw_rect(draw, x + lx - 3.5*s, y + 6*s, 7*s, 3*s,
                          fill=self._darken(leg_c, 15) + (220,))

    def draw_mammoth(self, draw, x, y, size=1.0, color=(150, 130, 100)):
        """Draw a woolly mammoth — long curved tusks, small ears, hump, shaggy fur."""
        s = size
        c = tuple(color[:3])
        fur_c = self._lighten(c, 5)
        dark_fur = self._darken(c, 15)
        self.draw_shadow_circle(draw, x, y + 4, 28*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        # Body (large rounded ellipse — stockier than elephant)
        body_w, body_h = 40*s, 24*s
        self.draw_ellipse(draw, x, y - body_h//2 - 2*s, body_w, body_h,
                          fill=fur_c + (220,), stroke=dark_fur + (180,), stroke_width=2)

        # Hump (distinctive shoulder hump)
        hump_pts = [(x - 6*s, y - 16*s), (x, y - 22*s), (x + 8*s, y - 20*s),
                    (x + 12*s, y - 14*s), (x + 6*s, y - 12*s)]
        self.draw_polygon(draw, hump_pts, fill=fur_c + (220,),
                          stroke=dark_fur + (160,), stroke_width=2)

        # Head (domed, lower than modern elephant)
        head_r = 10*s
        hx = x + 14*s
        hy = y - 14*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 3) + (220,),
                        stroke=dark_fur + (180,), stroke_width=2)

        # Small ear (mammoth ears are tiny vs African elephant)
        ear_pts = [(hx + 2*s, hy - 3*s), (hx - 2*s, hy - 8*s), (hx - 5*s, hy - 5*s),
                   (hx - 4*s, hy + 1*s)]
        self.draw_polygon(draw, ear_pts, fill=dark_fur + (200,),
                          stroke=self._darken(c, 25) + (160,), stroke_width=1)

        # Trunk (shorter, more curved than elephant)
        trunk_pts = [(hx + 6*s, hy + 1*s), (hx + 12*s, hy - 1*s), (hx + 14*s, hy + 3*s),
                     (hx + 12*s, hy + 10*s), (hx + 8*s, hy + 14*s)]
        self.draw_polygon(draw, trunk_pts, fill=fur_c + (220,),
                          stroke=dark_fur + (160,), stroke_width=1)
        # Trunk wrinkle lines
        for wy in range(3):
            wy2 = hy + 3*s + wy * 3*s
            wx1 = hx + 10*s - wy * s
            wx2 = hx + 13*s - wy * s
            self.draw_line(draw, wx1, wy2, wx2, wy2, color=dark_fur + (100,), width=1)

        # Long curved tusks (mammoth signature — very long, upward curve)
        tusk_color = (245, 240, 230)
        tusk_pts = [(hx + 8*s, hy + 4*s), (hx + 14*s, hy + 4*s),
                    (hx + 18*s, hy - 2*s), (hx + 20*s, hy - 6*s),
                    (hx + 16*s, hy - 4*s), (hx + 10*s, hy + 0*s)]
        self.draw_polygon(draw, tusk_pts, fill=tusk_color + (220,),
                          stroke=(160, 150, 130, 150), stroke_width=1)

        # Second tusk (behind, slightly offset)
        tusk2_pts = [(hx + 7*s, hy + 5*s), (hx + 13*s, hy + 5*s),
                     (hx + 16*s, hy - 1*s), (hx + 14*s, hy - 2*s),
                     (hx + 9*s, hy + 0*s)]
        self.draw_polygon(draw, tusk2_pts, fill=tusk_color + (180,),
                          stroke=(160, 150, 130, 120), stroke_width=1)

        # Eye
        self.draw_circle(draw, hx + 4*s, hy - 2*s, 1.5*s, fill=(25, 20, 15, 200))
        self.draw_circle(draw, hx + 4*s, hy - 2*s, 0.5*s, fill=(255, 255, 255, 150))

        # Shaggy fur texture (hanging hair along belly and legs)
        # Belly fur
        for fx in range(-12, 13, 3):
            fx2 = x + fx * s
            fy2 = y - 2*s
            fur_len = int(3*s + (fx % 4) * 0.5*s)
            self.draw_line(draw, fx2, fy2, fx2 - s, fy2 + fur_len,
                          color=dark_fur + (120,), width=int(1.5*s))

        # Legs (thick columns with fur)
        leg_c = dark_fur
        leg_positions = [-12*s, -4*s, 4*s, 12*s]
        for lx in leg_positions:
            lx_pos = x + lx
            self.draw_rect(draw, lx_pos - 4*s, y - 3*s, 8*s, 12*s,
                          fill=leg_c + (220,), stroke=self._darken(leg_c, 10) + (160,), stroke_width=1)
            # Fur tufts at bottom of legs
            self.draw_ellipse(draw, lx_pos, y + 8*s, 9*s, 3*s,
                             fill=dark_fur + (200,), stroke=self._darken(dark_fur, 10) + (140,), stroke_width=1)
            # Hoof
            self.draw_rect(draw, lx_pos - 3.5*s, y + 9*s, 7*s, 2*s,
                          fill=self._darken(leg_c, 20) + (220,))

    def draw_dog(self, draw, x, y, size=1.0, color=(180, 140, 100)):
        """Draw a dog — four legs, tail, floppy ears, snout."""
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

        body_w, body_h = 24*s, 12*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        for side in [-1, 1]:
            self.draw_line(draw, x + side * 8*s, y - 2*s, x + side * 14*s, y + 8*s,
                          color=self._darken(c, 15), width=int(2.5*s))

        tail_color = self._lighten(c, 10)
        self.draw_line(draw, x - body_w//2, y - 6*s, x - body_w//2 - 6*s, y - 12*s,
                      color=tail_color, width=int(2.5*s))
        self.draw_circle(draw, x - body_w//2 - 6*s, y - 12*s, 2*s,
                        fill=tail_color + (220,))

        head_r = 6*s
        hx = x + body_w//2 + 4*s
        hy = y - body_h + 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        snout_pts = [(hx + 2*s, hy - s), (hx + 8*s, hy), (hx + 8*s, hy + 3*s),
                     (hx + 2*s, hy + 4*s)]
        self.draw_polygon(draw, snout_pts, fill=self._lighten(c, 12) + (220,),
                          stroke=self._darken(c, 10) + (160,), stroke_width=1)

        self.draw_circle(draw, hx + 8*s, hy + 1.5*s, 1.5*s, fill=(40, 35, 30, 200))

        # Single ear (floppy, side profile)
        ex = hx + 4*s; ey = hy - 3*s
        self.draw_ellipse(draw, ex - 2.5*s, ey - 4*s, 5*s, 8*s,
                          fill=self._darken(c, 10) + (200,),
                          stroke=self._darken(c, 20) + (160,), stroke_width=1)

        self.draw_circle(draw, hx + 2*s, hy - 2*s, 1.5*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 2*s, hy - 2*s, 0.5*s, fill=(255, 255, 255, 160))

        mouth_line = self._darken(c, 20)
        self.draw_line(draw, hx + 6*s, hy + 3*s, hx + 8*s, hy + 3.5*s, color=mouth_line, width=1)
        self.draw_line(draw, hx + 6*s, hy + 3*s, hx + 4*s, hy + 4*s, color=mouth_line, width=1)

    def draw_cat(self, draw, x, y, size=1.0, color=(200, 160, 120), pose="standing", mood=None):
        """Draw a cat — standing or sitting pose, with optional mood expression."""

        def _draw_face(hx, hy, mood, s):
            """Draw cat face with mood expression."""
            if mood == "sad":
                # Droopy half-closed eye (sad slant)
                self.draw_line(draw, hx + 2*s, hy - 2*s, hx + 4*s, hy - 1*s,
                              color=(30, 25, 20, 220), width=int(1.5*s))
                self.draw_arc(draw, hx + 2*s, hy - 2*s, 2*s, 0, 180,
                             color=(30, 25, 20, 200), width=1)
                # Tear duct (red)
                self.draw_circle(draw, hx + 4*s, hy - 0.5*s, 1.5*s, fill=(200, 80, 80, 180))
                # Big teardrop streaming down
                self.draw_ellipse(draw, hx + 4*s, hy + 1*s, int(2*s), int(4*s),
                                 fill=(180, 200, 240, 160))
                self.draw_ellipse(draw, hx + 4*s, hy + 3.5*s, int(1.5*s), int(3*s),
                                 fill=(180, 200, 240, 120))
                # Tear streak line
                self.draw_line(draw, hx + 4*s, hy + 4*s, hx + 4*s, hy + 8*s,
                              color=(180, 200, 240, 80), width=int(1.5*s))
                # Downward frowning mouth
                self.draw_line(draw, hx + 2*s, hy + 4*s, hx + 4*s, hy + 5*s,
                              color=(140, 100, 80, 180), width=int(1.5*s))
                self.draw_line(draw, hx + 4*s, hy + 5*s, hx + 6*s, hy + 4.5*s,
                              color=(140, 100, 80, 150), width=1)
                # Drooping whiskers (sagging downward)
                self.draw_line(draw, hx + 5*s, hy + 3*s, hx + 10*s, hy + 5*s,
                              color=(180, 170, 160, 150), width=1)
                self.draw_line(draw, hx + 5*s, hy + 4*s, hx + 9*s, hy + 7*s,
                              color=(180, 170, 160, 120), width=1)
                self.draw_line(draw, hx + 5*s, hy + 3*s, hx + 0*s, hy + 5*s,
                              color=(180, 170, 160, 150), width=1)
                self.draw_line(draw, hx + 5*s, hy + 4*s, hx + 1*s, hy + 7*s,
                              color=(180, 170, 160, 120), width=1)
                # Red nose from crying
                self.draw_circle(draw, hx + 5*s, hy + 1.5*s, 2*s, fill=(220, 120, 120, 200))
            elif mood == "angry":
                # Angry eyes (slanted)
                self.draw_line(draw, hx + 2*s, hy - 1.5*s, hx + 4.5*s, hy - s,
                              color=(30, 25, 20, 200), width=int(1.5*s))
                self.draw_line(draw, hx + 1.5*s, hy - 2*s, hx + 3*s, hy - 0.5*s,
                              color=(30, 25, 20, 150), width=int(s))
                # Snout
                self.draw_circle(draw, hx + 5*s, hy + 1*s, 2.5*s, fill=(240, 200, 190, 200))
                # Angry mouth (zigzag)
                self.draw_line(draw, hx + 3*s, hy + 2*s, hx + 5*s, hy + 1*s,
                              color=(140, 100, 80, 150), width=1)
                self.draw_line(draw, hx + 5*s, hy + 1*s, hx + 6*s, hy + 2*s,
                              color=(140, 100, 80, 150), width=1)
            elif mood == "happy":
                # Happy eyes (closed arcs)
                self.draw_arc(draw, hx + 3*s, hy - s, 1.5*s, 180, 0,
                             color=(30, 25, 20, 200), width=int(1.5*s))
                # Snout
                self.draw_circle(draw, hx + 5*s, hy + 1*s, 2.5*s, fill=(240, 200, 190, 200))
                # Happy mouth (smile)
                self.draw_arc(draw, hx + 3.5*s, hy + s, 2*s, 0, 180,
                             color=(140, 100, 80, 150), width=1)
            elif mood == "surprised":
                # Wide eyes
                self.draw_circle(draw, hx + 3*s, hy - s, 2*s, fill=(255, 255, 255, 220))
                self.draw_circle(draw, hx + 3*s, hy - s, s, fill=(30, 25, 20, 200))
                # Open mouth
                self.draw_circle(draw, hx + 4.5*s, hy + 2*s, 2*s, fill=(200, 100, 100, 200))
            elif mood == "proud":
                # Smug half-closed eyes
                self.draw_line(draw, hx + 2*s, hy - 1.5*s, hx + 4*s, hy - 2*s,
                              color=(30, 25, 20, 220), width=int(1.5*s))
                # Chin lifted (snout slightly higher)
                self.draw_circle(draw, hx + 5*s, hy + 0.5*s, 2.5*s, fill=(240, 200, 190, 200))
                # Smug smile
                self.draw_arc(draw, hx + 3*s, hy + 1.5*s, 2*s, 0, 180,
                             color=(140, 100, 80, 180), width=int(1.5*s))
                # Perked ear hint (pupil highlight)
                self.draw_circle(draw, hx + 3*s, hy - 2.5*s, 0.8*s, fill=(255, 255, 255, 180))
            elif mood == "sneaky":
                # Narrowed, cunning eyes
                self.draw_line(draw, hx + 2*s, hy - 1*s, hx + 4*s, hy - 0.5*s,
                              color=(30, 25, 20, 220), width=int(1.5*s))
                self.draw_circle(draw, hx + 3*s, hy - 1*s, 0.8*s, fill=(30, 25, 20, 200))
                # One ear back (asymmetrical)
                self.draw_line(draw, hx + 3*s, hy - 4*s, hx + 5*s, hy - 7*s,
                              color=(180, 140, 100, 120), width=int(2*s))
                # Sly half-smile
                self.draw_line(draw, hx + 3.5*s, hy + 2*s, hx + 5.5*s, hy + 2.5*s,
                              color=(140, 100, 80, 160), width=1)
            elif mood == "focused":
                # Intense wide eyes (hunting mode)
                self.draw_circle(draw, hx + 3*s, hy - s, 2*s, fill=(255, 255, 255, 220))
                self.draw_circle(draw, hx + 3*s, hy - s, 1.2*s, fill=(30, 25, 20, 220))
                # Pupil slit
                self.draw_line(draw, hx + 3*s, hy - 2*s, hx + 3*s, hy + 0.5*s,
                              color=(30, 25, 20, 220), width=int(s * 0.5))
                # Flattened ears
                self.draw_line(draw, hx + 3*s, hy - 4*s, hx + 6*s, hy - 2*s,
                              color=(180, 140, 100, 150), width=int(2*s))
                # Tense, straight mouth
                self.draw_line(draw, hx + 3*s, hy + 2*s, hx + 6*s, hy + 2*s,
                              color=(140, 100, 80, 160), width=1)
            elif mood == "mysterious":
                # Glowing wide eyes in shadow
                self.draw_circle(draw, hx + 3*s, hy - s, 2*s, fill=(200, 220, 100, 200))
                self.draw_circle(draw, hx + 3*s, hy - s, 0.8*s, fill=(30, 25, 20, 200))
                # Slight knowing smile
                self.draw_arc(draw, hx + 3*s, hy + 1*s, 2*s, 0, 180,
                             color=(140, 100, 80, 120), width=1)
            elif mood == "cautious":
                # Wide eyes, scanning
                self.draw_circle(draw, hx + 2.5*s, hy - 1.5*s, 1.8*s, fill=(255, 255, 255, 200))
                self.draw_circle(draw, hx + 2.5*s, hy - 1.5*s, 0.8*s, fill=(30, 25, 20, 200))
                self.draw_circle(draw, hx + 3.5*s, hy - 1.5*s, 1.8*s, fill=(255, 255, 255, 200))
                self.draw_circle(draw, hx + 3.5*s, hy - 1.5*s, 0.8*s, fill=(30, 25, 20, 200))
                # Ears slightly back
                self.draw_line(draw, hx + 2*s, hy - 4*s, hx + 4*s, hy - 8*s,
                              color=(180, 140, 100, 180), width=int(2*s))
                self.draw_line(draw, hx + 5*s, hy - 4*s, hx + 6*s, hy - 7*s,
                              color=(180, 140, 100, 120), width=int(1.5*s))
                # Tense mouth
                self.draw_line(draw, hx + 3*s, hy + 2*s, hx + 5*s, hy + 1.5*s,
                              color=(140, 100, 80, 150), width=1)
            elif mood == "triumphant":
                # Bright, wide eyes
                self.draw_circle(draw, hx + 3*s, hy - s, 2*s, fill=(255, 255, 255, 220))
                self.draw_circle(draw, hx + 3*s, hy - s, 1*s, fill=(30, 25, 20, 200))
                self.draw_circle(draw, hx + 3*s, hy - s, 0.5*s, fill=(255, 255, 255, 220))
                # Perked ears
                ear_pts = [(hx + 3*s, hy - 3*s), (hx + 4*s, hy - 9*s), (hx + 6*s, hy - 3*s)]
                self.draw_polygon(draw, ear_pts, fill=(240, 200, 180, 220))
                # Big confident smile
                self.draw_arc(draw, hx + 3*s, hy + 1.5*s, 2.5*s, 0, 180,
                             color=(140, 100, 80, 200), width=int(1.5*s))
                # Chin lifted
                self.draw_circle(draw, hx + 5*s, hy + 0.5*s, 2.5*s, fill=(245, 210, 200, 200))
            else:
                # Neutral / default eye (single dot + pupil)
                self.draw_circle(draw, hx + 3*s, hy - s, 1.5*s, fill=(30, 25, 20, 200))
                self.draw_circle(draw, hx + 3*s, hy - s, 0.5*s, fill=(255, 255, 255, 180))
                # Snout
                self.draw_circle(draw, hx + 5*s, hy + 1*s, 2.5*s, fill=(240, 200, 190, 200))

        s = size
        c = tuple(color[:3])

        if pose == "sitting":
            # Sitting side-profile cat (facing right)
            self.draw_shadow_circle(draw, x, y + 3, 16*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

            body_w, body_h = 16*s, 12*s
            bx = x - 2*s
            by = y - body_h - 4*s
            self.draw_ellipse(draw, bx, by, body_w, body_h,
                              fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

            # Tail curving up
            tail_pts = [(x - 7*s, y - 6*s), (x - 14*s, y - 14*s), (x - 16*s, y - 6*s),
                        (x - 12*s, y - 2*s)]
            self.draw_polygon(draw, tail_pts, fill=c + (210,),
                              stroke=self._darken(c, 15) + (160,), stroke_width=1)

            # Head (right side of body)
            head_r = 6*s
            hx = x + body_w//2 - 2*s + 3*s
            hy = y - body_h - 4*s - s
            self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                            stroke=self._darken(c, 15) + (180,), stroke_width=2)

            # Single ear (side profile)
            ear_pts = [(hx + 3*s, hy - 3*s), (hx + 4*s, hy - 9*s), (hx + 6*s, hy - 3*s)]
            self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 15) + (220,),
                              stroke=self._darken(c, 15) + (180,), stroke_width=1)
            inner_ear = [(hx + 3.5*s, hy - 3.5*s), (hx + 4*s, hy - 8*s), (hx + 5*s, hy - 3.5*s)]
            self.draw_polygon(draw, inner_ear, fill=(240, 200, 180, 180))

            # Eye
            _draw_face(hx, hy, mood, s)

            # Snout / whiskers — skip for moods that draw their own details
            if mood not in ("sad", "angry", "surprised", "proud", "sneaky", "focused", "mysterious", "cautious", "triumphant"):
                self.draw_circle(draw, hx + 5*s, hy + 2*s, 2.5*s, fill=(240, 200, 190, 200))

                # Whiskers
                for side in [-1, 1]:
                    self.draw_line(draw, hx + 5*s, hy + 2.5*s, hx + 5*s + side * 6*s, hy + 1.5*s,
                                  color=(180, 170, 160, 120), width=1)
                    self.draw_line(draw, hx + 5*s, hy + 3*s, hx + 5*s + side * 5*s, hy + 3.5*s,
                                  color=(180, 170, 160, 120), width=1)

                # Mouth line
                self.draw_line(draw, hx + 2*s, hy + 3*s, hx + 5*s, hy + 2*s, color=(140, 100, 80, 150), width=1)

            # Haunch (back leg tucked)
            haunch_r = 5*s
            self.draw_ellipse(draw, x - 7*s, y - 6*s, 8*s, 6*s,
                             fill=self._darken(c, 5) + (200,),
                             stroke=self._darken(c, 15) + (160,), stroke_width=1)

            # Front leg hanging down
            self.draw_line(draw, x - s, y - 2*s, x + s, y + 4*s,
                          color=self._darken(c, 15), width=int(3*s))
            self.draw_line(draw, x + 2*s, y - 2*s, x + 4*s, y + 4*s,
                          color=self._darken(c, 15), width=int(3*s))

            # Back foot tucked
            self.draw_ellipse(draw, x - 7*s, y - 2*s, 5*s, 3*s,
                             fill=self._darken(c, 5) + (200,),
                             stroke=self._darken(c, 15) + (160,), stroke_width=1)

            return

        # ── Standing pose (original) ──
        self.draw_shadow_circle(draw, x, y + 3, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

        body_w, body_h = 20*s, 10*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h - 2*s, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        tail_pts = [(x - 10*s, y - 8*s), (x - 16*s, y - 12*s), (x - 18*s, y - 6*s),
                    (x - 14*s, y - 2*s)]
        self.draw_polygon(draw, tail_pts, fill=c + (210,),
                          stroke=self._darken(c, 15) + (160,), stroke_width=1)

        head_r = 5*s
        hx = x + body_w//2 + 3*s
        hy = y - body_h - 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Single ear (side profile)
        ear_pts = [(hx + 3*s, hy - 3*s), (hx + 4*s, hy - 8*s), (hx + 6*s, hy - 3*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 15) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)
        inner_ear = [(hx + 3.5*s, hy - 3.5*s), (hx + 4*s, hy - 7*s), (hx + 5*s, hy - 3.5*s)]
        self.draw_polygon(draw, inner_ear, fill=(240, 200, 180, 180))

        # standing pose face
        _draw_face(hx, hy, mood, s)

        # Whiskers (only for moods that don't draw their own)
        if mood not in ("sad", "angry", "surprised", "proud"):
            self.draw_circle(draw, hx + 5*s, hy + 1*s, 2.5*s, fill=(240, 200, 190, 200))
            for side in [-1, 1]:
                self.draw_line(draw, hx + 5*s, hy + 1.5*s, hx + 5*s + side * 6*s, hy + 0.5*s,
                              color=(180, 170, 160, 120), width=1)
                self.draw_line(draw, hx + 5*s, hy + 2*s, hx + 5*s + side * 5*s, hy + 2.5*s,
                              color=(180, 170, 160, 120), width=1)
            self.draw_line(draw, hx + 2*s, hy + 2*s, hx + 5*s, hy + 1*s, color=(140, 100, 80, 150), width=1)

        for side in [-1, 1]:
            self.draw_line(draw, x + side * 6*s, y - 3*s, x + side * 8*s, y + 8*s,
                          color=self._darken(c, 15), width=int(2*s))

    def draw_bear(self, draw, x, y, size=1.0, color=(120, 80, 60)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 18*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        body_w, body_h = 30*s, 18*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Shoulder hump
        hump_pts = [(x - 4*s, y - body_h - s), (x + 4*s, y - body_h - 6*s), (x + 10*s, y - body_h - s)]
        self.draw_polygon(draw, hump_pts, fill=self._darken(c, 5) + (200,))

        # Head (side profile facing right — far ear hidden)
        head_r = 9*s
        hx = x + body_w//2 + s
        hy = y - body_h + 4*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Only near ear visible in side profile
        ear_r = 3.5*s
        self.draw_circle(draw, hx + 5*s, hy - 7*s, ear_r,
                        fill=self._lighten(c, 12) + (220,),
                        stroke=self._darken(c, 10) + (160,), stroke_width=1)
        self.draw_circle(draw, hx + 5*s, hy - 7*s, ear_r * 0.5,
                        fill=self._darken(c, 5) + (180,))

        # Snout / muzzle
        snout_r = 4.5*s
        self.draw_ellipse(draw, hx + 3*s - snout_r, hy - snout_r*0.3, snout_r*2, snout_r*1.3,
                          fill=self._lighten(c, 15) + (200,))
        self.draw_circle(draw, hx + 7*s, hy + 1*s, 1.8*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 3*s, hy - 2*s, 1.8*s, fill=(30, 25, 20, 200))

        # Legs (thick bear limbs)
        leg_c = self._darken(c, 15)
        for lx in [-8*s, 4*s]:
            for side in [-1, 1]:
                self.draw_rect(draw, x + lx + side * 3*s, y - 6*s, 5*s, 10*s,
                              fill=leg_c + (220,), stroke=self._darken(leg_c, 10) + (160,), stroke_width=1)

        tx = x - body_w//2 - 2*s
        self.draw_circle(draw, tx, y - body_h + 4*s, 3*s, fill=self._darken(c, 10) + (200,))

    def draw_deer(self, draw, x, y, size=1.0, color=(180, 140, 100)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

        body_w, body_h = 22*s, 12*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        head_r = 5*s
        hx = x + body_w//2 + 4*s
        hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        for antler_branch in range(3):
            ax = hx + 2*s + antler_branch * 2*s
            self.draw_line(draw, ax, hy - 4*s, ax + 2*s, hy - 8*s - antler_branch * 2*s,
                          color=self._darken(c, 25), width=int(1.5*s))
            self.draw_line(draw, ax + 2*s, hy - 8*s - antler_branch * 2*s,
                          ax + 4*s, hy - 6*s - antler_branch * 2*s,
                          color=self._darken(c, 25), width=int(1*s))

        # Only near ear visible in side profile
        ear_pts = [(hx + 3*s, hy - 3*s), (hx + 4*s, hy - 7*s), (hx + 5*s, hy - 3*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 12) + (220,),
                          stroke=self._darken(c, 10) + (160,), stroke_width=1)

        snout_pts = [(hx + 3*s, hy - s), (hx + 7*s, hy), (hx + 7*s, hy + 2*s), (hx + 3*s, hy + 2*s)]
        self.draw_polygon(draw, snout_pts, fill=self._lighten(c, 8) + (200,))

        self.draw_circle(draw, hx + 7*s, hy + 0.5*s, 1.2*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 3*s, hy - 1.5*s, 1.2*s, fill=(30, 25, 20, 200))

        leg_c = self._darken(c, 15)
        for lx in [-8*s, 4*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * 2*s, y - 4*s,
                              x + lx + side * 2*s, y + 8*s,
                              color=leg_c, width=int(2*s))
                self.draw_line(draw, x + lx + side * 2*s, y + 4*s,
                              x + lx + side * s, y + 8*s,
                              color=self._darken(c, 20), width=1)

        self.draw_circle(draw, x - body_w//2 - 2*s, y - body_h//2, 2*s,
                        fill=c + (200,))

    def draw_rabbit(self, draw, x, y, size=1.0, color=(200, 180, 170)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))

        body_w, body_h = 16*s, 10*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        head_r = 5*s
        hx = x + body_w//2 + 3*s
        hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Only near ear visible in side profile
        ear_pts = [(hx + 2*s, hy - 3*s), (hx + 3*s, hy - 12*s), (hx + 4*s, hy - 3*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 15) + (220,),
                          stroke=self._darken(c, 10) + (160,), stroke_width=1)
        inner_ear = [(hx + 2.5*s, hy - 4*s), (hx + 3*s, hy - 10*s), (hx + 3.5*s, hy - 4*s)]
        self.draw_polygon(draw, inner_ear, fill=(240, 200, 190, 180))

        snout_r = 2.5*s
        self.draw_circle(draw, hx + 5*s, hy + 1*s, snout_r, fill=(240, 220, 210, 200))
        self.draw_circle(draw, hx + 6.5*s, hy + 0.5*s, 1*s, fill=(40, 35, 30, 200))

        self.draw_circle(draw, hx + 3*s, hy - 1*s, 1.3*s, fill=(30, 25, 20, 200))

        for side in [-1, 1]:
            self.draw_line(draw, hx + 5*s, hy + 1.5*s, hx + 5*s + side * 4*s, hy + 0.5*s,
                          color=(180, 170, 160, 100), width=1)

        tail_r = 2.5*s
        self.draw_circle(draw, x - body_w//2 - s, y - body_h + 3*s, tail_r,
                        fill=self._lighten(c, 20) + (200,))

        leg_c = self._darken(c, 12)
        for lx in [-5*s, 3*s]:
            for side in [-1, 1]:
                self.draw_ellipse(draw, x + lx + side * 2*s - 2*s, y - 2*s, 3*s, 5*s,
                                  fill=leg_c + (200,))

    def draw_cow(self, draw, x, y, size=1.0, color=(240, 230, 220)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 16*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        spot_color = (60, 50, 50)
        body_w, body_h = 28*s, 16*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        for sx, sy, sw, sh in [(-6*s, -12*s, 6*s, 5*s), (4*s, -10*s, 5*s, 4*s), (-2*s, -6*s, 4*s, 3*s)]:
            self.draw_ellipse(draw, x + sx, y + sy, sw, sh, fill=spot_color + (180,))

        head_r = 7*s
        hx = x + body_w//2 + 3*s
        hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        self.draw_ellipse(draw, hx + 2*s - 2*s, hy - 5*s - 2*s, 3*s, 4*s, fill=spot_color + (200,))

        # Single near horn, single near ear (side profile)
        horn_pts = [(hx + 3*s, hy - 5*s), (hx + 4*s, hy - 9*s), (hx + 5*s, hy - 5*s)]
        self.draw_polygon(draw, horn_pts, fill=(200, 190, 170, 220),
                          stroke=(140, 130, 110, 160), stroke_width=1)

        ear_pts = [(hx + 4*s, hy - 3*s), (hx + 6*s, hy - 5*s), (hx + 5*s, hy - 2*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 10) + (200,))

        snout_r = 3.5*s
        self.draw_ellipse(draw, hx + 4*s - snout_r, hy - snout_r, snout_r*2, snout_r*1.5,
                          fill=(230, 200, 200, 200))
        for nostril_side in [-1, 1]:
            self.draw_circle(draw, hx + 6*s + nostril_side * s, hy + 1*s, 1*s, fill=(40, 35, 30, 200))

        self.draw_circle(draw, hx + 3*s, hy - 2*s, 1.5*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 3*s, hy - 2*s, 0.5*s, fill=(255, 255, 255, 150))

        bell_c = (200, 180, 100)
        self.draw_circle(draw, hx + s, hy + 4*s, 2*s, fill=bell_c + (200,),
                        stroke=(160, 140, 80, 160), stroke_width=1)

        leg_c = self._darken(c, 15)
        for lx in [-9*s, 5*s]:
            for side in [-1, 1]:
                self.draw_rect(draw, x + lx + side * 2*s, y - 4*s, 4*s, 9*s,
                              fill=leg_c + (220,), stroke=self._darken(leg_c, 10) + (160,), stroke_width=1)
                self.draw_rect(draw, x + lx + side * 2*s - s, y + 5*s, 6*s, 2*s,
                              fill=self._darken(leg_c, 15) + (220,))

        tx = x - body_w//2 - 2*s
        self.draw_line(draw, tx, y - body_h + 4*s, tx - 5*s, y - 6*s,
                      color=self._darken(c, 10), width=int(2*s))
        tail_tip = (200, 180, 180)
        self.draw_circle(draw, tx - 5*s, y - 6*s, 2*s, fill=tail_tip + (200,))

    def draw_pyramid(self, draw, x, y, size=1.0, color=(180, 150, 120), steps=5):
        """Draw a Maya step pyramid — proper proportions, temple on top, stone texture."""
        s = max(size, 2.0)
        c = tuple(color[:3])
        base_w = int(24 * s)
        max_h = int(38 * s)
        self.draw_shadow_circle(draw, x, y + 3, base_w // 2, offset=(4, 4), blur_radius=6, color=(0, 0, 0, 40))

        # Steps from bottom to top
        n = max(4, steps)
        for i in range(n):
            t = i / n
            lw = int(base_w * (1 - t * 0.55))
            lh = int(max_h / n)
            ly = y - max_h + i * lh
            lx = x - lw // 2
            # Step color: darker at bottom, lighter at top
            shade = self._darken(c, 8 * (n - i)) if i < n - 1 else self._lighten(c, 10)
            self.draw_rect(draw, lx, ly, lw, lh, fill=shade + (235,),
                          stroke=self._darken(c, 20) + (180,), stroke_width=2)
            # Stone joint lines per step face
            joints = 2 + i
            for j in range(1, joints):
                jx = lx + lw * j // joints
                self.draw_line(draw, jx, ly, jx, ly + lh, color=self._darken(c, 25) + (80,), width=1)
            # Horizontal stone line
            self.draw_line(draw, lx, ly + lh // 2, lx + lw, ly + lh // 2,
                          color=self._darken(c, 20) + (60,), width=1)

        # Temple shrine on top
        sh_w = int(base_w * 0.35)
        sh_h = int(max_h * 0.15)
        sh_x = x - sh_w // 2
        sh_y = y - max_h - sh_h
        self.draw_rect(draw, sh_x, sh_y, sh_w, sh_h, fill=self._lighten(c, 15) + (235,),
                      stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Roof crest
        cr_w = int(sh_w * 0.6)
        cr_h = int(sh_h * 0.5)
        self.draw_rect(draw, x - cr_w // 2, sh_y - cr_h, cr_w, cr_h, fill=self._darken(c, 5) + (220,),
                      stroke=self._darken(c, 20) + (160,), stroke_width=2)
        # Doorway in shrine
        dw, dh = int(sh_w * 0.35), int(sh_h * 0.7)
        self.draw_rect(draw, x - dw // 2, sh_y + sh_h - dh, dw, dh, fill=(20, 18, 15, 230))
        # Door arch
        self.draw_arc(draw, x - dw // 2, sh_y + sh_h - dh, dw // 2, 0, 180,
                     color=(20, 18, 15, 230), width=2)

        # Staircase (center, going up)
        stair_w = int(base_w * 0.22)
        for i in range(n):
            st = i / n
            sy = y - max_h + i * (max_h // n)
            sw = int(stair_w * (1 - st * 0.4))
            self.draw_line(draw, x - sw // 2, sy, x + sw // 2, sy,
                          color=self._darken(c, 25) + (150,), width=2)

        # Base platform
        base_h = int(max_h * 0.08)
        self.draw_rect(draw, x - base_w // 2 - 4, y - base_h, base_w + 8, base_h,
                      fill=self._darken(c, 15) + (235,), stroke=self._darken(c, 25) + (180,), stroke_width=2)

    def draw_egyptian_pyramid(self, draw, x, y, size=1.0, color=(200, 175, 130)):
        """Draw an Egyptian-style smooth-sided pyramid."""
        s = max(size, 2.0)
        c = tuple(color[:3])
        base_w = int(28 * s)
        height = int(40 * s)
        self.draw_shadow_circle(draw, x, y + 2, base_w // 3, offset=(4, 4), blur_radius=8, color=(0, 0, 0, 40))

        # Main pyramid triangle
        tip = (x, y - height)
        bl = (x - base_w // 2, y)
        br = (x + base_w // 2, y)
        self.draw_polygon(draw, [bl, tip, br], fill=c + (235,),
                         stroke=self._darken(c, 20) + (180,), stroke_width=2)

        # Shadow side (right half)
        shadow = self._darken(c, 25)
        mid = (x + base_w // 6, y)
        self.draw_polygon(draw, [tip, mid, br], fill=shadow + (80,))

        # Stone block lines (horizontal)
        n_lines = max(4, int(height / 20))
        for i in range(1, n_lines):
            t = i / n_lines
            ly = y - height * t
            lw = int(base_w * (1 - t))
            self.draw_line(draw, x - lw // 2, ly, x + lw // 2, ly,
                          color=self._darken(c, 15) + (60,), width=1)

        # Gold capstone
        cap_h = int(height * 0.08)
        cap_w = int(base_w * 0.12)
        cap_tip = (x, y - height - cap_h)
        cap_bl = (x - cap_w // 2, y - height)
        cap_br = (x + cap_w // 2, y - height)
        self.draw_polygon(draw, [cap_bl, cap_tip, cap_br], fill=(220, 195, 80, 220),
                         stroke=(180, 155, 50, 200), stroke_width=1)

        # Base platform
        base_h = int(4 * s)
        self.draw_rect(draw, x - base_w // 2 - 6, y - base_h, base_w + 12, base_h,
                      fill=self._darken(c, 10) + (235,), stroke=self._darken(c, 20) + (180,), stroke_width=2)

    def draw_sphinx(self, draw, x, y, size=1.0, color=(190, 165, 120)):
        """Draw a sphinx — lion body with human head, side profile."""
        s = max(size, 2.0)
        c = tuple(color[:3])

        # Shadow
        self.draw_shadow_circle(draw, x + 5*s, y + s, 20*s, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 35))

        # Lion body (reclining, side view, facing right)
        body_w, body_h = 30*s, 10*s
        bx, by = x - 2*s, y - body_h - 4*s
        self.draw_ellipse(draw, bx, by, body_w, body_h,
                         fill=c + (230,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Haunch (back leg)
        haunch_r = 6*s
        self.draw_ellipse(draw, x - 8*s, y - 7*s, haunch_r * 2, haunch_r,
                         fill=self._darken(c, 5) + (220,), stroke=self._darken(c, 15) + (160,), stroke_width=1)

        # Tail curling
        tail_pts = [(x - 12*s, y - 3*s), (x - 16*s, y - 10*s), (x - 15*s, y - 14*s), (x - 12*s, y - 12*s)]
        self.draw_polygon(draw, tail_pts, fill=c + (210,), stroke=self._darken(c, 15) + (160,), stroke_width=1)

        # Front leg extended
        leg_pts = [(x + 14*s, y - 2*s), (x + 18*s, y + 3*s), (x + 19*s, y + 4*s), (x + 17*s, y + 1*s)]
        self.draw_polygon(draw, leg_pts, fill=self._darken(c, 5) + (220,),
                         stroke=self._darken(c, 15) + (160,), stroke_width=1)

        # Chest
        chest_r = 7*s
        cx = x + 11*s
        cy = y - 5*s
        self.draw_circle(draw, cx, cy, chest_r, fill=self._lighten(c, 10) + (230,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Head (human, side profile facing right)
        head_r = 6*s
        hx = x + 17*s
        hy = y - 12*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 8) + (235,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Face features (profile right)
        # Nose
        self.draw_polygon(draw, [(hx + 3*s, hy - s), (hx + 5*s, hy), (hx + 3*s, hy + 2*s)],
                         fill=self._lighten(c, 5) + (220,), stroke=self._darken(c, 10) + (160,), stroke_width=1)

        # Headdress (nemes) — striped head cloth
        headdress_pts = [(hx - 4*s, hy - 5*s), (hx + 2*s, hy - 5*s),
                        (hx + 4*s, hy - 2*s), (hx + 3*s, hy + 4*s),
                        (hx - 2*s, hy + 5*s), (hx - 5*s, hy + 3*s)]
        self.draw_polygon(draw, headdress_pts, fill=(180, 140, 80, 220),
                         stroke=(130, 100, 50, 180), stroke_width=1)
        # Headdress stripes
        for si in range(3):
            sy = hy - 4*s + si * 2*s
            self.draw_line(draw, hx - 3*s, sy, hx + 1*s, sy, color=(210, 175, 120, 120), width=1)

        # Eye
        self.draw_arc(draw, hx + s, hy - s, 2*s, 0, 180, color=(30, 25, 20, 200), width=int(1.5*s))

        # Base platform
        base_h = int(3 * s)
        self.draw_rect(draw, x - 14*s, y - base_h, 36*s, base_h,
                      fill=self._darken(c, 10) + (230,), stroke=self._darken(c, 20) + (160,), stroke_width=2)

    def draw_mummy_cat(self, draw, x, y, size=1.0, color=(220, 210, 190)):
        """Draw a mummified cat — wrapped bundle with linen bandages."""
        s = max(size, 2.0)
        c = tuple(color[:3])

        # Shadow
        self.draw_shadow_circle(draw, x + 2*s, y + 2*s, 10*s, offset=(2, 2), blur_radius=4, color=(0, 0, 0, 35))

        # Mummy body (cat-shaped bundle, reclining)
        body_w, body_h = 22*s, 10*s
        bx, by = x - body_w // 2, y - body_h - 2*s
        self.draw_ellipse(draw, bx, by, body_w, body_h,
                         fill=c + (235,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Head wrapping (round bundle)
        head_r = 6*s
        hx = x + 10*s
        hy = y - 8*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (235,),
                        stroke=self._darken(c, 10) + (180,), stroke_width=2)

        # Ears (small pointed through wrappings)
        ear_pts = [(hx + 3*s, hy - 4*s), (hx + 4*s, hy - 8*s), (hx + 6*s, hy - 4*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 8) + (220,),
                         stroke=self._darken(c, 10) + (160,), stroke_width=1)

        # Bandage lines — horizontal and diagonal across body
        for i in range(6):
            t = (i + 1) / 7
            by = y - body_h - 2*s + t * body_h
            self.draw_line(draw, x - body_w // 2 + 2*s, by, x + body_w // 2 - 2*s, by,
                          color=(180, 170, 150, 100), width=int(1.5*s))

        # Diagonal bandages
        for i in range(4):
            t = (i + 1) / 5
            bx1 = x - body_w // 2 + t * body_w
            bx2 = bx1 + 4*s
            by1 = y - 2*s - t * body_h * 0.5
            by2 = y - 2*s - (t + 0.2) * body_h * 0.5
            self.draw_line(draw, bx1, by1, bx2, by2,
                          color=(180, 170, 150, 80), width=int(s))

        # Painted eyes on head wrapping (Egyptian style)
        eye_color = (30, 25, 20)
        self.draw_ellipse(draw, hx + 2*s, hy - s, int(3*s), int(2*s), fill=(255, 255, 255, 200))
        self.draw_circle(draw, hx + 3*s, hy - s, s, fill=eye_color + (220,))
        # Kohl eyeliner (thick black line)
        self.draw_line(draw, hx + s, hy - 2*s, hx + 5*s, hy - 2*s,
                      color=(20, 15, 10, 200), width=int(s))

        # Ankh symbol on chest
        ankh_x = x
        ankh_y = y - 4*s
        self.draw_circle(draw, ankh_x, ankh_y - 2*s, int(1.5*s), fill=(200, 180, 60, 200))
        self.draw_line(draw, ankh_x, ankh_y - 3*s, ankh_x, ankh_y + 3*s,
                      color=(200, 180, 60, 200), width=int(1.5*s))
        self.draw_line(draw, ankh_x - 2*s, ankh_y + s, ankh_x + 2*s, ankh_y + s,
                      color=(200, 180, 60, 200), width=int(1.5*s))

    def draw_egyptian_art(self, draw, x, y, size=1.0, color=(200, 170, 100)):
        """Draw Egyptian-style artwork — cat profile on papyrus with hieroglyph border."""
        s = max(size, 2.0)
        c = tuple(color[:3])

        # Papyrus background panel
        panel_w = int(32 * s)
        panel_h = int(28 * s)
        px = x - panel_w // 2
        py = y - panel_h
        self.draw_rect(draw, px, py, panel_w, panel_h,
                      fill=(220, 205, 170, 235), stroke=(160, 140, 100, 180), stroke_width=2)

        # Border — hieroglyphic pattern (top and bottom bands)
        border_h = int(3 * s)
        for band_y in [py, py + panel_h - border_h]:
            self.draw_rect(draw, px + 2, band_y, panel_w - 4, border_h,
                          fill=(60, 50, 40, 180))
            # Small symbols in border
            for sym in range(max(2, int(panel_w / (6 * s)))):
                sx = px + 4 + sym * int(6 * s)
                sy = band_y + border_h // 2
                self.draw_circle(draw, sx, sy, int(s * 0.5), fill=(200, 180, 120, 200))
                self.draw_line(draw, sx, sy - s, sx, sy + s, color=(200, 180, 120, 200), width=1)

        # Stylized cat profile (facing right)
        cat_color = (50, 40, 30)
        cx = x - 4*s
        cy = y - 14*s

        # Body (long, elegant)
        body_w, body_h = 14*s, 5*s
        self.draw_ellipse(draw, cx - body_w // 2, cy, body_w, body_h,
                         fill=cat_color + (220,))

        # Head
        head_r = 4*s
        hx = cx + 6*s
        hy = cy + s
        self.draw_circle(draw, hx, hy, head_r, fill=cat_color + (220,))

        # Ear (pointed, Egyptian style)
        ear_pts = [(hx + 3*s, hy - 2*s), (hx + 4*s, hy - 7*s), (hx + 6*s, hy - 2*s)]
        self.draw_polygon(draw, ear_pts, fill=cat_color + (220,))

        # Eye (stylized, almond shape)
        self.draw_line(draw, hx + 2*s, hy - s, hx + 4*s, hy - s,
                      color=(255, 220, 100, 200), width=int(1.5*s))

        # Tail curved up
        tail_pts = [(cx - 7*s, cy + s), (cx - 12*s, cy - 3*s), (cx - 14*s, cy + s)]
        self.draw_polygon(draw, tail_pts, fill=cat_color + (200,))

        # Legs
        for lx in [cx - 4*s, cx + 2*s]:
            self.draw_line(draw, lx, cy + body_h // 2, lx + s, cy + body_h + 3*s,
                          color=cat_color + (200,), width=int(2*s))

    def draw_granary(self, draw, x, y, size=1.0, color=(170, 150, 110)):
        """Draw an Egyptian grain storage building."""
        s = max(size, 2.0)
        c = tuple(color[:3])

        # Shadow
        self.draw_shadow_circle(draw, x, y + 2, 12*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        # Main building (rectangular with dome top)
        body_w = int(18 * s)
        body_h = int(16 * s)
        bx = x - body_w // 2
        by = y - body_h

        # Mud-brick walls
        self.draw_rect(draw, bx, by, body_w, body_h,
                      fill=c + (230,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Dome roof
        dome_w = body_w + 4*s
        dome_h = int(6 * s)
        dome_y = by - dome_h
        self.draw_ellipse(draw, x - dome_w // 2, dome_y, dome_w, dome_h * 2,
                         fill=self._lighten(c, 5) + (230,), stroke=self._darken(c, 10) + (180,), stroke_width=2)

        # Door opening
        door_w = int(4 * s)
        door_h = int(6 * s)
        self.draw_rect(draw, x - door_w // 2, y - door_h, door_w, door_h,
                      fill=(50, 40, 30, 230))

        # Grain chute (small opening high up)
        chute_w = int(3 * s)
        chute_h = int(s)
        self.draw_rect(draw, x - chute_w // 2, by + 3*s, chute_w, chute_h,
                      fill=(200, 180, 80, 200))

        # Grain spilling out
        spill_pts = [(x, by + 3*s + chute_h), (x - 3*s, by + 5*s), (x + 3*s, by + 5*s)]
        self.draw_polygon(draw, spill_pts, fill=(210, 190, 70, 180))

        # Mud-brick texture lines
        for row in range(3):
            ry = by + 5*s + row * 4*s
            self.draw_line(draw, bx + 2, ry, bx + body_w - 2, ry,
                          color=self._darken(c, 10) + (80,), width=1)

    def draw_cat_statue(self, draw, x, y, size=1.0, color=(50, 45, 35)):
        """Draw an Egyptian Bastet-style cat statue (seated, upright)."""
        s = max(size, 2.0)
        c = tuple(color[:3])

        # Shadow
        self.draw_shadow_circle(draw, x + 2*s, y + 2*s, 8*s, offset=(2, 2), blur_radius=4, color=(0, 0, 0, 35))

        # Base pedestal
        base_w = int(14 * s)
        base_h = int(3 * s)
        self.draw_rect(draw, x - base_w // 2, y - base_h, base_w, base_h,
                      fill=self._darken(c, 5) + (230,), stroke=self._darken(c, 15) + (160,), stroke_width=2)

        # Body (seated upright)
        body_w, body_h = 12*s, 16*s
        bx, by = x - body_w // 2, y - body_h - base_h
        self.draw_ellipse(draw, bx, by, body_w, body_h,
                         fill=c + (230,), stroke=self._lighten(c, 15) + (180,), stroke_width=2)

        # Chest (lighter/gold accent)
        chest_w = int(6 * s)
        chest_h = int(8 * s)
        self.draw_ellipse(draw, x - chest_w // 2, by + 2*s, chest_w, chest_h,
                         fill=(200, 170, 80, 200))

        # Head (upright, pointed ears)
        head_r = 5*s
        hx = x
        hy = by - 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=c + (235,),
                        stroke=self._lighten(c, 15) + (180,), stroke_width=2)

        # Ears (tall, pointed)
        ear_size = 3*s
        for side in [-1, 1]:
            ear_pts = [(hx + side * 3*s, hy - 3*s),
                      (hx + side * 4*s, hy - 8*s),
                      (hx + side * 5*s, hy - 3*s)]
            self.draw_polygon(draw, ear_pts, fill=c + (220,),
                             stroke=self._lighten(c, 10) + (160,), stroke_width=1)
            # Inner ear
            inner_ear = [(hx + side * 3.5*s, hy - 3.5*s),
                        (hx + side * 4*s, hy - 7*s),
                        (hx + side * 4.5*s, hy - 3.5*s)]
            self.draw_polygon(draw, inner_ear, fill=(230, 200, 150, 150))

        # Eyes (Egyptian style — almond, gold)
        for side in [-1, 1]:
            self.draw_ellipse(draw, hx + side * 2*s - 1.5*s, hy - 1*s, int(3*s), int(2*s),
                            fill=(255, 220, 80, 200))
            self.draw_circle(draw, hx + side * 2*s, hy, int(s * 0.6), fill=(30, 25, 20, 220))
            # Kohl eyeliner
            self.draw_line(draw, hx + side * 3*s, hy - 2*s, hx + side * 3*s, hy + s,
                          color=(20, 15, 10, 180), width=int(s))

        # Nose
        self.draw_circle(draw, hx, hy + 2*s, int(s), fill=self._darken(c, 10) + (200,))

        # Whiskers (decorative)
        for side in [-1, 1]:
            self.draw_line(draw, hx + side * 3*s, hy + 2*s, hx + side * 7*s, hy + s,
                          color=self._lighten(c, 20) + (100,), width=1)
            self.draw_line(draw, hx + side * 3*s, hy + 3*s, hx + side * 6*s, hy + 3*s,
                          color=self._lighten(c, 20) + (100,), width=1)

        # Gold collar/necklace
        self.draw_rect(draw, x - 4*s, hy + 4*s, 8*s, int(1.5*s),
                      fill=(220, 190, 80, 220), stroke=(180, 150, 50), stroke_width=1)

        # Earring (gold ring in ear)
        self.draw_circle(draw, hx + 5*s, hy - 2*s, int(s), fill=(220, 190, 80, 200))

    def draw_temple(self, draw, x, y, size=1.0, color=(160, 130, 100)):
        """Draw a Maya temple — corbel arch, roof comb, stepped platform."""
        s = max(size, 1.5)
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 14*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))

        # Stepped platform (3 tiers)
        tiers = 3
        for i in range(tiers):
            tw = int(24 * s * (1 - i * 0.15))
            th = int(6 * s)
            ty = y - (tiers - i) * th
            tx = x - tw // 2
            shade = self._darken(c, 5 * (tiers - i))
            self.draw_rect(draw, tx, ty, tw, th, fill=shade + (235,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Upper walls
        uw = int(18 * s)
        uh = int(14 * s)
        uy = y - tiers * int(6*s) - uh
        self.draw_rect(draw, x - uw//2, uy, uw, uh, fill=self._lighten(c, 5) + (235,),
                      stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Roof comb (tall crest on top)
        rw = int(uw * 0.45)
        rh = int(16 * s)
        ry = uy - rh
        self.draw_rect(draw, x - rw//2, ry, rw, rh, fill=self._darken(c, 10) + (220,),
                      stroke=self._darken(c, 20) + (160,), stroke_width=2)
        # Roof comb cutouts (decorative slots)
        for slot in range(3):
            sx = x - rw//3 + slot * int(rw//3)
            sy = ry + int(rh * 0.2)
            sh2 = int(rh * 0.5)
            self.draw_rect(draw, sx - 2, sy, 4, sh2, fill=(120, 100, 80, 180))

        # Corbel arch doorway
        dw = int(uw * 0.25)
        dh = int(uh * 0.65)
        dx = x - dw // 2
        dy = uy + uh - dh
        # Door frame
        self.draw_rect(draw, dx, dy, dw, dh, fill=(15, 12, 10, 235))
        # Corbel arch top (triangular)
        self.draw_polygon(draw, [(dx, dy), (x, dy - int(dw * 0.4)), (dx + dw, dy)],
                         fill=(15, 12, 10, 235))

        # Staircase
        for i in range(tiers * 3):
            sy = y - i * int(2*s)
            sw = int(10 * s * (1 - i * 0.03))
            self.draw_line(draw, x - sw//2, sy, x + sw//2, sy,
                          color=self._darken(c, 20) + (130,), width=2)

        # Platform base
        self.draw_rect(draw, x - int(13*s), y - int(3*s), int(26*s), int(3*s),
                      fill=self._darken(c, 15) + (235,), stroke=self._darken(c, 25) + (180,), stroke_width=2)

    def draw_leaf(self, draw, x, y, size=1.0, color=(100, 160, 60)):
        """Draw a detailed leaf with veins."""
        s = size
        c = tuple(color[:3])
        # Shadow
        self.draw_shadow_circle(draw, x + 2, y + 2, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        # Leaf body
        self.draw_ellipse(draw, x - 8*s, y - 4*s, 16*s, 8*s,
                         fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Stem
        self.draw_line(draw, x - 8*s, y, x - 14*s, y + 2*s,
                      color=self._darken(c, 20) + (200,), width=2)
        # Center vein
        self.draw_line(draw, x - 7*s, y, x + 7*s, y,
                      color=self._darken(c, 20) + (140,), width=1)
        # Side veins
        for side in [-1, 1]:
            for v in range(3):
                vx = x + side * (2 + v * 2) * s
                vy = y + side * (1 + v) * s
                self.draw_line(draw, vx, y, vx + side * 2*s, vy,
                              color=self._darken(c, 20) + (100,), width=1)

    def draw_throne(self, draw, x, y, size=1.0, color=(140, 100, 70)):
        """Draw a simple throne/seat."""
        s = size
        c = tuple(color[:3])
        tw, th = 18*s, 22*s
        bw = int(tw * 0.7)
        self.draw_rect(draw, x - bw//2, y - th, bw, int(th*0.6), fill=c + (200,),
                      stroke=self._darken(c, 15) + (160,), stroke_width=2)
        self.draw_rect(draw, x - tw//2, y - int(th*0.35), tw, int(th*0.35), fill=self._lighten(c, 10) + (220,),
                      stroke=self._darken(c, 15) + (180,), stroke_width=2)
        for side in [-1, 1]:
            ax = x + side * tw//2
            self.draw_rect(draw, ax - int(1.5*s), y - th, int(3*s), int(th*0.5), fill=self._darken(c, 10) + (200,),
                          stroke=self._darken(c, 20) + (160,), stroke_width=1)
        for side in [-1, 1]:
            lx = x + side * int(tw*0.35)
            self.draw_rect(draw, lx - int(s), y - int(th*0.3), int(2*s), int(th*0.3), fill=self._darken(c, 20) + (220,))

    def draw_cracked_ground(self, draw, x, y, width=1.0, height=1.0):
        """Draw cracked earth pattern."""
        w = int(width * 100)
        h = int(height * 60)
        self.draw_rect(draw, x - w//2, y - h//2, w, h, fill=(180, 160, 130, 200),
                      stroke=(60, 55, 50, 150), stroke_width=1)
        import random as _r
        _r.seed(hash((x, y)) & 0xFFFFFFFF)
        for _ in range(10):
            sx = x + _r.randint(-w//2, w//2)
            sy = y + _r.randint(-h//2, h//2)
            for _ in range(3):
                ex = sx + _r.randint(-15, 15)
                ey = sy + _r.randint(-12, 12)
                self.draw_line(draw, sx, sy, ex, ey, color=(100, 85, 70, 200), width=2)
                sx, sy = ex, ey

    def draw_basket(self, draw, x, y, size=1.0, color=(160, 140, 100)):
        """Draw a simple basket."""
        s = size
        c = tuple(color[:3])
        bw, bh = 14*s, 10*s
        self.draw_ellipse(draw, x - bw//2, y - bh//2, bw, bh,
                         fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Rim
        self.draw_ellipse(draw, x - bw//2, y - bh//2 - s, bw, int(bh*0.2),
                         fill=self._lighten(c, 15) + (200,), stroke=self._darken(c, 15) + (160,), stroke_width=1)
        # Weave lines
        for i in range(4):
            wy = y - bh//2 + i * int(bh/4)
            self.draw_line(draw, x - bw//2, wy, x + bw//2, wy,
                          color=self._darken(c, 15) + (80,), width=1)

    def draw_smartphone(self, draw, x, y, size=1.0, color=(30, 30, 35)):
        """Draw a smartphone with screen."""
        s = size
        c = tuple(color[:3])
        pw, ph = 10*s, 18*s
        self.draw_rect(draw, x - pw//2, y - ph//2, pw, ph,
                      fill=c + (230,), stroke=self._lighten(c, 10) + (200,), stroke_width=2, rx=int(2*s))
        # Screen
        sx, sy = x - pw//2 + int(1.5*s), y - ph//2 + int(2*s)
        sw, sh = pw - int(3*s), ph - int(4*s)
        self.draw_rect(draw, sx, sy, sw, sh, fill=(50, 120, 220, 220), rx=int(s))
        # Screen content: cat face
        self.draw_circle(draw, x, y - s, 3*s, fill=(200, 160, 120, 220))
        # Ears
        for side in [-1, 1]:
            ear = [(x + side*2*s, y - 3*s), (x + side*3*s, y - 6*s), (x + side*4*s, y - 3*s)]
            self.draw_polygon(draw, ear, fill=(200, 160, 120, 220))
        # Eyes on screen
        for side in [-1, 1]:
            self.draw_circle(draw, x + side*s, y - 2*s, s*0.6, fill=(255, 255, 255, 200))
        # Home button
        bx = int(1.5*s)
        self.draw_circle(draw, x, y + ph//2 - bx - 1, s*0.8, fill=(60, 60, 65, 200))

    def draw_camera(self, draw, x, y, size=1.0, color=(60, 55, 50)):
        """Draw a camera."""
        s = size
        c = tuple(color[:3])
        bw, bh = 14*s, 10*s
        # Body
        self.draw_rect(draw, x - bw//2, y - bh//2, bw, bh,
                      fill=c + (230,), stroke=self._darken(c, 15) + (200,), stroke_width=2, rx=int(s))
        # Top hump
        self.draw_rect(draw, x - int(4*s), y - bh//2 - int(3*s), int(8*s), int(3*s),
                      fill=self._darken(c, 5) + (220,), stroke=self._darken(c, 15) + (200,), stroke_width=2, rx=int(s))
        # Lens (outer)
        self.draw_circle(draw, x, y, 5*s, fill=(20, 20, 25, 230))
        # Lens (inner)
        self.draw_circle(draw, x, y, 3*s, fill=(40, 40, 50, 220))
        self.draw_circle(draw, x, y, 2*s, fill=(60, 60, 80, 200))
        self.draw_circle(draw, x, y, s, fill=(100, 120, 180, 180))
        # Flash
        self.draw_rect(draw, x + int(3*s), y - bh//2 + int(s), int(2*s), int(2*s),
                      fill=(255, 240, 200, 200))

    def draw_tv_monitor(self, draw, x, y, size=1.0, color=(40, 40, 45)):
        """Draw a TV/monitor."""
        s = size
        c = tuple(color[:3])
        mw, mh = 20*s, 14*s
        # Bezel
        self.draw_rect(draw, x - mw//2, y - mh//2, mw, mh,
                      fill=c + (230,), stroke=self._lighten(c, 10) + (200,), stroke_width=2, rx=int(s))
        # Screen
        sx, sy = x - mw//2 + int(1.5*s), y - mh//2 + int(1.5*s)
        sw, sh = mw - int(3*s), mh - int(3*s)
        self.draw_rect(draw, sx, sy, sw, sh, fill=(60, 70, 100, 230))
        # Screen content: cat silhouette
        self.draw_circle(draw, x, y, 3*s, fill=(180, 200, 220, 180))
        for side in [-1, 1]:
            ear = [(x + side*2*s, y - 3*s), (x + side*3*s, y - 5*s), (x + side*4*s, y - 3*s)]
            self.draw_polygon(draw, ear, fill=(180, 200, 220, 180))
        # Stand
        self.draw_rect(draw, x - int(3*s), y + mh//2, int(6*s), int(2*s),
                      fill=self._darken(c, 10) + (200,))
        self.draw_rect(draw, x - int(5*s), y + mh//2 + int(2*s), int(10*s), int(2*s),
                      fill=self._darken(c, 10) + (200,), rx=int(s))

    def draw_cat_toy(self, draw, x, y, size=1.0, color=(200, 80, 50)):
        """Draw a cat toy (ball with string)."""
        s = size
        c = tuple(color[:3])
        # Ball
        self.draw_circle(draw, x, y, 3*s, fill=c + (230,),
                        stroke=self._darken(c, 15) + (200,), stroke_width=2)
        # Stripe
        self.draw_line(draw, x - 3*s, y, x + 3*s, y,
                      color=self._lighten(c, 20) + (180,), width=int(s))
        # String
        self.draw_line(draw, x, y - 3*s, x - 8*s, y - 10*s,
                      color=(180, 160, 120, 200), width=int(s*0.5))
        # Feather at end of string
        fe = [(x - 8*s, y - 10*s), (x - 12*s, y - 14*s), (x - 10*s, y - 12*s),
              (x - 14*s, y - 12*s), (x - 10*s, y - 10*s), (x - 14*s, y - 8*s)]
        self.draw_polygon(draw, fe, fill=(180, 200, 220, 200))

    def draw_dragon(self, draw, x, y, size=1.0, color=(60, 120, 60)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 20*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 40))

        body_w, body_h = 30*s, 14*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h,
                          fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        tail_pts = [(x - 16*s, y - 4*s), (x - 26*s, y - 8*s), (x - 32*s, y - 4*s),
                    (x - 30*s, y), (x - 20*s, y - 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (210,),
                          stroke=self._darken(c, 20) + (160,), stroke_width=1)

        for spine in range(5):
            sx2 = x - 28*s + spine * 3*s
            self.draw_polygon(draw, [(sx2, y - 6*s - spine * s), (sx2 + s, y - 10*s - spine * s), (sx2 + 2*s, y - 6*s - spine * s)],
                              fill=self._darken(c, 25) + (200,))

        neck_pts = [(x + 8*s, y - 12*s), (x + 14*s, y - 22*s), (x + 12*s, y - 26*s),
                    (x + 6*s, y - 20*s), (x + 4*s, y - 12*s)]
        self.draw_polygon(draw, neck_pts, fill=self._lighten(c, 5) + (220,),
                          stroke=self._darken(c, 15) + (180,), stroke_width=1)

        head_r = 8*s
        hx = x + 16*s
        hy = y - 24*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        jaw_pts = [(hx + 4*s, hy + 2*s), (hx + 12*s, hy + 3*s), (hx + 14*s, hy + 6*s),
                   (hx + 10*s, hy + 7*s), (hx + 4*s, hy + 4*s)]
        self.draw_polygon(draw, jaw_pts, fill=self._darken(c, 5) + (220,),
                          stroke=self._darken(c, 15) + (160,), stroke_width=1)

        for horn_side in [-1, 1]:
            horn_pts = [(hx + horn_side * 3*s, hy - 6*s),
                        (hx + horn_side * 5*s, hy - 14*s),
                        (hx + horn_side * 2*s, hy - 6*s)]
            self.draw_polygon(draw, horn_pts, fill=(60, 50, 40, 220))

        fire_pts = [(hx + 14*s, hy + 5*s), (hx + 20*s, hy + 2*s),
                    (hx + 24*s, hy + 5*s), (hx + 20*s, hy + 8*s)]
        self.draw_polygon(draw, fire_pts, fill=(240, 180, 40, 150))
        self.draw_polygon(draw, [(hx + 16*s, hy + 5*s), (hx + 22*s, hy + 4*s), (hx + 20*s, hy + 6*s)],
                          fill=(240, 80, 40, 120))

        self.draw_circle(draw, hx + 4*s, hy - 2*s, 2*s, fill=(220, 180, 40, 220))
        self.draw_circle(draw, hx + 4*s, hy - 2*s, 0.8*s, fill=(30, 25, 20, 200))

        wing_color = self._lighten(c, 15)
        for side in [-1, 1]:
            wing_pts = [(x + side * 4*s, y - 12*s),
                        (x + side * 14*s, y - 24*s),
                        (x + side * 10*s, y - 6*s)]
            self.draw_polygon(draw, wing_pts, fill=wing_color + (180,),
                              stroke=self._darken(c, 15) + (140,), stroke_width=1)
            for rib in range(3):
                rx = x + side * (6 + rib * 3) * s
                ry = y - (14 + rib * 3) * s
                self.draw_line(draw, x + side * 4*s, y - 12*s, rx, ry,
                              color=self._darken(c, 20), width=1)

        leg_c = self._darken(c, 15)
        for lx in [-8*s, 4*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * 2*s, y - 2*s,
                              x + lx + side * 4*s, y + 8*s,
                              color=leg_c, width=int(3*s))
                claw_pts = [(x + lx + side * 4*s, y + 8*s),
                            (x + lx + side * 5*s, y + 10*s),
                            (x + lx + side * 3*s, y + 10*s)]
                self.draw_polygon(draw, claw_pts, fill=(60, 50, 40, 220))

    def draw_snake(self, draw, x, y, size=1.0, color=(80, 140, 60)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 16*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

        body_pts = []
        for i in range(20):
            t = i / 20
            angle = t * math.pi * 2
            bx = x - 16*s * math.cos(angle)
            by = y - 8*s * math.sin(angle) + t * 4*s
            body_pts.append((bx, by))
        self.draw_polygon(draw, body_pts, fill=c + (200,),
                          stroke=self._darken(c, 15) + (160,), stroke_width=1)

        band_color = self._darken(c, 20)
        for band in range(5):
            bi = band * 4
            if bi + 2 < len(body_pts):
                self.draw_line(draw, int(body_pts[bi][0]), int(body_pts[bi][1]),
                              int(body_pts[bi+2][0]), int(body_pts[bi+2][1]),
                              color=band_color, width=int(2*s))

        head_r = 4*s
        hx = x + 16*s
        hy = y + 4*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        tongue_len = 6*s
        self.draw_line(draw, hx + 4*s, hy, hx + 4*s + tongue_len, hy,
                      color=(200, 60, 60, 200), width=1)
        self.draw_line(draw, hx + 4*s + tongue_len, hy,
                      hx + 4*s + tongue_len + 2*s, hy - 2*s, color=(200, 60, 60, 200), width=1)
        self.draw_line(draw, hx + 4*s + tongue_len, hy,
                      hx + 4*s + tongue_len + 2*s, hy + 2*s, color=(200, 60, 60, 200), width=1)

        self.draw_circle(draw, hx + 2*s, hy - 1.5*s, 1.2*s, fill=(220, 200, 60, 220))
        self.draw_circle(draw, hx + 2*s, hy - 1.5*s, 0.4*s, fill=(30, 25, 20, 200))

    def draw_turtle(self, draw, x, y, size=1.0, color=(80, 140, 60)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

        shell_w, shell_h = 24*s, 14*s
        self.draw_ellipse(draw, x - shell_w//2, y - shell_h, shell_w, shell_h,
                          fill=self._darken(c, 5) + (220,),
                          stroke=self._darken(c, 20) + (180,), stroke_width=2)

        plate_color = self._lighten(c, 15)
        for px2, py2, pw, ph in [(x - 6*s, y - 10*s, 5*s, 4*s), (x + 2*s, y - 11*s, 6*s, 5*s),
                                  (x - 4*s, y - 5*s, 4*s, 3*s), (x + 4*s, y - 6*s, 5*s, 3*s)]:
            self.draw_ellipse(draw, px2, py2, pw, ph, fill=plate_color + (180,),
                              stroke=self._darken(c, 10) + (120,), stroke_width=1)

        shell_line = self._darken(c, 15)
        self.draw_line(draw, x, y - shell_h, x, y, color=shell_line, width=1)
        self.draw_line(draw, x - shell_w//4, y - shell_h + 2*s, x + shell_w//4, y - shell_h + 2*s,
                      color=shell_line, width=1)

        head_r = 4*s
        hx = x + shell_w//2 + 2*s
        hy = y - shell_h + 3*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,),
                        stroke=self._darken(c, 15) + (180,), stroke_width=2)

        self.draw_circle(draw, hx + 2*s, hy - 1*s, 1.2*s, fill=(30, 25, 20, 200))

        leg_c = self._darken(c, 12)
        for lx, ly in [(-8*s, -2*s), (-6*s, 4*s), (6*s, -2*s), (8*s, 4*s)]:
            self.draw_ellipse(draw, x + lx - 2*s, y + ly, 4*s, 3*s,
                              fill=leg_c + (200,))

        tail_pts = [(x - shell_w//2 - 2*s, y - 3*s),
                    (x - shell_w//2 - 5*s, y - 2*s),
                    (x - shell_w//2 - 2*s, y - s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (200,))

    def draw_giraffe(self, draw, x, y, size=1.0, color=(220, 180, 100)):
        s = size
        c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        body_w, body_h = 20*s, 12*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        spot_c = (160, 120, 60)
        for sx, sy, sw, sh in [(-4*s, -10*s, 4*s, 3*s), (2*s, -9*s, 3*s, 3*s), (-2*s, -5*s, 3*s, 3*s), (5*s, -6*s, 4*s, 3*s)]:
            self.draw_ellipse(draw, x + sx, y + sy, sw, sh, fill=spot_c + (160,))
        neck_len = 28*s
        neck_pts = [(x + 6*s, y - 12*s), (x + 10*s, y - 12*s - neck_len), (x + 6*s, y - 12*s - neck_len), (x + 2*s, y - 12*s)]
        self.draw_polygon(draw, neck_pts, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=1)
        for spot in range(6):
            sy2 = y - (14 + spot * 4) * s
            self.draw_ellipse(draw, x + 3*s, sy2, 3*s, 2*s, fill=spot_c + (150,))
        head_r = 5*s; hx = x + 6*s; hy = y - 12*s - neck_len + 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Single ossicone and ear (side profile)
        oss_pts = [(hx + 2*s, hy - 4*s), (hx + 2.5*s, hy - 7*s), (hx + 3*s, hy - 4*s)]
        self.draw_polygon(draw, oss_pts, fill=self._darken(c, 5) + (200,))
        ear_pts = [(hx + 3*s, hy - 3*s), (hx + 5*s, hy - 4*s), (hx + 4*s, hy - s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 12) + (200,))
        snout_r = 3*s
        self.draw_ellipse(draw, hx + 4*s - snout_r, hy - snout_r, snout_r*2, snout_r*1.5, fill=self._lighten(c, 15) + (200,))
        self.draw_circle(draw, hx + 6*s, hy + 1*s, 1*s, fill=(40, 35, 30, 200))
        self.draw_circle(draw, hx + 3*s, hy - 1.5*s, 1.3*s, fill=(30, 25, 20, 200))
        leg_c = self._darken(c, 15)
        for lx in [-6*s, 4*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 4*s, x + lx + side * s, y + 10*s, color=leg_c, width=int(2*s))
                self.draw_line(draw, x + lx + side * s, y + 9*s, x + lx + side * 0.5*s, y + 10*s, color=self._darken(c, 20), width=1)
        tx = x - body_w//2 - 2*s
        self.draw_line(draw, tx, y - body_h + 4*s, tx - 4*s, y - body_h + 2*s, color=self._darken(c, 10), width=int(1.5*s))
        self.draw_line(draw, tx, y - body_h + 4*s, tx - 4*s, y - body_h + 6*s, color=self._darken(c, 10), width=int(1*s))

    def draw_camel(self, draw, x, y, size=1.0, color=(190, 160, 120)):
        s = size; c = tuple(color[:3])
        dc = self._darken(c, 30)
        self.draw_shadow_circle(draw, x, y + 3, 20*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))

        # Body
        body_w, body_h = 30*s, 16*s
        self.draw_ellipse(draw, x, y - body_h//2, body_w, body_h, fill=c + (220,), stroke=dc + (180,), stroke_width=2)

        # Humps (large, connected to body)
        hump1 = self.draw_ellipse(draw, x - 7*s, y - body_h//2 - 8*s, 14*s, 12*s, fill=self._lighten(c, 5) + (220,), stroke=dc + (180,), stroke_width=1)
        hump2 = self.draw_ellipse(draw, x + 7*s, y - body_h//2 - 7*s, 12*s, 11*s, fill=self._lighten(c, 5) + (220,), stroke=dc + (180,), stroke_width=1)

        # Neck (thick, curved forward)
        neck_pts = [(x + 8*s, y - 10*s), (x + 16*s, y - 24*s), (x + 14*s, y - 30*s),
                    (x + 10*s, y - 28*s), (x + 4*s, y - 12*s)]
        self.draw_polygon(draw, neck_pts, fill=c + (220,), stroke=dc + (180,), stroke_width=1)

        # Head
        head_r = 5*s; hx = x + 18*s; hy = y - 28*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=dc + (180,), stroke_width=2)

        # Long snout
        snout_pts = [(hx + 3*s, hy - s), (hx + 10*s, hy - s), (hx + 10*s, hy + 2*s), (hx + 3*s, hy + 3*s)]
        self.draw_polygon(draw, snout_pts, fill=self._lighten(c, 12) + (200,), stroke=dc + (140,), stroke_width=1)
        self.draw_circle(draw, hx + 10*s, hy + 0.5*s, 1*s, fill=(40, 35, 30, 200))
        self.draw_circle(draw, hx + 2*s, hy - 1.5*s, 1.3*s, fill=(30, 25, 20, 200))

        # Single ear
        ear_pts = [(hx + 4*s, hy - 5*s), (hx + 5*s, hy - 9*s), (hx + 6*s, hy - 5*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 12) + (200,), stroke=dc + (160,), stroke_width=1)

        # Legs (long with knobby knees)
        leg_c = self._darken(c, 20)
        for lx in [-10*s, 6*s]:
            for side in [-1, 1]:
                ex = x + lx + side * 2*s
                self.draw_line(draw, ex, y - 4*s, ex, y + 6*s, color=leg_c, width=int(3*s))
                self.draw_line(draw, ex - s, y + 6*s, ex - s, y + 12*s, color=leg_c, width=int(2*s))
                self.draw_line(draw, ex + s, y + 6*s, ex + s, y + 12*s, color=leg_c, width=int(2*s))
                self.draw_circle(draw, ex, y + 4*s, 1.5*s, fill=self._lighten(c, 10) + (180,))

        # Tail
        tx = x - body_w//2 - s
        self.draw_line(draw, tx, y - body_h//2 + 2*s, tx - 4*s, y - body_h//2 - 2*s, color=dc, width=int(2*s))

    def draw_rhino(self, draw, x, y, size=1.0, color=(130, 120, 110)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 18*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))
        body_w, body_h = 30*s, 16*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 8*s; hx = x + body_w//2 + 2*s; hy = y - body_h + 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        horn_pts = [(hx + 5*s, hy - 4*s), (hx + 7*s, hy - 12*s), (hx + 6*s, hy - 4*s)]
        self.draw_polygon(draw, horn_pts, fill=(200, 190, 180, 220), stroke=(140, 130, 120, 160), stroke_width=1)
        horn2_pts = [(hx + 3*s, hy - 2*s), (hx + 4*s, hy - 6*s), (hx + 3.5*s, hy - 2*s)]
        self.draw_polygon(draw, horn2_pts, fill=(200, 190, 180, 200))
        # Single ear (side profile)
        self.draw_circle(draw, hx + 5*s, hy - 5*s, 3*s, fill=self._darken(c, 5) + (200,))
        self.draw_circle(draw, hx + 3*s, hy - 1*s, 1.5*s, fill=(30, 25, 20, 200))
        leg_c = self._darken(c, 15)
        for lx in [-10*s, 4*s]:
            for side in [-1, 1]:
                self.draw_rect(draw, x + lx + side * 3*s, y - 4*s, 6*s, 9*s, fill=leg_c + (220,), stroke=self._darken(leg_c, 10) + (160,), stroke_width=1)
        tx = x - body_w//2 - 2*s
        self.draw_line(draw, tx, y - body_h + 4*s, tx - 4*s, y - body_h//2, color=self._darken(c, 10), width=int(2*s))

    def draw_hippo(self, draw, x, y, size=1.0, color=(150, 130, 140)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 20*s, offset=(3, 3), blur_radius=4, color=(0, 0, 0, 35))
        body_w, body_h = 34*s, 18*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 10*s; hx = x + body_w//2 + 4*s; hy = y - body_h + 4*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        jaw_pts = [(hx + 2*s, hy + 2*s), (hx + 12*s, hy + 4*s), (hx + 14*s, hy + 8*s), (hx + 8*s, hy + 8*s), (hx + 2*s, hy + 4*s)]
        self.draw_polygon(draw, jaw_pts, fill=self._lighten(c, 8) + (220,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        # Single ear (side profile)
        self.draw_circle(draw, hx + 7*s, hy - 7*s, 3*s, fill=self._lighten(c, 10) + (200,))
        self.draw_circle(draw, hx + 6*s, hy - 2*s, 1.5*s, fill=(30, 25, 20, 200))
        for nostril in [-1, 1]:
            self.draw_circle(draw, hx + 10*s + nostril * 1.5*s, hy + 2*s, 1.5*s, fill=(40, 35, 30, 200))
        leg_c = self._darken(c, 15)
        for lx in [-12*s, 6*s]:
            for side in [-1, 1]:
                self.draw_rect(draw, x + lx + side * 3*s, y - 4*s, 6*s, 8*s, fill=leg_c + (220,), stroke=self._darken(leg_c, 10) + (160,), stroke_width=1)
        tx = x - body_w//2 - s
        self.draw_line(draw, tx, y - body_h//2, tx - 3*s, y - body_h//2, color=self._darken(c, 10), width=int(1.5*s))

    def draw_monkey(self, draw, x, y, size=1.0, color=(140, 110, 80)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_r = 8*s
        self.draw_circle(draw, x, y - 6*s, body_r, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 5*s; hx = x + 6*s; hy = y - 12*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        face_r = 3*s
        self.draw_ellipse(draw, hx + 2*s - face_r, hy - face_r, face_r*2, face_r*1.8, fill=(220, 190, 170, 200))
        # Single ear (side profile)
        self.draw_circle(draw, hx + 4*s, hy, 2*s, fill=self._lighten(c, 12) + (200,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        self.draw_circle(draw, hx + 4*s, hy - s, 1.2*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 6*s, hy + 0.5*s, 1*s, fill=(40, 35, 30, 200))
        mouth_pts = [(hx + 4*s, hy + 2*s), (hx + 7*s, hy + 2*s), (hx + 5.5*s, hy + 3*s)]
        self.draw_polygon(draw, mouth_pts, fill=(160, 100, 80, 200))
        for side in [-1, 1]:
            arm_pts = [(x + side * 6*s, y - 8*s), (x + side * 12*s, y), (x + side * 10*s, y + 6*s)]
            self.draw_line(draw, int(arm_pts[0][0]), int(arm_pts[0][1]), int(arm_pts[1][0]), int(arm_pts[1][1]), color=self._darken(c, 10), width=int(2.5*s))
            self.draw_line(draw, int(arm_pts[1][0]), int(arm_pts[1][1]), int(arm_pts[2][0]), int(arm_pts[2][1]), color=self._darken(c, 10), width=int(2*s))
        leg_c = self._darken(c, 12)
        for side in [-1, 1]:
            self.draw_line(draw, x + side * 4*s, y - 2*s, x + side * 5*s, y + 8*s, color=leg_c, width=int(2.5*s))
        tail_pts = [(x, y - 10*s), (x - 6*s, y - 4*s), (x - 8*s, y - 6*s)]
        self.draw_polygon(draw, tail_pts, fill=c + (200,))

    def draw_squirrel(self, draw, x, y, size=1.0, color=(160, 120, 80)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 8*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 12*s, 8*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 4*s; hx = x + body_w//2 + 2*s; hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Single ear (side profile)
        ear_pts = [(hx + 2*s, hy - 3*s), (hx + 3*s, hy - 6*s), (hx + 3.5*s, hy - 3*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 15) + (200,))
        self.draw_circle(draw, hx + 3*s, hy - s, 1*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 4.5*s, hy + 0.5*s, 0.8*s, fill=(40, 35, 30, 200))
        tail_pts = [(x - 6*s, y - 6*s), (x - 12*s, y - 10*s), (x - 10*s, y - 2*s), (x - 6*s, y - 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._lighten(c, 15) + (200,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        leg_c = self._darken(c, 12)
        for lx in [-3*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 5*s, color=leg_c, width=int(1.5*s))

    def draw_lizard(self, draw, x, y, size=1.0, color=(100, 160, 80)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 20*s, 6*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        tail_pts = [(x - 10*s, y - 3*s), (x - 18*s, y - 5*s), (x - 20*s, y - 3*s), (x - 16*s, y - s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (200,))
        head_r = 4*s; hx = x + body_w//2 + 2*s; hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        snout_pts = [(hx + 2*s, hy - s), (hx + 6*s, hy - 2*s), (hx + 6*s, hy + s), (hx + 2*s, hy + 2*s)]
        self.draw_polygon(draw, snout_pts, fill=self._lighten(c, 12) + (200,))
        self.draw_circle(draw, hx + 3*s, hy - 1*s, 1*s, fill=(220, 200, 60, 220))
        leg_c = self._darken(c, 12)
        for lx in [-6*s, 4*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * 2*s, y - 2*s, x + lx + side * 3*s, y + 4*s, color=leg_c, width=int(1.5*s))

    def draw_frog(self, draw, x, y, size=1.0, color=(80, 160, 60)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 16*s, 10*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 6*s; hx = x + body_w//2 + 2*s; hy = y - body_h + 3*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Single eye (side profile)
        self.draw_circle(draw, hx + 3*s, hy - 4*s, 2.5*s, fill=self._lighten(c, 15) + (220,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        self.draw_circle(draw, hx + 3*s, hy - 4*s, 1*s, fill=(30, 25, 20, 200))
        mouth_pts = [(hx + 2*s, hy + 2*s), (hx + 8*s, hy + 3*s), (hx + 6*s, hy + 4*s)]
        self.draw_polygon(draw, mouth_pts, fill=self._darken(c, 10) + (200,))
        leg_c = self._darken(c, 12)
        for side in [-1, 1]:
            self.draw_line(draw, x + side * 6*s, y - 2*s, x + side * 8*s, y + 6*s, color=leg_c, width=int(3*s))
            self.draw_line(draw, x + side * 3*s, y - 2*s, x + side * 5*s, y + 6*s, color=leg_c, width=int(2*s))

    def draw_goat(self, draw, x, y, size=1.0, color=(200, 170, 140)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        body_w, body_h = 20*s, 12*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        neck_pts = [(x + 6*s, y - 10*s), (x + 10*s, y - 18*s), (x + 8*s, y - 20*s), (x + 4*s, y - 10*s)]
        self.draw_polygon(draw, neck_pts, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=1)
        head_r = 4*s; hx = x + 12*s; hy = y - 18*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Single near horn and ear (side profile)
        horn_pts = [(hx + 2*s, hy - 3*s), (hx + 3*s, hy - 9*s), (hx + s, hy - 3*s)]
        self.draw_polygon(draw, horn_pts, fill=(200, 190, 170, 220), stroke=(140, 130, 110, 160), stroke_width=1)
        ear_pts = [(hx + 3*s, hy - 2*s), (hx + 5*s, hy - 3*s), (hx + 4*s, hy)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 12) + (200,))
        beard_pts = [(hx + 2*s, hy + 3*s), (hx + 3*s, hy + 7*s), (hx + 4*s, hy + 3*s)]
        self.draw_polygon(draw, beard_pts, fill=self._darken(c, 10) + (200,))
        self.draw_circle(draw, hx + 3*s, hy - 1*s, 1.2*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 5*s, hy + 0.5*s, 1*s, fill=(40, 35, 30, 200))
        leg_c = self._darken(c, 15)
        for lx in [-7*s, 3*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 8*s, color=leg_c, width=int(2*s))
        tx = x - body_w//2 - s
        self.draw_line(draw, tx, y - body_h + 4*s, tx - 3*s, y - body_h + 2*s, color=self._darken(c, 10), width=int(1.5*s))

    def draw_sheep(self, draw, x, y, size=1.0, color=(240, 235, 230)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        self.draw_circle(draw, x, y - 6*s, 10*s, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        import math
        for wi in range(8):
            a = wi * math.pi / 4
            wx = x + 8*s * math.cos(a)
            wy = y - 6*s + 8*s * math.sin(a) - 2*s
            self.draw_circle(draw, wx, wy, 4*s, fill=self._lighten(c, 5) + (200,))
        head_r = 4*s; hx = x + 8*s; hy = y - 12*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._darken(c, 10) + (220,), stroke=(60, 55, 50, 180), stroke_width=2)
        # Single ear (side profile)
        ear_pts = [(hx + 3*s, hy - 2*s), (hx + 5*s, hy - 3*s), (hx + 4*s, hy)]
        self.draw_polygon(draw, ear_pts, fill=self._darken(c, 10) + (200,))
        self.draw_circle(draw, hx + 2*s, hy - 1*s, 1*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 4*s, hy + 0.5*s, 0.8*s, fill=(40, 35, 30, 200))
        leg_c = self._darken(c, 20)
        for lx in [-5*s, 3*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 8*s, color=leg_c, width=int(2*s))
        tx = x - 8*s
        self.draw_line(draw, tx, y - 8*s, tx - 4*s, y - 8*s, color=self._darken(c, 10), width=int(1.5*s))

    def draw_pig(self, draw, x, y, size=1.0, color=(240, 200, 180)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        body_w, body_h = 24*s, 14*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 6*s; hx = x + body_w//2 + 2*s; hy = y - body_h + 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        snout_r = 3*s
        self.draw_ellipse(draw, hx + 4*s - snout_r, hy - snout_r, snout_r*2, snout_r*1.5, fill=self._lighten(c, 10) + (200,))
        for nostril in [-1, 1]:
            self.draw_circle(draw, hx + 6*s + nostril * s, hy, 1*s, fill=(40, 35, 30, 200))
        # Single ear (side profile)
        ear_pts = [(hx + 3*s, hy - 5*s), (hx + 4*s, hy - 8*s), (hx + 5*s, hy - 5*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 8) + (200,))
        self.draw_circle(draw, hx + 3*s, hy - 2*s, 1.2*s, fill=(30, 25, 20, 200))
        leg_c = self._darken(c, 12)
        for lx in [-8*s, 4*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * 2*s, y - 2*s, x + lx + side * 2*s, y + 6*s, color=leg_c, width=int(2.5*s))
        tx = x - body_w//2 - s
        self.draw_line(draw, tx, y - body_h//2, tx - 3*s, y - body_h//2 - s, color=self._darken(c, 10), width=int(1.5*s))

    def draw_rat(self, draw, x, y, size=1.0, color=(160, 140, 130)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 1, 6*s, offset=(2, 2), blur_radius=2, color=(0, 0, 0, 20))
        self.draw_ellipse(draw, x - 5*s, y - 5*s, 10*s, 7.5*s, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 3*s; hx = x + 5*s; hy = y - 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        snout_pts = [(hx + 2*s, hy - s), (hx + 5*s, hy), (hx + 5*s, hy + s), (hx + 2*s, hy + 2*s)]
        self.draw_polygon(draw, snout_pts, fill=self._lighten(c, 12) + (200,))
        self.draw_circle(draw, hx + 5*s, hy, 0.8*s, fill=(40, 35, 30, 200))
        # Single ear (side profile)
        self.draw_circle(draw, hx + 2*s, hy - 3*s, 2*s, fill=self._lighten(c, 15) + (200,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        self.draw_circle(draw, hx + 2*s, hy - 1*s, 0.8*s, fill=(30, 25, 20, 200))
        tail_pts = [(x - 5*s, y), (x - 10*s, y - 3*s), (x - 12*s, y), (x - 10*s, y + 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._lighten(c, 5) + (200,))
        leg_c = self._darken(c, 12)
        for lx in [-2*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y, x + lx + side * s, y + 4*s, color=leg_c, width=int(1.5*s))

    def draw_beaver(self, draw, x, y, size=1.0, color=(140, 110, 80)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))

        body_w, body_h = 18*s, 12*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Head (side profile, larger)
        head_r = 4.5*s; hx = x + body_w//2 + 2*s; hy = y - body_h + 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)

        # Single round ear (near side)
        self.draw_circle(draw, hx + 3*s, hy - 4*s, 1.5*s, fill=self._lighten(c, 12) + (200,))

        # Eye
        self.draw_circle(draw, hx + 2.5*s, hy - 1*s, 1*s, fill=(30, 25, 20, 200))

        # Prominent buck teeth
        tooth_pts = [(hx + 4*s, hy + 1.5*s), (hx + 6*s, hy + 1.5*s), (hx + 6*s, hy + 3.5*s), (hx + 4*s, hy + 3.5*s)]
        self.draw_polygon(draw, tooth_pts, fill=(240, 230, 200, 220))

        # Flat paddle tail with cross-hatch
        tail_pts = [(x - 9*s, y - 2*s), (x - 16*s, y - 5*s), (x - 20*s, y - 2*s), (x - 20*s, y + 2*s), (x - 16*s, y + 5*s), (x - 9*s, y + 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 15) + (200,), stroke=self._darken(c, 25) + (160,), stroke_width=1)
        # Cross-hatch on tail
        for ti in range(3):
            txx = x - (12 + ti * 3) * s
            self.draw_line(draw, txx, y - 3*s - ti*s, txx + s, y + 4*s + ti*s, color=self._darken(c, 20) + (100,), width=1)

        leg_c = self._darken(c, 12)
        for lx in [-4*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 6*s, color=leg_c, width=int(2.5*s))

    def draw_otter(self, draw, x, y, size=1.0, color=(140, 110, 100)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 18*s, 6*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        tail_pts = [(x - 9*s, y - 2*s), (x - 16*s, y - 3*s), (x - 18*s, y), (x - 14*s, y + 2*s)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (200,))
        head_r = 4*s; hx = x + body_w//2 + 2*s; hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Single ear (side profile)
        self.draw_circle(draw, hx + 3*s, hy - 3*s, 1.5*s, fill=self._lighten(c, 12) + (200,))
        self.draw_circle(draw, hx + 3*s, hy - 1*s, 1*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 5*s, hy + 0.5*s, 0.8*s, fill=(40, 35, 30, 200))
        leg_c = self._darken(c, 12)
        for lx in [-5*s, 3*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 4*s, color=leg_c, width=int(1.5*s))

    def draw_hedgehog(self, draw, x, y, size=1.0, color=(150, 120, 90)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 14*s, 10*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        import math
        spine_c = self._darken(c, 25)
        for si in range(12):
            a = si * math.pi / 6
            sx = x + 8*s * math.cos(a)
            sy = y - 5*s + 6*s * math.sin(a)
            self.draw_line(draw, sx, sy, sx + 2*s * math.cos(a), sy + 2*s * math.sin(a) - 3*s, color=spine_c, width=int(1.2*s))
        head_r = 3.5*s; hx = x + body_w//2 + 2*s; hy = y - body_h + 2*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 15) + (220,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        self.draw_circle(draw, hx + 2*s, hy - 1*s, 0.8*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 4*s, hy + 0.5*s, 0.6*s, fill=(40, 35, 30, 200))
        leg_c = self._darken(c, 10)
        for lx in [-3*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y, x + lx + side * s, y + 4*s, color=leg_c, width=int(1.5*s))

    def draw_bat(self, draw, x, y, size=1.0, color=(60, 50, 45)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 16*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))

        # Body (small oval)
        self.draw_ellipse(draw, x - 3*s, y - 5*s, 6*s, 8*s, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=1)

        # Head
        head_r = 2.5*s; hx = x; hy = y - 8*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._darken(c, 5) + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=1)

        # Ears (two pointed triangles on top)
        for side in [-1, 1]:
            ear_pts = [(hx + side * 1.5*s, hy - 1.5*s), (hx + side * 2.5*s, hy - 6*s), (hx + side * 3.5*s, hy - 1.5*s)]
            self.draw_polygon(draw, ear_pts, fill=c + (200,))

        # Eyes (small glowing dots)
        self.draw_circle(draw, hx - 1*s, hy - 0.5*s, 0.5*s, fill=(200, 180, 60, 200))
        self.draw_circle(draw, hx + 1*s, hy - 0.5*s, 0.5*s, fill=(200, 180, 60, 200))

        # Wings (broad membrane shape)
        wing_color = self._darken(c, 10)
        for side in [-1, 1]:
            # Main wing membrane
            wing_pts = [(x + side * 3*s, y - 4*s), (x + side * 16*s, y - 10*s), (x + side * 20*s, y - 4*s),
                        (x + side * 18*s, y + 4*s), (x + side * 12*s, y + 6*s), (x + side * 5*s, y + 2*s)]
            self.draw_polygon(draw, wing_pts, fill=wing_color + (180,), stroke=self._darken(c, 15) + (120,), stroke_width=1)

            # Wing finger bones (3 ribs radiating from wrist)
            wx = x + side * 3*s; wy = y - 4*s
            for rib in range(3):
                rx = x + side * (8 + rib * 5) * s
                ry = y - (6 + rib * 3) * s
                self.draw_line(draw, wx, wy, rx, ry, color=self._darken(c, 15), width=int(1.2*s))

        # Clawed feet hanging down
        for side in [-1, 1]:
            self.draw_line(draw, x + side * 1.5*s, y + 2*s, x + side * 2*s, y + 6*s, color=c, width=int(2*s))
            # Tiny claws
            self.draw_line(draw, x + side * 2*s, y + 6*s, x + side * 2.5*s, y + 8*s, color=self._darken(c, 10), width=1)
            self.draw_line(draw, x + side * 2*s, y + 6*s, x + side * 1.5*s, y + 8*s, color=self._darken(c, 10), width=1)

    def draw_kangaroo(self, draw, x, y, size=1.0, color=(180, 140, 100)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 3, 14*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        body_w, body_h = 18*s, 16*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 5*s; hx = x + 6*s; hy = y - 16*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        # Single ear (side profile)
        ear_pts = [(hx + 2*s, hy - 4*s), (hx + 3*s, hy - 9*s), (hx + 4*s, hy - 4*s)]
        self.draw_polygon(draw, ear_pts, fill=self._lighten(c, 15) + (200,))
        snout_pts = [(hx + 3*s, hy - s), (hx + 7*s, hy), (hx + 7*s, hy + 2*s), (hx + 3*s, hy + 2*s)]
        self.draw_polygon(draw, snout_pts, fill=self._lighten(c, 12) + (200,))
        self.draw_circle(draw, hx + 7*s, hy + 0.5*s, 0.8*s, fill=(40, 35, 30, 200))
        self.draw_circle(draw, hx + 3*s, hy - 1.5*s, 1.2*s, fill=(30, 25, 20, 200))
        pouch_pts = [(x - 2*s, y - 6*s), (x + 2*s, y - 6*s), (x + 3*s, y - 2*s), (x - 3*s, y - 2*s)]
        self.draw_polygon(draw, pouch_pts, fill=self._darken(c, 5) + (200,), stroke=self._darken(c, 10) + (140,), stroke_width=1)
        leg_c = self._darken(c, 15)
        for side in [-1, 1]:
            self.draw_line(draw, x + side * 3*s, y - 2*s, x + side * 6*s, y + 10*s, color=leg_c, width=int(3*s))
            self.draw_line(draw, x + side * s, y - 2*s, x + side * 2*s, y + 6*s, color=self._darken(c, 10), width=int(1.5*s))
        tail_pts = [(x - 4*s, y - 6*s), (x - 10*s, y), (x - 8*s, y + 2*s), (x - 4*s, y)]
        self.draw_polygon(draw, tail_pts, fill=self._darken(c, 10) + (200,))

    def draw_sloth(self, draw, x, y, size=1.0, color=(140, 120, 100)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 14*s, 10*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 4*s; hx = x + body_w//2 + 2*s; hy = y - body_h + 3*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        face_mask = self._lighten(c, 20)
        self.draw_ellipse(draw, hx + s - 2*s, hy - 2*s, 3*s, 3*s, fill=face_mask + (200,))
        eye_mask = self._darken(c, 20)
        for side in [-1, 1]:
            self.draw_ellipse(draw, hx + side * s, hy - s, 1.5*s, 1*s, fill=eye_mask + (200,))
        self.draw_circle(draw, hx + 2*s, hy - 3*s, 0.5*s, fill=(30, 25, 20, 200))
        self.draw_line(draw, hx + 2*s, hy + 1*s, hx + 4*s, hy + 1*s, color=(60, 50, 40, 150), width=1)
        for side in [-1, 1]:
            self.draw_line(draw, x + side * 6*s, y - 6*s, x + side * 10*s, y + 4*s, color=self._darken(c, 10), width=int(2*s))
            self.draw_line(draw, x + side * 6*s, y - 6*s, x + side * 8*s, y + 6*s, color=self._darken(c, 10), width=int(1.5*s))
        leg_c = self._darken(c, 10)
        for lx in [-4*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 5*s, color=leg_c, width=int(2*s))

    def draw_raccoon(self, draw, x, y, size=1.0, color=(150, 140, 130)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 16*s, 10*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 4*s; hx = x + body_w//2 + 2*s; hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 5) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        mask_c = self._darken(c, 30)
        for side in [-1, 1]:
            mask_pts = [(hx + side * s, hy - 2*s), (hx + side * 3*s, hy - 3*s), (hx + side * 4*s, hy - 1*s), (hx + side * 2*s, hy)]
            self.draw_polygon(draw, mask_pts, fill=mask_c + (200,))
        self.draw_circle(draw, hx + 3*s, hy - 1.5*s, 1*s, fill=(30, 25, 20, 200))
        self.draw_circle(draw, hx + 5*s, hy + 0.5*s, 0.8*s, fill=(40, 35, 30, 200))
        # Single ear (side profile)
        self.draw_circle(draw, hx + 3*s, hy - 3.5*s, 2*s, fill=self._lighten(c, 10) + (200,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        tail_pts = [(x - 8*s, y - 4*s), (x - 14*s, y - 6*s), (x - 12*s, y - s), (x - 8*s, y - s)]
        self.draw_polygon(draw, tail_pts, fill=c + (200,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        for band in range(4):
            bx = x - (10 + band * 1.5) * s
            self.draw_line(draw, bx, y - 5*s - band * 0.5*s, bx, y - s + band * 0.3*s, color=self._darken(c, 25), width=int(1.2*s))
        leg_c = self._darken(c, 12)
        for lx in [-4*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 5*s, color=leg_c, width=int(1.5*s))

    def draw_skunk(self, draw, x, y, size=1.0, color=(40, 35, 30)):
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 25))
        body_w, body_h = 16*s, 8*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        stripe_c = (240, 240, 240)
        stripe_pts = [(x - 2*s, y - 6*s), (x + 2*s, y - 6*s), (x + 4*s, y - 3*s), (x, y - 2*s)]
        self.draw_polygon(draw, stripe_pts, fill=stripe_c + (180,))
        tail_pts = [(x - 8*s, y - 4*s), (x - 16*s, y - 6*s), (x - 18*s, y - 2*s), (x - 14*s, y + s), (x - 8*s, y - s)]
        self.draw_polygon(draw, tail_pts, fill=c + (200,), stroke=self._darken(c, 10) + (160,), stroke_width=1)
        tail_stripe = [(x - 10*s, y - 4*s), (x - 16*s, y - 5*s), (x - 14*s, y - s), (x - 10*s, y - 2*s)]
        self.draw_polygon(draw, tail_stripe, fill=stripe_c + (160,))
        head_r = 3.5*s; hx = x + body_w//2 + 2*s; hy = y - body_h + s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        white_stripe = [(hx - s, hy - 3*s), (hx + s, hy - 3*s), (hx + s, hy + s), (hx - s, hy + s)]
        self.draw_polygon(draw, white_stripe, fill=stripe_c + (180,))
        self.draw_circle(draw, hx + 2*s, hy - 1*s, 0.8*s, fill=(30, 25, 20, 200))
        leg_c = self._darken(c, 10)
        for lx in [-4*s, 2*s]:
            for side in [-1, 1]:
                self.draw_line(draw, x + lx + side * s, y - 2*s, x + lx + side * s, y + 5*s, color=leg_c, width=int(1.5*s))

    def draw_fantasy_creature(self, draw, x, y, size=1.0, color=(100, 80, 60)):
        """Draw a bipedal fantasy creature (troll, goblin, dwarf, etc.)."""
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 12*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        body_w, body_h = 16*s, 18*s
        self.draw_ellipse(draw, x - body_w//2, y - body_h, body_w, body_h, fill=c + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        head_r = 6*s; hx = x; hy = y - body_h - 4*s
        self.draw_circle(draw, hx, hy, head_r, fill=self._lighten(c, 10) + (220,), stroke=self._darken(c, 15) + (180,), stroke_width=2)
        for side in [-1, 1]:
            self.draw_line(draw, x + side * body_w//3, y - 8*s, x + side * body_w//1.5, y + 4*s, color=self._darken(c, 10), width=int(2.5*s))
        leg_c = self._darken(c, 15)
        for side in [-1, 1]:
            self.draw_line(draw, x + side * 4*s, y - 2*s, x + side * 5*s, y + 10*s, color=leg_c, width=int(3*s))
        self.draw_circle(draw, hx + 2*s, hy - 1*s, 1.5*s, fill=(220, 200, 60, 220))

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

    def draw_fern(self, draw, x, y, size=1.0, color=(60, 130, 50)):
        """Draw a prehistoric fern / cycad."""
        s = size; c = tuple(color[:3])
        # Stem
        self.draw_line(draw, x, y, x, y - 12*s, color=(40, 90, 30), width=int(2*s))
        # Fronds (curving outward)
        for side, offset in [(-1, -2), (1, 2)]:
            for i in range(4):
                fy = y - (2 + i * 3) * s
                tip_x = x + side * (6 + i * 2) * s
                tip_y = fy - 2*s
                self.draw_line(draw, x, fy, tip_x, tip_y, color=c, width=int(1.5*s))
                # Leaflets along frond
                for j in range(3):
                    lx = x + side * (2 + j * 2) * s
                    ly = fy - (j * 0.5) * s
                    self.draw_line(draw, lx, ly, lx + side * 2*s, ly - 2*s, color=self._lighten(c, 15), width=int(1*s))
        # Central curled frond
        self.draw_arc(draw, x, y - 14*s, 4*s, 180, 360, color=(50, 110, 40), width=int(2*s))

    def draw_asteroid(self, draw, x, y, size=1.0, color=(200, 100, 40)):
        """Draw a fiery asteroid streaking across the sky."""
        s = size; c = tuple(color[:3])
        self.draw_shadow_circle(draw, x, y + 2, 10*s, offset=(3, 3), blur_radius=5, color=(0, 0, 0, 60))
        # Fire trail
        for t in range(5):
            tx = x - (6 + t * 5)*s
            ty = y - t*2*s
            tr = (5 - t)*1.5*s
            alpha = 80 - t*15
            self.draw_circle(draw, tx, ty, tr, fill=(255, 160, 40, alpha))
        # Main body (irregular rock)
        pts = [(x - 8*s, y), (x - 4*s, y - 8*s), (x + 4*s, y - 6*s), (x + 8*s, y - 2*s), (x + 2*s, y + 6*s), (x - 6*s, y + 4*s)]
        self.draw_polygon(draw, pts, fill=(120, 90, 60, 230), stroke=(60, 45, 30, 200), stroke_width=2)
        # Fire glow around edges
        self.draw_circle(draw, x - 2*s, y + 2*s, 6*s, fill=(255, 120, 30, 40))
        # Cracks
        self.draw_line(draw, x - 2*s, y - 4*s, x + 3*s, y - 2*s, color=(60, 45, 30), width=1)
        self.draw_line(draw, x - 3*s, y + 2*s, x + 2*s, y + 3*s, color=(60, 45, 30), width=1)

    def draw_crater(self, draw, x, y, size=1.0, color=(100, 80, 60)):
        """Draw an impact crater on the ground."""
        s = size; c = tuple(color[:3])
        r = 20*s
        # Outer rim (shadow)
        self.draw_shadow_circle(draw, x, y + 2, r, offset=(2, 2), blur_radius=4, color=(0, 0, 0, 50))
        # Outer rim (raised edge)
        pts = []
        for a in range(0, 370, 15):
            rad = math.radians(a)
            px = x + int(math.cos(rad) * (r + 2*s))
            py = y + int(math.sin(rad) * (r*0.5 + s))
            pts.append((px, py))
        if pts:
            self.draw_polygon(draw, pts, fill=self._darken(c, 10) + (220,), stroke=self._darken(c, 25) + (180,), stroke_width=2)
        # Inner depression (darker)
        inner_r = r * 0.6
        pts_inner = []
        for a in range(0, 370, 15):
            rad = math.radians(a)
            px = x + int(math.cos(rad) * inner_r)
            py = y + 2 + int(math.sin(rad) * inner_r * 0.4)
            pts_inner.append((px, py))
        if pts_inner:
            self.draw_polygon(draw, pts_inner, fill=(50, 40, 30, 250), stroke=(30, 25, 20, 180), stroke_width=1)
        # Center crack
        self.draw_line(draw, x - 6*s, y + 4*s, x + 5*s, y + 6*s, color=(25, 20, 15), width=2)
        self.draw_line(draw, x - 3*s, y + 2*s, x + 2*s, y + 8*s, color=(25, 20, 15), width=1)

    def draw_skeleton(self, draw, x, y, size=1.0, color=(220, 200, 180)):
        """Draw a fossilized skeleton (large bones)."""
        s = size; c = tuple(color[:3])
        # Shadow
        self.draw_shadow_circle(draw, x, y + 3, 10*s, offset=(2, 2), blur_radius=3, color=(0, 0, 0, 30))
        # Skull
        skull_pts = [(x - 5*s, y - 2*s), (x + 6*s, y - 4*s), (x + 10*s, y), (x + 8*s, y + 3*s), (x + 2*s, y + 4*s), (x - 4*s, y + 2*s)]
        self.draw_polygon(draw, skull_pts, fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=2)
        # Eye socket
        self.draw_circle(draw, x + 3*s, y - 1, 2.5*s, fill=(60, 55, 50, 230))
        # Jaw line
        self.draw_line(draw, x - 3*s, y + 2*s, x + 8*s, y + 2*s, color=self._darken(c, 15), width=int(1.5*s))
        # Teeth
        for tx in range(int(x + 2*s), int(x + 8*s), 2):
            self.draw_line(draw, tx, y + 1, tx, y + 3*s, color=(240, 235, 225), width=1)
        # Spine (vertebrae)
        vx = x - 6*s
        for v in range(5):
            v_px = vx - v * 3*s
            vy_off = 1 if v % 2 == 0 else -1
            self.draw_circle(draw, v_px, y - vy_off, 1.5*s, fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=1)
            self.draw_line(draw, v_px, y - 3*s, v_px, y + 2*s, color=self._darken(c, 10), width=1)
        # Ribs (curved)
        for r_idx in range(4):
            rx = x - 4*s - r_idx * 2*s
            self.draw_arc(draw, rx, y - 3*s, 4*s, 200, 340, color=self._darken(c, 10), width=int(1.5*s))
        # Tail bones
        tx2 = x - 18*s
        for t in range(4):
            self.draw_circle(draw, tx2 - t*2*s, y + t*s, s, fill=c + (200,), stroke=self._darken(c, 20) + (150,), stroke_width=1)
        # Leg bones (long)
        self.draw_line(draw, x - 2*s, y + 3*s, x - 4*s, y + 10*s, color=self._darken(c, 10), width=int(2*s))
        self.draw_line(draw, x + 4*s, y + 3*s, x + 3*s, y + 10*s, color=self._darken(c, 10), width=int(2*s))

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

    def draw_book(self, draw, x, y, size=1.0, color=(140, 100, 60), title=""):
        """Draw an open book with pages. x, y are pixel coords, size = scale."""
        s = max(size * 15, 10)
        cx, cy = x, y
        bw = int(40 * s)
        bh = int(30 * s)
        spine_w = max(3, int(3 * s))

        # Left page
        draw.polygon([
            (cx - bw/2, cy - bh/2),
            (cx - spine_w/2, cy - bh/2),
            (cx - spine_w/2, cy + bh/2),
            (cx - bw/2, cy + bh/2),
        ], fill=(245, 235, 215), outline=(70, 60, 50), width=2)

        # Right page
        draw.polygon([
            (cx + spine_w/2, cy - bh/2),
            (cx + bw/2, cy - bh/2),
            (cx + bw/2, cy + bh/2),
            (cx + spine_w/2, cy + bh/2),
        ], fill=(250, 242, 225), outline=(70, 60, 50), width=2)

        # Spine
        draw.polygon([
            (cx - spine_w/2, cy - bh/2),
            (cx + spine_w/2, cy - bh/2),
            (cx + spine_w/2, cy + bh/2),
            (cx - spine_w/2, cy + bh/2),
        ], fill=(120, 90, 60), outline=(50, 35, 25), width=2)

        # Title
        if title:
            from PIL import ImageFont
            try:
                font_sz = int(12 * s)
                fnt = ImageFont.truetype("arial.ttf", font_sz)
                tx = cx - bw/4
                ty = cy
                draw.text((tx+1, ty+1), title, fill=(100, 90, 70), font=fnt, anchor="mm")
                draw.text((tx, ty), title, fill=(30, 25, 15), font=fnt, anchor="mm")
            except Exception:
                pass

        # Page lines
        for i in range(8):
            ly = cy - bh/3 + i * (bh / 9)
            lx1 = cx - bw/2 + 4 * s
            lx2 = cx - spine_w/2 - 4 * s
            draw.line([(lx1, ly), (lx2, ly)], fill=(160, 150, 140, 120), width=1)

        # Cover edges (dark outline)
        draw.rectangle([
            cx - bw/2 - 2*s, cy - bh/2 - 2*s,
            cx - spine_w/2 + 2*s, cy + bh/2 + 2*s
        ], outline=color, width=max(2, int(2 * s + 0.5)))
        draw.rectangle([
            cx + spine_w/2 - 2*s, cy - bh/2 - 2*s,
            cx + bw/2 + 2*s, cy + bh/2 + 2*s
        ], outline=color, width=max(2, int(2 * s + 0.5)))

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
        s = max(size, 0.3); c = tuple(color[:3])
        r = int(24 * s)
        self.draw_shadow_circle(draw, x, y + r, r, offset=(3, 2), blur_radius=4, color=(0, 0, 0, 40))
        self.draw_circle(draw, x, y, r, fill=c + (200,), stroke=self._darken(c, 20) + (180,), stroke_width=2)
        # Clip region for continents on globe
        scale = r * 0.85
        def globe_pt(lon, lat):
            # lon: -1..1, lat: -1..1, project onto visible hemisphere
            gx = x + int(lon * scale)
            gy = y - int(lat * scale * 0.8)
            return (gx, gy)
        # Continent outlines projected onto globe
        def globe_poly(pts, col):
            gpts = [globe_pt(p[0], p[1]) for p in pts]
            self.draw_polygon(draw, gpts, fill=col, stroke=self._darken(col, 30) + (160,), stroke_width=1)
        gcol = (60, 120, 80, 180)
        # North America
        globe_poly([(-0.7, 0.2), (-0.4, 0.3), (-0.2, 0.1), (-0.3, -0.1),
                    (-0.4, -0.15), (-0.5, -0.1), (-0.6, 0.0)], gcol)
        # South America
        globe_poly([(-0.3, -0.15), (-0.15, -0.2), (-0.1, -0.4),
                    (-0.2, -0.55), (-0.3, -0.5), (-0.3, -0.3)], gcol)
        # Europe + Africa
        globe_poly([(0.1, 0.25), (0.3, 0.2), (0.35, 0.0), (0.3, -0.2),
                    (0.2, -0.3), (0.1, -0.2), (0.05, 0.0), (0.0, 0.15)], gcol)
        # Asia
        globe_poly([(0.3, 0.2), (0.6, 0.15), (0.75, 0.0), (0.7, -0.15),
                    (0.6, -0.2), (0.5, -0.15), (0.35, 0.0)], gcol)
        # Australia
        globe_poly([(0.6, -0.35), (0.7, -0.4), (0.75, -0.5), (0.65, -0.55)], gcol)
        # Grid lines (latitude/longitude)
        self.draw_arc(draw, x, y, int(r * 0.7), 180, 360, color=(255, 255, 255, 40), width=1)
        self.draw_arc(draw, x, y, int(r * 0.5), 0, 180, color=(255, 255, 255, 30), width=1)
        self.draw_arc(draw, x, y, int(r * 0.85), 195, 345, color=(255, 255, 255, 20), width=1)
        # Stand
        self.draw_rect(draw, x - 2 * s, y + r, 4 * s, int(6 * s),
                      fill=(80, 70, 60, 200), stroke=(50, 45, 40, 180), stroke_width=1)
        self.draw_rect(draw, x - 5 * s, y + r + int(6 * s), int(10 * s), int(3 * s),
                      fill=(80, 70, 60, 200), stroke=(50, 45, 40, 180), stroke_width=1)

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

    def draw_world_map(self, draw, x, y, size=1.0, color=(220, 200, 160)):
        """Draw a world map with simplified continent outlines."""
        s = max(size, 0.3)
        c = tuple(color[:3])
        w = int(30 * s)
        h = int(20 * s)
        # Map background
        self.draw_rect(draw, x - w//2, y - h//2, w, h, fill=(180, 200, 220, 200),
                      stroke=(40, 35, 30, 150), stroke_width=1)
        # Continent generator helper
        def draw_continent(poly, col):
            pts = [(x - w//2 + int(p[0] * w), y - h//2 + int(p[1] * h)) for p in poly]
            self.draw_polygon(draw, pts, fill=col, stroke=self._darken(col, 30) + (180,), stroke_width=1)
        land = (80, 140, 80, 200)
        # North America
        na = [(0.05, 0.12), (0.22, 0.05), (0.35, 0.15), (0.30, 0.30),
              (0.25, 0.32), (0.22, 0.28), (0.18, 0.30), (0.12, 0.22)]
        draw_continent(na, land)
        # South America
        sa = [(0.22, 0.35), (0.30, 0.33), (0.32, 0.45), (0.28, 0.58),
              (0.25, 0.62), (0.22, 0.55), (0.20, 0.42)]
        draw_continent(sa, land)
        # Europe
        eu = [(0.42, 0.08), (0.52, 0.06), (0.58, 0.12), (0.55, 0.18),
              (0.50, 0.20), (0.46, 0.18), (0.42, 0.15)]
        draw_continent(eu, land)
        # Africa
        af = [(0.42, 0.22), (0.55, 0.20), (0.58, 0.35), (0.55, 0.50),
              (0.52, 0.52), (0.48, 0.45), (0.45, 0.35), (0.42, 0.28)]
        draw_continent(af, (70, 130, 70, 200))
        # Asia
        asia = [(0.50, 0.08), (0.65, 0.05), (0.85, 0.10), (0.95, 0.18),
                (0.92, 0.30), (0.85, 0.35), (0.78, 0.32), (0.70, 0.30),
                (0.65, 0.28), (0.58, 0.22), (0.52, 0.18)]
        draw_continent(asia, land)
        # India
        ind = [(0.60, 0.32), (0.65, 0.30), (0.68, 0.38), (0.64, 0.42), (0.60, 0.38)]
        draw_continent(ind, land)
        # Australia
        au = [(0.82, 0.50), (0.92, 0.48), (0.95, 0.55), (0.90, 0.60), (0.85, 0.58)]
        draw_continent(au, land)

    def draw_train(self, draw, x, y, size=1.0, color=(80, 40, 40)):
        """Draw a train with locomotive and one carriage."""
        s = max(size, 0.3); c = tuple(color[:3])
        # Locomotive body
        lw, lh = int(20*s), int(12*s)
        cx, cy = x - int(14*s), y
        self.draw_rect(draw, cx-lw//2, cy-lh//2, lw, lh, fill=c+(200,),
                      stroke=self._darken(c,30)+(180,), stroke_width=1)
        # Cabin
        self.draw_rect(draw, cx+lw//2-int(8*s), cy-lh//2-int(4*s), 8*s, lh//2+4*s,
                      fill=self._lighten(c,10)+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        # Chimney
        self.draw_rect(draw, cx-lw//2+2*s, cy-lh//2-int(4*s), 3*s, 4*s,
                      fill=(60,40,40,200), stroke=(40,30,30,150), stroke_width=1)
        # Cow catcher
        self.draw_polygon(draw, [(cx-lw//2, cy+lh//4), (cx-lw//2-4*s, cy+lh//2), (cx-lw//2, cy+lh//2)],
                         fill=(100,80,60,200))
        # Wheels (locomotive)
        for wx in [cx-lw//2+3*s, cx+lw//2-3*s]:
            self.draw_circle(draw, wx, cy+lh//2+2*s, 3*s, fill=(40,40,40,200), stroke=(20,20,20,180), stroke_width=1)
            self.draw_circle(draw, wx, cy+lh//2+2*s, 1*s, fill=(80,80,80,150))
        # Carriage
        cw, ch = int(18*s), int(10*s)
        cx2 = x + int(12*s)
        # Connector
        self.draw_line(draw, cx+lw//2, cy, cx2-cw//2, cy, color=(60,50,40,160), width=int(2*s))
        cy2 = cy
        self.draw_rect(draw, cx2-cw//2, cy2-ch//2, cw, ch, fill=self._lighten(c,15)+(200,),
                      stroke=self._darken(c,20)+(150,), stroke_width=1)
        # Carriage wheels
        for wx in [cx2-cw//2+3*s, cx2+cw//2-3*s]:
            self.draw_circle(draw, wx, cy+ch//2+2*s, 2*s, fill=(40,40,40,200), stroke=(20,20,20,180), stroke_width=1)
        # Windows
        for wx in [cx2-4*s, cx2+2*s]:
            self.draw_rect(draw, wx, cy-ch//4, 4*s, 4*s, fill=(180,200,230,180), stroke=(100,120,150,100), stroke_width=1)
        # Smoke
        for i in range(3):
            sy = cy-lh//2-int(6*s)-i*5*s
            sr = 3*s + i*2*s
            self.draw_circle(draw, cx-lw//2+int(3.5*s)+i*2*s, sy, sr, fill=(180,180,180,max(30,120-i*30)))

    def draw_india_map(self, draw, x, y, size=1.0, color=(140, 180, 100)):
        """Draw simplified outline of India."""
        s = max(size, 0.3); c = tuple(color[:3])
        w = int(20 * s); h = int(24 * s)
        # Outline as percentage points (clockwise from top-left-ish)
        pts = [
            (0.25, 0.05), (0.35, 0.02), (0.50, 0.00), (0.60, 0.03),  # Himalayan top
            (0.70, 0.05), (0.75, 0.08),  # Northeast
            (0.72, 0.15), (0.68, 0.18),  # Bangladesh bulge
            (0.60, 0.25), (0.55, 0.30),  # East coast
            (0.50, 0.40), (0.45, 0.50), (0.40, 0.60),  # Tapering south
            (0.38, 0.65),  # Kanyakumari tip
            (0.42, 0.62), (0.45, 0.55),  # Up west
            (0.40, 0.45), (0.35, 0.35),  # West coast
            (0.30, 0.25), (0.28, 0.20),  # Goa/Mumbai area
            (0.22, 0.15), (0.18, 0.12),  # Gujarat
            (0.20, 0.08), (0.22, 0.06),  # Pakistan border
        ]
        poly = [(x - w//2 + int(p[0]*w), y - h//2 + int(p[1]*h)) for p in pts]
        self.draw_polygon(draw, poly, fill=c+(200,), stroke=self._darken(c,25)+(180,), stroke_width=1)
        # Sri Lanka
        sl = [(x - 2*s, y + 8*s), (x + 2*s, y + 8*s), (x + 1*s, y + 11*s), (x - 1*s, y + 11*s)]
        self.draw_polygon(draw, sl, fill=(80, 140, 70, 180), stroke=(60, 100, 50, 160), stroke_width=1)

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
        if self.hand_drawn and self.technique:
            self._sketch_ellipse(draw, x, y, w//2, h//2, fill=fill, stroke=stroke or self.technique["stroke"], stroke_width=stroke_width)
            return
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
            base = self.paper_color if self.hand_drawn else None
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
            elif atmos.get("particles") == "ash":
                self._draw_ash_particles(draw, count=atmos.get("ash_count", 80))
            elif atmos.get("particles") == "mist":
                self._draw_mist(draw)
            elif atmos.get("particles") == "sunbeams":
                self._draw_sunbeams(draw)
            elif atmos.get("particles") == "sparkles":
                self.draw_stars(draw, count=atmos.get("star_count", 30))

            # ── Landscape features (mountains, ground, trees, clouds) ──
            if isinstance(bg, dict):
                self._render_landscape(draw, bg)

        # ── Elements (all types) sorted by z_index ──
        sorted_elems = sorted(desc.get("elements", []), key=lambda e: e.get("z_index", 2))
        for elem in sorted_elems:
            self._render_element(draw, elem)

        # ── Ash/smoke overlay ──
        if atmos.get("fog") == "ash":
            draw.rectangle([0, 0, self.w, self.h], fill=(30, 20, 10, 60))

        # ── Post-processing ──
        self._clean_canvas = canvas.copy()
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
        s = (elem.get("scale") or elem.get("size") or 1.0)

        # Colors
        fill = elem.get("fill", elem.get("fill_color", elem.get("color", None)))
        stroke = elem.get("stroke", elem.get("stroke_color", elem.get("line_color", None)))
        if fill and isinstance(fill, list): fill = tuple(fill)
        if stroke and isinstance(stroke, list): stroke = tuple(stroke)
        opacity = elem.get("opacity", 255)

        # ── Hand-drawn style overrides ──
        if self.hand_drawn:
            if stroke is None:
                stroke = self.technique["stroke"]
            fill = self._sketchify_fill(fill)
            # Force a stroke width override via elem context
            elem["_stroke_width"] = max(elem.get("stroke_width", 1), self.technique["stroke_width"])

        def _tc(c):
            if c is None: return None
            return tuple(c[:3]) if isinstance(c, (list, tuple)) else c

        fill = self._tc(fill)
        stroke = self._tc(stroke)

        # ── Drop shadow ──
        if elem.get("shadow") and etype not in ("text", "circle", "none"):
            r = max(10, int(20 * s))
            draw.ellipse([x - r, y - r + 4, x + r, y + r + 4], fill=(0, 0, 0, 50))

        self._render_element_dispatch(draw, elem, etype, x, y, s, fill, stroke, opacity)

    def _render_element_dispatch(self, draw, elem, etype, x, y, s, fill, stroke, opacity=255):
        """Dispatch to the correct draw method based on element type."""

        # ── Alias table: map alternative names to canonical types ──
        ALIAS = {
            "seagull": "bird", "bird_flock": "bird", "flying_bird": "bird",
            "drifting_cloud": "cloud", "cloud_small": "cloud", "storm_cloud": "cloud",
            "sunrise": "sun", "dawn": "sun", "morning": "sun", "sunset": "sun", "twilight": "sun",
            "full_moon": "moon",
            "human_silhouette": "human", "silhouette": "human", "shadow_figure": "human",
            "cliff": "mountain", "canyon": "mountain", "valley": "mountain",
            "dune": "hill", "sand_dune": "hill",
            "snowflake": "snow", "raindrop": "rain",
            "spark": "star", "sparkle": "star", "glowing_eye": "star",
            "falling_leaf": "leaf", "drifting_leaf": "leaf",
            "floating_ember": "fire", "campfire": "fire", "bonfire": "fire", "flickering_torch": "torch",
            "palm_tree": "tree", "pine_tree": "tree", "dead_tree": "tree",
            "grass_patch": "grass", "blowing_grass": "grass",
            "moving_wave": "wave", "flowing_river": "river",
            "running_animal": "animal", "animal_track": "footprint",
            "shrub": "bush", "berry_bush": "bush",
            "lantern_glow": "lamp", "lantern": "lamp", "torch_glow": "torch",
            "window_light": "window",
            "cave_entrance": "cave", "hidden_path": "path",
            "ancient_ruin": "building", "ruin": "building", "abandoned_house": "building", "house": "building",
            "sealed_door": "door", "gateway": "gate",
            "forgotten_map": "map", "map_table": "map",
            "thought_bubble": "lightbulb", "answer_mark": "question_mark",
            "magnifying_glass": "microscope",
            "paw_print": "footprint",
            "cracked_stone": "rock", "leaf_pile": "leaf",
            "smoke_column": "smoke",
            "drifting_log": "log", "log": "tree",
            "shark_fin": "shark",
            "fish_school": "fish",
            "shipwreck": "ship", "sail_ship": "ship",
            "skull_flag": "flag",
            "horseman": "horse",
            "fallen_weapon": "sword",
            "watchtower": "tower",
            "thought_bubble": "lightbulb",
            "puzzle_piece": "puzzle",
            "marching_group": "crowd_small",
            "village_people": "crowd_small",
            "marketplace": "market_stall",
            "wood": "tree",
            "plank": "wall",
            "stone": "rock",
            "brick": "rect",
            "cobblestone": "path",
            "signpost": "flag",
            "wheelbarrow": "cart",
            "story": "book",
            "tale": "book",
            "legend": "book",
            "myth": "book",
        }
        resolved = ALIAS.get(etype, etype)

        if resolved != etype:
            # Recursive call with resolved type, preserving all params
            elem = dict(elem)
            elem["type"] = resolved
            return self._render_element_dispatch(draw, elem, resolved, x, y, s, fill, stroke, opacity)

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
            skin = self._tc(elem.get("skin_color", (235, 200, 175))) or (235, 200, 175)
            mood = elem.get("mood", self.desc.get("mood", "peaceful"))
            pose = elem.get("pose", "standing")
            self.draw_human(draw, x, y, s, c, skin, gender="neutral", mood=mood, pose=pose)
        elif etype == "man":
            c = fill or (70, 50, 100)
            skin = self._tc(elem.get("skin_color", (235, 200, 175))) or (235, 200, 175)
            mood = elem.get("mood", self.desc.get("mood", "peaceful"))
            pose = elem.get("pose", "standing")
            self.draw_human(draw, x, y, s, c, skin, gender="man", mood=mood, pose=pose)
        elif etype == "woman":
            c = fill or (140, 80, 120)
            skin = self._tc(elem.get("skin_color", (230, 190, 170))) or (230, 190, 170)
            mood = elem.get("mood", self.desc.get("mood", "peaceful"))
            pose = elem.get("pose", "standing")
            self.draw_human(draw, x, y, s, c, skin, gender="woman", mood=mood, pose=pose)
        elif etype == "child":
            c = fill or (100, 140, 180)
            skin = self._tc(elem.get("skin_color", (240, 210, 190))) or (240, 210, 190)
            mood = elem.get("mood", self.desc.get("mood", "peaceful"))
            pose = elem.get("pose", "standing")
            self.draw_human(draw, x, y, s * 0.65, c, skin, gender="child", mood=mood, pose=pose)

        elif etype == "house":
            c = fill or (180, 150, 120)
            roof = self._tc(elem.get("roof_color", (150, 50, 40))) or (150, 50, 40)
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

        # ── Space ──
        elif etype == "planet":
            self.draw_planet(draw, x, y, s, fill or (80, 140, 200))
        elif etype == "blackhole":
            self.draw_blackhole(draw, x, y, s, fill or (0, 0, 0))
        elif etype == "galaxy":
            self.draw_galaxy(draw, x, y, s, fill or (60, 20, 80))
        elif etype == "star":
            self.draw_star(draw, x, y, s, fill or (255, 255, 200))
        elif etype == "asteroid":
            self.draw_asteroid(draw, x, y, s, fill or (120, 110, 100))

        # ── Weather ──
        elif etype == "snow":
            self.draw_snow(draw, x, y, s, fill or (230, 240, 250))
        elif etype == "rain":
            self.draw_rain(draw, x, y, s, fill or (180, 200, 230))
        elif etype == "lightning":
            self.draw_lightning(draw, x, y, s, fill or (255, 230, 50))
        elif etype == "storm":
            self.draw_storm(draw, x, y, s, fill or (60, 60, 80))
        elif etype == "fog":
            self.draw_fog(draw, x, y, s, fill or (200, 210, 220))
        elif etype == "desert":
            self.draw_desert(draw, x, y, s, fill or (220, 190, 120))

        # ── Science / Tech ──
        elif etype == "brain":
            self.draw_brain(draw, x, y, s, fill or (200, 180, 200))
        elif etype == "computer":
            self.draw_computer(draw, x, y, s, fill or (30, 45, 80))
        elif etype == "network":
            self.draw_network(draw, x, y, s, fill or (60, 200, 120))
        elif etype == "ai":
            self.draw_ai(draw, x, y, s, fill or (100, 200, 255))
        elif etype == "circuit":
            self.draw_circuit(draw, x, y, s, fill or (80, 220, 140))
        elif etype == "data":
            self.draw_data(draw, x, y, s, fill or (20, 25, 40))
        elif etype == "microscope":
            self.draw_microscope(draw, x, y, s, fill or (180, 200, 230))
        elif etype == "experiment":
            self.draw_experiment(draw, x, y, s, fill or (100, 200, 150))

        elif etype == "grass":
            self.draw_grass(draw, x, y, s, fill or (50, 130, 50))

        # ── Generic primitives (fallback) ──

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
            bc = self._tc(elem.get("bg_color")) or (255, 250, 240)
            border = self._tc(elem.get("border_color")) or self._tc(stroke) or (40, 35, 30)
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
            # ellipse is forbidden — skip; no generic oval shapes
            pass

        elif etype == "x_mark":
            c = fill or (180, 40, 40)
            l = 12 * s
            self.draw_line(draw, x-l, y-l, x+l, y+l, color=c, width=int(3*s+1), opacity=opacity)
            self.draw_line(draw, x+l, y-l, x-l, y+l, color=c, width=int(3*s+1), opacity=opacity)

        elif etype == "ship":
            self.draw_ship(draw, x, y, s, fill or (80, 60, 40), self._tc(elem.get("sail_color", (220, 210, 190))))

        elif etype == "wave":
            self.draw_wave(draw, x, y, s, fill or (40, 100, 180))

        elif etype == "canoe":
            self.draw_canoe(draw, x, y, s, fill or (80, 55, 35))
        elif etype == "kayak":
            self.draw_kayak(draw, x, y, s, fill or (60, 80, 120))
        elif etype == "raft":
            self.draw_raft(draw, x, y, s, fill or (100, 80, 50))
        elif etype == "pirate_ship":
            self.draw_pirate_ship(draw, x, y, s, fill or (60, 40, 30))
        elif etype == "galleon":
            self.draw_galleon(draw, x, y, s, fill or (70, 50, 35))

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
            bw = int(elem.get("width", 0.12) * self.w) if "width" in elem else int(40 * s)
            bh = int(elem.get("height", 0.25) * self.h) if "height" in elem else int(60 * s)
            c = fill or (120, 100, 80)
            wc = self._tc(elem.get("window_color", (255, 220, 100))) or (255, 220, 100)
            self.draw_building(draw, x, y, bw, bh, c, wc)

        elif etype == "factory":
            bw = int(elem.get("width", 0.15) * self.w)
            bh = int(elem.get("height", 0.22) * self.h)
            self.draw_factory(draw, x, y, bw, bh, fill or (130, 110, 90),
                              self._tc(elem.get("window_color", (200, 180, 100))) or (200, 180, 100))

        elif etype == "shop":
            bw = int(elem.get("width", 0.12) * self.w)
            bh = int(elem.get("height", 0.2) * self.h)
            self.draw_shop(draw, x, y, bw, bh, fill or (180, 150, 120),
                           self._tc(elem.get("window_color", (255, 240, 200))) or (255, 240, 200))

        elif etype == "cannon":
            c = fill or (60, 60, 60)
            self.draw_cannon(draw, x, y, s, c)

        elif etype == "wall":
            c = fill or (140, 120, 100)
            self.draw_wall(draw, x, y, s, c)

        elif etype == "tent":
            c = fill or (160, 140, 100)
            self.draw_tent(draw, x, y, s, c)

        elif etype == "chain":
            c = fill or (100, 90, 80)
            self.draw_chain(draw, x, y, s, c)

        elif etype == "tower":
            c = fill or (130, 110, 90)
            self.draw_tower(draw, x, y, s, c)

        elif etype == "fortress":
            c = fill or (120, 100, 80)
            self.draw_fortress(draw, x, y, s, c)

        elif etype == "soldier":
            c = fill or (140, 60, 60)
            self.draw_soldier(draw, x, y, s, c)

        elif etype == "alien":
            c = fill or (80, 200, 120)
            self.draw_alien(draw, x, y, s, c)

        elif etype == "artifact":
            c = fill or (100, 255, 200)
            self.draw_artifact(draw, x, y, s, c)

        elif etype == "candle":
            c = fill or (255, 220, 180)
            self.draw_candle(draw, x, y, s, c)

        elif etype == "flag":
            c = fill or (200, 50, 50)
            self.draw_flag(draw, x, y, s, c)

        elif etype == "animal":
            c = fill or (100, 80, 60)
            self.draw_animal(draw, x, y, s, c)

        elif etype == "asteroid":
            c = fill or (200, 100, 40)
            self.draw_asteroid(draw, x, y, s, c)

        elif etype == "crater":
            c = fill or (100, 80, 60)
            self.draw_crater(draw, x, y, s, c)

        elif etype == "skeleton":
            c = fill or (220, 200, 180)
            self.draw_skeleton(draw, x, y, s, c)

        elif etype == "crocodile":
            c = fill or (60, 130, 50)
            self.draw_crocodile(draw, x, y, s, c)

        elif etype == "dinosaur":
            c = fill or (80, 100, 60)
            self.draw_dinosaur(draw, x, y, s, c)

        elif etype == "horse":
            c = fill or (140, 100, 70)
            self.draw_horse(draw, x, y, s, c)

        elif etype == "elephant":
            c = fill or (130, 130, 140)
            self.draw_elephant(draw, x, y, s, c)

        elif etype == "dog":
            c = fill or (180, 140, 100)
            self.draw_dog(draw, x, y, s, c)

        elif etype == "cat":
            c = fill or (200, 160, 120)
            pose = elem.get("pose", "standing")
            mood = elem.get("mood", self.desc.get("mood", None))
            self.draw_cat(draw, x, y, s, c, pose=pose, mood=mood)

        elif etype == "bear":
            c = fill or (120, 80, 60)
            self.draw_bear(draw, x, y, s, c)

        elif etype == "deer":
            c = fill or (180, 140, 100)
            self.draw_deer(draw, x, y, s, c)

        elif etype == "rabbit":
            c = fill or (200, 180, 170)
            self.draw_rabbit(draw, x, y, s, c)

        elif etype == "cow":
            c = fill or (240, 230, 220)
            self.draw_cow(draw, x, y, s, c)

        elif etype in ("pyramid", "step_pyramid"):
            c = fill or (180, 150, 120)
            self.draw_pyramid(draw, x, y, s, c, steps=elem.get("steps", 3))

        elif etype == "egyptian_pyramid":
            c = fill or (200, 175, 130)
            self.draw_egyptian_pyramid(draw, x, y, s, c)

        elif etype == "sphinx":
            c = fill or (190, 165, 120)
            self.draw_sphinx(draw, x, y, s, c)

        elif etype == "mummy_cat":
            c = fill or (220, 210, 190)
            self.draw_mummy_cat(draw, x, y, s, c)

        elif etype == "egyptian_art":
            c = fill or (200, 170, 100)
            self.draw_egyptian_art(draw, x, y, s, c)

        elif etype == "granary":
            c = fill or (170, 150, 110)
            self.draw_granary(draw, x, y, s, c)

        elif etype == "cat_statue":
            c = fill or (50, 45, 35)
            self.draw_cat_statue(draw, x, y, s, c)

        elif etype in ("temple", "mayan_temple"):
            c = fill or (160, 130, 100)
            self.draw_temple(draw, x, y, s, c)

        elif etype == "leaf":
            c = fill or (100, 160, 60)
            self.draw_leaf(draw, x, y, s, c)

        elif etype == "throne":
            c = fill or (140, 100, 70)
            self.draw_throne(draw, x, y, s, c)

        elif etype == "cracked_ground":
            self.draw_cracked_ground(draw, x, y, elem.get("width", 1.0), elem.get("height", 1.0))

        elif etype == "basket":
            c = fill or (160, 140, 100)
            self.draw_basket(draw, x, y, s, c)

        elif etype == "dragon":
            c = fill or (60, 120, 60)
            self.draw_dragon(draw, x, y, s, c)

        elif etype == "snake":
            c = fill or (80, 140, 60)
            self.draw_snake(draw, x, y, s, c)

        elif etype == "turtle":
            c = fill or (80, 140, 60)
            self.draw_turtle(draw, x, y, s, c)

        elif etype == "giraffe":
            c = fill or (220, 180, 100)
            self.draw_giraffe(draw, x, y, s, c)

        elif etype == "camel":
            c = fill or (190, 160, 120)
            self.draw_camel(draw, x, y, s, c)

        elif etype == "rhino":
            c = fill or (130, 120, 110)
            self.draw_rhino(draw, x, y, s, c)

        elif etype == "hippo":
            c = fill or (150, 130, 140)
            self.draw_hippo(draw, x, y, s, c)

        elif etype == "monkey":
            c = fill or (140, 110, 80)
            self.draw_monkey(draw, x, y, s, c)

        elif etype == "squirrel":
            c = fill or (160, 120, 80)
            self.draw_squirrel(draw, x, y, s, c)

        elif etype == "lizard":
            c = fill or (100, 160, 80)
            self.draw_lizard(draw, x, y, s, c)

        elif etype == "frog":
            c = fill or (80, 160, 60)
            self.draw_frog(draw, x, y, s, c)

        elif etype == "goat":
            c = fill or (200, 170, 140)
            self.draw_goat(draw, x, y, s, c)

        elif etype == "sheep":
            c = fill or (240, 235, 230)
            self.draw_sheep(draw, x, y, s, c)

        elif etype == "pig":
            c = fill or (240, 200, 180)
            self.draw_pig(draw, x, y, s, c)

        elif etype == "rat":
            c = fill or (160, 140, 130)
            self.draw_rat(draw, x, y, s, c)

        elif etype == "beaver":
            c = fill or (140, 110, 80)
            self.draw_beaver(draw, x, y, s, c)

        elif etype == "otter":
            c = fill or (140, 110, 100)
            self.draw_otter(draw, x, y, s, c)

        elif etype == "hedgehog":
            c = fill or (150, 120, 90)
            self.draw_hedgehog(draw, x, y, s, c)

        elif etype == "bat":
            c = fill or (60, 50, 45)
            self.draw_bat(draw, x, y, s, c)

        elif etype == "kangaroo":
            c = fill or (180, 140, 100)
            self.draw_kangaroo(draw, x, y, s, c)

        elif etype == "sloth":
            c = fill or (140, 120, 100)
            self.draw_sloth(draw, x, y, s, c)

        elif etype == "raccoon":
            c = fill or (150, 140, 130)
            self.draw_raccoon(draw, x, y, s, c)

        elif etype == "skunk":
            c = fill or (40, 35, 30)
            self.draw_skunk(draw, x, y, s, c)

        elif etype in ("werewolf", "vampire", "zombie", "golem", "troll", "orc",
                        "minotaur", "satyr", "fairy", "elf", "dwarf",
                        "giant", "ogre", "goblin", "gnome", "sprite", "nymph",
                        "fantasy_creature"):
            c = fill or (100, 80, 60)
            self.draw_fantasy_creature(draw, x, y, s, c)

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

        elif etype == "fern":
            c = fill or (60, 130, 50)
            self.draw_fern(draw, x, y, s, c)

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
            w = int(elem.get("width", 20))
            self.draw_path(draw, x, y, int(x2), int(y2), c, w)

        elif etype in ("book", "newspaper", "magazine", "journal"):
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
        elif etype == "world_map":
            self.draw_world_map(draw, x, y, s, fill or (220, 200, 160))
        elif etype == "india_map":
            self.draw_india_map(draw, x, y, s, fill or (140, 180, 100))

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

        elif etype in ("glacier", "glaciers"):
            self.draw_glacier(draw, x, y, s, fill or (200, 220, 240))

        elif etype in ("iceberg", "icebergs"):
            self.draw_iceberg(draw, x, y, s, fill or (210, 225, 245))

        elif etype in ("shadow_figure", "silhouette", "shadow_man"):
            self.draw_shadow_figure(draw, x, y, s, fill or (20, 25, 30))

        elif etype in ("moon_path", "moonlight_path", "moon_reflection"):
            self.draw_moon_path(draw, x, y, s, fill or (200, 210, 230))

        elif etype == "jar":
            self.draw_jar(draw, x, y, s, fill or (200, 210, 220))

        elif etype == "shelf":
            self.draw_shelf(draw, x, y, s, fill or (120, 90, 60))

        # ── Household items ──
        elif etype in ("chair", "stool", "bench"):
            self.draw_chair(draw, x, y, s, fill or (120, 90, 60))
        elif etype in ("table", "desk", "counter"):
            if etype == "desk":
                self.draw_desk(draw, x, y, s, fill or (130, 90, 50))
            else:
                self.draw_table(draw, x, y, s, fill or (140, 100, 60))
        elif etype in ("sofa", "couch", "settee"):
            self.draw_sofa(draw, x, y, s, fill or (160, 80, 80))
        elif etype in ("bed", "bunk", "cot"):
            self.draw_bed(draw, x, y, s, fill or (180, 160, 140))
        elif etype in ("cupboard", "cabinet", "wardrobe"):
            self.draw_cupboard(draw, x, y, s, fill or (160, 130, 100))
        elif etype in ("fridge", "refrigerator"):
            self.draw_fridge(draw, x, y, s, fill or (240, 240, 245))
        elif etype in ("oven", "stove", "range", "cooker"):
            self.draw_oven(draw, x, y, s, fill or (220, 220, 225))
        elif etype in ("sink", "basin"):
            self.draw_sink(draw, x, y, s, fill or (220, 230, 240))
        elif etype in ("toilet", "commode"):
            self.draw_toilet(draw, x, y, s, fill or (240, 240, 245))
        elif etype in ("bathtub", "tub", "bath"):
            self.draw_bathtub(draw, x, y, s, fill or (230, 235, 240))
        elif etype in ("mirror", "glass"):
            self.draw_mirror(draw, x, y, s, fill or (200, 210, 225))
        elif etype in ("curtain", "drape", "drapes"):
            self.draw_curtain(draw, x, y, s, fill or (180, 140, 160))
        elif etype in ("pillow", "cushion"):
            self.draw_pillow(draw, x, y, s, fill or (255, 250, 240))
        elif etype in ("door", "gateway"):
            self.draw_door(draw, x, y, s, fill or (160, 130, 100))
        elif etype in ("window", "casement"):
            self.draw_window(draw, x, y, s, fill or (200, 220, 240))
        elif etype in ("bike", "bicycle", "motorcycle", "scooter"):
            self.draw_bike(draw, x, y, s, fill or (60, 60, 70))
        elif etype == "car":
            self.draw_car(draw, x, y, s, fill or (150, 80, 80))
        elif etype in ("train", "locomotive", "railway", "railroad_car"):
            self.draw_train(draw, x, y, s, fill or (80, 40, 40))

        elif etype in ("island", "isle"):
            r = 15*s
            self.draw_circle(draw, x, y, r, fill=(180,200,100,200), stroke=(100,140,60,180), stroke_width=2)
            self.draw_circle(draw, x-3*s, y-3*s, r*0.4, fill=(80,160,80,200))
            self.draw_ellipse(draw, x-r, y+2*s, r*2, r*0.3, fill=(180,200,220,150))

        # ── Horse aliases ──
        elif etype in ("horse", "pony", "stallion", "mare", "foal", "mustang",
                        "clydesdale", "thoroughbred", "palomino", "zebra", "donkey",
                        "mule", "unicorn", "centaur"):
            self.draw_horse(draw, x, y, s, fill or (140, 100, 70))

        # ── Elephant / Mammoth aliases ──
        elif etype in ("elephant", "calf", "tusker"):
            self.draw_elephant(draw, x, y, s, fill or (130, 130, 140))
        elif etype == "mammoth":
            self.draw_mammoth(draw, x, y, s, fill or (150, 130, 100))

        # ── Dog aliases ──
        elif etype in ("dog", "puppy", "hound", "poodle", "terrier", "beagle",
                        "retriever", "shepherd", "wolf", "fox", "hyena"):
            self.draw_dog(draw, x, y, s, fill or (180, 140, 100))

        # ── Cat aliases ──
        elif etype in ("cat", "kitten", "lion", "tiger", "leopard", "panther",
                        "jaguar", "cheetah", "lynx", "bobcat", "cougar", "puma"):
            self.draw_cat(draw, x, y, s, fill or (200, 160, 120))

        # ── Bear aliases ──
        elif etype in ("bear", "panda", "koala"):
            self.draw_bear(draw, x, y, s, fill or (120, 80, 60))

        # ── Deer aliases ──
        elif etype in ("deer", "moose", "elk", "reindeer", "caribou", "antelope"):
            self.draw_deer(draw, x, y, s, fill or (180, 140, 100))

        # ── Rabbit aliases ──
        elif etype in ("rabbit", "bunny", "hare"):
            self.draw_rabbit(draw, x, y, s, fill or (200, 180, 170))

        # ── Cow aliases ──
        elif etype in ("cow", "bull", "ox", "bison", "buffalo", "yak"):
            self.draw_cow(draw, x, y, s, fill or (240, 230, 220))

        # ── Dragon aliases ──
        elif etype in ("dragon", "griffin", "phoenix", "chimera", "wyvern",
                        "hydra", "basilisk", "pegasus"):
            self.draw_dragon(draw, x, y, s, fill or (60, 120, 60))

        # ── Snake aliases ──
        elif etype in ("snake", "serpent", "python", "cobra", "viper", "worm"):
            self.draw_snake(draw, x, y, s, fill or (80, 140, 60))

        # ── Turtle aliases ──
        elif etype in ("turtle", "tortoise", "terrapin"):
            self.draw_turtle(draw, x, y, s, fill or (80, 140, 60))

        # ── Giraffe aliases ──
        elif etype in ("giraffe", "okapi"):
            self.draw_giraffe(draw, x, y, s, fill or (220, 180, 100))

        # ── Camel aliases ──
        elif etype in ("camel", "dromedary", "bactrian"):
            self.draw_camel(draw, x, y, s, fill or (190, 160, 120))

        # ── Rhino aliases ──
        elif etype in ("rhino", "rhinoceros"):
            self.draw_rhino(draw, x, y, s, fill or (130, 120, 110))

        # ── Hippo aliases ──
        elif etype in ("hippo", "hippopotamus"):
            self.draw_hippo(draw, x, y, s, fill or (150, 130, 140))

        # ── Monkey aliases ──
        elif etype in ("monkey", "ape", "gorilla", "chimp", "chimpanzee", "orangutan", "baboon"):
            self.draw_monkey(draw, x, y, s, fill or (140, 110, 80))

        # ── Squirrel aliases ──
        elif etype in ("squirrel", "chipmunk", "groundhog"):
            self.draw_squirrel(draw, x, y, s, fill or (160, 120, 80))

        # ── Lizard aliases ──
        elif etype in ("lizard", "gecko", "iguana", "chameleon", "salamander", "newt"):
            self.draw_lizard(draw, x, y, s, fill or (100, 160, 80))

        # ── Frog aliases ──
        elif etype in ("frog", "toad", "tadpole"):
            self.draw_frog(draw, x, y, s, fill or (80, 160, 60))

        # ── Goat aliases ──
        elif etype in ("goat", "ibex", "ram"):
            self.draw_goat(draw, x, y, s, fill or (200, 170, 140))

        # ── Sheep aliases ──
        elif etype in ("sheep", "lamb"):
            self.draw_sheep(draw, x, y, s, fill or (240, 235, 230))

        # ── Pig aliases ──
        elif etype in ("pig", "hog", "boar", "sow"):
            self.draw_pig(draw, x, y, s, fill or (240, 200, 180))

        # ── Rat / mouse aliases ──
        elif etype in ("rat", "mouse", "hamster", "gerbil", "vole"):
            self.draw_rat(draw, x, y, s, fill or (160, 140, 130))

        # ── Beaver aliases ──
        elif etype in ("beaver", "muskrat"):
            self.draw_beaver(draw, x, y, s, fill or (140, 110, 80))

        # ── Otter aliases ──
        elif etype in ("otter", "mink", "ferret", "weasel"):
            self.draw_otter(draw, x, y, s, fill or (140, 110, 100))

        # ── Hedgehog aliases ──
        elif etype in ("hedgehog", "porcupine"):
            self.draw_hedgehog(draw, x, y, s, fill or (150, 120, 90))

        # ── Bat aliases ──
        elif etype in ("bat", "vampire_bat"):
            self.draw_bat(draw, x, y, s, fill or (60, 50, 45))

        # ── Kangaroo aliases ──
        elif etype in ("kangaroo", "wallaby", "joey"):
            self.draw_kangaroo(draw, x, y, s, fill or (180, 140, 100))

        # ── Sloth aliases ──
        elif etype in ("sloth", "anteater"):
            self.draw_sloth(draw, x, y, s, fill or (140, 120, 100))

        # ── Raccoon aliases ──
        elif etype in ("raccoon", "coati"):
            self.draw_raccoon(draw, x, y, s, fill or (150, 140, 130))

        # ── Skunk aliases ──
        elif etype in ("skunk", "badger"):
            self.draw_skunk(draw, x, y, s, fill or (40, 35, 30))

        # ── Animal aliases ──
        elif etype in ("beast", "monster", "creature", "animal"):
            self.draw_animal(draw, x, y, s, fill or (100, 80, 60))

        # ── Fantasy creature aliases ──
        elif etype in ("werewolf", "vampire", "zombie", "golem", "troll", "orc",
                        "minotaur", "satyr", "fairy", "elf", "dwarf",
                        "giant", "ogre", "goblin", "gnome", "sprite", "nymph",
                        "fantasy_creature"):
            self.draw_fantasy_creature(draw, x, y, s, fill or (100, 80, 60))

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
                        "pyramid", "lighthouse", "church",
                        "monument", "shrine", "tomb", "dome", "column",
                        "gate", "wall", "bridge", "ruin", "statue",
                        "barn", "stable", "silo", "well", "fountain",
                        "cabin", "hut", "shelter", "tent", "pavilion"):
            bw = int(elem.get("width", 0.12) * self.w)
            bh = int(elem.get("height", 0.25) * self.h)
            self.draw_building(draw, x, y, bw, bh, fill or (120, 100, 80),
                              window_color=self._tc(elem.get("window_color", (255, 220, 100))) or (255, 220, 100))
        elif etype == "windmill":
            self.draw_windmill(draw, x, y, s, fill or (150, 130, 110))

        elif etype in ("factory", "mill", "refinery", "warehouse"):
            bw = int(elem.get("width", 0.15) * self.w)
            bh = int(elem.get("height", 0.22) * self.h)
            self.draw_factory(draw, x, y, bw, bh, fill or (130, 110, 90),
                              self._tc(elem.get("window_color", (200, 180, 100))) or (200, 180, 100))

        elif etype in ("shop", "store", "market", "bakery", "cafe",
                        "restaurant", "pharmacy", "bookshop", "boutique"):
            bw = int(elem.get("width", 0.12) * self.w)
            bh = int(elem.get("height", 0.2) * self.h)
            self.draw_shop(draw, x, y, bw, bh, fill or (180, 150, 120),
                           self._tc(elem.get("window_color", (255, 240, 200))) or (255, 240, 200))

        # ── Ship / boat aliases ──
        elif etype in ("boat", "sailboat", "vessel", "raft",
                        "kayak", "rowboat", "warship", "galleon"):
            self.draw_ship(draw, x, y, s, fill or (80, 60, 40),
                          self._tc(elem.get("sail_color", (220, 210, 190))))

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
            self.draw_heart(draw, x, y, s=int(40 * s), color=fill)
        elif etype == "smartphone":
            self.draw_smartphone(draw, x, y, size=s, color=fill or (30, 30, 35))
        elif etype == "camera":
            self.draw_camera(draw, x, y, size=s, color=fill or (60, 55, 50))
        elif etype == "tv_monitor":
            self.draw_tv_monitor(draw, x, y, size=s, color=fill or (40, 40, 45))
        elif etype == "cat_toy":
            self.draw_cat_toy(draw, x, y, size=s, color=fill or (200, 80, 50))
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
            self.draw_astronaut(draw, x, y, s=s, color=fill)
        elif etype == "spaceship":
            s = elem.get("scale", 1.0)
            self.draw_spaceship(draw, x, y, s=s, color=fill)
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

        # ── Narrator characters in scene ──
        elif etype == "ding":
            s = elem.get("scale", 1.0)
            c = fill or (200, 200, 210)
            self.draw_scene_ding(draw, x, y, s, c)

        elif etype == "dong":
            s = elem.get("scale", 1.0)
            c = fill or (200, 200, 210)
            self.draw_scene_dong(draw, x, y, s, c)

        elif etype == "think_owl":
            s = elem.get("scale", 1.0)
            c = fill or (200, 200, 210)
            self.draw_scene_think(draw, x, y, s, c)

        elif etype == "book":
            c = fill or (160, 120, 80)
            title = elem.get("title", "")
            self.draw_book(draw, x, y, size=s, color=c, title=title)

        elif etype == "footprint":
            c = fill or (100, 90, 100)
            self.draw_footprint(draw, x, y, size=s, color=c)

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

        elif etype == "bell":
            self.draw_bell(draw, x, y, s, fill or (200, 180, 100))
        elif etype == "cactus":
            self.draw_cactus(draw, x, y, s, fill or (50, 140, 50))
        elif etype == "castle":
            self.draw_castle(draw, x, y, s, fill or (130, 110, 90))
        elif etype == "chest":
            self.draw_chest(draw, x, y, s, fill or (140, 90, 50))
        elif etype == "food":
            self.draw_food(draw, x, y, s, fill or (220, 180, 100))
        elif etype == "furniture":
            self.draw_furniture(draw, x, y, s, fill or (140, 110, 80))
        elif etype == "pottery":
            self.draw_pottery(draw, x, y, s, fill or (180, 140, 100))
        elif etype == "question":
            self.draw_question(draw, x, y, s, fill or (180, 60, 60))
        elif etype == "tool":
            self.draw_tool(draw, x, y, s, fill or (150, 130, 110))
        elif etype == "vehicle":
            self.draw_vehicle(draw, x, y, s, fill or (140, 100, 100))
        else:
            # Unknown type — skip silently, no generic oval/shape fallback
            pass

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

    def draw_astronaut(self, draw, x, y, s=1.0, color=None):
        c = color or (220, 220, 230)
        hs = int(14 * s)  # helmet size
        self.draw_circle(draw, x, y - int(2 * s), hs, fill=c + (200,), stroke=(160, 160, 170, 200), stroke_width=2)
        self.draw_rect(draw, x - hs, y, int(2 * hs), int(22 * s), fill=c + (200,), stroke=(160, 160, 170, 200), stroke_width=2, rx=2)
        # Visor
        self.draw_circle(draw, x - int(hs * 0.35), y - int(4 * s), int(hs * 0.35), fill=(100, 140, 200, 180))
        self.draw_circle(draw, x + int(hs * 0.35), y - int(4 * s), int(hs * 0.35), fill=(100, 140, 200, 180))
        # Boots
        self.draw_rect(draw, x - int(hs * 0.7), y + int(22 * s), int(hs * 0.6), int(6 * s), fill=c + (180,), stroke=(160, 160, 170, 150), stroke_width=1, rx=1)
        self.draw_rect(draw, x + int(hs * 0.1), y + int(22 * s), int(hs * 0.6), int(6 * s), fill=c + (180,), stroke=(160, 160, 170, 150), stroke_width=1, rx=1)
        # Backpack
        self.draw_rect(draw, x + hs - 2, y + int(2 * s), int(6 * s), int(14 * s), fill=(180, 190, 200, 200), stroke=(140, 150, 160, 150), stroke_width=1)

    def draw_spaceship(self, draw, x, y, s=1.0, color=None):
        c = color or (160, 180, 210)
        ws = int(24 * s)
        self.draw_ellipse(draw, x - ws, y - int(ws * 0.25), int(2 * ws), int(ws * 0.45), fill=c + (200,), stroke=(120, 140, 180, 200), stroke_width=2)
        # Cockpit
        self.draw_ellipse(draw, x - int(ws * 0.3), y - int(ws * 0.3), int(ws * 0.35), int(ws * 0.25), fill=(100, 160, 255, 150), stroke=(80, 120, 200, 150), stroke_width=1)
        # Engine flame
        self.draw_polygon(draw, [(x, y + int(ws * 0.35)), (x - int(ws * 0.2), y + int(ws * 0.55)), (x + int(ws * 0.2), y + int(ws * 0.55))], fill=(200, 100, 60, 200))
        # Wings
        self.draw_polygon(draw, [(x - ws, y - int(ws * 0.05)), (x - int(ws * 1.1), y + int(ws * 0.15)), (x - ws, y + int(ws * 0.1))], fill=c + (180,))
        self.draw_polygon(draw, [(x + ws, y - int(ws * 0.05)), (x + int(ws * 1.1), y + int(ws * 0.15)), (x + ws, y + int(ws * 0.1))], fill=c + (180,))

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
        """Draw a realistic whale (side view, facing right)."""
        s = max(size, 0.3)
        c = tuple(color[:3])
        bl = int(50 * s)
        bh = int(18 * s)
        # Body profile polygon (teardrop: blunt head, tapered tail)
        body_pts = []
        steps = 24
        for i in range(steps + 1):
            t = i / steps
            # x: -bl/2 (tail) to +bl/2 (head)
            px = x - bl//2 + t * bl
            # y: ellipse-like height, but biased toward head
            angle = math.pi * t
            ry = bh // 2 * (math.sin(angle) ** 0.7)
            if t < 0.35:
                ry = ry * (1 + 0.3 * (1 - t / 0.35))
            py = y - ry
            body_pts.append((int(px), int(py)))
        # Bottom half (mirror-ish)
        for i in range(steps, -1, -1):
            t = i / steps
            px = x - bl//2 + t * bl
            angle = math.pi * t
            ry = bh // 2 * (math.sin(angle) ** 0.7)
            if t < 0.35:
                ry = ry * (1 + 0.3 * (1 - t / 0.35))
            py = y + ry
            body_pts.append((int(px), int(py)))
        self.draw_shadow(draw, [(body_pts[0][0], body_pts[0][1] + 2)] + [(bx, by + 2) for bx, by in body_pts[1:]],
                         offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
        self.draw_polygon(draw, body_pts, fill=c + (220,), stroke=self._darken(c, 20) + (180,), stroke_width=1)
        # Belly (lighter underside strip)
        belly_pts = body_pts[len(body_pts)//2:] + body_pts[:len(body_pts)//2]
        belly_pts = [(bx, y + int(6 * s)) for bx in (x - bl//2, x + bl//3)]
        self.draw_ellipse(draw, x, y + int(6 * s), int(28 * s), int(6 * s),
                         fill=self._lighten(c, 40) + (160,))
        # Tail flukes
        tail_x = x - bl//2
        tail_c = self._darken(c, 15)
        self.draw_polygon(draw, [(tail_x, y), (tail_x - int(12 * s), y - int(10 * s)),
                                 (tail_x - int(4 * s), y - int(3 * s))],
                         fill=tail_c + (200,), stroke=self._darken(tail_c, 20) + (160,), stroke_width=1)
        self.draw_polygon(draw, [(tail_x, y), (tail_x - int(12 * s), y + int(10 * s)),
                                 (tail_x - int(4 * s), y + int(3 * s))],
                         fill=tail_c + (200,), stroke=self._darken(tail_c, 20) + (160,), stroke_width=1)
        # Dorsal fin
        df_x = x - int(3 * s)
        df_y = y - int(9 * s)
        self.draw_polygon(draw, [(df_x, df_y), (df_x - int(3 * s), df_y - int(5 * s)),
                                 (df_x + int(4 * s), df_y + int(2 * s))],
                         fill=c + (200,), stroke=self._darken(c, 20) + (160,), stroke_width=1)
        # Pectoral fin
        pf_x = x + int(8 * s)
        pf_y = y + int(9 * s)
        self.draw_polygon(draw, [(pf_x, pf_y), (pf_x - int(6 * s), pf_y + int(6 * s)),
                                 (pf_x + int(3 * s), pf_y + int(1 * s))],
                         fill=self._darken(c, 10) + (180,))
        # Eye
        self.draw_circle(draw, x + int(16 * s), y - int(5 * s), int(2 * s), fill=(20, 25, 30, 220))
        # Mouth line
        draw.arc([int(x + 8 * s), int(y - 2 * s), int(x + 18 * s), int(y + 4 * s)],
                 -20, 90, fill=(40, 35, 30, 150), width=1)
        # Blow spout
        spout_x = x + int(4 * s)
        spout_y = y - int(9 * s)
        for i in range(5):
            sx = spout_x + (i - 2) * int(3 * s)
            sy = spout_y - int(4 * s) - i * int(1.5 * s)
            draw.ellipse([sx - int(1.5 * s), sy - int(1.5 * s),
                         sx + int(1.5 * s), sy + int(1.5 * s)],
                        fill=(220, 235, 250, 150))

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

    # ── Space / Universe ──────────────────────────────────────────
    def draw_planet(self, draw, x, y, size=1.0, color=(80, 140, 200)):
        s = max(size, 0.3); c = tuple(color[:3])
        r = int(20 * s)
        self.draw_shadow_circle(draw, x, y+r, r, offset=(3,2), blur_radius=4, color=(0,0,0,40))
        self.draw_circle(draw, x, y, r, fill=c+(200,), stroke=self._darken(c,20)+(180,), stroke_width=2)
        for i in range(3):
            by = y - r + int(r * 0.3 * (i+1))
            bw = int((r*2 - abs(by-y)*1.2) * 0.7)
            if bw > 4:
                self.draw_line(draw, x-bw//2, by, x+bw//2, by, color=self._lighten(c,20)+(60,), width=int(1.5*s))
        self.draw_arc(draw, x, y, int(r*1.6), 200, 340, color=self._lighten(c,30)+(120,), width=int(3*s))
        self.draw_arc(draw, x, y, int(r*1.3), 200, 340, color=(200,200,200,80), width=int(2*s))
        self.draw_circle(draw, x-int(r*0.3), y-int(r*0.3), int(r*0.3), fill=(255,255,255,30))

    def draw_blackhole(self, draw, x, y, size=1.0, color=(0, 0, 0)):
        s = max(size, 0.3)
        r = int(25 * s)
        self.draw_shadow_circle(draw, x, y+r, r, offset=(3,2), blur_radius=6, color=(0,0,0,60))
        for i in range(5, 0, -1):
            self.draw_circle(draw, x, y, r + i*3, fill=(200, 80, 180, 10 + i*15))
        self.draw_circle(draw, x, y, r, fill=(5, 5, 15, 230), stroke=(180, 60, 160, 150), stroke_width=2)
        self.draw_ellipse(draw, x-r*2, y+int(r*0.3), 4*r, int(r*1.2), fill=(255, 200, 100, 40),
                         stroke=(255, 150, 50, 100), stroke_width=1)
        self.draw_ellipse(draw, x-r*2, y+int(r*0.2), 4*r, int(r*0.8), fill=(200, 100, 255, 30),
                         stroke=(200, 80, 200, 80), stroke_width=1)
        for ang in [45, 135, 225, 315]:
            ex = x + int(r*1.3 * math.cos(ang * math.pi/180))
            ey = y + int(r*1.3 * math.sin(ang * math.pi/180))
            self.draw_circle(draw, ex, ey, 2*s, fill=(255, 200, 255, 100))

    def draw_galaxy(self, draw, x, y, size=1.0, color=(60, 20, 80)):
        s = max(size, 0.3); c = tuple(color[:3])
        w = int(80 * s); h = int(30 * s)
        self.draw_ellipse(draw, x-w//2, y-h//2, w, h, fill=c+(30,), stroke=(255,255,255,15), stroke_width=1)
        for arm in range(2):
            angle_offset = arm * math.pi
            pts = []
            for t in range(30):
                a = angle_offset + t * 0.3
                rad = int(3*s + t * 1.5*s)
                px = x + int(rad * math.cos(a))
                py = y + int(rad * math.sin(a) * 0.4)
                pts.append((px, py))
            for i in range(len(pts)-1):
                self.draw_line(draw, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                               color=self._lighten(c,40)+(100,), width=int(1.5*s))
        self.draw_circle(draw, x, y, int(8*s), fill=(255, 220, 150, 80))
        self.draw_circle(draw, x, y, int(4*s), fill=(255, 255, 200, 120))
        for _ in range(20):
            sx = x + int(self.rng.randint(-w//2, w//2))
            sy = y + int(self.rng.randint(-h//2, h//2))
            self.draw_circle(draw, sx, sy, max(1, int(0.5*s)), fill=(255,255,255,self.rng.randint(30,150)))

    def draw_star(self, draw, x, y, size=1.0, color=(255, 255, 200)):
        s = max(size, 0.3); c = tuple(color[:3])
        if s < 0.5:
            self.draw_circle(draw, x, y, max(1, int(2*s)), fill=c+(200,))
            return
        r = int(6 * s)
        pts = []
        for i in range(10):
            a = -math.pi/2 + i * math.pi/5
            rad = r if i % 2 == 0 else int(r * 0.4)
            pts.append((x + int(rad * math.cos(a)), y + int(rad * math.sin(a))))
        self.draw_polygon(draw, pts, fill=c+(200,), stroke=self._darken(c,20)+(180,), stroke_width=1)

    def draw_asteroid(self, draw, x, y, size=1.0, color=(120, 110, 100)):
        s = max(size, 0.3); c = tuple(color[:3])
        r = int(6 * s)
        pts = []
        for i in range(8):
            a = i * math.pi/4 + self.rng.random()*0.3
            rr = r * (0.6 + self.rng.random()*0.4)
            pts.append((x + int(rr * math.cos(a)), y + int(rr * math.sin(a))))
        self.draw_polygon(draw, pts, fill=c+(200,), stroke=self._darken(c,25)+(150,), stroke_width=1)
        self.draw_circle(draw, x-int(r*0.2), y-int(r*0.2), int(r*0.3), fill=(80,80,80,80))

    # ── Weather ───────────────────────────────────────────────────
    def draw_snow(self, draw, x, y, size=1.0, color=(230, 240, 250)):
        s = max(size, 0.3); c = tuple(color[:3])
        fr = int(6 * s)
        for i in range(6):
            a = i * math.pi/3
            ex = x + int(fr * math.cos(a))
            ey = y + int(fr * math.sin(a))
            self.draw_line(draw, x, y, ex, ey, color=c+(200,), width=max(1, int(1.5*s)))
            ba = a + math.pi/6
            bx = ex + int(fr*0.5 * math.cos(ba))
            by = ey + int(fr*0.5 * math.sin(ba))
            self.draw_line(draw, ex, ey, bx, by, color=c+(160,), width=1)
            ba2 = a - math.pi/6
            bx2 = ex + int(fr*0.5 * math.cos(ba2))
            by2 = ey + int(fr*0.5 * math.sin(ba2))
            self.draw_line(draw, ex, ey, bx2, by2, color=c+(160,), width=1)
        self.draw_circle(draw, x, y, int(1.5*s), fill=c+(220,))

    def draw_rain(self, draw, x, y, size=1.0, color=(180, 200, 230)):
        s = max(size, 0.3); c = tuple(color[:3])
        for i in range(8):
            rx = x + int(self.rng.randint(-15, 15) * s)
            ry = y + int(self.rng.randint(-12, 12) * s)
            length = int(5*s + self.rng.random()*3*s)
            self.draw_line(draw, rx, ry, rx-2*s, ry+length, color=tuple(c)+(max(40,200-i*20),), width=max(1, int(1.2*s)))

    def draw_lightning(self, draw, x, y, size=1.0, color=(255, 230, 50)):
        s = max(size, 0.3); c = tuple(color[:3])
        pts = [(x, y-int(20*s))]
        cx, cy = x, y-int(20*s)
        for _ in range(5):
            cx += int(self.rng.randint(-6, 4) * s)
            cy += int(4 * s + self.rng.random()*3*s)
            pts.append((cx, cy))
        pts.append((cx+int(self.rng.randint(-3, 3)*s), cy+int(6*s)))
        for ptx, pty in pts:
            self.draw_circle(draw, ptx, pty, 5*s, fill=(255, 200, 50, 40))
        for i in range(len(pts)-1):
            self.draw_line(draw, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                          color=c+(230,), width=max(2, int(2.5*s)))

    def draw_storm(self, draw, x, y, size=1.0, color=(60, 60, 80)):
        s = max(size, 0.3); c = tuple(color[:3])
        r = int(30 * s)
        self.draw_circle(draw, x, y, r, fill=c+(100,))
        self.draw_circle(draw, x-int(10*s), y-int(8*s), int(r*0.7), fill=self._darken(c,10)+(120,))
        self.draw_circle(draw, x+int(12*s), y-int(5*s), int(r*0.6), fill=self._darken(c,5)+(110,))
        for t in range(20):
            a = t * 0.4
            rad = int(3*s + t * 1.2*s)
            sx = x + int(rad * math.cos(a))
            sy = y + int(rad * math.sin(a) * 0.5)
            self.draw_circle(draw, sx, sy, max(1, int(1.5*s)), fill=(200,200,220,80))
        for _ in range(6):
            rx = x + int(self.rng.randint(-r, r))
            ry = y + int(self.rng.randint(0, r))
            self.draw_line(draw, rx, ry, rx-1*s, ry+8*s, color=(180,190,220,80), width=1)

    def draw_fog(self, draw, x, y, size=1.0, color=(200, 210, 220)):
        s = max(size, 0.3); c = tuple(color[:3])
        for i in range(6):
            fy = y - int(15*s) + i * int(6*s)
            fw = int(40*s - i*4*s)
            fh = int(3*s + self.rng.random()*2*s)
            self.draw_ellipse(draw, x-fw//2, fy-fh//2, fw, fh, fill=tuple(c)+(max(15, 60-i*8),), stroke=None, stroke_width=0)

    def draw_desert(self, draw, x, y, size=1.0, color=(220, 190, 120)):
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(40*s), int(24*s)
        self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=(200,170,140,200), stroke=(150,120,90,100), stroke_width=1)
        self.draw_circle(draw, x, y-h//2+6*s, 6*s, fill=(255,200,80,200), stroke=(200,160,40,180), stroke_width=1)
        for i in range(4):
            dy = y - h//2 + int(12*s) + i * int(4*s)
            dm = int(15*s - i*3*s)
            pts = [(x-dm, dy), (x-dm//2, dy-3*s-i*s), (x, dy-2*s), (x+dm//2, dy-4*s-i*s), (x+dm, dy)]
            self.draw_polygon(draw, pts, fill=(180+i*10, 160+i*8, 100+i*5, 180),
                            stroke=self._darken(c,20)+(120,), stroke_width=1)
        cx, cy = x-w//2+6*s, y+h//2-6*s
        self.draw_rect(draw, cx-1*s, cy-6*s, 2*s, 6*s, fill=(60,100,40,200))
        self.draw_rect(draw, cx-4*s, cy-5*s, 3*s, 1.5*s, fill=(60,100,40,200))
        self.draw_rect(draw, cx+1*s, cy-5*s, 3*s, 1.5*s, fill=(60,100,40,200))

    def draw_grass(self, draw, x, y, size=1.0, color=(50, 130, 50)):
        s = max(size, 0.3); c = tuple(color[:3])
        for i in range(8):
            gx = x + int((self.rng.random()-0.5) * 20*s)
            gy = y + int((self.rng.random()-0.5) * 4*s)
            gh = int(4*s + self.rng.random()*3*s)
            variant = self.rng.randint(-10, 10)
            gc = (max(0,min(255,c[0]+variant)), max(0,min(255,c[1]+variant)), max(0,min(255,c[2]+variant)), 180)
            self.draw_line(draw, gx, gy, gx+int((self.rng.random()-0.5)*3*s), gy-gh,
                          color=gc, width=max(1, int(1.2*s)))

    # ── Science / Technology ──────────────────────────────────────
    def draw_brain(self, draw, x, y, size=1.0, color=(200, 180, 200)):
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(30*s), int(22*s)
        self.draw_shadow_circle(draw, x, y+h//2, w//2, offset=(2,2), blur_radius=4, color=(0,0,0,30))
        lpts = [(x-2*s, y-h//2), (x-w//2-2*s, y-h//4), (x-w//2, y+h//4), (x-2*s, y+h//2)]
        self.draw_polygon(draw, lpts, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        rpts = [(x+2*s, y-h//2), (x+w//2+2*s, y-h//4), (x+w//2, y+h//4), (x+2*s, y+h//2)]
        self.draw_polygon(draw, rpts, fill=self._lighten(c,10)+(200,), stroke=self._darken(c,15)+(150,), stroke_width=1)
        self.draw_line(draw, x, y-h//2, x, y+h//2, color=self._darken(c,25)+(120,), width=1)
        for side, ox in [(-1, -1), (1, 1)]:
            for i in range(4):
                fy = y - h//2 + int(h*0.4) + i * int(h*0.15)
                fx = x + ox * int(3*s + i*2*s)
                self.draw_line(draw, x+ox*2*s, fy, fx, fy, color=self._darken(c,20)+(80,), width=1)

    def draw_computer(self, draw, x, y, size=1.0, color=(30, 45, 80)):
        s = max(size, 0.3); c = tuple(color[:3])
        mw, mh = int(24*s), int(18*s)
        self.draw_rect(draw, x-mw//2, y-mh//2, mw, mh, fill=c+(200,), stroke=self._lighten(c,40)+(180,), stroke_width=1)
        self.draw_rect(draw, x-mw//2+2*s, y-mh//2+2*s, mw-4*s, mh-6*s, fill=(40, 60, 100, 220))
        self.draw_rect(draw, x-2*s, y-4*s, 4*s, 3*s, fill=(60, 140, 220, 150))
        self.draw_rect(draw, x-2*s, y+mh//2, 4*s, 3*s, fill=c+(180,), stroke=self._darken(c,15)+(120,), stroke_width=1)
        self.draw_rect(draw, x-5*s, y+mh//2+3*s, 10*s, 2*s, fill=c+(180,), stroke=self._darken(c,15)+(120,), stroke_width=1)
        kw, kh = int(20*s), int(4*s)
        self.draw_rect(draw, x-kw//2, y+mh//2+7*s, kw, kh, fill=(40,40,50,200), stroke=(60,60,70,150), stroke_width=1)

    def draw_network(self, draw, x, y, size=1.0, color=(60, 200, 120)):
        s = max(size, 0.3); c = tuple(color[:3])
        nodes = [(x, y-int(12*s)), (x-int(12*s), y+int(8*s)), (x+int(12*s), y+int(8*s))]
        for i, j in [(0, 1), (0, 2), (1, 2)]:
            self.draw_line(draw, nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1],
                          color=self._lighten(c,20)+(100,), width=int(1.5*s))
        for nx, ny in nodes:
            self.draw_circle(draw, nx, ny, 4*s, fill=c+(200,), stroke=self._lighten(c,30)+(180,), stroke_width=1)
            self.draw_circle(draw, nx, ny, 1.5*s, fill=(255,255,255,120))

    def draw_ai(self, draw, x, y, size=1.0, color=(100, 200, 255)):
        s = max(size, 0.3); c = tuple(color[:3])
        self.draw_circle(draw, x, y, 8*s, fill=c+(180,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        for i in range(3):
            a = i * 2.1
            self.draw_line(draw, x+int(3*s*math.cos(a)), y+int(3*s*math.sin(a)),
                          x+int(6*s*math.cos(a)), y+int(6*s*math.sin(a)),
                          color=self._darken(c,20)+(100,), width=1)
        for ang, dist in [(0.3, 10), (2.5, 11), (4.0, 9)]:
            sx = x + int(dist*s * math.cos(ang))
            sy = y + int(dist*s * math.sin(ang))
            self.draw_line(draw, sx-2*s, sy, sx+2*s, sy, color=(255,255,200,180), width=1)
            self.draw_line(draw, sx, sy-2*s, sx, sy+2*s, color=(255,255,200,180), width=1)

    def draw_circuit(self, draw, x, y, size=1.0, color=(80, 220, 140)):
        s = max(size, 0.3); c = tuple(color[:3])
        w, h = int(30*s), int(24*s)
        self.draw_rect(draw, x-w//2, y-h//2, w, h, fill=(20, 30, 20, 200), stroke=self._lighten(c,20)+(100,), stroke_width=1)
        for i in range(4):
            ty = y - h//2 + int(5*s) + i * int(5*s)
            self.draw_line(draw, x-w//2+3*s, ty, x+w//2-3*s, ty, color=c+(180,), width=1)
        for i in range(5):
            tx = x - w//2 + int(4*s) + i * int(6*s)
            self.draw_line(draw, tx, y-h//2+3*s, tx, y+h//2-3*s, color=c+(180,), width=1)
        for i in range(4):
            for j in range(3):
                nx = x - w//2 + int(5*s) + i * int(7*s)
                ny = y - h//2 + int(5*s) + j * int(7*s)
                self.draw_circle(draw, nx, ny, 1.5*s, fill=self._lighten(c,30)+(200,))

    def draw_data(self, draw, x, y, size=1.0, color=(20, 25, 40)):
        s = max(size, 0.3); c = tuple(color[:3])
        dw, dh = int(20*s), int(20*s)
        self.draw_rect(draw, x-dw//2, y-dh//2+int(4*s), dw, dh-int(8*s), fill=c+(200,), stroke=self._lighten(c,30)+(150,), stroke_width=1)
        self.draw_ellipse(draw, x-dw//2, y-dh//2, dw, int(8*s), fill=self._lighten(c,15)+(220,), stroke=self._lighten(c,40)+(180,), stroke_width=1)
        self.draw_ellipse(draw, x-dw//2, y+dh//2-int(4*s), dw, int(8*s), fill=c+(200,), stroke=self._lighten(c,20)+(150,), stroke_width=1)
        for i in range(3):
            ly = y - dh//2 + int(6*s) + i * int(5*s)
            self.draw_line(draw, x-dw//2+2*s, ly, x+dw//2-2*s, ly, color=self._lighten(c,40)+(60,), width=1)

    def draw_microscope(self, draw, x, y, size=1.0, color=(180, 200, 230)):
        s = max(size, 0.3); c = tuple(color[:3])
        self.draw_rect(draw, x-int(15*s), y+int(6*s), 30*s, 3*s, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)
        self.draw_rect(draw, x-int(2*s), y-int(20*s), 4*s, 26*s, fill=c+(220,), stroke=self._darken(c,15)+(150,), stroke_width=1)
        self.draw_rect(draw, x-int(4*s), y-int(24*s), 8*s, 6*s, fill=self._lighten(c,10)+(200,), stroke=self._darken(c,15)+(150,), stroke_width=1, rx=1)
        self.draw_rect(draw, x-int(1.5*s), y+int(2*s), 3*s, 4*s, fill=(60,60,70,200))
        self.draw_rect(draw, x-int(8*s), y+int(6*s), 16*s, 2*s, fill=(100,100,110,200), stroke=(80,80,90,150), stroke_width=1)
        self.draw_rect(draw, x-int(8*s), y+int(6*s), 3*s, 1*s, fill=(60,60,70,200))
        self.draw_rect(draw, x+5*s, y+int(6*s), 3*s, 1*s, fill=(60,60,70,200))
        self.draw_circle(draw, x, y+int(12*s), 4*s, fill=(200,200,220,100), stroke=(150,150,180,100), stroke_width=1)

    def draw_experiment(self, draw, x, y, size=1.0, color=(100, 200, 150)):
        s = max(size, 0.3); c = tuple(color[:3])
        pts = [(x-int(5*s), y-int(10*s)), (x+int(5*s), y-int(10*s)),
               (x+int(8*s), y+int(2*s)), (x+int(3*s), y+int(12*s)),
               (x-int(3*s), y+int(12*s)), (x-int(8*s), y+int(2*s))]
        self.draw_polygon(draw, pts, fill=(200,220,230,180), stroke=(80,120,160,150), stroke_width=1)
        liq = [(x-int(7*s), y+int(4*s)), (x+int(7*s), y+int(4*s)),
               (x+int(3*s), y+int(12*s)), (x-int(3*s), y+int(12*s))]
        self.draw_polygon(draw, liq, fill=c+(160,), stroke=None, stroke_width=0)
        for _ in range(3):
            bx = x + int(self.rng.randint(-4, 4) * s)
            by = y + int(6*s + self.rng.random()*4*s)
            self.draw_circle(draw, bx, by, 1.5*s, fill=(255,255,255,120))
        self.draw_line(draw, x-int(5*s), y-int(10*s), x+int(5*s), y-int(10*s), color=(100,120,140,180), width=int(1.5*s))

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

    def draw_glacier(self, draw, x, y, size=1.0, color=(200, 220, 240)):
        """Draw a jagged glacier / ice cliff."""
        s = size * 30
        cx, cy = x, y
        pts = []
        segments = 8
        for i in range(segments + 1):
            angle = -math.pi * (0.3 + 0.4 * i / segments)
            r = s * (0.7 + self.rng.random() * 0.3)
            px = cx + int(r * math.cos(angle))
            py = cy + int(r * math.sin(angle))
            if i == 0 or i == segments:
                py = cy + int(s * 1.1)
            pts.append((px, py))
        self.draw_polygon(draw, pts, fill=color, stroke=(180, 200, 220, 200), stroke_width=2)

        # Snow cap / highlight
        cap = []
        for i in range(segments // 2 + 1):
            angle = -math.pi * (0.3 + 0.4 * i / segments)
            r = s * (0.5 + self.rng.random() * 0.15)
            px = cx + int(r * math.cos(angle))
            py = cy + int(r * math.sin(angle))
            cap.append((px, py))
        if len(cap) > 2:
            self.draw_polygon(draw, cap, fill=(230, 240, 255, 180), stroke=None)

    def draw_iceberg(self, draw, x, y, size=1.0, color=(210, 225, 245)):
        """Draw a floating iceberg with underwater portion."""
        s = size * 25
        cx, cy = x, y
        top = []
        segs = 6
        for i in range(segs + 1):
            angle = -math.pi * (0.25 + 0.5 * i / segs)
            r = s * (0.6 + self.rng.random() * 0.4)
            px = cx + int(r * math.cos(angle))
            py = cy + int(r * math.sin(angle)) - int(s * 0.3)
            if i == 0 or i == segs:
                py = cy + int(s * 0.1)
            top.append((px, py))
        self.draw_polygon(draw, top, fill=(230, 240, 255), stroke=(190, 210, 230, 180), stroke_width=1)

        # Underwater portion (darker)
        under = []
        for i in range(segs + 1):
            angle = math.pi * (0.25 + 0.5 * i / segs)
            r = s * (0.7 + self.rng.random() * 0.5)
            px = cx + int(r * math.cos(angle))
            py = cy + int(r * math.sin(angle)) + int(s * 0.4)
            if i == 0 or i == segs:
                py = cy + int(s * 0.1)
            under.append((px, py))
        if len(under) > 2:
            self.draw_polygon(draw, under, fill=(160, 190, 215, 180), stroke=None)

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

    # ── Household items ────────────────────────────────────────

    def draw_chair(self, draw, x, y, size=1.0, color=(120, 90, 60)):
        s = max(size, 0.5); c = tuple(color[:3])
        w, h = int(70*s), int(90*s)
        # Backrest
        bw = int(55*s)
        bx = x - bw//2
        self.draw_rect(draw, bx, y-h, bw, int(55*s), fill=self._lighten(c,10), stroke=self._darken(c,20), stroke_width=1)
        # Seat
        seat_w = int(60*s)
        self.draw_rect(draw, x-seat_w//2, y-int(35*s), seat_w, int(8*s), fill=self._lighten(c,15), stroke=self._darken(c,20), stroke_width=1)
        # Front legs
        for off in [-int(25*s), int(25*s)]:
            self.draw_line(draw, x+off, y-int(27*s), x+off, y, color=self._darken(c,15), width=max(int(3*s), 2))
        # Back legs (slightly inset)
        for off in [-int(18*s), int(18*s)]:
            self.draw_line(draw, x+off, y-int(27*s), x+off, y+int(5*s), color=self._darken(c,25), width=max(int(2*s), 1))
        # Crossbar
        cy = y - int(12*s)
        self.draw_line(draw, x-int(25*s), cy, x+int(25*s), cy, color=self._darken(c,20), width=max(int(2*s), 1))

    def draw_table(self, draw, x, y, size=1.0, color=(140, 100, 60)):
        s = max(size, 0.5); c = tuple(color[:3])
        tw = int(100*s)
        tt = int(8*s)
        # Top
        self.draw_rect(draw, x-tw//2, y-int(70*s), tw, tt, fill=self._lighten(c,15), stroke=self._darken(c,20), stroke_width=1)
        # Legs
        for off in [-int(40*s), int(40*s)]:
            self.draw_line(draw, x+off, y-int(62*s), x+off, y, color=self._darken(c,20), width=max(int(3*s), 2))
        # Crossbar
        cy = y - int(25*s)
        self.draw_line(draw, x-int(40*s), cy, x+int(40*s), cy, color=self._darken(c,15), width=max(int(2*s), 1))

    def draw_sofa(self, draw, x, y, size=1.0, color=(160, 80, 80)):
        s = max(size, 0.5); c = tuple(color[:3])
        sw = int(100*s)
        sh = int(40*s)
        # Back
        self.draw_rect(draw, x-sw//2, y-sh-int(30*s), sw, int(30*s), fill=self._darken(c,5), stroke=self._darken(c,20), stroke_width=1)
        # Seat base
        self.draw_rect(draw, x-sw//2, y-sh, sw, sh, fill=self._lighten(c,10), stroke=self._darken(c,20), stroke_width=1)
        # Armrests
        for ax in [x-sw//2, x+sw//2-int(12*s)]:
            self.draw_rect(draw, ax, y-sh-int(20*s), int(12*s), sh+int(20*s), fill=self._darken(c,10), stroke=self._darken(c,25), stroke_width=1)
        # Cushions
        for i in range(3):
            cx = x - sw//2 + int(12*s) + i * int(28*s)
            self.draw_rect(draw, cx, y-sh+3, int(24*s), sh-6, fill=self._lighten(c,15), stroke=self._darken(c,15), stroke_width=1)
        # Legs
        for off in [-int(45*s), int(45*s)]:
            self.draw_rect(draw, x+off, y, int(5*s), int(8*s), fill=self._darken(c,25))

    def draw_bed(self, draw, x, y, size=1.0, color=(180, 160, 140)):
        s = max(size, 0.5); c = tuple(color[:3])
        bw = int(110*s)
        bh = int(50*s)
        # Headboard
        self.draw_rect(draw, x-bw//2, y-bh-int(15*s), int(10*s), bh+int(15*s), fill=self._darken(c,15), stroke=self._darken(c,30), stroke_width=1)
        # Mattress
        self.draw_rect(draw, x-bw//2+int(8*s), y-bh, bw-int(8*s), bh, fill=self._lighten(c,10), stroke=self._darken(c,20), stroke_width=1)
        # Pillow
        self.draw_rect(draw, x-bw//2+int(12*s), y-bh+4, int(20*s), int(12*s), fill=(255,250,240,200), stroke=(200,195,190,180), stroke_width=1)
        # Blanket
        self.draw_rect(draw, x-bw//2+int(35*s), y-bh+4, bw-int(43*s), bh-8, fill=self._lighten(c,20), stroke=self._darken(c,15), stroke_width=1)
        # Legs
        for off in [-int(45*s), int(45*s)]:
            self.draw_rect(draw, x+off, y, int(4*s), int(6*s), fill=self._darken(c,25))

    def draw_desk(self, draw, x, y, size=1.0, color=(130, 90, 50)):
        s = max(size, 0.5); c = tuple(color[:3])
        dw = int(90*s)
        dt = int(6*s)
        # Top
        self.draw_rect(draw, x-dw//2, y-int(60*s), dw, dt, fill=self._lighten(c,15), stroke=self._darken(c,20), stroke_width=1)
        # Drawer
        self.draw_rect(draw, x-dw//2+4, y-int(40*s), dw-8, int(10*s), fill=self._lighten(c,10), stroke=self._darken(c,20), stroke_width=1)
        self.draw_circle(draw, x, y-int(35*s), 2, fill=(180,160,100,200))
        # Legs
        for off in [-int(38*s), int(38*s)]:
            self.draw_line(draw, x+off, y-int(54*s), x+off, y, color=self._darken(c,20), width=max(int(3*s), 2))

    def draw_cupboard(self, draw, x, y, size=1.0, color=(160, 130, 100)):
        s = max(size, 0.5); c = tuple(color[:3])
        cw = int(60*s)
        ch = int(90*s)
        # Body
        self.draw_rect(draw, x-cw//2, y-ch, cw, ch, fill=self._lighten(c,10), stroke=self._darken(c,20), stroke_width=1)
        # Top molding
        self.draw_rect(draw, x-cw//2-3, y-ch, cw+6, int(5*s), fill=self._darken(c,10), stroke=self._darken(c,25), stroke_width=1)
        # Doors
        for side in [-1, 1]:
            dx = x + side * cw//4
            self.draw_rect(draw, dx-3, y-ch+8, cw//2-4, ch-10, fill=self._lighten(c,15), stroke=self._darken(c,20), stroke_width=1)
            self.draw_circle(draw, dx+side*3, y-ch//2, 2, fill=(180,160,100,200))

    def draw_fridge(self, draw, x, y, size=1.0, color=(240, 240, 245)):
        s = max(size, 0.5); c = tuple(color[:3])
        fw = int(55*s)
        fh = int(100*s)
        # Body
        self.draw_rect(draw, x-fw//2, y-fh, fw, fh, fill=c+(200,), stroke=(180,180,185,200), stroke_width=1)
        # Top door
        self.draw_rect(draw, x-fw//2+3, y-fh+5, fw-6, int(42*s), fill=self._lighten(c,5), stroke=(180,180,185,180), stroke_width=1)
        # Bottom door
        self.draw_rect(draw, x-fw//2+3, y-int(48*s), fw-6, int(43*s), fill=self._lighten(c,5), stroke=(180,180,185,180), stroke_width=1)
        # Handles
        for hy in [y-fh+8, y-int(48*s)+4]:
            self.draw_rect(draw, x+fw//2-8, hy, 4, int(5*s), fill=(150,150,150,200))

    def draw_oven(self, draw, x, y, size=1.0, color=(220, 220, 225)):
        s = max(size, 0.5); c = tuple(color[:3])
        ow = int(70*s)
        oh = int(80*s)
        # Body
        self.draw_rect(draw, x-ow//2, y-oh, ow, oh, fill=c+(200,), stroke=(180,180,185,200), stroke_width=1)
        # Burners
        for bx in [x-3, x+3]:
            self.draw_circle(draw, bx*s, y-oh+5, int(10*s), fill=(50,50,55,150))
        # Door
        self.draw_rect(draw, x-ow//2+4, y-int(35*s), ow-8, int(30*s), fill=(200,200,205,200), stroke=(160,160,165,180), stroke_width=1)
        # Handle
        self.draw_rect(draw, x-ow//2+6, y-int(35*s)-3, ow-12, 3, fill=(150,150,150,200))

    def draw_sink(self, draw, x, y, size=1.0, color=(220, 230, 240)):
        s = max(size, 0.5); c = tuple(color[:3])
        sw = int(80*s)
        sh = int(40*s)
        # Counter
        self.draw_rect(draw, x-sw//2, y-sh, sw, sh, fill=c+(200,), stroke=(180,190,200,200), stroke_width=1)
        # Basin
        self.draw_rect(draw, x-int(15*s), y-sh+6, int(30*s), sh-12, fill=(200,210,220,200), stroke=(170,180,190,180), stroke_width=1)
        # Faucet
        self.draw_line(draw, x, y-sh, x, y-sh-int(15*s), color=(180,180,190,200), width=max(int(2*s), 1))
        self.draw_arc(draw, x, y-sh-int(15*s), int(10*s), 0, 180, color=(180,180,190,200), width=max(int(2*s), 1))

    def draw_toilet(self, draw, x, y, size=1.0, color=(240, 240, 245)):
        s = max(size, 0.5); c = tuple(color[:3])
        # Tank
        self.draw_rect(draw, x-int(18*s), y-int(70*s), int(36*s), int(25*s), fill=c+(200,), stroke=(180,180,185,200), stroke_width=1)
        # Bowl
        self.draw_ellipse(draw, x-int(22*s), y-int(40*s), int(44*s), int(35*s), fill=c+(200,), stroke=(180,180,185,200), stroke_width=1)
        # Seat
        self.draw_ellipse(draw, x-int(14*s), y-int(35*s), int(28*s), int(22*s), fill=(220,220,225,200), stroke=(180,180,185,180), stroke_width=1)
        # Flush
        self.draw_rect(draw, x-int(8*s), y-int(72*s), int(16*s), int(4*s), fill=(200,200,210,200))

    def draw_bathtub(self, draw, x, y, size=1.0, color=(230, 235, 240)):
        s = max(size, 0.5); c = tuple(color[:3])
        tw = int(100*s)
        th = int(45*s)
        # Tub body
        self.draw_rect(draw, x-tw//2, y-th, tw, th, fill=c+(200,), stroke=(180,190,200,200), stroke_width=1)
        # Inner
        self.draw_rect(draw, x-tw//2+4, y-th+4, tw-8, th-8, fill=(200,210,220,180), stroke=(170,180,190,150), stroke_width=1)
        # Feet
        for fx in [x-tw//2+6, x+tw//2-6]:
            self.draw_circle(draw, fx, y, int(5*s), fill=(180,160,120,200))

    def draw_mirror(self, draw, x, y, size=1.0, color=(200, 210, 225)):
        s = max(size, 0.5); c = tuple(color[:3])
        mw = int(50*s)
        mh = int(70*s)
        # Frame
        self.draw_rect(draw, x-mw//2, y-mh, mw, mh, fill=(160,140,120,200), stroke=(120,100,80,200), stroke_width=1)
        # Glass
        self.draw_rect(draw, x-mw//2+3, y-mh+3, mw-6, mh-6, fill=c+(180,), stroke=(180,190,205,150), stroke_width=1)
        # Reflection
        self.draw_line(draw, x-mw//2+6, y-mh+6, x-mw//2+20, y-mh+6, color=(255,255,255,80), width=2)

    def draw_curtain(self, draw, x, y, size=1.0, color=(180, 140, 160)):
        s = max(size, 0.5); c = tuple(color[:3])
        cw = int(80*s)
        ch = int(100*s)
        # Rod
        self.draw_line(draw, x-cw//2-6, y-ch, x+cw//2+6, y-ch, color=(100,90,80,200), width=max(int(3*s), 2))
        # Left panel
        self.draw_rect(draw, x-cw//2, y-ch+5, cw//2-4, ch-5, fill=c+(180,), stroke=self._darken(c,20), stroke_width=1)
        self.draw_line(draw, x-cw//2 + cw//4, y-ch+5, x-cw//2 + cw//4, y, color=self._darken(c,15)+(80,), width=1)
        # Right panel
        self.draw_rect(draw, x+4, y-ch+5, cw//2-4, ch-5, fill=c+(180,), stroke=self._darken(c,20), stroke_width=1)
        self.draw_line(draw, x+4 + cw//4, y-ch+5, x+4 + cw//4, y, color=self._darken(c,15)+(80,), width=1)

    def draw_pillow(self, draw, x, y, size=1.0, color=(255, 250, 240)):
        s = max(size, 0.5); c = tuple(color[:3])
        pw = int(60*s)
        ph = int(40*s)
        self.draw_ellipse(draw, x-pw//2, y-ph//2, pw, ph, fill=c+(200,), stroke=(200,195,190,180), stroke_width=1)
        self.draw_line(draw, x-ph//3, y-ph//2, x-ph//3, y+ph//2, color=(200,195,190,80), width=1)

    def draw_door(self, draw, x, y, size=1.0, color=(160, 130, 100)):
        s = max(size, 0.5); c = tuple(color[:3])
        dw = int(55*s)
        dh = int(100*s)
        # Frame
        self.draw_rect(draw, x-dw//2-3, y-dh, dw+6, dh, fill=self._darken(c,25), stroke=self._darken(c,35), stroke_width=1)
        # Door
        self.draw_rect(draw, x-dw//2+1, y-dh+2, dw-2, dh-2, fill=c+(200,), stroke=self._darken(c,20), stroke_width=1)
        # Panels
        for py in [y-dh+6, y-dh//2+2]:
            self.draw_rect(draw, x-dw//2+5, py, dw-10, dh//2-10, fill=self._lighten(c,10), stroke=self._darken(c,15), stroke_width=1)
        # Handle
        self.draw_circle(draw, x+dw//2-8, y-dh//2, 3, fill=(180,160,100,200))

    def draw_window(self, draw, x, y, size=1.0, color=(200, 220, 240)):
        s = max(size, 0.5); c = tuple(color[:3])
        ww = int(60*s)
        wh = int(80*s)
        # Frame
        self.draw_rect(draw, x-ww//2, y-wh, ww, wh, fill=(160,140,120,200), stroke=(120,100,80,200), stroke_width=1)
        # Glass
        self.draw_rect(draw, x-ww//2+3, y-wh+3, ww-6, wh-6, fill=c+(180,), stroke=(180,200,220,150), stroke_width=1)
        # Cross
        self.draw_line(draw, x, y-wh+3, x, y-3, color=(160,140,120,150), width=max(int(2*s), 1))
        self.draw_line(draw, x-ww//2+3, y-wh//2, x+ww//2-3, y-wh//2, color=(160,140,120,150), width=max(int(2*s), 1))
        # Sill
        self.draw_rect(draw, x-ww//2-4, y-3, ww+8, 4, fill=(140,120,100,200))

    def draw_bike(self, draw, x, y, size=1.0, color=(60, 60, 70)):
        """Draw a bicycle (side view)."""
        s = max(size, 0.5)
        c = tuple(color[:3])
        # Wheels
        wheel_r = int(3 * s)
        wheel_w = max(int(1.2 * s), 1)
        axle_spacing = int(7 * s)
        bx, fx = x - axle_spacing, x + axle_spacing
        by = fy = y
        draw.ellipse([bx - wheel_r, by - wheel_r, bx + wheel_r, by + wheel_r],
                     outline=c, width=wheel_w)
        draw.ellipse([fx - wheel_r, fy - wheel_r, fx + wheel_r, fy + wheel_r],
                     outline=c, width=wheel_w)
        # Spokes
        for cx, cy in [(bx, by), (fx, fy)]:
            draw.line([cx - wheel_r + 1, cy, cx + wheel_r - 1, cy], fill=c, width=1)
            draw.line([cx, cy - wheel_r + 1, cx, cy + wheel_r - 1], fill=c, width=1)
        # Frame (compact proportions)
        seat_x = x - int(1 * s)
        seat_y = y - int(6 * s)
        pedal_x = x
        pedal_y = y - int(2 * s)
        fw = max(int(1.5 * s), 1)
        draw.line([(bx, by), (pedal_x, pedal_y)], fill=c, width=fw)
        draw.line([(pedal_x, pedal_y), (seat_x, seat_y)], fill=c, width=fw)
        draw.line([(bx, by), (seat_x, seat_y)], fill=c, width=fw)
        head_x = fx
        head_y = seat_y
        draw.line([(seat_x, seat_y), (head_x, head_y)], fill=c, width=fw)
        head_bot_x = fx
        head_bot_y = y - int(1 * s)
        draw.line([(head_bot_x, head_bot_y), (pedal_x, pedal_y)], fill=c, width=fw)
        draw.line([(fx, fy), (head_bot_x, head_bot_y)], fill=c, width=fw)
        draw.line([(head_x, head_y), (head_bot_x, head_bot_y)], fill=c, width=fw)
        # Seat
        seat_pad = int(2 * s)
        draw.polygon([(seat_x - seat_pad, seat_y), (seat_x + seat_pad, seat_y),
                      (seat_x + seat_pad - 1, seat_y - int(s)),
                      (seat_x - seat_pad + 1, seat_y - int(s))],
                     fill=(80, 70, 60), outline=c, width=1)
        # Handlebars
        stem_top_y = head_y - int(2 * s)
        draw.line([(head_x, head_y), (head_x, stem_top_y)], fill=c, width=fw)
        draw.line([(head_x - int(3 * s), stem_top_y),
                   (head_x + int(2 * s), stem_top_y)], fill=c, width=fw)
        for gx in [head_x - int(3 * s), head_x + int(2 * s)]:
            draw.line([(gx, stem_top_y - int(s)), (gx, stem_top_y + int(s))],
                      fill=(40, 35, 30), width=int(1.5 * s))
        # Pedal
        draw.line([(pedal_x - int(1.5 * s), pedal_y),
                   (pedal_x + int(1.5 * s), pedal_y)], fill=c, width=int(1.5 * s))

    def draw_car(self, draw, x, y, size=1.0, color=(150, 80, 80)):
        """Draw a simple car."""
        s = max(size, 0.5)
        c = tuple(color[:3])
        cw = int(24 * s)
        ch = int(7 * s)
        # Shadow
        self.draw_shadow(draw, [(x - cw//2, y - ch//2), (x + cw//2, y - ch//2),
                                (x + cw//2, y + ch//2), (x - cw//2, y + ch//2)],
                         offset=(2, 3), blur_radius=3, color=(0, 0, 0, 25))
        # Body
        self.draw_rect(draw, x - cw//2, y - ch//2, cw, ch, fill=c, stroke=(40, 35, 30, 150), stroke_width=1)
        # Cabin
        cab_w = cw // 2
        cab_h = int(ch * 0.8)
        cab_y = y - ch//2 - int(0.4 * ch)
        self.draw_rect(draw, x - cab_w//2, cab_y, cab_w, cab_h, fill=(180, 200, 230, 200),
                      stroke=(40, 35, 30, 150), stroke_width=1)
        # Wheels
        wheel_r = int(1.5 * s)
        for wx in [x - cw//4, x + cw//4]:
            draw.ellipse([wx - wheel_r, y + ch//2 - wheel_r // 2,
                         wx + wheel_r, y + ch//2 + wheel_r],
                        fill=(30, 30, 30), outline=(60, 60, 60), width=1)

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
        """Apply final touches: paper grain, sketch stylization, vignette."""

        # ── Hand-drawn sketch stylization ──
        if self.hand_drawn and self.technique:
            tx = self.technique
            arr = np.array(canvas, dtype=np.float32)

            # 1. Darken dark lines (edge enhancement)
            gray = np.mean(arr[..., :3], axis=2)
            dark_mask = (gray < 80).astype(np.float32)
            for c in range(3):
                arr[..., c] = np.where(dark_mask > 0,
                                       arr[..., c] * (1.0 - tx["edge_strength"] * 0.3),
                                       arr[..., c])

            # 2. Paper grain + tint
            noise = np.random.RandomState(hash((self.w, self.h, 42)) & 0x7FFFFFFF) \
                .randint(0, max(1, int(tx["noise"] * 1.2)), (self.h, self.w)).astype(np.float32)
            paper_rgb = np.array(tx["paper_tint"], dtype=np.float32)
            for c in range(3):
                arr[..., c] = arr[..., c] * 0.92 + paper_rgb[c] * 0.08 + (noise - tx["noise"]/2) * 0.15
                arr[..., c] = np.clip(arr[..., c], 0, 255)

            # 3. Soften if technique calls for it
            if tx["blur_sigma"] > 0.01:
                blur_arr = np.copy(arr)
                from scipy.ndimage import gaussian_filter
                for c in range(3):
                    blur_arr[..., c] = gaussian_filter(arr[..., c], sigma=tx["blur_sigma"])
                arr = arr * 0.6 + blur_arr * 0.4

            canvas = Image.fromarray(arr.astype(np.uint8))

            # 4. Edge-darkening overlay (pen/pencil pressure simulation)
            if tx["edge_strength"] > 0.1:
                edge_arr = np.array(canvas.convert("L"), dtype=np.float32)
                from scipy.ndimage import sobel
                edge_x = sobel(edge_arr, axis=1)
                edge_y = sobel(edge_arr, axis=0)
                edge_mag = np.sqrt(edge_x**2 + edge_y**2)
                edge_mask = np.clip(edge_mag / (60.0 / tx["edge_strength"]), 0, 1)
                edge_overlay = np.ones((self.h, self.w, 3), dtype=np.float32) * 255
                for c in range(3):
                    edge_overlay[..., c] = np.where(
                        edge_mask > 0.3,
                        255 * (1 - edge_mask * 0.5 * tx["edge_strength"]),
                        255
                    )
                arr2 = np.array(canvas, dtype=np.float32)
                arr2_rgb = arr2[..., :3] * (edge_overlay / 255.0) * 0.85 + paper_rgb[None, None, :] * 0.15
                arr2_rgb = np.clip(arr2_rgb, 0, 255).astype(np.uint8)
                arr2 = np.dstack([arr2_rgb, arr2[..., 3:4].astype(np.uint8)]) if arr2.shape[2] == 4 else arr2_rgb
                canvas = Image.fromarray(arr2)

            return canvas

            return canvas

        # ── Original clean post-processing (non-hand-drawn) ──
        grain_intensity = style.get("grain", 0.04)
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
            haze = Image.new("RGBA", (self.w, self.h), (200, 210, 220, fog_alpha))
            canvas = Image.alpha_composite(canvas, haze)

        # Light sharpen for cleaner look (instead of blur)
        canvas = canvas.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=2))

        return canvas

    # ═══════════════════════════════════════════════════════════════
    # Narrator character silhouettes for story scenes
    # These are small background figures (Ding/Dong/Think)
    # ═══════════════════════════════════════════════════════════════

    def draw_scene_ding(self, draw, x, y, s=1.0, color=(200,200,210)):
        """Ding narrator silhouette — robed figure with scroll staff."""
        c = color
        s = int(30 * s)
        # Robe body (trapezoid)
        draw.ellipse([x-s//2, y-s, x+s//2, y+s], fill=c, outline=None)
        # Head
        head_r = s//3
        draw.ellipse([x-head_r, y-s-head_r, x+head_r, y-s+head_r], fill=(235,220,200), outline=None)
        # Scroll staff on right
        staff_x = x + s//2 + 2
        draw.line([staff_x, y-s, staff_x, y+s], fill=(180,160,140), width=max(2, s//10))
        # Scroll top
        draw.ellipse([staff_x-3, y-s-2, staff_x+3, y-s+4], fill=(220,200,180), outline=None)
        # Hood hint
        draw.arc([x-head_r, y-s-head_r, x+head_r, y-s+head_r], 0, 180, fill=(160,150,170), width=2)

    def draw_scene_dong(self, draw, x, y, s=1.0, color=(200,200,210)):
        """Dong narrator silhouette — gowned figure with mirror."""
        c = color
        s = int(30 * s)
        # Gown body
        draw.ellipse([x-s//2, y-s, x+s//2, y+s], fill=c, outline=None)
        # Head
        head_r = s//3
        draw.ellipse([x-head_r, y-s-head_r, x+head_r, y-s+head_r], fill=(220,195,180), outline=None)
        # Gown waist taper
        draw.polygon([x-s//2, y, x+s//2, y, x+s//2+4, y+s, x-s//2-4, y+s], fill=(180,170,190), outline=None)
        # Hair (longer)
        draw.ellipse([x-head_r-2, y-s, x+head_r+2, y-s+head_r//2], fill=(120,80,60), outline=None)
        # Mirror on left
        mir_x = x - s//2 - 6
        mir_r = s//4
        draw.ellipse([mir_x-mir_r, y-mir_r, mir_x+mir_r, y+mir_r], fill=(200,220,240), outline=(160,180,200), width=2)
        # Mirror handle
        draw.line([mir_x, y+mir_r, mir_x, y+mir_r+6], fill=(160,140,120), width=2)

    def draw_scene_think(self, draw, x, y, s=1.0, color=(200,200,210)):
        """Think owl narrator silhouette."""
        c = color
        s = int(25 * s)
        # Body (oval)
        draw.ellipse([x-s//2, y-s//2, x+s//2, y+s//2], fill=c, outline=None)
        # Head (round)
        head_r = s//3
        draw.ellipse([x-head_r, y-s//2-head_r, x+head_r, y-s//2+head_r], fill=c, outline=None)
        # Eye circles (large, wide)
        eye_r = max(3, s//8)
        draw.ellipse([x-s//4-eye_r, y-s//2-eye_r, x-s//4+eye_r, y-s//2+eye_r], fill=(255,240,200), outline=None)
        draw.ellipse([x+s//4-eye_r, y-s//2-eye_r, x+s//4+eye_r, y-s//2+eye_r], fill=(255,240,200), outline=None)
        # Pupils
        p_r = max(2, eye_r//2)
        draw.ellipse([x-s//4-p_r, y-s//2-p_r, x-s//4+p_r, y-s//2+p_r], fill=(60,40,20), outline=None)
        draw.ellipse([x+s//4-p_r, y-s//2-p_r, x+s//4+p_r, y-s//2+p_r], fill=(60,40,20), outline=None)
        # Beak
        beak_pts = [(x, y-s//2+head_r//2), (x-3, y-s//2+head_r+2), (x+3, y-s//2+head_r+2)]
        draw.polygon(beak_pts, fill=(220,180,80), outline=None)
        # Wing lines
        draw.arc([x-s//2, y-s//2, x, y+s//2], 90, 270, fill=(170,170,180), width=2)
        draw.arc([x, y-s//2, x+s//2, y+s//2], 270, 90, fill=(170,170,180), width=2)

    def draw_footprint(self, draw, x, y, size=1.0, color=(100, 90, 100)):
        """Draw a simple footprint (animal/paw print)."""
        s = max(size * 8, 5)
        cx, cy = x, y

        # Main pad
        draw.ellipse([
            cx - int(12 * s), cy - int(4 * s),
            cx + int(12 * s), cy + int(12 * s)
        ], fill=color, outline=(30, 25, 20), width=2)

        # Four toe pads
        toe_positions = [(-10, -8), (-3, -11), (3, -11), (10, -8)]
        for tx, ty in toe_positions:
            draw.ellipse([
                cx + int(tx * s) - int(4 * s), cy + int(ty * s) - int(3 * s),
                cx + int(tx * s) + int(4 * s), cy + int(ty * s) + int(3 * s)
            ], fill=color, outline=(30, 25, 20), width=1)

        # Claw marks
        claw_positions = [(-10, -13), (-3, -16), (3, -16), (10, -13)]
        for cx2, cy2 in claw_positions:
            draw.ellipse([
                cx + int(cx2 * s) - int(2 * s), cy + int(cy2 * s) - int(2 * s),
                cx + int(cx2 * s) + int(2 * s), cy + int(cy2 * s) + int(1 * s)
            ], fill=(min(color[0]+60, 255), min(color[1]+60, 255), min(color[2]+60, 255)))

    def draw_bell(self, draw, x, y, size=1.0, color=(200, 180, 100)):
        s = size; c = tuple(color[:3])
        w, h = int(14*s), int(16*s)
        self.draw_shadow(draw, [(x-w//2, y), (x+w//2, y), (x+w//2, y-h), (x-w//2, y-h)], offset=(2,2), blur_radius=3, color=(0,0,0,30))
        pts = [(x-w//2, y), (x+w//2, y), (x+int(w*0.35), y-h), (x-int(w*0.35), y-h)]
        self.draw_polygon(draw, pts, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=2)
        self.draw_circle(draw, x, y-int(2*s), int(2.5*s), fill=(180,120,80,200))
        self.draw_circle(draw, x, y-h+int(2*s), int(2.5*s), fill=self._lighten(c,10)+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)

    def draw_cactus(self, draw, x, y, size=1.0, color=(50, 140, 50)):
        s = size; c = tuple(color[:3])
        bw, bh = int(8*s), int(20*s)
        self.draw_rect(draw, x-bw//2, y-bh, bw, bh, fill=c+(220,), stroke=self._darken(c,20)+(160,), stroke_width=2, rx=4)
        la_x, la_y = x-bw//2-int(4*s), y-bh+int(6*s)
        self.draw_rect(draw, la_x, la_y, int(8*s), int(5*s), fill=c+(220,), stroke=self._darken(c,20)+(160,), stroke_width=2, rx=3)
        self.draw_rect(draw, la_x, la_y-int(5*s), int(5*s), int(7*s), fill=c+(220,), stroke=self._darken(c,20)+(160,), stroke_width=2, rx=3)
        ra_x, ra_y = x+bw//2-int(4*s), y-bh+int(10*s)
        self.draw_rect(draw, ra_x, ra_y, int(8*s), int(5*s), fill=c+(220,), stroke=self._darken(c,20)+(160,), stroke_width=2, rx=3)
        self.draw_rect(draw, ra_x+int(3*s), ra_y-int(4*s), int(5*s), int(6*s), fill=c+(220,), stroke=self._darken(c,20)+(160,), stroke_width=2, rx=3)
        for sx, sy in [(x, y-bh+int(4*s)), (x, y-bh+int(10*s)), (x, y-bh+int(16*s))]:
            self.draw_line(draw, sx, sy, sx+int(2*s), sy-int(2*s), color=(30,100,30), width=1)
            self.draw_line(draw, sx, sy, sx-int(2*s), sy-int(2*s), color=(30,100,30), width=1)

    def draw_castle(self, draw, x, y, size=1.0, color=(130, 110, 90)):
        s = size; c = tuple(color[:3])
        kw, kh = int(20*s), int(28*s)
        self.draw_shadow(draw, [(x-kw//2, y), (x+kw//2, y), (x+kw//2, y-kh), (x-kw//2, y-kh)], offset=(2,3), blur_radius=4, color=(0,0,0,40))
        self.draw_rect(draw, x-kw//2, y-kh, kw, kh, fill=c+(210,), stroke=self._darken(c,20)+(150,), stroke_width=2)
        for i in range(5):
            bx = x-kw//2 + i*(kw//5)
            self.draw_rect(draw, bx, y-kh-int(5*s), kw//5, int(5*s), fill=c+(220,), stroke=self._darken(c,20)+(150,), stroke_width=1, rx=1)
        self.draw_rect(draw, x-int(6*s), y-int(10*s), int(12*s), int(10*s), fill=self._darken(c,30)+(180,), stroke=(60,50,40,150), stroke_width=2)
        for wy in [y-kh+int(8*s), y-kh+int(16*s)]:
            self.draw_rect(draw, x-int(3*s), wy-int(3*s), int(6*s), int(6*s), fill=(180,190,200,150), stroke=(50,40,30,100), stroke_width=1)
        self.draw_line(draw, x, y-kh-int(5*s), x, y-kh-int(10*s), color=(80,60,40), width=2)
        self.draw_polygon(draw, [(x, y-kh-int(10*s)), (x+int(6*s), y-kh-int(7*s)), (x, y-kh-int(5*s))], fill=(180,40,40,200))

    def draw_chest(self, draw, x, y, size=1.0, color=(140, 90, 50)):
        s = size; c = tuple(color[:3])
        hw, hh = int(18*s), int(12*s)
        self.draw_shadow(draw, [(x-hw, y+hh), (x+hw, y+hh), (x+hw, y), (x-hw, y)], offset=(2,2), blur_radius=3, color=(0,0,0,30))
        self.draw_rect(draw, x-hw, y, int(2*hw), hh, fill=c+(200,), stroke=self._darken(c,30)+(180,), stroke_width=2, rx=3)
        self.draw_rect(draw, x-hw+int(2*s), y-hh//2, int(2*hw)-int(4*s), hh//2, fill=(200,180,80,220), stroke=(180,150,50,180), stroke_width=2, rx=2)
        self.draw_rect(draw, x-int(3*s), y+int(3*s), int(6*s), int(4*s), fill=(200,180,80,200), stroke=(180,150,50,180), stroke_width=1)
        bw = int(2*hw)
        for bx in [x-hw, x-bw//4, x+bw//4-int(4*s), x+hw-int(4*s)]:
            self.draw_line(draw, bx, y, bx, y+hh, color=self._darken(c,20)+(100,), width=2)

    def draw_food(self, draw, x, y, size=1.0, color=(220, 180, 100)):
        s = size; c = tuple(color[:3])
        pr = int(12*s)
        self.draw_ellipse(draw, x-pr, y-int(pr*0.4), int(2*pr), int(pr*0.8), fill=(240,235,225,220), stroke=(200,190,180,180), stroke_width=2)
        colors = [(220,100,80), (180,200,60), (240,180,60)]
        for i, fc in enumerate(colors):
            angle = math.radians(i*120 - 90)
            fx = x + int(math.cos(angle)*pr*0.4)
            fy = y + int(math.sin(angle)*pr*0.15)
            self.draw_circle(draw, fx, fy, int(3*s), fill=fc+(200,))

    def draw_furniture(self, draw, x, y, size=1.0, color=(140, 110, 80)):
        s = max(size, 0.5); c = tuple(color[:3])
        tw, th = int(20*s), int(5*s)
        self.draw_rect(draw, x-tw//2, y-th, tw, th, fill=self._lighten(c,10)+(220,), stroke=self._darken(c,20)+(160,), stroke_width=2, rx=2)
        for ox in [-int(8*s), int(8*s)]:
            self.draw_line(draw, x+ox, y, x+ox, y+int(8*s), color=self._darken(c,20)+(180,), width=max(int(3*s),2))
        self.draw_rect(draw, x-int(6*s), y-int(3*s), int(12*s), int(3*s), fill=self._darken(c,5)+(180,), stroke=self._darken(c,20)+(120,), stroke_width=1)
        self.draw_circle(draw, x, y-int(1.5*s), int(1.5*s), fill=(180,160,120,200))

    def draw_pottery(self, draw, x, y, size=1.0, color=(180, 140, 100)):
        s = size; c = tuple(color[:3])
        vw, vh = int(14*s), int(18*s)
        self.draw_shadow(draw, [(x-vw//2, y), (x+vw//2, y), (x+vw//2, y-vh), (x-vw//2, y-vh)], offset=(2,3), blur_radius=3, color=(0,0,0,30))
        pts = [(x, y-vh), (x+vw//2, y-vh+int(4*s)), (x+vw//2, y-int(2*s)), (x, y), (x-vw//2, y-int(2*s)), (x-vw//2, y-vh+int(4*s))]
        self.draw_polygon(draw, pts, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=2)
        self.draw_ellipse(draw, x-int(6*s), y-vh-int(2*s), int(12*s), int(4*s), fill=self._lighten(c,10)+(220,), stroke=self._darken(c,20)+(160,), stroke_width=1)
        self.draw_ellipse(draw, x-int(5*s), y-vh+int(8*s), int(10*s), int(3*s), fill=self._darken(c,15)+(80,), stroke=None, stroke_width=0)

    def draw_question(self, draw, x, y, size=1.0, color=(180, 60, 60)):
        s = size; c = tuple(color[:3])
        r = 6 * s
        self.draw_arc(draw, x, y - 4 * s, r, 180, 360, color=c + (200,), width=max(int(2.5 * s), 2))
        self.draw_line(draw, x + int(r), y + 2 * s, x - int(2 * s), y + int(10 * s), color=c + (200,), width=max(int(2.5 * s), 2))
        self.draw_circle(draw, x - int(3 * s), y + int(12 * s), int(2 * s), fill=c + (220,))

    def draw_tool(self, draw, x, y, size=1.0, color=(150, 130, 110)):
        s = max(size, 0.5); c = tuple(color[:3])
        self.draw_line(draw, x, y+int(8*s), x, y-int(8*s), color=(160,130,80)+(200,), width=max(int(3*s),2))
        hw, hh = int(10*s), int(5*s)
        self.draw_rect(draw, x-hw//2, y-int(8*s)-hh, hw, hh, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=2, rx=1)
        claw_pts = [(x+hw//2, y-int(8*s)-hh), (x+hw//2+int(4*s), y-int(8*s)-int(3*s)), (x+hw//2, y-int(8*s))]
        self.draw_polygon(draw, claw_pts, fill=c+(200,), stroke=self._darken(c,20)+(150,), stroke_width=1)

    def draw_vehicle(self, draw, x, y, size=1.0, color=(140, 100, 100)):
        s = max(size, 0.5); c = tuple(color[:3])
        bw, bh = int(24*s), int(8*s)
        self.draw_rect(draw, x-bw//2, y-bh//2, bw, bh, fill=c+(220,), stroke=self._darken(c,20)+(150,), stroke_width=2, rx=3)
        cw, ch = int(12*s), int(7*s)
        self.draw_rect(draw, x-cw//2, y-bh//2-ch, cw, ch, fill=(180,200,230,200), stroke=self._darken(c,20)+(150,), stroke_width=1, rx=2)
        wr = int(2*s)
        for wx in [x-bw//3, x+bw//3]:
            draw.ellipse([wx-wr, y+bh//2-wr, wx+wr, y+bh//2+wr], fill=(30,30,30), outline=(60,60,60), width=1)
        self.draw_circle(draw, x-bw//2+int(2*s), y-int(s), int(1.5*s), fill=(255,240,180,200))


# ── Convenience function ──────────────────────────────────────

def generate_sketch(prompt: str, scene_desc: dict = None, width=W, height=H, seed=None) -> Image.Image:
    """Generate a sketch from a text prompt and optional structured description.

    If scene_desc is None, uses the offline dynamic scene composer.
    """
    gen = SketchGenerator(width, height, seed)

    if scene_desc is None:
        scene_desc = llm_generate_scene(prompt)

# ── Convenience function ──────────────────────────────────────

def generate_sketch(prompt: str) -> dict:
    """Generate a structured scene description from any text prompt.

    Uses the offline dynamic scene composer (no external API).
    Returns a dict describing background, elements, mood, etc.
    """
    from src.dynamic_scene import compose_dynamic_scene
    result = compose_dynamic_scene(prompt)
    if result:
        return result
    return _fallback_scene()


def _fallback_scene() -> dict:
    """Simple scene when composition fails — no generic ovals."""
    return {
        "bg": {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]},
        "elements": [
            {"type": "hill", "x": 0.5, "y": 0.75, "width": 0.5, "height": 0.12, "fill": [60, 120, 60]},
            {"type": "cloud", "x": 0.3, "y": 0.2, "scale": 2.5},
            {"type": "cloud", "x": 0.7, "y": 0.25, "scale": 2.0},
        ],
        "atmosphere": {"particles": "none", "fog": False},
        "mood": "peaceful",
    }
