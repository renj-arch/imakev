"""Test action-based spatial relationships."""
import sys
sys.path.insert(0, '.')
from auto_story import generate_script_from_narration

script = generate_script_from_narration("""A man found a brick on the road.

He picked it up.

"Maybe it will be useful someday," he thought.

Years passed.

He carried the brick everywhere.

It became heavy.

Painful.

Exhausting.

One day, a child asked,

"Why are you carrying that?"

The man stopped.

He couldn't remember.

So he put it down.

And for the first time in years, the journey felt light.""")

for s in script["scenes"]:
    elems = s["visual"].get("elements", [])
    print(f"Scene {s['scene_num']}:")
    for e in elems:
        print(f'  {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')
    print()
