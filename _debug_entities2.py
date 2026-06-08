"""Find missing ENTITIES by searching for patterns."""
import sys, re
sys.path.insert(0, '.')
with open('auto_story.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Split global _ENTITY_MAP and local ENTITIES
parts = content.split('# ═══════════════════════════════════════════════════════════════')
# The global map is before the second occurrence of this separator
# Actually let me find where global _ENTITY_MAP starts

# Find global _ENTITY_MAP (the earlier one used by _infer_visuals)
global_start = content.find('_ENTITY_MAP = {')
global_end = content.find('\n\n', content.find('}', global_start)) 
if global_end < global_start:
    global_end = content.find('\n\n\n', global_start)

# Find local ENTITIES (the one in _extract_entities)
local_fn_start = content.find('def _extract_entities(text: str)')
entities_start = content.find('ENTITIES = [', local_fn_start)
# Find matching close bracket
depth = 0
entities_end = entities_start
for i in range(entities_start, len(content)):
    if content[i] == '[': depth += 1
    elif content[i] == ']':
        depth -= 1
        if depth == 0:
            entities_end = i + 1
            break

# Extract local phrases
local_block = content[entities_start:entities_end]
local_phrases = set()
for m in re.finditer(r'\("([^"]+)"', local_block):
    local_phrases.add(m.group(1))

# Extract global phrases
global_block = content[global_start:global_end+200]
global_phrases = set()
for m in re.finditer(r'"([^"]+)":\s*\{', global_block):
    global_phrases.add(m.group(1))

missing = global_phrases - local_phrases
print(f"Global _ENTITY_MAP phrases: {len(global_phrases)}")
print(f"Local ENTITIES phrases: {len(local_phrases)}")
print(f"Missing from local: {len(missing)}")
print()
meaningful = sorted([p for p in missing if len(p) >= 3 and not p.isdigit()])
for p in meaningful:
    print(f'  "{p}"')
