"""Debug action handlers — tests through _enrich_story_context where actions now live."""
import sys, re
sys.path.insert(0, '.')
from auto_story import _infer_visuals_local, _enrich_story_context

texts = [
    "One day, a child asked, \"Why are you carrying that?\"",
    "He picked up the heavy rock.",
    "The man stopped and put it down.",
]

for text in texts:
    print(f"=== {text} ===")
    r = _infer_visuals_local(text, 5, 7)
    if r:
        vis = r.get("visual", {})
        elements = vis.get("elements", [])
        print(f"  Before enrich ({len(elements)} elems):")
        for e in elements:
            print(f'    {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f}')

        # Run enrichment with mock state (need extra persistent entities for realistic test)
        state = {"entity_history": [["man", "human", "rock", "child"]], "prev_elements": [
            {"type": "man", "x": 0.5, "y": 0.5, "scale": 1},
            {"type": "human", "x": 0.6, "y": 0.5, "scale": 1},
            {"type": "rock", "x": 0.3, "y": 0.6, "scale": 1},
            {"type": "key", "x": 0.4, "y": 0.55, "scale": 1},
        ], "bg": None}
        visuals = {"visual": vis}
        _enrich_story_context(visuals, text, state, 5, 7)
        enriched = visuals.get("visual", {}).get("elements", [])
        print(f"  After enrich ({len(enriched)} elems):")
        for e in enriched:
            print(f'    {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')
    print()
