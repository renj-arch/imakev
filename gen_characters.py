"""Generate character portrait avatars for Ding, Dong, Think voices."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw


def draw_owl(draw, x, y, s=1.0):
    """Draw Think as a wide-eyed owl."""
    bx, by = x, y + int(8*s)
    bw, bh = int(16*s), int(18*s)
    draw.ellipse([bx - bw//2, by - bh//2, bx + bw//2, by + bh//2],
                 fill=(140, 100, 60, 220), outline=(80, 50, 30), width=2)
    draw.ellipse([bx - int(8*s), by, bx + int(8*s), by + int(8*s)],
                 fill=(200, 180, 150, 200))
    hx, hy = x, y - int(4*s)
    hr = int(10*s)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                 fill=(150, 110, 70, 220), outline=(80, 50, 30), width=2)
    for dx in [-1, 1]:
        draw.polygon([(hx + dx*int(7*s), hy - int(6*s)),
                      (hx + dx*int(4*s), hy - int(12*s)),
                      (hx + dx*int(1*s), hy - int(6*s))],
                     fill=(120, 80, 50, 220))
    for dx in [-1, 1]:
        draw.ellipse([hx + dx*int(4*s) - int(5*s), hy - int(2*s) - int(5*s),
                      hx + dx*int(4*s) + int(5*s), hy - int(2*s) + int(5*s)],
                     fill=(255, 255, 240, 230), outline=(60, 40, 20), width=1)
        draw.ellipse([hx + dx*int(4*s) - int(3*s), hy - int(2*s) - int(3*s),
                      hx + dx*int(4*s) + int(3*s), hy - int(2*s) + int(3*s)],
                     fill=(40, 30, 20, 230))
        draw.ellipse([hx + dx*int(5*s) - int(1*s), hy - int(3*s) - int(1*s),
                      hx + dx*int(5*s) + int(1*s), hy - int(3*s) + int(1*s)],
                     fill=(255, 255, 255, 200))
    draw.polygon([(hx - int(2*s), hy + int(3*s)),
                  (hx + int(2*s), hy + int(3*s)),
                  (hx, hy + int(7*s))],
                 fill=(220, 180, 60, 220), outline=(160, 120, 40), width=1)
    for dx in [-1, 1]:
        fx = bx + dx*int(5*s)
        fy = by + bh//2
        draw.line([(fx, fy), (fx - int(3*s), fy + int(5*s))], fill=(180, 140, 80), width=int(2*s))
        draw.line([(fx, fy), (fx, fy + int(6*s))], fill=(180, 140, 80), width=int(2*s))
        draw.line([(fx, fy), (fx + int(3*s), fy + int(5*s))], fill=(180, 140, 80), width=int(2*s))
    draw.polygon([(hx - hr + int(2*s), hy + int(6*s)),
                  (hx + hr - int(2*s), hy + int(6*s)),
                  (hx + int(8*s), hy + int(14*s)),
                  (hx - int(8*s), hy + int(14*s))],
                 fill=(60, 100, 180, 180))


def draw_ding(draw, x, y, s=1.0):
    """Draw Ding the Storykeeper: medieval sage in robe holding scroll."""
    bx, by = x, y + int(6*s)
    bw, bh = int(14*s), int(22*s)
    draw.ellipse([bx - bw//2, by, bx + bw//2, by + bh],
                 fill=(40, 50, 100, 220), outline=(25, 35, 70), width=2)
    draw.rectangle([bx - bw//2, by + bh - int(6*s), bx + bw//2, by + bh],
                   fill=(60, 70, 130, 200))
    hx, hy = x, y - int(4*s)
    hr = int(8*s)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                 fill=(230, 190, 160, 220), outline=(160, 120, 90), width=2)
    draw.polygon([(hx - int(5*s), hy + int(3*s)),
                  (hx + int(5*s), hy + int(3*s)),
                  (hx + int(3*s), hy + int(14*s)),
                  (hx - int(3*s), hy + int(14*s))],
                 fill=(220, 215, 210, 200))
    for dx in [-1, 1]:
        draw.ellipse([hx + dx*int(3*s) - int(2*s), hy - int(2*s) - 1,
                      hx + dx*int(3*s) + int(2*s), hy - int(2*s) + 1],
                     fill=(40, 35, 30, 220))
    draw.point([hx, hy + int(2*s)], fill=(160, 120, 90))
    for dx in [-1, 1]:
        draw.line([(hx + dx*int(5*s), hy - int(5*s)),
                   (hx + dx*int(2*s), hy - int(4*s))],
                  fill=(200, 195, 190), width=int(2*s))
    draw.ellipse([hx - int(7*s), hy - int(7*s) - int(4*s),
                  hx + int(7*s), hy - int(7*s) + int(4*s)],
                 fill=(40, 40, 80, 220), outline=(25, 25, 50), width=1)
    sx = x + int(10*s)
    sy = y + int(6*s)
    draw.rectangle([sx, sy - int(6*s), sx + int(3*s), sy + int(6*s)],
                   fill=(240, 220, 180, 220), outline=(180, 160, 120), width=1)
    draw.ellipse([sx - 1, sy - int(7*s), sx + int(3*s) + 1, sy - int(4*s)],
                 fill=(220, 200, 160, 220))
    draw.ellipse([sx - 1, sy + int(4*s), sx + int(3*s) + 1, sy + int(7*s)],
                 fill=(220, 200, 160, 220))


def draw_dong(draw, x, y, s=1.0):
    """Draw Dong the Reflector: elegant renaissance woman with mirror."""
    bx, by = x, y + int(6*s)
    bw, bh = int(12*s), int(24*s)
    draw.polygon([(bx - bw//2, by), (bx + bw//2, by),
                  (bx + int(8*s), by + bh), (bx - int(8*s), by + bh)],
                 fill=(120, 50, 100, 220), outline=(80, 30, 60), width=2)
    draw.polygon([(bx - int(4*s), by), (bx + int(4*s), by),
                  (bx + int(2*s), by + int(10*s)), (bx - int(2*s), by + int(10*s))],
                 fill=(100, 40, 80, 200))
    hx, hy = x, y - int(4*s)
    hr = int(7*s)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                 fill=(240, 200, 175, 220), outline=(170, 130, 100), width=2)
    draw.ellipse([hx - int(8*s), hy - int(9*s), hx + int(8*s), hy - int(4*s)],
                 fill=(60, 40, 30, 220))
    draw.ellipse([hx - int(5*s), hy - int(3*s), hx - int(2*s), hy + int(2*s)],
                 fill=(60, 40, 30, 220))
    draw.ellipse([hx + int(2*s), hy - int(3*s), hx + int(5*s), hy + int(2*s)],
                 fill=(60, 40, 30, 220))
    for dx in [-1, 1]:
        draw.ellipse([hx + dx*int(3*s) - int(2*s), hy - int(2*s) - int(2*s),
                      hx + dx*int(3*s) + int(2*s), hy - int(2*s) + int(2*s)],
                     fill=(80, 100, 140, 230))
        draw.ellipse([hx + dx*int(4*s) - 1, hy - int(3*s) - 1,
                      hx + dx*int(4*s) + 1, hy - int(3*s) + 1],
                     fill=(255, 255, 255, 180))
    draw.arc([hx - int(3*s), hy + int(1*s), hx + int(3*s), hy + int(5*s)],
             0, 180, fill=(140, 100, 80), width=1)
    mx = x - int(10*s)
    my = y + int(6*s)
    draw.line([(mx, my + int(5*s)), (mx, my + int(10*s))], fill=(180, 160, 100), width=int(2*s))
    draw.ellipse([mx - int(5*s), my - int(5*s), mx + int(5*s), my + int(5*s)],
                 fill=(200, 180, 120, 180), outline=(160, 140, 80), width=2)
    draw.ellipse([mx - int(3*s), my - int(3*s), mx + int(3*s), my + int(3*s)],
                 fill=(200, 220, 240, 150))
    draw.ellipse([mx - int(2*s), my - int(2*s), mx, my],
                 fill=(230, 240, 255, 120))


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    for name, func in [("ding", draw_ding), ("dong", draw_dong), ("think", draw_owl)]:
        size = 256
        img = Image.new("RGB", (size, size), (25, 25, 45))
        draw = ImageDraw.Draw(img)
        func(draw, size // 2, size // 2 + 10, s=3.0)
        out = f"output/char_{name}.png"
        img.save(out)
        print(f"{out}: {os.path.getsize(out)} bytes")
