"""Render crocodile narration scenes as images."""
import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from auto_story import generate_script_from_narration
from src.sketch_generator import SketchGenerator

NARRATION = """Sixty-six million years ago, the world ended. An asteroid slammed into Earth. Forests burned. The sky darkened. Food chains collapsed. And the dinosaurs, rulers of the planet for over 150 million years, disappeared. Yet somehow, one ancient predator survived. A creature so old that if you saw its ancestors, you'd instantly recognize them. The crocodile. How did crocodiles outlive the dinosaurs themselves?

Long before humans existed, Earth belonged to reptiles. Towering dinosaurs roamed the land. Pterosaurs ruled the skies. Gigantic marine reptiles hunted the oceans. Among them lived the ancestors of modern crocodiles. But they weren't exactly like today's crocodiles. Some were small and agile. Some ran on land. Others became powerful aquatic hunters. The crocodile family experimented with many lifestyles. Most eventually disappeared. Only a few lineages remained.

Then came the asteroid. A mountain-sized rock hurtling through space. When it struck Earth, the explosion released unimaginable energy. Dust and ash filled the atmosphere. Sunlight struggled to reach the ground. Plants died. Animals that depended on plants died. Then predators starved too. The entire ecosystem began collapsing. Many large animals had no way to survive.

But crocodiles had something special. First, they didn't need much food. Unlike warm-blooded mammals and many dinosaurs, crocodiles are cold-blooded. Their bodies use energy very efficiently. A crocodile can survive for astonishingly long periods with little food. While other predators starved quickly, crocodiles could wait. Patiently. Silently.

Crocodiles are masters of patience. Imagine a hungry dinosaur needing food constantly. Now imagine a crocodile spending hours barely moving, days drifting in water, weeks conserving energy. When disaster struck, this ability became a superpower. The crocodile's strategy wasn't speed, intelligence, or strength. It was patience. Water also became a refuge. Lakes, rivers, and wetlands suffered less dramatic temperature swings than the land. Aquatic ecosystems continued functioning longer than many forests. Crocodiles already lived there, perfectly positioned to ride out the catastrophe.

Crocodiles are opportunists, not picky eaters. Fish, birds, small animals, carrion — whatever is available. They don't depend on a single food source. When ecosystems became chaotic, flexibility mattered. The more options an animal had, the better its chances.

Years passed into decades, then centuries. The world slowly recovered. New forests grew. New ecosystems formed. The dinosaurs never returned, but crocodiles remained. Waiting. Watching. Surviving. Today, crocodiles are called living fossils. Their basic design proved remarkably successful through asteroid impacts, mass extinctions, ice ages, and changing continents.

The story of crocodiles isn't about being the strongest — the dinosaurs were stronger. It isn't about being the fastest — many animals were faster. It's about adaptability, efficiency, and patience. When Earth faced one of the worst disasters in its history, those traits mattered more than power. So if you visit a river today and see a crocodile gliding through the water, you're looking at a survivor from a world long gone. A predator whose ancestors watched the age of dinosaurs rise and fall."""

# ── Generate scenes from narration ──
print("Generating scenes from narration...")
script = generate_script_from_narration(NARRATION)
scenes = script["scenes"]
print(f"Total scenes: {len(scenes)}\n")

# ── Render each scene as an image ──
for s in scenes:
    snum = s["scene_num"]
    title = s.get("title", "")
    mood = s.get("mood", "")
    narration = s.get("narration", "")
    visual = s.get("visual", {})
    bg = visual.get("bg", {})
    bg_type = bg.get("type", "gradient")
    elems = visual.get("elements", [])

    print(f"Scene {snum}: {title}")
    print(f"  Mood: {mood}  |  BG: {bg_type}  |  Elems: {len(elems)}")
    for e in elems:
        print(f'    {e["type"]:15s} x={e.get("x",0):.2f} y={e.get("y",0):.2f} z={e.get("z_index",2)}')
    print()

renderer = SketchGenerator(width=1024, height=768, seed=42)

print("Rendering scenes...")
for s in scenes:
    snum = s["scene_num"]
    visual = s.get("visual", {})
    img = renderer.render_scene(visual)
    filename = f"crocodile_scene{snum:02d}.png"
    filepath = os.path.join("output", filename)
    img.save(filepath)
    print(f"  Scene {snum}: {filepath}")

print("\nDone!")
