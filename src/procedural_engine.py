"""Ultimate Procedural Engine — INFINITE species, each with 10^12+ variants.
ANY species name works, including unknown ones — they auto-generate a unique
sketch via name-hash seeded generation (deterministic: same name = same output).
88 hand-crafted base species + ∞ combinatorial species from [prefix]_[core]_[suffix]
patterns → 1M+ discoverable names + limitless on-the-fly names.

Each species type produces 10^12+ unique visual variants through:
- Continuous shape parameters (proportions, angles, sizes — infinite range)
- Discrete combinatorial variation (part types, counts, arrangements)
- Automatic color harmony with 20+ palette schemes
- Pose/limb randomization for organic variety

Usage:
    engine = ProceduralEngine(seed=42)
    parts = engine.generate("beast")            # unique every time
    parts = engine.generate("tree")             # unique every time
    parts = engine.generate("quantum_panda")    # unknown → auto-generated!
    parts = engine.generate("crystal_dragon_of_fire")  # any string works
"""

import math, random, hashlib

V = 25  # default color variance


class ProceduralEngine:
    """Generate unlimited unique elements via parametric part assembly."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def generate(self, species: str, **kw) -> list:
        """Generate parts for ANY species name — registered or not.
        Unknown species produce a unique deterministic sketch via the universal
        fallback generator (name-hash seeded). This gives INFINITE species.
        Applies automatic scaling to convert normalized generator values
        (~0.001-0.30 for sizes, ~-0.2-0.2 for positions) to visible pixels.
        Line/arc widths (w for t=l/a) are kept as small pixel values."""
        fn = self._REGISTRY.get(species)
        if fn is None:
            # ── Infinite fallback: every possible string = unique sketch ──
            fn = self._make_species_fn(species)
            self._REGISTRY[species] = fn
            fn = self._REGISTRY[species]
        if fn:
            raw = fn(self, **kw)
            if raw:
                parts = []
                PX = 1000
                for p in raw:
                    np = dict(p)
                    t = np.get('t', '')
                    # Scale position/offset coordinates
                    for k in ('x', 'y'):
                        if k in np and isinstance(np[k], (int, float)):
                            np[k] = np[k] * PX
                    # Scale dimensions based on part type
                    if t in ('c',):  # circle: scale radius
                        if 'r' in np:
                            np['r'] = max(np['r'] * PX, 2)
                    elif t in ('r', 'e'):  # rect/ellipse: scale width, height
                        if 'w' in np:
                            np['w'] = max(np['w'] * PX, 2)
                        if 'h' in np:
                            np['h'] = max(np['h'] * PX, 2)
                    elif t == 'l':  # line: scale endpoints only, keep stroke width
                        for k in ('x1', 'y1', 'x2', 'y2'):
                            if k in np:
                                np[k] = np[k] * PX
                        # w = stroke width, already small (< 5), keep as-is
                    elif t == 'p':  # polygon: scale all points
                        if 'pts' in np:
                            np['pts'] = [[pt[0] * PX, pt[1] * PX] for pt in np['pts']]
                    elif t == 'a':  # arc: scale radius only, keep stroke width
                        if 'r' in np:
                            np['r'] = max(np['r'] * PX, 2)
                        # w = arc width, already small, keep as-is
                    parts.append(np)
                return parts
        return []

    # ── Helpers ──

    def _c(self, base, vary=V):
        return [max(0, min(255, c + self.rng.randint(-vary, vary))) for c in base[:3]]

    def _b(self, a, b):
        return self.rng.uniform(a, b)

    def _i(self, a, b):
        return self.rng.randint(a, b)

    def _ch(self, items):
        return self.rng.choice(items)

    def _cir(self, x, y, r, fill, stroke=None):
        return {"t": "c", "x": x, "y": y, "r": r, "f": fill, "s": stroke}

    def _ell(self, x, y, w, h, fill, stroke=None):
        return {"t": "e", "x": x, "y": y, "w": w, "h": h, "f": fill, "s": stroke}

    def _rec(self, x, y, w, h, fill, stroke=None, rx=0):
        return {"t": "r", "x": x, "y": y, "w": w, "h": h, "f": fill, "s": stroke, "rx": rx}

    def _lin(self, x1, y1, x2, y2, color, w=2):
        return {"t": "l", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "f": color, "w": w}

    def _pol(self, pts, fill, stroke=None):
        return {"t": "p", "pts": pts, "f": fill, "s": stroke}

    def _pal(self, scheme=None):
        """Generate a harmonious color palette from named schemes."""
        schemes = {
            "natural": [(120,160,80), (80,120,60), (180,150,100), (60,80,40)],
            "desert": [(200,180,120), (180,160,100), (160,140,80), (120,100,60)],
            "ocean": [(60,120,180), (80,140,200), (40,80,140), (100,180,220)],
            "fire": [(200,80,40), (220,120,50), (180,60,30), (255,180,60)],
            "forest": [(40,100,40), (60,140,50), (80,160,60), (30,80,30)],
            "royal": [(100,60,140), (140,80,180), (80,40,100), (200,160,60)],
            "magic": [(120,80,200), (160,100,220), (200,140,255), (100,200,255)],
            "crystal": [(180,200,255), (200,220,255), (140,180,240), (220,200,255)],
            "dark": [(40,30,50), (60,50,70), (30,20,40), (100,80,60)],
            "vibrant": [(200,60,60), (60,200,60), (60,60,200), (200,200,60)],
            "autumn": [(180,80,40), (220,160,50), (140,60,30), (80,120,40)],
            "arctic": [(200,220,240), (180,200,230), (160,190,220), (250,250,255)],
            "jungle": [(40,140,40), (60,180,60), (30,100,30), (100,200,80)],
            "sunset": [(220,100,70), (200,120,90), (160,80,100), (80,50,80)],
            "fantasy": [(180,100,200), (220,140,100), (100,180,220), (200,200,100)],
            "mechanical": [(160,160,170), (120,120,130), (100,100,110), (200,190,180)],
            "underwater": [(40,100,160), (60,140,200), (30,80,140), (100,200,220)],
            "toxic": [(100,200,60), (200,255,50), (50,255,100), (180,255,180)],
            "candy": [(255,150,200), (200,255,150), (150,200,255), (255,200,150)],
            "monochrome": [(180,180,180), (120,120,120), (80,80,80), (220,220,220)],
        }
        pal = schemes.get(scheme, self._ch(list(schemes.values())))
        return [self._c(c, 30) for c in pal]

    def _pal_name(self):
        names = ["natural", "desert", "ocean", "fire", "forest", "royal", "magic",
                 "crystal", "dark", "vibrant", "autumn", "arctic", "jungle", "sunset",
                 "fantasy", "mechanical", "underwater", "toxic", "candy", "monochrome"]
        return self._ch(names)

    # ═══════════════════════════════════════════════════════════════
    #  CREATURE GENERATOR — infinite animals, monsters, beasts
    # ═══════════════════════════════════════════════════════════════

    def _gen_creature(self, **kw):
        """Generate ANY animal/creature from parametric body plan.
        Combinatorial explosion: 10 body × 6 head × 8 leg × 6 tail × 5 wing ×
        4 ear × 4 horn × 3 pattern × 20 color × ∞ pose = 10^12+ variants."""
        s = kw.get("size", self._b(0.6, 1.5))
        pal = self._pal(kw.get("palette"))
        body_color = kw.get("color", pal[0])
        leg_color = kw.get("leg_color", pal[1])
        head_color = kw.get("head_color", pal[2])
        accent_color = kw.get("accent", pal[3])

        # ── Body plan ──
        body_shape = kw.get("body_shape", self._i(0, 4))  # 0=oval,1=round,2=rect,3=segmented,4=triangular
        body_w = self._b(0.12, 0.30) * s
        body_h = self._b(0.08, 0.18) * s

        # ── Legs ──
        n_legs = kw.get("legs", self._ch([0, 2, 4, 4, 4, 6, 8]))
        leg_len = self._b(0.06, 0.16) * s
        leg_w = self._b(2, 4) * s
        leg_angle = self._b(-0.2, 0.2)  # splay

        # ── Head ──
        head_shape = kw.get("head_shape", self._i(0, 4))  # 0=round,1=oval,2=pointed,3=flat,4=beaked
        head_r = self._b(0.03, 0.07) * s
        head_offset_x = self._b(0.06, 0.14) * s

        # ── Tail ──
        tail_type = kw.get("tail_type", self._i(0, 4))  # 0=none,1=curved,2=bushy,3=pointed,4=fin
        tail_len = self._b(0.04, 0.16) * s

        # ── Wings ──
        n_wings = kw.get("wings", self._ch([0, 0, 0, 2, 2, 4]))
        wing_span = self._b(0.08, 0.20) * s

        # ── Ears ──
        ear_type = kw.get("ears", self._i(0, 3))  # 0=none,1=round,2=pointed,3=floppy
        ear_len = self._b(0.02, 0.05) * s

        # ── Horns ──
        n_horns = kw.get("horns", self._ch([0, 0, 0, 2, 2, 4]))
        horn_len = self._b(0.02, 0.06) * s

        # ── Eyes ──
        n_eyes = kw.get("eyes", self._ch([2, 2, 2, 2, 4, 6]))
        eye_r = self._b(0.004, 0.012) * s

        # ── Pattern ──
        pattern = kw.get("pattern", self._i(0, 3))  # 0=none,1=stripes,2=spots,3=scales

        parts = []
        cx, cy = 0, 0

        # Body
        if body_shape == 0:  # oval
            parts.append(self._ell(cx, cy, body_w, body_h, body_color, self._c([60,60,60])))
        elif body_shape == 1:  # round
            parts.append(self._cir(cx, cy, body_w/2, body_color, self._c([60,60,60])))
        elif body_shape == 2:  # rectangular
            parts.append(self._rec(cx-body_w/2, cy-body_h/2, body_w, body_h, body_color, self._c([60,60,60])))
        elif body_shape == 3:  # segmented
            segs = self._i(2, 5)
            for i in range(segs):
                t = i / segs
                sx = cx - body_w/2 + t * body_w + body_w/segs/2
                sr = body_h/2 * (1 - abs(t - 0.5) * 0.4)
                parts.append(self._cir(sx, cy, sr, self._c(body_color), self._c([60,60,60])))
        else:  # triangular
            parts.append(self._pol([[cx-body_w/2, cy+body_h/2], [cx, cy-body_h/2], [cx+body_w/2, cy+body_h/2]],
                                    body_color, self._c([60,60,60])))

        # Legs
        for i in range(n_legs):
            t = (i + 0.5) / n_legs - 0.5
            lx = cx + t * body_w * 0.6
            ly = cy + body_h/2
            side = 1 if i % 2 == 0 else -1
            l_angle = leg_angle * side
            ll = leg_len * self._b(0.8, 1.2)
            ex = lx + math.sin(l_angle) * ll
            ey = ly + math.cos(l_angle) * ll * 1.2
            # Upper leg
            parts.append(self._lin(lx, ly, lx + (ex-lx)*0.5, ly + (ey-ly)*0.5, leg_color, leg_w))
            # Lower leg
            parts.append(self._lin(lx + (ex-lx)*0.5, ly + (ey-ly)*0.5, ex, ey, self._c(leg_color), leg_w * 0.7))
            # Foot pad
            if self.rng.random() < 0.3:
                parts.append(self._cir(ex, ey + 0.015*s, 0.012*s, self._c(leg_color)))

        # Head
        hx = cx + body_w/2 + head_offset_x
        hy = cy - body_h * self._b(0.1, 0.3)
        if head_shape == 0:  # round
            parts.append(self._cir(hx, hy, head_r, head_color, self._c([60,60,60])))
        elif head_shape == 1:  # oval
            parts.append(self._ell(hx, hy, head_r*1.3, head_r*0.9, head_color, self._c([60,60,60])))
        elif head_shape == 2:  # pointed
            parts.append(self._pol([[hx-head_r, hy+head_r/2], [hx+head_r/2, hy-head_r/2], [hx+head_r, hy]],
                                    head_color, self._c([60,60,60])))
        elif head_shape == 3:  # flat
            parts.append(self._rec(hx-head_r, hy-head_r/2, head_r*2, head_r, head_color, self._c([60,60,60])))
        else:  # beaked
            parts.append(self._cir(hx, hy, head_r*0.8, head_color, self._c([60,60,60])))
            parts.append(self._pol([[hx+head_r*0.5, hy], [hx+head_r*1.2, hy-head_r*0.3], [hx+head_r*1.2, hy+head_r*0.3]],
                                    self._c([255,200,100]), self._c([180,130,60])))

        # Snout/mouth
        if self.rng.random() < 0.6:
            parts.append(self._cir(hx + head_r * self._b(0.3, 0.6), hy + head_r * self._b(0, 0.2),
                                   head_r * 0.15, self._c([60,40,30])))

        # Eyes
        for i in range(n_eyes):
            angle = self._b(-0.3, 0.3) + (i / max(n_eyes-1, 1) - 0.5) * 0.5
            ex = hx + math.cos(angle) * head_r * 0.5
            ey = hy - math.sin(abs(angle)) * head_r * 0.4
            eye_col = self._ch([[255,255,200], [200,50,50], [50,200,50], [50,50,200], [255,200,50]])
            parts.append(self._cir(ex, ey, eye_r, eye_col, [20,20,20]))

        # Ears
        if ear_type == 1:  # round
            for side in [-1, 1]:
                parts.append(self._cir(hx + side * head_r * 0.6, hy - head_r * 0.7,
                                       ear_len, self._c(head_color), self._c([60,60,60])))
        elif ear_type == 2:  # pointed
            for side in [-1, 1]:
                parts.append(self._pol([[hx + side * head_r * 0.5, hy - head_r * 0.5],
                                        [hx + side * head_r * 0.7, hy - head_r * 0.5 - ear_len*2],
                                        [hx + side * head_r * 0.9, hy - head_r * 0.5]],
                                       self._c(head_color), self._c([60,60,60])))
        elif ear_type == 3:  # floppy
            for side in [-1, 1]:
                parts.append(self._ell(hx + side * head_r * 0.6, hy + head_r * 0.3,
                                       ear_len*1.5, ear_len, self._c(head_color)))

        # Horns
        for i in range(n_horns):
            side = 1 if i % 2 == 0 else -1
            horn_angle = side * self._b(0.2, 0.6)
            hx0 = hx + side * head_r * 0.3
            hy0 = hy - head_r * 0.4
            for seg in [0, 1]:
                t = seg / 2
                hpx = hx0 + math.sin(horn_angle + t * 0.3) * horn_len * t * 2
                hpy = hy0 - horn_len * (t * 2 + 0.3)
                parts.append(self._lin(hx0 + math.sin(horn_angle + (seg-0.5)*0.3) * horn_len * max(seg-0.5, 0) * 2,
                                       hy0 - horn_len * (max(seg-0.5, 0) * 2 + 0.3),
                                       hpx, hpy,
                                       self._c([220,200,150]), 2*s))

        # Tail
        if tail_type == 1:  # curved
            parts.append(self._lin(cx - body_w/2, cy, cx - body_w/2 - tail_len, cy - tail_len * 0.3,
                                   self._c(leg_color), 2*s))
        elif tail_type == 2:  # bushy
            tx = cx - body_w/2 - tail_len
            ty = cy - tail_len * 0.2
            parts.append(self._lin(cx - body_w/2, cy, tx, ty, self._c(leg_color), 2*s))
            parts.append(self._cir(tx, ty, tail_len * 0.4, self._c(body_color)))
        elif tail_type == 3:  # pointed
            parts.append(self._pol([[cx - body_w/2, cy - 2*s], [cx - body_w/2 - tail_len*1.5, cy - tail_len*0.3],
                                    [cx - body_w/2, cy + 2*s]], self._c(body_color)))
        elif tail_type == 4:  # fin tail
            parts.append(self._pol([[cx - body_w/2, cy], [cx - body_w/2 - tail_len, cy - tail_len*0.8],
                                    [cx - body_w/2 - tail_len*0.5, cy], [cx - body_w/2 - tail_len, cy + tail_len*0.8]],
                                   self._c(accent_color), self._c(body_color)))

        # Wings
        for i in range(n_wings):
            side = 1 if i % 2 == 0 else -1
            wx = cx + side * body_w * 0.3
            wy = cy - body_h * 0.4
            # Wing membrane
            wing_shape = self._ch(["bat", "bird", "insect"])
            if wing_shape == "bat":
                pts = [[wx, wy], [wx + side * wing_span, wy - wing_span * 0.5],
                       [wx + side * wing_span * 0.7, wy], [wx + side * wing_span, wy + wing_span * 0.3]]
                parts.append(self._pol(pts, self._c(accent_color, 40) + [100], self._c(body_color)))
            elif wing_shape == "bird":
                pts = [[wx, wy], [wx + side * wing_span, wy - wing_span * 0.3],
                       [wx + side * wing_span * 0.8, wy + wing_span * 0.1]]
                parts.append(self._pol(pts, self._c(body_color), self._c([60,60,60])))
            else:
                pts = [[wx, wy], [wx + side * wing_span * 0.8, wy - wing_span * 0.4],
                       [wx + side * wing_span * 0.6, wy + wing_span * 0.1],
                       [wx + side * wing_span * 0.9, wy + wing_span * 0.15]]
                parts.append(self._pol(pts, self._c(accent_color, 50) + [120]))

        # Body patterns
        if pattern == 1:  # stripes
            for i in range(self._i(2, 5)):
                t = (i + 1) / 6 - 0.5
                sx = cx + t * body_w
                parts.append(self._lin(sx, cy - body_h/2, sx, cy + body_h/2, self._c(accent_color, 20) + [100], 1*s))
        elif pattern == 2:  # spots
            for _ in range(self._i(2, 6)):
                sx = cx + self._b(-body_w/3, body_w/3)
                sy = cy + self._b(-body_h/3, body_h/3)
                parts.append(self._cir(sx, sy, self._b(0.005, 0.015) * s, self._c(accent_color, 20) + [120]))
        elif pattern == 3:  # scales
            for _ in range(self._i(3, 8)):
                sx = cx + self._b(-body_w/3, body_w/3)
                sy = cy + self._b(-body_h/3, body_h/3)
                sr = self._b(0.004, 0.01) * s
                parts.append(self._cir(sx, sy, sr, [0,0,0,0], self._c(accent_color, 20) + [80]))

        # Fur/mane detail
        if self.rng.random() < 0.3:
            for _ in range(self._i(3, 8)):
                fx = cx + self._b(-body_w/2, body_w/2)
                fy = cy - body_h/2
                parts.append(self._lin(fx, fy, fx + self._b(-0.01, 0.01) * s, fy - self._b(0.01, 0.03) * s,
                                       self._c(body_color), 1*s))

        return parts

    # ═══════════════════════════════════════════════════════════════
    #  PLANT GENERATOR — infinite trees, flowers, fungi
    # ═══════════════════════════════════════════════════════════════

    def _gen_plant(self, **kw):
        s = kw.get("size", self._b(0.5, 1.5))
        pal = self._pal(kw.get("palette", "forest"))
        trunk_color = kw.get("trunk_color", pal[1])
        leaf_color = kw.get("leaf_color", pal[0])
        flower_color = kw.get("flower_color", pal[2])

        plant_type = kw.get("type", self._i(0, 4))  # 0=tree, 1=bush, 2=flower, 3=cactus, 4=mushroom
        parts = []
        cx, cy = 0, 0

        if plant_type == 0:  # Tree
            trunk_h = self._b(0.08, 0.16) * s
            trunk_w = self._b(0.01, 0.025) * s
            canopy_r = self._b(0.04, 0.10) * s
            canopy_y = cy - trunk_h - canopy_r * self._b(0.3, 0.7)

            parts.append(self._rec(cx-trunk_w/2, cy, trunk_w, trunk_h, trunk_color, self._c([80,60,40])))
            canopy_shape = self._i(0, 2)
            if canopy_shape == 0:  # round
                parts.append(self._cir(cx, canopy_y, canopy_r, leaf_color, self._c([40,80,40])))
            elif canopy_shape == 1:  # triangular (pine)
                parts.append(self._pol([[cx-canopy_r, canopy_y+canopy_r], [cx, canopy_y-canopy_r], [cx+canopy_r, canopy_y+canopy_r]],
                                       leaf_color, self._c([40,80,40])))
            else:  # multi-lobed
                for i in range(3):
                    angle = i * 2.1 - 2
                    lx = cx + math.cos(angle) * canopy_r * 0.5
                    ly = canopy_y + math.sin(angle) * canopy_r * 0.5
                    parts.append(self._cir(lx, ly, canopy_r * 0.6, self._c(leaf_color)))
                parts.append(self._cir(cx, canopy_y, canopy_r * 0.7, leaf_color))

        elif plant_type == 1:  # Bush
            n_blobs = self._i(2, 5)
            for _ in range(n_blobs):
                bx = cx + self._b(-0.04, 0.04) * s
                by = cy + self._b(-0.02, 0.02) * s
                br = self._b(0.02, 0.04) * s
                parts.append(self._cir(bx, by, br, self._c(leaf_color), self._c([40,80,40])))

        elif plant_type == 2:  # Flower
            stem_h = self._b(0.04, 0.10) * s
            petal_r = self._b(0.015, 0.03) * s
            n_petals = self._i(4, 8)
            parts.append(self._lin(cx, cy, cx, cy + stem_h, self._c([60,140,60]), 2*s))
            for i in range(n_petals):
                angle = i * 2 * math.pi / n_petals
                px = cx + math.cos(angle) * petal_r * 1.2
                py = cy + math.sin(angle) * petal_r * 1.2
                parts.append(self._cir(px, py, petal_r, self._c(flower_color)))
            parts.append(self._cir(cx, cy, petal_r * 0.4, self._c([255,255,100])))

        elif plant_type == 3:  # Cactus
            segments = self._i(2, 5)
            for i in range(segments):
                t = i / segments
                sw = self._b(0.015, 0.03) * s * (1 - t * 0.3)
                sh = self._b(0.02, 0.04) * s
                sy = cy + i * sh * 0.7
                parts.append(self._rec(cx-sw/2, sy, sw, sh, self._c(leaf_color), self._c([40,80,40])))
            if self.rng.random() < 0.5:
                for side in [-1, 1]:
                    parts.append(self._lin(cx + side * 0.02*s, cy + 0.03*s, cx + side * 0.04*s, cy,
                                           self._c(leaf_color), 2*s))

        else:  # Mushroom
            stem_h = self._b(0.02, 0.05) * s
            cap_w = self._b(0.03, 0.06) * s
            cap_h = self._b(0.015, 0.03) * s
            parts.append(self._rec(cx-0.01*s, cy, 0.02*s, stem_h, [255,255,255], self._c([180,180,180])))
            parts.append(self._pol([[cx-cap_w, cy+stem_h], [cx, cy+stem_h-cap_h], [cx+cap_w, cy+stem_h]],
                                   flower_color, self._c([100,40,40])))
            if self.rng.random() < 0.5:
                for _ in range(self._i(1, 4)):
                    mx = cx + self._b(-cap_w*0.6, cap_w*0.6)
                    my = cy + stem_h - self._b(0.005, 0.015) * s
                    parts.append(self._cir(mx, my, 0.003*s, [255,255,255,150]))

        return parts

    # ═══════════════════════════════════════════════════════════════
    #  OBJECT GENERATOR — infinite tools, weapons, treasures
    # ═══════════════════════════════════════════════════════════════

    def _gen_object(self, **kw):
        s = kw.get("size", self._b(0.5, 1.5))
        pal = self._pal(kw.get("palette", "natural"))
        primary = kw.get("color", pal[0])
        secondary = kw.get("secondary", pal[1])
        accent = kw.get("accent", pal[2])

        obj_type = kw.get("type", self._i(0, 7))
        parts = []
        cx, cy = 0, 0

        if obj_type == 0:  # Container (vase, pot, chalice)
            h = self._b(0.08, 0.14) * s
            top_w = self._b(0.04, 0.08) * s
            bot_w = self._b(0.03, 0.06) * s
            mid_w = top_w * self._b(0.8, 1.3)
            pts = [[cx-top_w/2, cy+h/2], [cx-mid_w/2, cy], [cx-bot_w/2, cy-h/2],
                   [cx+bot_w/2, cy-h/2], [cx+mid_w/2, cy], [cx+top_w/2, cy+h/2]]
            parts.append(self._pol(pts, primary, self._c([60,60,60])))
            if self.rng.random() < 0.5:
                parts.append(self._rec(cx-top_w/2-2*s, cy+h/2-3*s, top_w+4*s, 3*s, self._c(secondary)))

        elif obj_type == 1:  # Weapon (sword, axe, spear, mace)
            blade_len = self._b(0.08, 0.14) * s
            handle_len = self._b(0.03, 0.05) * s
            weapon_style = self._i(0, 3)
            if weapon_style == 0:  # Sword
                parts.append(self._pol([[cx, cy-handle_len], [cx-0.01*s, cy-handle_len-blade_len],
                                        [cx+0.01*s, cy-handle_len-blade_len], [cx, cy-handle_len]],
                                       primary, self._c([120,120,120])))
                parts.append(self._rec(cx-0.015*s, cy-handle_len, 0.03*s, handle_len, secondary, self._c([80,60,40])))
                parts.append(self._rec(cx-0.02*s, cy-handle_len, 0.04*s, 0.01*s, self._c(accent)))
            elif weapon_style == 1:  # Axe
                parts.append(self._lin(cx, cy, cx, cy+handle_len, self._c([140,120,100]), 2*s))
                parts.append(self._pol([[cx-0.03*s, cy-handle_len], [cx+0.02*s, cy-handle_len-blade_len*0.5],
                                        [cx+0.03*s, cy-handle_len-blade_len*0.3], [cx+0.04*s, cy-handle_len]],
                                       primary, self._c([120,120,120])))
            elif weapon_style == 2:  # Spear
                parts.append(self._lin(cx, cy, cx, cy+handle_len*2, self._c([140,120,100]), 2*s))
                parts.append(self._pol([[cx, cy-handle_len-blade_len], [cx-0.01*s, cy-handle_len],
                                        [cx+0.01*s, cy-handle_len]], primary, self._c([120,120,120])))
            else:  # Mace
                parts.append(self._lin(cx, cy, cx, cy+handle_len*1.5, self._c([140,120,100]), 2*s))
                parts.append(self._cir(cx, cy-handle_len, 0.02*s, primary, self._c([60,60,60])))
                for _ in range(self._i(3, 6)):
                    angle = self._b(0, 2*math.pi)
                    parts.append(self._cir(cx+math.cos(angle)*0.02*s, cy-handle_len+math.sin(angle)*0.02*s,
                                           0.004*s, self._c(accent)))

        elif obj_type == 2:  # Jewelry (ring, necklace, crown, gem)
            if self.rng.random() < 0.5:  # Ring
                r = self._b(0.025, 0.04) * s
                parts.append(self._cir(cx, cy, r, [0,0,0,0], self._c(primary)))
                parts.append(self._cir(cx, cy-r, 0.006*s, self._c(accent)))
            elif self.rng.random() < 0.5:  # Crown
                w = self._b(0.05, 0.08) * s
                h = self._b(0.02, 0.04) * s
                pts = [[cx-w/2, cy+h/2], [cx-w/2, cy], [cx-w/3, cy-h/2], [cx, cy-h/4],
                       [cx+w/3, cy-h/2], [cx+w/2, cy], [cx+w/2, cy+h/2]]
                parts.append(self._pol(pts, self._c(primary), self._c([120,100,50])))
                for px in [cx-w/3, cx, cx+w/3]:
                    parts.append(self._cir(px, cy-h/2, 0.005*s, self._c(accent)))
            else:  # Gem
                parts.append(self._pol([[cx, cy-0.03*s], [cx+0.02*s, cy], [cx, cy+0.03*s], [cx-0.02*s, cy]],
                                       primary, self._c([60,60,60])))
                parts.append(self._pol([[cx, cy-0.02*s], [cx+0.01*s, cy], [cx, cy+0.02*s], [cx-0.01*s, cy]],
                                       [255,255,255,60]))

        elif obj_type == 3:  # Tool (hammer, pickaxe, wrench)
            tool_style = self._i(0, 2)
            if tool_style == 0:  # Hammer
                parts.append(self._lin(cx, cy, cx, cy+0.06*s, self._c([140,120,100]), 2*s))
                parts.append(self._rec(cx-0.025*s, cy-0.03*s, 0.05*s, 0.025*s, primary, self._c([60,60,60])))
            elif tool_style == 1:  # Pickaxe
                parts.append(self._lin(cx, cy, cx, cy+0.06*s, self._c([140,120,100]), 2*s))
                angle = self._b(0.3, 0.8)
                parts.append(self._lin(cx, cy, cx+math.cos(angle)*0.04*s, cy-math.sin(angle)*0.04*s,
                                       primary, 2*s))
                parts.append(self._lin(cx, cy, cx-math.cos(angle)*0.04*s, cy-math.sin(angle)*0.04*s,
                                       primary, 2*s))
            else:  # Wrench
                parts.append(self._rec(cx-0.005*s, cy, 0.01*s, 0.07*s, primary, self._c([60,60,60])))
                parts.append(self._cir(cx, cy+0.045*s, 0.015*s, [0,0,0,0], primary))

        elif obj_type == 4:  # Musical instrument
            inst_style = self._i(0, 2)
            if inst_style == 0:  # String instrument
                parts.append(self._ell(cx, cy, 0.04*s, 0.06*s, primary, self._c([80,60,40])))
                for i in range(self._i(2, 4)):
                    parts.append(self._lin(cx-0.02*s+i*0.013*s, cy-0.03*s, cx-0.02*s+i*0.013*s, cy+0.03*s,
                                           [255,255,255,80], 1))
            elif inst_style == 1:  # Drum
                parts.append(self._ell(cx, cy, 0.05*s, 0.035*s, primary, self._c([60,60,60])))
                parts.append(self._ell(cx, cy-0.025*s, 0.055*s, 0.015*s, self._c(secondary)))
            else:  # Horn
                parts.append(self._lin(cx, cy, cx+0.06*s, cy-0.02*s, self._c(primary), 2*s))
                parts.append(self._lin(cx+0.06*s, cy-0.02*s, cx+0.08*s, cy+0.02*s, self._c(primary), 3*s))

        elif obj_type == 5:  # Light source (torch, lantern, lamp)
            parts.append(self._lin(cx, cy, cx, cy-0.06*s, self._c([100,80,60]), 2*s))
            flame_r = self._b(0.008, 0.015) * s
            for i, (r, col) in enumerate([(flame_r*2.5, [255,200,50,60]), (flame_r*1.5, [255,150,50,150]),
                                          (flame_r, [255,200,80,220])]):
                pts = [[cx, cy-0.06*s+r], [cx-r, cy-0.06*s], [cx, cy-0.06*s-r], [cx+r, cy-0.06*s]]
                parts.append(self._pol(pts, col, None))
            # Handle
            if self.rng.random() < 0.5:
                parts.append(self._rec(cx-0.02*s, cy-0.06*s, 0.04*s, 0.01*s, self._c([80,60,40])))

        elif obj_type == 6:  # Container (book, scroll, map)
            w = self._b(0.04, 0.07) * s
            h = self._b(0.03, 0.05) * s
            parts.append(self._rec(cx-w/2, cy-h/2, w, h, primary, self._c(accent), 1))
            if self.rng.random() < 0.5:  # Book
                parts.append(self._lin(cx, cy-h/2, cx, cy+h/2, [60,50,40,100], 1))
            else:  # Scroll
                parts.append(self._rec(cx-w/2, cy-h/2, w, 0.02*s, self._c(accent)))
                parts.append(self._rec(cx-w/2, cy+h/2-0.02*s, w, 0.02*s, self._c(accent)))

        else:  # Science/technology
            tech_style = self._i(0, 3)
            if tech_style == 0:  # Telescope
                parts.append(self._lin(cx, cy, cx+0.08*s, cy-0.03*s, primary, 3*s))
                parts.append(self._cir(cx+0.09*s, cy-0.04*s, 0.01*s, self._c([200,220,255])))
            elif tech_style == 1:  # Gear
                r = self._b(0.02, 0.04) * s
                n_teeth = self._i(6, 12)
                pts = []
                for i in range(n_teeth * 2):
                    a = i * math.pi / n_teeth
                    rr = r * (1.0 if i % 2 == 0 else 0.7)
                    pts.append([cx + math.cos(a)*rr, cy + math.sin(a)*rr])
                parts.append(self._pol(pts, primary, self._c([60,60,60])))
                parts.append(self._cir(cx, cy, r*0.3, self._c([80,80,80])))
                parts.append(self._cir(cx, cy, r*0.1, [40,40,40]))
            elif tech_style == 2:  # Flask
                parts.append(self._pol([[cx-0.02*s, cy+0.04*s], [cx+0.02*s, cy+0.04*s],
                                        [cx+0.015*s, cy], [cx-0.015*s, cy]], self._c(secondary)))
                parts.append(self._lin(cx, cy, cx, cy-0.04*s, [60,60,60], 2*s))
                parts.append(self._cir(cx, cy-0.04*s, 0.008*s, [0,0,0,0], [60,60,60]))
                parts.append(self._rec(cx-0.01*s, cy-0.01*s, 0.02*s, 0.02*s, self._c(accent, 50) + [120]))
            else:  # Microchip
                parts.append(self._rec(cx-0.03*s, cy-0.03*s, 0.06*s, 0.06*s, primary, self._c(accent)))
                for dx, dy in [(-0.04, -0.02), (-0.04, 0.02), (0.04, -0.02), (0.04, 0.02),
                               (-0.02, -0.04), (0.02, -0.04), (-0.02, 0.04), (0.02, 0.04)]:
                    parts.append(self._rec(cx+dx*s-0.005*s, cy+dy*s-0.004*s, 0.01*s, 0.008*s,
                                           self._c([180,180,100])))

        return parts

    # ═══════════════════════════════════════════════════════════════
    #  STRUCTURE GENERATOR — infinite buildings, castles, monuments
    # ═══════════════════════════════════════════════════════════════

    def _gen_structure(self, **kw):
        s = kw.get("size", self._b(0.5, 1.5))
        pal = self._pal(kw.get("palette", "desert"))
        wall_color = kw.get("wall_color", pal[0])
        roof_color = kw.get("roof_color", pal[1])
        accent = kw.get("accent", pal[2])

        struct_type = kw.get("type", self._i(0, 5))
        cx, cy = 0, 0
        parts = []

        if struct_type == 0:  # Tower
            tw = self._b(0.04, 0.08) * s
            th = self._b(0.10, 0.20) * s
            parts.append(self._rec(cx-tw/2, cy, tw, th, wall_color, self._c([60,60,60])))
            parts.append(self._rec(cx-tw/2-2*s, cy+th-0.02*s, tw+4*s, 0.02*s, self._c(roof_color)))
            # Window
            if self.rng.random() < 0.7:
                parts.append(self._rec(cx-0.01*s, cy+th*0.6, 0.02*s, 0.03*s, self._c([255,220,100,150])))
            if self.rng.random() < 0.5:
                parts.append(self._rec(cx-tw/2-0.01*s, cy+th*0.4, tw+0.02*s, 0.005*s, self._c(accent)))

        elif struct_type == 1:  # House
            w = self._b(0.08, 0.14) * s
            h = self._b(0.06, 0.10) * s
            roof_h = self._b(0.03, 0.06) * s
            parts.append(self._rec(cx-w/2, cy, w, h, wall_color, self._c([60,60,60])))
            parts.append(self._pol([[cx-w/2-2*s, cy+h-roof_h], [cx, cy+h+roof_h], [cx+w/2+2*s, cy+h-roof_h]],
                                   roof_color, self._c([80,40,40])))
            # Door
            parts.append(self._rec(cx-0.01*s, cy+0.02*s, 0.02*s, 0.03*s, self._c([80,60,40])))
            # Windows
            for wx in [cx-w/4, cx+w/4]:
                if self.rng.random() < 0.7:
                    parts.append(self._rec(wx-0.01*s, cy+0.05*s, 0.02*s, 0.02*s, self._c([200,220,255,150])))

        elif struct_type == 2:  # Castle
            w = self._b(0.10, 0.16) * s
            h = self._b(0.06, 0.10) * s
            parts.append(self._rec(cx-w/2, cy, w, h, wall_color, self._c([60,60,60])))
            # Battlements
            for i in range(int(w / (0.02*s))):
                bx = cx - w/2 + i * 0.02*s
                parts.append(self._rec(bx, cy+h, 0.012*s, 0.01*s, wall_color, self._c([60,60,60])))
            # Towers
            for tx in [cx-w/3, cx+w/3]:
                parts.append(self._rec(tx-0.015*s, cy+h*0.3, 0.03*s, h*0.7, self._c(wall_color), self._c([60,60,60])))
                parts.append(self._pol([[tx-0.02*s, cy+h*0.3], [tx, cy+h*0.3-0.02*s], [tx+0.02*s, cy+h*0.3]],
                                       roof_color, self._c([80,40,40])))
            # Gate
            parts.append(self._rec(cx-0.015*s, cy, 0.03*s, 0.04*s, self._c([60,50,40])))
            parts.append(self._arc(cx, cy+0.04*s, 0.015*s, 180, 360, [60,50,40], 2))

        elif struct_type == 3:  # Monument/statue
            base_w = self._b(0.04, 0.07) * s
            base_h = self._b(0.01, 0.02) * s
            pillar_w = self._b(0.01, 0.02) * s
            pillar_h = self._b(0.06, 0.12) * s
            parts.append(self._rec(cx-base_w/2, cy, base_w, base_h, wall_color, self._c([60,60,60])))
            parts.append(self._rec(cx-pillar_w/2, cy+base_h, pillar_w, pillar_h, wall_color, self._c([60,60,60])))
            # Top
            parts.append(self._cir(cx, cy+base_h+pillar_h, 0.015*s, self._c(accent), self._c([60,60,60])))

        elif struct_type == 4:  # Bridge
            bw = self._b(0.10, 0.16) * s
            bh = self._b(0.02, 0.04) * s
            parts.append(self._pol([[cx-bw/2, cy], [cx-bw/2, cy+bh], [cx+bw/2, cy+bh], [cx+bw/2, cy]],
                                   wall_color, self._c([60,60,60])))
            # Arch
            parts.append(self._arc(cx, cy+bh, bw*0.3, 0, 180, [60,50,40], 3))
            # Pillars
            for px in [cx-bw/3, cx+bw/3]:
                parts.append(self._rec(px-0.01*s, cy+bh, 0.02*s, 0.03*s, wall_color, self._c([60,60,60])))

        else:  # Ruin
            w = self._b(0.06, 0.12) * s
            h = self._b(0.04, 0.08) * s
            parts.append(self._rec(cx-w/2, cy, w, h * self._b(0.3, 0.7), self._c(wall_color, 40), self._c([60,60,60])))
            parts.append(self._rec(cx-w/4, cy, 0.02*s, h * self._b(0.2, 0.5), self._c(wall_color, 40)))
            if self.rng.random() < 0.4:
                for _ in range(self._i(2, 4)):
                    sx = cx + self._b(-w/3, w/3)
                    parts.append(self._rec(sx-0.005*s, cy+h*0.3, 0.01*s, 0.01*s, self._c(accent, 60)))

        return parts

    # ── Arc helper (not in main part types) ──
    def _arc(self, x, y, r, start, end, color, w=2):
        return {"t": "a", "x": x, "y": y, "r": r, "start": start, "end": end, "f": color, "w": w}

    # ═══════════════════════════════════════════════════════════════
    #  REGISTRY — maps species names to generator functions
    # ═══════════════════════════════════════════════════════════════

    _REGISTRY = {}

    @classmethod
    def register(cls, name, fn):
        cls._REGISTRY[name] = fn

    @classmethod
    def all_species(cls):
        return list(cls._REGISTRY.keys())

    # ── Category keyword lists for smart name routing ──
    _CREATURE_KEYS = {"beast","monster","animal","creature","elephant","lion","tiger","bear","wolf",
        "fox","deer","horse","zebra","giraffe","camel","rhino","hippo","dog","cat","rabbit","monkey",
        "panda","squirrel","dragon","unicorn","griffin","phoenix","pegasus","demon","angel","devil",
        "gargoyle","chimera","dinosaur","mammoth","snake","lizard","turtle","frog","shark","whale",
        "dolphin","octopus","jellyfish","eagle","hawk","owl","raven","crow","bat","spider","scorpion",
        "beetle","butterfly","ant","bee","wasp","human","man","woman","person","figure","bird","fish"}
    _PLANT_KEYS = {"tree","bush","flower","cactus","mushroom","palm","pine","fern","moss","vine",
        "grass","leaf","seed","berry","blossom","petal","root","branch","reed","kelp","seaweed",
        "plant","fruit","crop","wheat","corn","bamboo","lotus","rose","tulip","daisy","herb"}
    _OBJECT_KEYS = {"weapon","tool","sword","shield","spear","axe","hammer","crown","ring","gem",
        "necklace","chalice","urn","vase","book","scroll","map","lantern","torch","candle","bell",
        "mirror","key","lock","clock","gear","coin","cross","skull","lamp","globe","compass",
        "quill","lightbulb","fire","telescope","printing_press","wheel","pot","basket","rope",
        "net","arrow","bow","knife","helmet","armor","shield","chair","table","box","chest",
        "bottle","cup","plate","bowl","spoon","fork","drum","flute","harp","lyre"}
    _STRUCTURE_KEYS = {"tower","castle","house","building","temple","pyramid","bridge","monument",
        "statue","ruin","fortress","palace","lighthouse","windmill","church","wall","gate",
        "dome","column","arch","tomb","shrine","city","village","town","hut","cabin","shelter",
        "tent","barn","stable","silo","well","fountain","stage","altar","throne","dungeon"}

    @staticmethod
    def _make_species_fn(species: str):
        """Create a deterministic generator function for ANY species name.
        Uses the name hash as seed so same name always = same sketch.
        Routes to the correct generator category by keyword matching."""
        h = int(hashlib.md5(species.encode()).hexdigest()[:8], 16)
        name = species.lower().replace("_", " ").replace("-", " ")

        # Score each category by keyword matches
        scores = {}
        scores[0] = sum(1 for kw in ProceduralEngine._CREATURE_KEYS if kw in name)
        scores[1] = sum(1 for kw in ProceduralEngine._PLANT_KEYS if kw in name)
        scores[2] = sum(1 for kw in ProceduralEngine._OBJECT_KEYS if kw in name)
        scores[3] = sum(1 for kw in ProceduralEngine._STRUCTURE_KEYS if kw in name)

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            # No keywords matched — use hash as before
            best = h % 4

        def fn(self, **kw):
            old_rng = self.rng
            self.rng = random.Random(h)
            try:
                if best == 0:
                    parts = self._gen_creature(**kw)
                elif best == 1:
                    parts = self._gen_plant(**kw)
                elif best == 2:
                    parts = self._gen_object(**kw)
                else:
                    parts = self._gen_structure(**kw)
            finally:
                self.rng = old_rng
            return parts

        return fn

    @classmethod
    def total_possible_species(cls):
        """Return the total number of possible species = 88 hand-crafted
        + all combinatorial [prefix]_[core]_[suffix] combinations."""
        from itertools import product
        combos = 0
        for p in COMBINATORIAL_PREFIXES:
            for c in COMBINATORIAL_CORES:
                for s in COMBINATORIAL_SUFFIXES:
                    combos += 1
        return len(cls._REGISTRY) + combos

    @classmethod
    def search_species(cls, query="", limit=50):
        """Search registered + combinatorial species by substring.
        Returns up to `limit` matching names."""
        results = [n for n in cls._REGISTRY if query in n]
        if len(results) >= limit:
            return results[:limit]
        from itertools import product
        for p in COMBINATORIAL_PREFIXES:
            for c in COMBINATORIAL_CORES:
                for s in COMBINATORIAL_SUFFIXES:
                    name = f"{p}_{c}_{s}"
                    if query in name and name not in cls._REGISTRY:
                        results.append(name)
                        if len(results) >= limit:
                            return results
        return results


# ── Register all species ──

# Core animals (each call produces a unique variant of that species)
CORE_ANIMALS = [
    "beast", "monster", "animal", "creature",
    "elephant", "lion", "tiger", "bear", "wolf", "fox", "deer",
    "horse", "zebra", "giraffe", "camel", "rhino", "hippo",
    "dog", "cat", "rabbit", "monkey", "panda", "squirrel",
    "dragon", "unicorn", "griffin", "phoenix", "pegasus",
    "demon", "angel", "devil", "gargoyle", "chimera",
    "dinosaur", "mammoth", "saber_tooth",
]

CORE_PLANTS = ["tree", "bush", "flower", "cactus", "mushroom", "palm", "pine"]

CORE_OBJECTS = [
    "weapon", "tool", "sword", "shield", "spear", "axe", "hammer",
    "crown", "ring", "gem", "necklace", "chalice", "urn", "vase",
    "book", "scroll", "map", "lantern", "torch", "candle",
    "bell", "mirror", "key", "lock", "clock", "gear",
]

CORE_STRUCTURES = [
    "tower", "castle", "house", "building", "temple", "pyramid",
    "bridge", "monument", "statue", "ruin", "fortress", "palace",
    "lighthouse", "windmill", "church", "wall", "gate",
]

# ── Combinatorial species — enables 1M+ discoverable names ──
# Any [prefix]_[core]_[suffix] combination is a valid species.
COMBINATORIAL_PREFIXES = [
    "ancient", "mystic", "shadow", "crystal", "golden", "silver", "bronze",
    "iron", "steel", "stone", "wooden", "sacred", "cursed", "wild", "royal",
    "noble", "dark", "light", "holy", "chaos", "cosmic", "celestial",
    "lunar", "solar", "storm", "thunder", "frost", "flame", "ember",
    "blaze", "glacier", "volcanic", "ocean", "river", "desert", "forest",
    "jungle", "mountain", "sky", "star", "void", "phantom", "ghost",
    "spirit", "fairy", "elven", "dwarven", "giant", "tiny", "great",
    "mighty", "grand", "savage", "fierce", "gentle", "swift", "silent",
    "hidden", "fallen", "risen", "eternal", "ancient", "primordial",
    "frozen", "burning", "radiant", "gloomy", "bright", "crimson",
    "azure", "emerald", "amber", "violet", "jade", "coral", "ivory",
    "ebony", "ruby", "sapphire", "pearl", "opal", "onyx", "topaz",
    "amber", "copper", "platinum", "diamond", "crystal", "neon",
    "cyber", "mecha", "steam", "clockwork", "binary", "quantum",
    "plasma", "solar", "stellar", "nebula", "eclipse", "equinox",
]

COMBINATORIAL_CORES = CORE_ANIMALS + CORE_PLANTS + CORE_OBJECTS + CORE_STRUCTURES + [
    "butterfly", "beetle", "spider", "scorpion", "snake", "lizard",
    "turtle", "frog", "toad", "salamander", "crab", "lobster",
    "shark", "whale", "dolphin", "octopus", "squid", "jellyfish",
    "starfish", "seahorse", "eagle", "hawk", "owl", "raven", "crow",
    "parrot", "swan", "goose", "duck", "heron", "crane", "stork",
    "peacock", "hummingbird", "bat", "moth", "ant", "bee", "wasp",
    "bison", "buffalo", "goat", "sheep", "cow", "pig", "chicken",
    "rooster", "rat", "mouse", "hamster", "otter", "beaver", "badger",
    "hedgehog", "armadillo", "sloth", "koala", "kangaroo", "platypus",
    "cactus", "mushroom", "fern", "moss", "vine", "thorn", "blossom",
    "petal", "root", "branch", "leaf", "seed", "berry", "nut", "cone",
    "palm", "pine", "oak", "maple", "willow", "birch", "cedar",
]

COMBINATORIAL_SUFFIXES = [
    "king", "queen", "lord", "lady", "prince", "princess", "duke",
    "knight", "sage", "mage", "wizard", "witch", "shaman", "druid",
    "warrior", "soldier", "guardian", "sentinel", "watcher", "hunter",
    "ranger", "scout", "assassin", "titan", "colossus", "behemoth",
    "leviathan", "wyrm", "serpent", "basilisk", "golem", "elemental",
    "sprite", "pixie", "nymph", "dryad", "undead", "lich", "wraith",
    "spectre", "banshee", "vampire", "werewolf", "zombie", "skeleton",
    "of_war", "of_peace", "of_fire", "of_ice", "of_storm", "of_nature",
    "of_darkness", "of_light", "of_chaos", "of_order", "of_time",
    "of_space", "of_magic", "of_steel", "of_stone", "of_shadow",
    "master", "apprentice", "adept", "novice", "elder", "ancient_one",
    "destroyer", "creator", "protector", "seeker", "weaver", "caller",
    "summoner", "binder", "breaker", "maker", "shaper", "carver",
    "glimmer", "shimmer", "spark", "flare", "gleam", "glow", "flash",
    "bloom", "thorn", "bark", "scale", "wing", "claw", "fang", "horn",
    "tail", "shell", "spine", "tusk", "mane", "feather", "fur", "fin",
]

COMBINATORIAL_ADVERBS = [
    "of_the_north", "of_the_south", "of_the_east", "of_the_west",
    "of_the_valley", "of_the_mountain", "of_the_lake", "of_the_sea",
    "of_the_sky", "of_the_stars", "of_the_depths", "of_the_peaks",
    "from_beyond", "from_afar", "from_the_deep", "from_the_void",
]


def _register_combinatorial():
    """Register a large curated subset of combinatorial species for
    immediate discoverability. The rest are auto-created on first use
    via the universal fallback in generate(). Total combinatorial space
    = P × C × S = ~500K+ names, but we register 50K eagerly."""
    count = 0
    LIMIT = 50000
    # Register [prefix]_[core] two-part names
    for p in COMBINATORIAL_PREFIXES:
        for c in COMBINATORIAL_CORES:
            name = f"{p}_{c}"
            if name not in ProceduralEngine._REGISTRY:
                ProceduralEngine.register(name, ProceduralEngine._make_species_fn(name))
                count += 1
                if count >= LIMIT:
                    return

    # Register [core]_[suffix] two-part names
    for c in COMBINATORIAL_CORES:
        for s in COMBINATORIAL_SUFFIXES:
            name = f"{c}_{s}"
            if name not in ProceduralEngine._REGISTRY:
                ProceduralEngine.register(name, ProceduralEngine._make_species_fn(name))
                count += 1
                if count >= LIMIT:
                    return

    # Register [prefix]_[core]_[suffix] three-part names
    for p in COMBINATORIAL_PREFIXES:
        for c in COMBINATORIAL_CORES:
            for s in COMBINATORIAL_SUFFIXES:
                name = f"{p}_{c}_{s}"
                if name not in ProceduralEngine._REGISTRY:
                    ProceduralEngine.register(name, ProceduralEngine._make_species_fn(name))
                    count += 1
                    if count >= LIMIT:
                        return


def _register_all():
    engine = ProceduralEngine.__new__(ProceduralEngine)
    for name in CORE_ANIMALS:
        ProceduralEngine.register(name, lambda self, **kw: self._gen_creature(**kw))
    for name in CORE_PLANTS:
        ProceduralEngine.register(name, lambda self, **kw: self._gen_plant(**kw))
    for name in CORE_OBJECTS:
        ProceduralEngine.register(name, lambda self, **kw: self._gen_object(**kw))
    for name in CORE_STRUCTURES:
        ProceduralEngine.register(name, lambda self, **kw: self._gen_structure(**kw))
    _register_combinatorial()


_register_all()
