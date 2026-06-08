"""Debug scene 1 positions step by step."""
import sys
sys.path.insert(0, '.')
from auto_story import _infer_visuals_local, _enrich_story_context, _extract_entities

text = "A man found a brick on the road."
print(f"Text: {text!r}")
entities = _extract_entities(text)
print(f"Entities: {[(e[0], e[1]) for e in entities]}")

r = _infer_visuals_local(text, 1, 7)
if r:
    vis = r.get("visual", {})
    elements = vis.get("elements", [])
    print(f"After _infer_visuals_local ({len(elements)} elems):")
    for e in elements:
        print(f'  {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')

    state = {"bg": None, "entity_history": [], "prev_elements": []}
    visuals = {"visual": vis}
    _enrich_story_context(visuals, text, state, 1, 7)
    enriched = visuals.get("visual", {}).get("elements", [])
    print(f"After _enrich_story_context ({len(enriched)} elems):")
    for e in enriched:
        print(f'  {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')
