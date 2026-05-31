"""Self-generating continuous kid's story — 'Pajama Explorers' series."""

import json, re
from pathlib import Path
import config
from src.script_generator import generate_script

STORY_FILE = config.ROOT_DIR / "story_state.json"

DEFAULT_STORY = {
    "chapter": 1,
    "previous_title": "The First Flight",
    "previous_summary": (
        "Three kids — Mia, Leo, and Sam — discover that at midnight their beds sprout feathery wings "
        "and fly out the window. They soar over the sleeping city, through clouds that taste like cotton candy, "
        "and land in a glowing meadow where fireflies spell out messages. A friendly talking fox named Ember "
        "greets them and says they've been chosen as the new Pajama Explorers. Their first mission: "
        "find the lost Lullaby Crystal before the shadow creatures silence all dreams forever."
    ),
    "world_state": "Pajama Explorers formed, Ember the fox is guide, searching for Lullaby Crystal",
}

KID_FANTASY_WORLDS = [
    "a forest where trees grow candy instead of fruit",
    "a floating island city held up by giant balloons",
    "an underground river of glowing rainbow water",
    "a desert made of sparkling crystal sand",
    "a cloud kingdom where buildings are made of marshmallow",
    "a cave where the walls are painted with stories that move",
    "a garden where flowers sing different songs",
    "a library where the books fly and whisper their plots",
    "a lake that reflects your dreams instead of your face",
    "a mountain with stairs that rearrange themselves",
    "a village of tiny fox-people who ride ladybugs",
    "a frozen palace made of starlight",
    "a jungle where the vines form bridges that play music when you step on them",
    "a sea of clouds with ships that sail on moonbeams",
]


def load_story() -> dict:
    if STORY_FILE.exists():
        with open(STORY_FILE) as f:
            return json.load(f)
    return dict(DEFAULT_STORY)


def save_story(story: dict):
    with open(STORY_FILE, "w") as f:
        json.dump(story, f, indent=2)


def parse_llm_response(text: str) -> dict | None:
    scenes = re.findall(r"(?:SCENE|Scene)\s*\d+[:\s]+(.+)", text)
    subtitles = re.findall(r"(?:SUBTITLE|Subtitle)\s*\d+[:\s]+(.+)", text)

    if not scenes:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 20]
        if paragraphs:
            scenes = paragraphs[:5]
            subtitles = scenes

    if scenes:
        prompts = []
        for s in scenes:
            keywords = s.lower()[:80]
            prompts.append(f"whimsical children's book illustration: {keywords}, magical colorful dreamlike, 9:16 vertical, soft lighting, vibrant pastels")
        return {
            "title": scenes[0][:50] if scenes else "Next Adventure",
            "script": ". ".join(subtitles) if subtitles else ". ".join(scenes),
            "scenes": prompts[:5],
            "subtitles": subtitles[:5] if subtitles else scenes[:5],
        }
    return None


def generate_next_chapter_via_llm(previous_summary: str, chapter: int) -> dict:
    import random
    new_world = random.choice(KID_FANTASY_WORLDS)

    prompt = (
        f"You are writing 'Pajama Explorers', a children's adventure series. "
        f"Three kids — Mia, Leo, and Sam — fly on their magical beds to dream worlds every midnight. "
        f"Ember the talking fox guides them.\n\n"
        f"Previously: {previous_summary}\n\n"
        f"Write Chapter {chapter}. This time they visit {new_world}.\n"
        f"Give me exactly 5 scenes with:\n"
        f"- SCENE 1: (visual description for illustration)\n"
        f"- SUBTITLE 1: (short spoken line, age 6-10 friendly)\n"
        f"... up to SCENE 5 and SUBTITLE 5.\n\n"
        f"Make it imaginative, gentle, and full of wonder. No scary villains. "
        f"End with them flying home safely as morning approaches."
    )

    result = generate_script(
        niche="children's fantasy adventure",
        topic=prompt,
    )

    if result and len(result) > 50:
        parsed = parse_llm_response(result)
        if parsed:
            return parsed

    return _fallback_chapter(chapter, new_world)


def _fallback_chapter(chapter: int, world: str) -> dict:
    titles = [
        f"The {world.split('where')[0].strip()} Adventure",
        f"Chapter {chapter}: A New Dream",
        f"The Midnight Flight to {world.split('where')[0].strip()}",
    ]
    scenes = [
        f"whimsical illustration: the three kids flying on their beds through a starry night sky, moonlight streaming past, cozy pajamas",
        f"whimsical illustration: {world}, vibrant colorful magical dream scene, children exploring with wonder",
        f"whimsical illustration: a friendly creature approaches the kids, offering help with bright curious eyes",
        f"whimsical illustration: the kids discover a magical object glowing with warm light, surrounded by floating sparkles",
        f"whimsical illustration: the kids fly home on their beds as the sun begins to rise, city rooftops below",
    ]
    subtitles = [
        f"At midnight, the beds began to glow. Mia, Leo, and Sam knew what that meant.",
        f"They fluttered down into the most amazing place they had ever seen.",
        f"A friendly creature peeked out. 'You're the Pajama Explorers!' it said.",
        f"Deep in the heart of the dream, they found something magical waiting just for them.",
        f"As the first light touched the sky, their beds lifted them gently home.",
    ]
    return {
        "title": f"Chapter {chapter}: {titles[0]}",
        "script": ". ".join(subtitles),
        "scenes": scenes[:5],
        "subtitles": subtitles[:5],
    }


def next_chapter() -> dict:
    story = load_story()
    chapter = story["chapter"] + 1

    print(f"\n  Writing Pajama Explorers Chapter {chapter}...")

    result = generate_next_chapter_via_llm(story["previous_summary"], chapter)

    title = result.get("title", f"Chapter {chapter}")
    script = result.get("script", "The adventure continues...")
    scenes = result.get("scenes", [])
    subtitles = result.get("subtitles", [])

    story["chapter"] = chapter
    story["previous_title"] = title
    story["previous_summary"] = f"Chapter {chapter}: {script[:200]}"
    story["world_state"] = f"Pajama Explorers, chapter {chapter}"
    save_story(story)

    print(f"  {title}")
    print(f"  {len(scenes)} scenes generated")

    return {
        "chapter": chapter,
        "title": title,
        "script": script,
        "scenes": scenes,
        "subtitles": subtitles,
    }
