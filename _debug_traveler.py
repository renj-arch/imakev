"""Debug scene by scene for Traveler's Map."""
import sys
sys.path.insert(0, '.')
from auto_story import _infer_visuals_local, _enrich_story_context, _extract_entities

texts = [
    "A traveler bought a map showing every road.",
    "He followed it perfectly.",
    "Years later he realized he had never discovered anything unexpected. The next journey, he occasionally left the path.",
    "That's when the stories began.",
]

total = len(texts)
state = {"bg": None, "entity_history": [], "prev_elements": []}

for scene_num, text in enumerate(texts, 1):
    print(f"=== SCENE {scene_num}/{total}: {text[:60]}... ===")
    entities = _extract_entities(text)
    print(f"  Entities: {[e[0] for e in entities]}")
    
    r = _infer_visuals_local(text, scene_num, total)
    if r:
        vis = r.get("visual", {})
        elements = vis.get("elements", [])
        print(f"  After _infer_visuals_local ({len(elements)} elems):")
        for e in elements:
            print(f'    {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')
        
        visuals = {"visual": vis}
        _enrich_story_context(visuals, text, state, scene_num, total)
        enriched = visuals.get("visual", {}).get("elements", [])
        print(f"  After _enrich_story_context ({len(enriched)} elems):")
        for e in enriched:
            print(f'    {e["type"]} x={e.get("x",0):.2f} y={e.get("y",0):.2f} s={e.get("scale",1):.2f}')
    print()
