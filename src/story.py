"""Self-generating continuous story — uses LLM to write each next chapter automatically."""

import json, re
from pathlib import Path
import config
from src.script_generator import generate_script

STORY_FILE = config.ROOT_DIR / "story_state.json"

DEFAULT_STORY = {
    "chapter": 1,
    "previous_title": "Cat Kidnapping & Bike Rescue Squad",
    "previous_summary": (
        "In the neon-lit dream city, a cat villain kidnapped a child. "
        "A rescue squad on futuristic bicycles chased the villain through impossible streets. "
        "The squad caught the villain and rescued the child."
    ),
    "world_state": "Neon city, rescue squad formed, villain caught, child rescued",
}


def load_story() -> dict:
    if STORY_FILE.exists():
        with open(STORY_FILE) as f:
            return json.load(f)
    return dict(DEFAULT_STORY)


def save_story(story: dict):
    with open(STORY_FILE, "w") as f:
        json.dump(story, f, indent=2)


def parse_llm_response(text: str) -> dict | None:
    """Parse structured output from LLM into scenes and subtitles."""
    scenes = re.findall(r"(?:SCENE|Scene)\s*\d+[:\s]+(.+)", text)
    subtitles = re.findall(r"(?:SUBTITLE|Subtitle)\s*\d+[:\s]+(.+)", text)

    # Fallback: split by double newlines
    if not scenes:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 20]
        if paragraphs:
            scenes = paragraphs[:6]
            subtitles = scenes

    # Generate default prompts from subtitles
    if scenes:
        prompts = []
        for s in scenes:
            keywords = s.lower()[:60]
            prompts.append(f"cinematic scene: {keywords}, neon cyberpunk style, 9:16 vertical, highly detailed")
        return {
            "title": scenes[0][:50] if scenes else "Next Chapter",
            "script": ". ".join(subtitles) if subtitles else ". ".join(scenes),
            "scenes": prompts[:6],
            "subtitles": subtitles[:6] if subtitles else scenes[:6],
        }
    return None


def generate_next_chapter_via_llm(previous_summary: str, chapter: int) -> dict:
    """Ask LLM to write the next chapter."""
    prompt = (
        f"You are writing the next chapter of a cinematic neon-noir series set in a dreamlike cyberpunk city.\n\n"
        f"Previously: {previous_summary}\n\n"
        f"Write Chapter {chapter} of the story. Give me exactly 5 scenes with:\n"
        f"- SCENE 1: (description, for image generation)\n"
        f"- SUBTITLE 1: (spoken line)\n"
        f"... up to SCENE 5 and SUBTITLE 5.\n\n"
        f"Make it cinematic, visual, action-packed. New events only."
    )

    result = generate_script(
        niche="cinematic cyberpunk story",
        topic=prompt,
    )

    if result and len(result) > 50:
        parsed = parse_llm_response(result)
        if parsed:
            return parsed

    # Fallback: generate 5 generic scenes
    return {
        "title": f"Chapter {chapter}: The Story Continues",
        "script": f"The neon city pulses with new energy. Something stirs in the shadows.",
        "scenes": [
            f"cinematic scene: the neon city at night, chapter {chapter}, dramatic lighting",
            f"cinematic scene: mysterious figure emerges from shadows, tension building",
            f"cinematic scene: fast pursuit through glowing streets, energy and motion",
            f"cinematic scene: dramatic confrontation under neon lights",
            f"cinematic scene: aftermath, city skyline, cinematic wide shot",
        ],
        "subtitles": [
            f"The neon city pulses with new energy. Chapter {chapter} begins.",
            "A mysterious figure emerges from the shadows of the dream city.",
            "The chase begins again through streets of light and code.",
            "Under the neon sky, destinies collide in a burst of light.",
            "The city breathes. The story continues...",
        ],
    }


def next_chapter() -> dict:
    story = load_story()
    chapter = story["chapter"] + 1

    print(f"\n  Writing Chapter {chapter} via LLM...")

    result = generate_next_chapter_via_llm(story["previous_summary"], chapter)

    title = result.get("title", f"Chapter {chapter}")
    script = result.get("script", "The story continues...")
    scenes = result.get("scenes", [])
    subtitles = result.get("subtitles", [])

    # Update story state
    story["chapter"] = chapter
    story["previous_title"] = title
    story["previous_summary"] = f"Chapter {chapter}: {script[:200]}"
    story["world_state"] = f"Neon city, chapter {chapter}"
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
