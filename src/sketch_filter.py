"""Photo-to-sketch filter — converts real photos into hand-drawn pencil style via OpenCV."""

import cv2
import numpy as np
from PIL import Image


def photo_to_sketch(img: Image.Image, line_style: str = "pencil") -> Image.Image:
    """Convert a photo to sketch/line-art style using OpenCV.
    
    line_style: 'pencil' (soft pencil), 'marker' (bold lines), 'charcoal' (thick dark)
    """
    arr = np.array(img)
    if len(arr.shape) == 2:
        gray = arr
    else:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    h, w = gray.shape

    if line_style == "pencil":
        inv = 255 - gray
        blur = cv2.GaussianBlur(inv, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blur + 1, scale=256)
        sketch = cv2.equalizeHist(sketch.astype(np.uint8))

    elif line_style == "marker":
        blur = cv2.bilateralFilter(gray, 9, 75, 75)
        edges = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                      cv2.THRESH_BINARY, 11, 2)
        sketch = 255 - edges

    elif line_style == "colored_sketch":
        # Colored pencil look
        gray_sketch = photo_to_sketch(img, "pencil")
        gray_3ch = cv2.cvtColor(gray_sketch, cv2.COLOR_GRAY2RGB)
        colored = arr.astype(np.float32)
        blended = cv2.addWeighted(colored, 0.4, gray_3ch.astype(np.float32), 0.6, 0)
        sketch = blended.astype(np.uint8)
        return Image.fromarray(sketch)

    else:
        # charcoal: thick dark lines
        blur = cv2.medianBlur(gray, 7)
        edges = cv2.Canny(blur, 30, 120)
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        sketch = 255 - edges

    # Clean up: remove small noise
    sketch = cv2.medianBlur(sketch, 3)
    sketch_rgb = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)

    return Image.fromarray(sketch_rgb)


def create_sketch_canvas(sketch_img: Image.Image, bg_color=(250, 250, 245),
                          w: int = 720, h: int = 1280) -> Image.Image:
    """Place sketch on a cream/white background canvas."""
    canvas = Image.new("RGB", (w, h), bg_color)
    sw, sh = sketch_img.size
    if sw > w or sh > h:
        sketch_img.thumbnail((w - 40, h - 200), Image.LANCZOS)
    x = (w - sketch_img.width) // 2
    y = (h - sketch_img.height) // 2 - 60
    if sketch_img.mode == "RGBA":
        canvas.paste(sketch_img, (x, y), sketch_img)
    else:
        canvas.paste(sketch_img, (x, y))
    return canvas
