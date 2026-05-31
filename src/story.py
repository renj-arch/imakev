"""Manages continuous story chapters - each video continues from the last."""

import json
from pathlib import Path
import config

STORY_FILE = config.ROOT_DIR / "story_state.json"

DEFAULT_STORY = {
    "chapter": 1,
    "previous_title": "Cat Kidnapping & Bike Rescue Squad",
    "previous_summary": (
        "In the neon-lit dream city, a mysterious cat villain kidnapped a child. "
        "A brave rescue squad on futuristic bicycles chased the villain through impossible streets. "
        "They caught the cat villain, rescued the child, and justice prevailed."
    ),
    "series": "Neon City Chronicles",
    "world_state": "child rescued, cat villain caught, city still bending",
}


def load_story() -> dict:
    if STORY_FILE.exists():
        with open(STORY_FILE) as f:
            return json.load(f)
    return dict(DEFAULT_STORY)


def save_story(story: dict):
    with open(STORY_FILE, "w") as f:
        json.dump(story, f, indent=2)


def next_chapter() -> dict:
    story = load_story()
    chapter = story["chapter"] + 1
    prev = story["previous_summary"]

    # Build next chapter prompts based on previous
    scenarios = {
        2: {
            "title": "The Cat Villain's Revenge",
            "prompt": "The cat villain escapes from custody and seeks revenge on the rescue squad. The children must defend their city.",
            "scenes": [
                "cat villain breaking out of prison, neon chains shattering, dramatic cinematic",
                "rescue squad children alerted by holographic alarm, determined faces, cinematic",
                "cat villain stalking through neon city, glowing eyes, revenge, cinematic",
                "children riding bicycles through city preparing for battle, cinematic",
                "showdown between rescue squad and cat villain on neon bridge, epic standoff, cinematic",
                "cat villain defeated again, but escapes into the shadows, cinematic ending",
            ],
            "subtitles": [
                "The cat villain breaks free from his neon prison, vengeance in his glowing eyes.",
                "The rescue squad is alerted. The city needs them once more.",
                "Through the neon streets, the villain stalks his prey.",
                "The children mount their light-cycles, ready for battle.",
                "An epic showdown on the neon bridge. The city holds its breath.",
                "The villain escapes into the shadows. The story continues...",
            ],
        },
        3: {
            "title": "The Hacker's Secret",
            "prompt": "A mysterious hacker joins the cat villain, corrupting the city's AI systems. The rescue squad must find the source.",
            "scenes": [
                "mysterious hacker in hoodie surrounded by holographic screens, cyberpunk cinematic",
                "city AI glitching, neon lights flickering, digital corruption spreading",
                "rescue squad investigating corrupted data streams on their bikes, cinematic",
                "chase through digital landscape with glitching buildings, surreal",
                "confrontation with the hacker in a neon data center, cinematic",
                "hacker escapes but leaves a cryptic message, the story deepens",
            ],
            "subtitles": [
                "A mysterious figure emerges from the digital underworld.",
                "The city's AI begins to glitch and corrupt around them.",
                "The rescue squad investigates the data streams, following the digital trail.",
                "They ride through a glitching cityscape where reality bends and warps.",
                "In the heart of the data center, they confront the hacker.",
                "The hacker vanishes, but leaves a cryptic clue behind...",
            ],
        },
    }

    scenario = scenarios.get(chapter, {
        "title": f"Neon City Chronicles - Chapter {chapter}",
        "prompt": f"Continuing from: {prev}. New adventure in the neon dream city.",
        "scenes": [f"cinematic scene {i+1} of the neon city, chapter {chapter}" for i in range(6)],
        "subtitles": [f"Chapter {chapter} unfolds..." for _ in range(6)],
    })

    story["chapter"] = chapter
    story["previous_title"] = scenario["title"]
    story["previous_summary"] = scenario["prompt"]
    save_story(story)

    return {
        "chapter": chapter,
        "title": scenario["title"],
        "script": scenario["prompt"],
        "scenes": scenario["scenes"],
        "subtitles": scenario["subtitles"],
    }
