"""SceneMapper — maps any narration sentence to visual elements + background."""
import random

rng = random.Random()

# ── Keyword → Element mapping ──
# Each entry: keyword -> list of element specs
# x,y are relative (0-1). Use None for auto-placement.

ELEMENT_MAP = {
    # World / geography
    "world": [{"type": "globe", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "map", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "earth": [{"type": "globe", "x": 0.5, "y": 0.4, "scale": 1.8}],
    "land": [{"type": "rect", "x": 0.5, "y": 0.5, "width": 0.3, "height": 0.2, "fill": [100, 140, 80, 180], "stroke": [60, 100, 50]}],
    "island": [{"type": "polygon", "x": 0.5, "y": 0.5, "points": [[0.4,0.45],[0.6,0.4],[0.65,0.5],[0.55,0.6],[0.4,0.55]], "fill": [120, 160, 80, 200], "stroke": [80, 120, 60]}],
    "continent": [{"type": "polygon", "x": 0.5, "y": 0.45, "points": [[0.3,0.35],[0.5,0.3],[0.7,0.35],[0.65,0.5],[0.35,0.55]], "fill": [100, 150, 80, 150], "stroke": [80, 120, 60]}],

    # Map / drawing
    "map": [{"type": "map", "x": 0.5, "y": 0.45, "scale": 1.5}, {"type": "scroll", "x": 0.5, "y": 0.45, "scale": 1.3}],
    "draw": [{"type": "quill", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "hand", "x": 0.5, "y": 0.5, "scale": 1.5}],
    "clay": [{"type": "rect", "x": 0.5, "y": 0.4, "width": 0.2, "height": 0.25, "fill": [180, 160, 130, 200], "stroke": [120, 100, 80]}],
    "tablet": [{"type": "rect", "x": 0.5, "y": 0.4, "width": 0.2, "height": 0.25, "fill": [180, 160, 130, 200], "stroke": [120, 100, 80]}],
    "scratch": [{"type": "hand", "x": 0.5, "y": 0.5, "scale": 1.5}, {"type": "line", "x": 0.45, "y": 0.4, "x2": 0.55, "y2": 0.42, "stroke": [100, 80, 60], "stroke_width": 2}],
    "circle": [{"type": "circle", "x": 0.5, "y": 0.4, "radius": 0.08, "fill": [200, 190, 170, 100], "stroke": [120, 100, 80]}],
    "line": [{"type": "line", "x": 0.4, "y": 0.4, "x2": 0.6, "y2": 0.4, "stroke": [140, 120, 100], "stroke_width": 3}],
    "dot": [{"type": "circle", "x": 0.5, "y": 0.5, "radius": 0.015, "fill": [180, 60, 60, 200]}],
    "mark": [{"type": "x_mark", "x": 0.5, "y": 0.45, "scale": 0.8, "fill": [180, 40, 40]}],

    # Writing / knowledge
    "book": [{"type": "book", "x": 0.5, "y": 0.45, "scale": 1.5}, {"type": "scroll", "x": 0.5, "y": 0.45, "scale": 1.2}],
    "write": [{"type": "quill", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "book", "x": 0.5, "y": 0.5, "scale": 1.2}],
    "read": [{"type": "book", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "eye", "x": 0.5, "y": 0.3, "scale": 1.5}],
    "knowledge": [{"type": "book", "x": 0.45, "y": 0.4, "scale": 1.5}, {"type": "lightbulb", "x": 0.6, "y": 0.3, "scale": 1.2}],
    "learn": [{"type": "book", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "eye", "x": 0.3, "y": 0.3, "scale": 1.5}],
    "story": [{"type": "book", "x": 0.5, "y": 0.45, "scale": 1.5}, {"type": "fire", "x": 0.5, "y": 0.65, "scale": 0.8}],

    # Navigation
    "star": [{"type": "star", "x": 0.5, "y": 0.2, "count": 30, "brightness": 200}, {"type": "moon", "x": 0.7, "y": 0.15, "radius": 25}],
    "north star": [{"type": "star", "x": 0.5, "y": 0.2, "count": 20, "brightness": 180}, {"type": "circle", "x": 0.5, "y": 0.15, "radius": 0.025, "fill": [255, 230, 100, 200]}],
    "sun": [{"type": "sun", "x": 0.5, "y": 0.25, "radius": 35}],
    "moon": [{"type": "moon", "x": 0.5, "y": 0.2, "radius": 30}],
    "sky": [{"type": "cloud", "x": 0.5, "y": 0.25, "scale": 0.8}],
    "ocean": [{"type": "water", "x": 0.5, "y": 0.5, "scale": 0.8}],
    "sea": [{"type": "water", "x": 0.5, "y": 0.5, "scale": 0.8}],
    "river": [{"type": "path", "x": 0.3, "y": 0.3, "x2": 0.7, "y2": 0.7, "width": 12, "fill": [60, 120, 200]}],
    "mountain": [{"type": "mountain", "x": 0.5, "y": 0.5, "scale": 0.6}, {"type": "mountain", "x": 0.3, "y": 0.55, "scale": 0.4}],
    "peak": [{"type": "mountain", "x": 0.5, "y": 0.45, "scale": 0.7}],
    "hill": [{"type": "hill", "x": 0.5, "y": 0.55, "scale": 0.6}],
    "compass": [{"type": "compass", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "direction": [{"type": "arrow", "x": 0.4, "y": 0.45, "x2": 0.6, "y2": 0.45, "stroke": [180, 80, 60], "stroke_width": 3}],
    "road": [{"type": "path", "x": 0.3, "y": 0.7, "x2": 0.7, "y2": 0.9, "width": 10, "fill": [140, 120, 90]}],
    "port": [{"type": "building", "x": 0.5, "y": 0.5, "scale": 0.6}, {"type": "ship", "x": 0.3, "y": 0.55, "scale": 0.5}],

    # People
    "people": [{"type": "human", "x": 0.35, "y": 0.6, "scale": 2.5}, {"type": "human", "x": 0.65, "y": 0.6, "scale": 2.5}],
    "person": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5}],
    "man": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [100, 70, 80]}],
    "woman": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [120, 80, 100]}],
    "sailor": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5, "fill": [60, 80, 100], "label": "sailor"}],
    "king": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [120, 60, 60], "label": "king"}, {"type": "crown", "x": 0.5, "y": 0.3, "scale": 1.5}],
    "scribe": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [70, 60, 90], "label": "scribe"}, {"type": "quill", "x": 0.7, "y": 0.45, "scale": 1.2}],
    "scholar": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [80, 70, 100], "label": "scholar"}, {"type": "book", "x": 0.7, "y": 0.45, "scale": 1.2}],
    "explorer": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5, "fill": [100, 80, 60], "label": "explorer"}, {"type": "compass", "x": 0.7, "y": 0.35, "scale": 1.2}],

    # Ships / travel
    "ship": [{"type": "ship", "x": 0.5, "y": 0.5, "scale": 0.6}],
    "sail": [{"type": "ship", "x": 0.5, "y": 0.5, "scale": 0.6}],
    "boat": [{"type": "ship", "x": 0.5, "y": 0.55, "scale": 0.5}],
    "travel": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5}, {"type": "path", "x": 0.3, "y": 0.7, "x2": 0.7, "y2": 0.85, "width": 8, "fill": [140, 120, 90]}],

    # Cities / buildings
    "city": [{"type": "building", "x": 0.3, "y": 0.5, "scale": 0.7}, {"type": "building", "x": 0.5, "y": 0.45, "scale": 0.8}, {"type": "building", "x": 0.7, "y": 0.5, "scale": 0.6}],
    "building": [{"type": "building", "x": 0.5, "y": 0.5, "scale": 0.7}],
    "house": [{"type": "house", "x": 0.5, "y": 0.55, "scale": 0.8}],
    "tower": [{"type": "building", "x": 0.5, "y": 0.45, "scale": 0.9}],
    "church": [{"type": "building", "x": 0.5, "y": 0.5, "scale": 0.7}, {"type": "cross", "x": 0.5, "y": 0.3, "scale": 1.2}],
    "wall": [{"type": "rect", "x": 0.5, "y": 0.5, "width": 0.4, "height": 0.15, "fill": [160, 140, 120, 180], "stroke": [100, 85, 70]}],

    # Nature
    "tree": [{"type": "tree", "x": 0.5, "y": 0.55, "scale": 0.7}],
    "forest": [{"type": "tree", "x": 0.2, "y": 0.55, "scale": 0.6}, {"type": "tree", "x": 0.4, "y": 0.5, "scale": 0.7}, {"type": "tree", "x": 0.6, "y": 0.55, "scale": 0.6}],
    "flower": [{"type": "circle", "x": 0.5, "y": 0.55, "radius": 0.02, "fill": [255, 150, 150, 200]}, {"type": "circle", "x": 0.5, "y": 0.57, "radius": 0.01, "fill": [255, 200, 50, 200]}],
    "cloud": [{"type": "cloud", "x": 0.5, "y": 0.2, "scale": 0.7}],
    "rain": [{"type": "cloud", "x": 0.5, "y": 0.2, "scale": 0.7}, {"type": "line", "x": 0.4, "y": 0.3, "x2": 0.4, "y2": 0.4, "stroke": [150, 180, 220], "stroke_width": 1}],
    "wind": [{"type": "line", "x": 0.3, "y": 0.35, "x2": 0.7, "y2": 0.35, "stroke": [180, 190, 200, 100], "stroke_width": 2}],
    "animal": [{"type": "animal", "x": 0.5, "y": 0.55, "scale": 1.0}],
    "bird": [{"type": "bird", "x": 0.5, "y": 0.3, "scale": 1.0}],
    "fish": [{"type": "fish", "x": 0.5, "y": 0.5, "scale": 1.0}],
    "horse": [{"type": "animal", "x": 0.5, "y": 0.55, "scale": 1.2, "fill": [120, 80, 60]}],
    "camel": [{"type": "animal", "x": 0.5, "y": 0.55, "scale": 1.2, "fill": [180, 160, 120]}],
    "monster": [{"type": "animal", "x": 0.5, "y": 0.5, "scale": 1.5, "fill": [60, 100, 60]}],

    # Time / history
    "century": [{"type": "clock", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "year": [{"type": "clock", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "time": [{"type": "clock", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "age": [{"type": "clock", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "history": [{"type": "scroll", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "clock", "x": 0.7, "y": 0.3, "scale": 1.2}],
    "ancient": [{"type": "book", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "scroll", "x": 0.7, "y": 0.5, "scale": 1.2}],

    # Ideas / discovery
    "idea": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.5}],
    "brilliant": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.8}],
    "genius": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.8}],
    "discover": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.5}, {"type": "globe", "x": 0.7, "y": 0.5, "scale": 1.2}],
    "invent": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.5}, {"type": "gear", "x": 0.7, "y": 0.5, "scale": 1.2}],
    "solution": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.5}],
    "problem": [{"type": "question_mark", "x": 0.5, "y": 0.35, "scale": 1.5}],
    "question": [{"type": "question_mark", "x": 0.5, "y": 0.35, "scale": 1.5}],
    "answer": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.5}, {"type": "book", "x": 0.7, "y": 0.5, "scale": 1.2}],
    "impossible": [{"type": "question_mark", "x": 0.5, "y": 0.35, "scale": 2.0}],

    # Danger / fear
    "danger": [{"type": "skull", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "death": [{"type": "skull", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "lost": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5}, {"type": "question_mark", "x": 0.7, "y": 0.3, "scale": 1.2}],
    "wrong": [{"type": "x_mark", "x": 0.5, "y": 0.4, "scale": 1.2, "fill": [180, 40, 40]}],

    # Printing / press
    "print": [{"type": "printing_press", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "press": [{"type": "printing_press", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "gutenberg": [{"type": "printing_press", "x": 0.5, "y": 0.45, "scale": 1.8}],

    # Religion / faith
    "faith": [{"type": "cross", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "god": [{"type": "cross", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "spiritual": [{"type": "cross", "x": 0.5, "y": 0.4, "scale": 1.5}],

    # Wealth / treasure
    "treasure": [{"type": "coin", "x": 0.45, "y": 0.45, "scale": 1.5}, {"type": "coin", "x": 0.55, "y": 0.5, "scale": 1.5}, {"type": "key", "x": 0.5, "y": 0.6, "scale": 1.2}],
    "gold": [{"type": "coin", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "money": [{"type": "coin", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "treasure": [{"type": "coin", "x": 0.5, "y": 0.45, "scale": 1.5}],

    # Power
    "king": [{"type": "crown", "x": 0.5, "y": 0.3, "scale": 1.5}],
    "queen": [{"type": "crown", "x": 0.5, "y": 0.3, "scale": 1.5}],
    "crown": [{"type": "crown", "x": 0.5, "y": 0.35, "scale": 1.5}],
    "royal": [{"type": "crown", "x": 0.5, "y": 0.35, "scale": 1.5}],

    # Technology
    "machine": [{"type": "gear", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "engine": [{"type": "gear", "x": 0.5, "y": 0.45, "scale": 1.5}],
    "mechanical": [{"type": "gear", "x": 0.5, "y": 0.45, "scale": 1.5}],

    # Science
    "science": [{"type": "telescope", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "globe", "x": 0.7, "y": 0.5, "scale": 1.2}],
    "measure": [{"type": "line", "x": 0.35, "y": 0.45, "x2": 0.65, "y2": 0.45, "stroke": [180, 80, 60], "stroke_width": 3}, {"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5}],
    "distance": [{"type": "line", "x": 0.3, "y": 0.45, "x2": 0.7, "y2": 0.45, "stroke": [60, 100, 180], "stroke_width": 2}, {"type": "arrow", "x": 0.3, "y": 0.4, "x2": 0.7, "y2": 0.4, "stroke": [60, 100, 180], "stroke_width": 2}],
    "grid": [{"type": "line", "x": 0.4, "y": 0.3, "x2": 0.4, "y2": 0.6, "stroke": [160, 150, 140], "stroke_width": 1}, {"type": "line", "x": 0.6, "y": 0.3, "x2": 0.6, "y2": 0.6, "stroke": [160, 150, 140], "stroke_width": 1}],

    # Modern
    "satellite": [{"type": "rect", "x": 0.5, "y": 0.25, "width": 0.08, "height": 0.04, "fill": [80, 80, 100, 200]}, {"type": "line", "x": 0.46, "y": 0.24, "x2": 0.44, "y2": 0.2, "stroke": [120, 120, 140], "stroke_width": 1}, {"type": "line", "x": 0.54, "y": 0.24, "x2": 0.56, "y2": 0.2, "stroke": [120, 120, 140], "stroke_width": 1}],
    "gps": [{"type": "circle", "x": 0.5, "y": 0.4, "radius": 0.03, "fill": [80, 180, 80, 100], "stroke": [60, 140, 60]}],
    "phone": [{"type": "rect", "x": 0.5, "y": 0.45, "width": 0.06, "height": 0.12, "fill": [40, 40, 50, 200], "stroke": [80, 80, 100], "stroke_width": 1, "rx": 2}],
    "pocket": [{"type": "rect", "x": 0.5, "y": 0.5, "width": 0.12, "height": 0.14, "fill": [80, 70, 60, 150], "stroke": [50, 45, 40]}],

    # Abstract
    "change": [{"type": "arrow", "x": 0.35, "y": 0.45, "x2": 0.65, "y2": 0.45, "stroke": [60, 160, 60], "stroke_width": 3}],
    "spread": [{"type": "circle", "x": 0.5, "y": 0.45, "radius": 0.05, "fill": [60, 160, 60, 80]}, {"type": "circle", "x": 0.5, "y": 0.45, "radius": 0.1, "fill": [60, 160, 60, 40]}],
    "new": [{"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 1.5}],
    "old": [{"type": "book", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "big": [{"type": "circle", "x": 0.5, "y": 0.4, "radius": 0.1, "fill": [200, 150, 100, 80], "stroke": [160, 120, 80]}],
    "small": [{"type": "circle", "x": 0.5, "y": 0.45, "radius": 0.03, "fill": [100, 150, 200, 100]}],

    # Misc
    "fire": [{"type": "fire", "x": 0.5, "y": 0.55, "scale": 1.2}],
    "light": [{"type": "lamp", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "dark": [{"type": "moon", "x": 0.5, "y": 0.2, "radius": 30}, {"type": "star", "x": 0.5, "y": 0.15, "count": 20, "brightness": 150}],
    "night": [{"type": "moon", "x": 0.5, "y": 0.2, "radius": 30}, {"type": "star", "x": 0.5, "y": 0.15, "count": 25, "brightness": 180}],
    "journey": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5}, {"type": "path", "x": 0.3, "y": 0.7, "x2": 0.7, "y2": 0.9, "width": 8, "fill": [140, 120, 90]}],
    "navigation": [{"type": "compass", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "map", "x": 0.7, "y": 0.5, "scale": 1.2}],
    "navigate": [{"type": "compass", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "ship", "x": 0.7, "y": 0.55, "scale": 0.5}],

    "memory": [{"type": "book", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5}],
    "constellation": [{"type": "star", "x": 0.5, "y": 0.2, "count": 30, "brightness": 200}],
    "climate": [{"type": "globe", "x": 0.5, "y": 0.4, "scale": 1.5}],
    "accurate": [{"type": "map", "x": 0.5, "y": 0.45, "scale": 1.5}, {"type": "compass", "x": 0.7, "y": 0.35, "scale": 1.2}],
    "reliable": [{"type": "compass", "x": 0.5, "y": 0.4, "scale": 1.5}, {"type": "map", "x": 0.7, "y": 0.5, "scale": 1.2}],
    "copies": [{"type": "printing_press", "x": 0.5, "y": 0.45, "scale": 1.5}, {"type": "book", "x": 0.7, "y": 0.45, "scale": 1.2}],
    "ordinary": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5}, {"type": "book", "x": 0.7, "y": 0.4, "scale": 1.2}],
    "triangulation": [{"type": "polygon", "x": 0.5, "y": 0.45, "points": [[0.35,0.5],[0.65,0.5],[0.5,0.25]], "fill": [180, 100, 60, 100], "stroke": [180, 80, 60]}],    
    "orbit": [{"type": "circle", "x": 0.5, "y": 0.35, "radius": 0.06, "fill": [80, 130, 255, 80], "stroke": [60, 110, 240]}, {"type": "circle", "x": 0.5, "y": 0.35, "radius": 0.02, "fill": [255, 215, 0, 100]}],
    "pocket": [{"type": "rect", "x": 0.5, "y": 0.5, "width": 0.12, "height": 0.16, "fill": [80, 70, 60, 150], "stroke": [50, 45, 40]}, {"type": "phone", "x": 0.5, "y": 0.5, "width": 0.06, "height": 0.12, "fill": [40, 40, 50, 200]}],
    "adventure": [{"type": "compass", "x": 0.5, "y": 0.35, "scale": 1.5}, {"type": "ship", "x": 0.7, "y": 0.55, "scale": 0.5}],
    "beginning": [{"type": "sun", "x": 0.5, "y": 0.3, "radius": 35}],
    "end": [{"type": "moon", "x": 0.5, "y": 0.25, "radius": 30}, {"type": "star", "x": 0.5, "y": 0.15, "count": 15, "brightness": 150}],

    # Map-specific
    "babylon": [{"type": "city", "x": 0.5, "y": 0.5, "scale": 0.7}, {"type": "text", "x": 0.5, "y": 0.15, "text": "BABYLON", "font_size": 24, "fill": [40, 35, 30]}],
    "greece": [{"type": "building", "x": 0.5, "y": 0.5, "scale": 0.7, "fill": [200, 200, 220]}, {"type": "text", "x": 0.5, "y": 0.15, "text": "GREECE", "font_size": 24, "fill": [40, 35, 30]}],
    "rome": [{"type": "building", "x": 0.5, "y": 0.5, "scale": 0.7, "fill": [180, 160, 140]}, {"type": "text", "x": 0.5, "y": 0.15, "text": "ROME", "font_size": 24, "fill": [40, 35, 30]}],
    "egypt": [{"type": "mountain", "x": 0.5, "y": 0.5, "scale": 0.6, "fill": [180, 160, 100]}, {"type": "text", "x": 0.5, "y": 0.15, "text": "EGYPT", "font_size": 24, "fill": [40, 35, 30]}],
    "china": [{"type": "building", "x": 0.5, "y": 0.5, "scale": 0.7, "fill": [160, 80, 80]}, {"type": "text", "x": 0.5, "y": 0.15, "text": "CHINA", "font_size": 24, "fill": [40, 35, 30]}],
    "europe": [{"type": "polygon", "x": 0.5, "y": 0.45, "points": [[0.4,0.35],[0.6,0.3],[0.7,0.4],[0.6,0.5],[0.4,0.5]], "fill": [100, 120, 180, 120]}],
    "africa": [{"type": "polygon", "x": 0.5, "y": 0.5, "points": [[0.4,0.45],[0.6,0.4],[0.55,0.55],[0.45,0.55]], "fill": [180, 160, 80, 120]}],
    "asia": [{"type": "polygon", "x": 0.5, "y": 0.45, "points": [[0.4,0.35],[0.7,0.3],[0.65,0.45],[0.45,0.45]], "fill": [160, 130, 60, 120]}],
    "jerusalem": [{"type": "city", "x": 0.5, "y": 0.5, "scale": 0.7}, {"type": "text", "x": 0.5, "y": 0.15, "text": "JERUSALEM", "font_size": 22, "fill": [40, 35, 30]}],
    "mediterranean": [{"type": "water", "x": 0.5, "y": 0.5, "scale": 0.7}],

    # People names
    "anaximander": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [100, 80, 120], "label": "Anaximander"}, {"type": "globe", "x": 0.7, "y": 0.35, "scale": 1.2}],
    "ptolemy": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [80, 70, 100], "label": "Ptolemy"}, {"type": "book", "x": 0.7, "y": 0.45, "scale": 1.2}],
    "mercator": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [80, 80, 100], "label": "Mercator"}, {"type": "map", "x": 0.7, "y": 0.45, "scale": 1.2}],
    "al-idrisi": [{"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [100, 80, 60], "label": "Al-Idrisi"}, {"type": "globe", "x": 0.7, "y": 0.35, "scale": 1.2}],
    "columbus": [{"type": "human", "x": 0.5, "y": 0.55, "scale": 2.5, "fill": [80, 90, 70], "label": "Columbus"}, {"type": "ship", "x": 0.7, "y": 0.5, "scale": 0.5}],
}

# ── Background map ──
BG_MAP = {
    "star": {"type": "night", "colors": [[8, 6, 28], [18, 14, 42]], "horizon": 0.55, "ground_color": [20, 18, 15]},
    "moon": {"type": "night", "colors": [[8, 6, 28], [18, 14, 42]], "horizon": 0.55, "ground_color": [20, 18, 15]},
    "night": {"type": "night", "colors": [[8, 6, 28], [18, 14, 42]], "horizon": 0.55, "ground_color": [20, 18, 15]},
    "dark": {"type": "night", "colors": [[5, 3, 20], [15, 12, 35]], "horizon": 0.55, "ground_color": [15, 13, 12]},
    "sun": {"type": "sunset", "colors": [[220, 100, 70], [200, 120, 90], [160, 80, 100], [80, 50, 80]]},
    "sunset": {"type": "sunset", "colors": [[220, 100, 70], [200, 120, 90], [160, 80, 100], [80, 50, 80]]},
    "ocean": {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [140, 180, 220], "horizon": 0.45, "water_color": [30, 70, 150]},
    "sea": {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [140, 180, 220], "horizon": 0.45, "water_color": [30, 70, 150]},
    "ship": {"type": "ocean", "sky_color": [200, 220, 240], "horizon_color": [160, 190, 220], "horizon": 0.45, "water_color": [30, 70, 150]},
    "sail": {"type": "ocean", "sky_color": [200, 220, 240], "horizon_color": [160, 190, 220], "horizon": 0.45, "water_color": [30, 70, 150]},
    "river": {"type": "gradient", "colors": [[180, 200, 220], [120, 160, 200]], "horizon": 0.5, "ground_color": [60, 80, 60]},
    "forest": {"type": "forest", "sky_color": [180, 200, 180], "horizon": 0.5, "ground_color": [40, 80, 40]},
    "tree": {"type": "forest", "sky_color": [180, 200, 180], "horizon": 0.5, "ground_color": [40, 80, 40]},
    "mountain": {"type": "gradient", "colors": [[190, 200, 210], [150, 170, 190]], "horizon": 0.55, "ground_color": [80, 100, 60]},
    "desert": {"type": "desert", "sky_color": [240, 220, 180], "horizon": 0.5, "ground_color": [200, 180, 120]},
    "city": {"type": "city", "sky_color": [200, 200, 210], "horizon": 0.5, "ground_color": [100, 100, 90]},
    "indoor": {"type": "indoor", "wall_color": [195, 175, 155], "floor_color": [135, 115, 95]},
    "house": {"type": "gradient", "colors": [[200, 210, 220], [160, 180, 200]], "horizon": 0.6, "ground_color": [60, 80, 50]},
    "fire": {"type": "night", "colors": [[15, 8, 8], [30, 18, 12]], "horizon": 0.55, "ground_color": [25, 18, 12]},
    "cloud": {"type": "gradient", "colors": [[210, 215, 220], [180, 190, 200]], "horizon": 0.6, "ground_color": [100, 110, 90]},
    "space": {"type": "night", "colors": [[2, 2, 15], [8, 8, 30]], "horizon": 0.5, "ground_color": [5, 5, 10]},
}

DEFAULT_BG = {"type": "gradient", "colors": [[200, 190, 180], [160, 150, 140]], "horizon": 0.6, "ground_color": [80, 70, 55]}

# ── Mood mapping ──
MOOD_MAP = {
    "idea": "hopeful", "discover": "hopeful", "brilliant": "hopeful", "solution": "hopeful",
    "new": "hopeful", "genius": "hopeful", "birth": "hopeful",
    "danger": "dramatic", "death": "somber", "wrong": "dramatic", "problem": "dramatic",
    "impossible": "dramatic", "lost": "somber",
    "star": "peaceful", "moon": "peaceful", "night": "peaceful", "sun": "peaceful",
    "ocean": "peaceful", "river": "peaceful",
    "ancient": "mysterious", "faith": "mysterious", "spiritual": "mysterious",
    "god": "mysterious", "monster": "mysterious",
    "king": "epic", "world": "epic", "history": "epic", "journey": "epic",
    "adventure": "epic", "satellite": "epic", "space": "epic",
}

DEFAULT_MOOD = "peaceful"

# ── Camera movement map ──
CAMERA_MAP = {
    "world": "ken_burns_in",
    "earth": "ken_burns_in", 
    "map": "ken_burns_in",
    "star": "pan_right",
    "night": "pan_right",
    "sky": "pan_right",
    "ocean": "pan_right",
    "sea": "pan_right",
    "travel": "pan_left",
    "journey": "pan_left",
    "river": "pan_right",
    "mountain": "dolly_in",
    "peak": "dolly_in",
    "building": "dolly_in",
    "discover": "ken_burns_out",
    "adventure": "ken_burns_out",
    "end": "ken_burns_out",
    "close": "dolly_in",
}

# ── Mapper function ──

def map_narration(narration: str):
    """Map a narration sentence to a full visual scene description."""
    text = narration.lower().strip()
    
    # Find matching keywords (longest match first)
    words = text.split()
    matched = []
    i = 0
    while i < len(words):
        best_key = None
        best_len = 0
        for key in ELEMENT_MAP:
            kwords = key.split()
            if i + len(kwords) <= len(words):
                if words[i:i+len(kwords)] == kwords:
                    if len(kwords) > best_len:
                        best_key = key
                        best_len = len(kwords)
        if best_key:
            matched.append(best_key)
            i += best_len
        else:
            i += 1

    # If no direct match, try partial word matching
    if not matched:
        for w in words:
            w_clean = w.strip(".,!?;:'\"")
            for key in ELEMENT_MAP:
                if w_clean in key or key in w_clean:
                    if key not in matched:
                        matched.append(key)
                    break

    # Pick elements (deduplicate, limit to 3)
    chosen = []
    seen_types = set()
    for key in matched:
        for cand in ELEMENT_MAP[key]:
            if cand["type"] not in seen_types or len(chosen) < 2:
                chosen.append(dict(cand))
                seen_types.add(cand["type"])
                if len(chosen) >= 3:
                    break
        if len(chosen) >= 3:
            break

    if not chosen:
        # Fallback: text + generic
        chosen = [{"type": "text", "x": 0.5, "y": 0.35, "text": narration[:30], "font_size": 20, "fill": [40, 35, 30]}]
        if rng.random() < 0.5:
            chosen.append({"type": "human", "x": 0.5, "y": 0.6, "scale": 2.5})

    # Pick background
    bg = DEFAULT_BG
    for key in matched:
        if key in BG_MAP:
            bg = BG_MAP[key]
            break
    # Also check individual words
    if bg == DEFAULT_BG:
        for w in words:
            wc = w.strip(".,!?;:'\"")
            if wc in BG_MAP:
                bg = BG_MAP[wc]
                break

    # Pick mood
    mood = DEFAULT_MOOD
    for key in matched:
        if key in MOOD_MAP:
            mood = MOOD_MAP[key]
            break
    if mood == DEFAULT_MOOD:
        for w in words:
            wc = w.strip(".,!?;:'\"")
            if wc in MOOD_MAP:
                mood = MOOD_MAP[wc]
                break

    # Pick camera
    camera = None
    for key in matched:
        if key in CAMERA_MAP:
            camera = CAMERA_MAP[key]
            break
    if not camera:
        for w in words:
            wc = w.strip(".,!?;:'\"")
            if wc in CAMERA_MAP:
                camera = CAMERA_MAP[wc]
                break

    # Randomize positions slightly so every scene looks unique
    for e in chosen:
        if "x" in e and isinstance(e["x"], (int, float)):
            e["x"] = round(max(0.1, min(0.9, e["x"] + rng.uniform(-0.05, 0.05))), 2)
        if "y" in e and isinstance(e["y"], (int, float)):
            e["y"] = round(max(0.1, min(0.85, e["y"] + rng.uniform(-0.03, 0.03))), 2)

    return {
        "bg": bg,
        "elements": chosen,
        "atmosphere": {"particles": "none", "fog": rng.random() < 0.2},
    }, mood, camera
