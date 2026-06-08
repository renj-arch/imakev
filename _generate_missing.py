"""Generate missing ENTITIES from global _ENTITY_MAP to local ENTITIES list."""
import sys, re

with open('auto_story.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Parse global _ENTITY_MAP
exec(compile(content.split('def _extract_entities')[0] + '\n_GLOBAL = _ENTITY_MAP', 'auto_story.py', 'exec'))

# Parse local ENTITIES phrases
fn_start = content.find('def _extract_entities(text: str)')
local_part = content[fn_start:]
es = local_part.find('ENTITIES = [')
depth = 0
ee = es
for i in range(es, len(local_part)):
    if local_part[i] == '[':
        depth += 1
    elif local_part[i] == ']':
        depth -= 1
        if depth == 0:
            ee = i + 1
            break
local_block = local_part[es:ee]
local_phrases = set()
for m in re.finditer(r'\("([^"]+)"', local_block):
    local_phrases.add(m.group(1))

# Global phrases
global_phrases = set(_GLOBAL.keys())
missing = global_phrases - local_phrases

# Color map for entity types
TYPE_COLORS = {
    "book": (180, 140, 100),
    "star": (255, 220, 80),
    "eye": (200, 180, 160),
    "hand": (200, 180, 160),
    "arrow": (160, 140, 100),
    "human": (80, 60, 120),
    "building": (140, 130, 150),
    "animal": (120, 100, 80),
    "bird": (60, 50, 40),
    "tree": (50, 120, 50),
    "plant": (50, 120, 50),
    "flower": (255, 100, 150),
    "rock": (160, 140, 120),
    "water": (40, 100, 180),
    "fire": (220, 120, 40),
    "mountain": (100, 90, 80),
    "hill": (140, 120, 80),
    "circle": (180, 180, 180),
    "cloud": (200, 200, 210),
    "compass": (180, 150, 80),
    "crown": (200, 180, 60),
    "key": (180, 160, 100),
    "clock": (180, 180, 160),
    "globe": (80, 160, 180),
    "skull": (220, 210, 190),
    "shadow_figure": (30, 35, 40),
    "moon_path": (180, 200, 220),
    "path": (140, 120, 80),
    "gear": (160, 150, 140),
    "lamp": (255, 220, 100),
    "totem": (120, 105, 85),
    "anchor": (80, 75, 70),
    "fish": (140, 160, 180),
    "house": (180, 160, 140),
    "ship": (80, 60, 40),
    "man": (70, 50, 100),
    "woman": (100, 80, 130),
    "child": (120, 110, 130),
    "sun": (255, 200, 80),
    "moon": (220, 220, 200),
    "heart": (200, 50, 70),
    "cross": (120, 80, 60),
    "hourglass": (180, 160, 140),
    "telescope": (100, 140, 180),
    "signal": (100, 200, 100),
    "filter": (120, 160, 200),
    "camera": (80, 80, 80),
    "brain": (200, 180, 200),
    "scroll": (220, 200, 170),
    "eye": (255, 250, 240),
    "fruit": (220, 180, 80),
    "awareness": (200, 220, 255),
    "discard": (120, 80, 80),
    "movement": (180, 200, 100),
    "color_swatch": (255, 200, 100),
    "edge": (200, 180, 160),
    "boat": (80, 55, 35),
    "canoe": (80, 55, 35),
}

print("Missing entries to add to local ENTITIES:\n")
print("# ── Migrated from global _ENTITY_MAP (missing from local) ──")
for p in sorted(missing):
    e = _GLOBAL[p]
    t = e["type"]
    c = TYPE_COLORS.get(t, (160, 140, 120))
    w = 3
    print(f'        ("{p}", "{t}", {c}, {w}),')
