"""Test Traveler's Map story through engine."""
import sys
sys.path.insert(0, '.')
from auto_story import generate_script_from_narration

script = generate_script_from_narration("""A traveler bought a map showing every road.

He followed it perfectly.

Years later he realized he had never discovered anything unexpected.

The next journey, he occasionally left the path.

That's when the stories began.""")

for s in script["scenes"]:
    elems = s["visual"].get("elements", [])
    print(f"Scene {s['scene_num']}: {s['mood']}")
    print(f"  Narration: {s['narration'][:80]}...")
    for e in elems:
        print(f'  {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')
    print()
