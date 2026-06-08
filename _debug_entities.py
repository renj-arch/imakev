"""Compare ENTITIES lists to find missing entries."""
import sys, re
sys.path.insert(0, '.')

# Read the file
with open('auto_story.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Get global _ENTITY_MAP
exec(compile(content.split('def _extract_entities')[0] + '\n_GLOBAL_MAP = _ENTITY_MAP', 'auto_story.py', 'exec'))

# Get local ENTITIES list
local_start = content.find('def _extract_entities')
local_code = content[local_start:]

# Find ENTITIES list
entities_start = local_code.find('ENTITIES = [')
# Count brackets to find the end
depth = 0
entities_end = entities_start
for i in range(entities_start, len(local_code)):
    if local_code[i] == '[':
        depth += 1
    elif local_code[i] == ']':
        depth -= 1
        if depth == 0:
            entities_end = i + 1
            break

local_block = local_code[entities_start:entities_end]

# Parse local ENTITIES tuples
local_phrases = set()
for m in re.finditer(r'\("([^"]+)"', local_block):
    local_phrases.add(m.group(1))

# Compare with global _ENTITY_MAP
global_phrases = set(_GLOBAL_MAP.keys())
missing = global_phrases - local_phrases

print(f"Global _ENTITY_MAP entries: {len(global_phrases)}")
print(f"Local ENTITIES entries: {len(local_phrases)}")
print(f"Missing from local: {len(missing)}")
print()

# Filter to meaningful ones
meaningful = sorted([p for p in missing if len(p) >= 3 and not p.isdigit()])
print(f"Meaningful missing entries ({len(meaningful)}):")
for p in meaningful:
    e = _GLOBAL_MAP[p]
    print(f'  "{p}" -> {e["type"]}')
