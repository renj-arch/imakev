"""History Minute script generator with bank + LLM + hardcoded fallback."""

import json, random
from pathlib import Path
from src.script_generator import _generate

BANK_PATH = Path(__file__).parent.parent / "bank" / "history_minute.json"

FALLBACKS = [
    {
        "topic": "The Gettysburg Address",
        "script": "Abraham Lincoln delivered the Gettysburg Address in 1863. It was only 272 words long and took about two minutes to deliver. The speech redefined the Civil War as a struggle for freedom and equality. Today it is considered one of the greatest speeches in American history."
    },
    {
        "topic": "The Leaning Tower of Pisa",
        "script": "The Leaning Tower of Pisa started tilting during construction in 1173. The soil was too soft on one side. Engineers tried to compensate by making upper floors taller on the short side. The tilt has been reduced by 4 degrees since restoration work. It still leans at about 4 degrees today."
    },
    {
        "topic": "The First Spacewalk",
        "script": "In 1965, Soviet cosmonaut Alexei Leonov made the first spacewalk. His spacesuit ballooned so much he couldn't fit back through the airlock. He had to manually release oxygen to reduce pressure. He made it inside with just minutes of oxygen left. A truly heroic moment in space history."
    },
]

SYSTEM_PROMPT_HISTORY = """You are a YouTube Shorts history content writer. Write short, engaging scripts (25-45 seconds when spoken) about fascinating historical events.

Rules:
- Hook in the first 3 seconds
- Fast-paced and conversational
- Focus on surprising or little-known historical facts
- Single clear topic or event
- 40-80 words max

Return ONLY the script text. No titles, no metadata."""


def _load_bank() -> list[dict]:
    if not BANK_PATH.exists():
        return []
    try:
        with open(BANK_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _pick_from_bank(used_topics: set[str] | None = None) -> dict | None:
    bank = _load_bank()
    if not bank:
        return None
    available = [e for e in bank if e.get("topic") not in (used_topics or set())]
    if not available:
        available = bank
    return random.choice(available)


def _pick_fallback(used_topics: set[str] | None = None) -> dict:
    available = [f for f in FALLBACKS if f.get("topic") not in (used_topics or set())]
    if not available:
        return random.choice(FALLBACKS)
    return random.choice(available)


def generate_history_script(topic: str = "", used_topics: set[str] | None = None, temperature: float = 0.8) -> str:
    bank_entry = _pick_from_bank(used_topics)
    if bank_entry and (not topic or bank_entry.get("topic", "").lower() == topic.lower()):
        print(f"  [Bank] Using bank script: {bank_entry['topic']}")
        return bank_entry["script"]

    if topic:
        prompt = f"Niche: History\nTopic: {topic}\n\nWrite a short engaging YouTube Shorts script about this historical event:"
    else:
        prompt = f"Niche: History\n\nWrite a short engaging YouTube Shorts script about a fascinating historical event:"

    prompt += "\n\nMake it surprising and conversational. Hook in the first 3 seconds."
    try:
        script = _generate(prompt, temperature=temperature, max_tokens=350, system=SYSTEM_PROMPT_HISTORY)
        if script and len(script) > 20:
            print("  [LLM] Generated via LLM")
            return script
    except Exception as e:
        print(f"  [LLM] Error: {e}")

    fallback = _pick_fallback(used_topics)
    print(f"  [Fallback] Using fallback script: {fallback['topic']}")
    return fallback["script"]
