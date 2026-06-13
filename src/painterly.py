"""Painterly post-processing — adds canvas artist touch to rendered frames."""
import random
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
import math

def canvas_texture(size, grain=40, opacity=0.15):
    """Generate a canvas weave texture overlay."""
    w, h = size
    canvas = Image.new("L", (w, h), 128)
    pixels = canvas.load()
    for x in range(w):
        for y in range(h):
            noise = random.randint(-grain, grain)
            # Horizontal weave
            weave = int(8 * math.sin(y * 0.3) * (1 + math.sin(x * 0.05)))
            # Vertical weave  
            weave2 = int(6 * math.sin(x * 0.25) * (1 + math.sin(y * 0.04)))
            pixels[x, y] = max(0, min(255, 128 + noise + weave + weave2))
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.5))
    return canvas


def brush_stroke_texture(size, density=0.3):
    """Generate a subtle brush stroke overlay — irregular paint patches."""
    w, h = size
    img = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(img)
    rng = random.Random(42)
    for _ in range(int(w * h * density * 0.0003)):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        angle = rng.uniform(0, math.pi)
        length = rng.randint(10, 40)
        width = rng.randint(2, 8)
        ex = x + length * math.cos(angle)
        ey = y + length * math.sin(angle)
        alpha = rng.randint(5, 20)
        draw.line([x, y, ex, ey], fill=alpha, width=width)
    img = img.filter(ImageFilter.GaussianBlur(1.5))
    return img


def color_grade(img, warmth=5, saturation_boost=0):
    """Apply subtle color grading for painterly feel."""
    if img.mode != "RGB":
        return img
    r, g, b = img.split()
    r = r.point(lambda x: min(255, x + warmth))
    b = b.point(lambda x: max(0, x - warmth))
    img = Image.merge("RGB", (r, g, b))
    if saturation_boost > 0:
        from PIL import ImageEnhance
        img = ImageEnhance.Color(img).enhance(1 + saturation_boost * 0.1)
    return img


def vignette(img, strength=0.3):
    """Add dark vignette around edges for depth."""
    w, h = img.size
    vignette = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(vignette)
    cx, cy = w // 2, h // 2
    max_r = math.sqrt(cx**2 + cy**2) * 1.2
    for x in range(w):
        for y in range(h):
            dx = x - cx
            dy = y - cy
            d = math.sqrt(dx**2 + dy**2) / max_r
            d = min(1.0, d)
            d = d ** 2  # quadratic falloff
            val = int(255 * (1 - d * strength))
            vignette.putpixel((x, y), val)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=w//15))
    if img.mode == "RGB":
        r, g, b = img.split()
        r = ImageChops.multiply(r, vignette)
        g = ImageChops.multiply(g, vignette)
        b = ImageChops.multiply(b, vignette)
        img = Image.merge("RGB", (r, g, b))
    return img


def soften_edges(img, radius=0.5):
    """Subtle edge soften — tones down harsh vector edges."""
    if radius <= 0:
        return img
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return Image.blend(img, blurred, 0.15)


def painterly_postprocess(img, style="oil"):
    """Apply full painterly post-processing pipeline.
    
    style: "oil" = rich warm, "watercolor" = soft faded, "sketch" = pencil-like
    """
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size

    # Step 1: Subtle edge soften
    img = soften_edges(img, 0.3)

    # Step 2: Color grading
    if style == "oil":
        img = color_grade(img, warmth=8, saturation_boost=2)
    elif style == "watercolor":
        img = color_grade(img, warmth=-5, saturation_boost=-1)
        img = soften_edges(img, 1.0)

    # Step 3: Canvas texture (blend as overlay)
    canvas = canvas_texture((w, h), grain=30, opacity=0.12)
    canvas_rgb = Image.merge("RGB", [canvas, canvas, canvas])
    img = Image.blend(img, canvas_rgb, 0.12)

    # Step 4: Subtle brush stroke texture
    brush = brush_stroke_texture((w, h), density=0.25)
    brush_rgb = Image.merge("RGB", [brush, brush, brush])
    img = Image.blend(img, brush_rgb, 0.08)

    # Step 5: Vignette
    img = vignette(img, strength=0.25)

    # Step 6: Slight contrast boost for pop
    from PIL import ImageEnhance
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.05)

    return img


def preview_painterly(input_path, output_path, style="oil"):
    """Apply painterly effect to an existing image and save."""
    img = Image.open(input_path).convert("RGB")
    result = painterly_postprocess(img, style)
    result.save(output_path)
    return result
