"""Fact generator — reads from content bank, LLM fallback."""

import random
import bank_manager

FACT_HOOKS = [
    "Did you know?", "This will blow your mind...",
    "Most people don't know this...", "Here's something crazy:",
    "Wait till you hear this:", "This fact is unbelievable:",
    "You won't believe this:", "Mind-blowing fact:",
]

NICHE_NAMES = [
    "space", "animals", "history", "science", "psychology",
    "human body", "ocean", "technology", "brain", "nature", "physics",
]

FALLBACK_FACTS = [
    "A day on Venus is longer than a year on Venus.",
    "Octopuses have three hearts and blue blood.",
    "Cleopatra lived closer to the iPhone than to the Great Pyramid.",
    "Water can boil and freeze at the same time at the triple point.",
    "The brain processes rejection similarly to physical pain.",
    "Your nose can distinguish over 1 trillion scents.",
    "About 94 percent of life on Earth lives in the ocean.",
    "The first computer virus was called Elk Cloner from 1983.",
    "Yawning helps cool down your brain.",
    "Trees communicate through underground fungal networks.",
    "Light takes about 8 minutes to reach Earth from the Sun.",
    "The first Olympic Games in 776 BC had only one footrace event.",
    "Bananas are technically berries but strawberries are not.",
    "A group of flamingos is called a flamboyance.",
    "Honey never spoils — jars over 3,000 years old are still edible.",
]


def generate_fact_script(niche: str = "") -> dict:
    entry = bank_manager.pick("facts")
    if entry:
        print(f"  Using banked facts ({bank_manager.count('facts')} left)")
        return entry

    print("  Bank empty, generating fresh facts...")
    if not niche:
        niche = random.choice(NICHE_NAMES)
    print(f"  Generating facts about: {niche}")

    facts = _try_llm(niche)
    if not facts:
        print("  LLM unavailable, using fallback bank")
        facts = random.sample(FALLBACK_FACTS, min(5, len(FALLBACK_FACTS)))

    hook = random.choice(FACT_HOOKS)
    title = f"{hook} {facts[0][:60]}..." if facts else f"Amazing {niche} Facts"

    image_prompts = []
    for fact in facts:
        keywords = fact.split()[:15]
        image_prompts.append(f"cinematic illustration: {' '.join(keywords)}, atmospheric lighting, 9:16 vertical, highly detailed, moody")

    tts_script = f"{hook} {' '.join(facts)}"

    return {
        "title": title[:70],
        "niche": niche,
        "hook": hook,
        "facts": facts,
        "image_prompts": image_prompts,
        "script": tts_script,
        "tts_script": tts_script,
    }


def _try_llm(niche: str) -> list | None:
    try:
        from src.script_generator import _generate
        prompt = (
            f"Write 5 surprising true facts about {niche}. "
            f"Each fact must be 100% accurate and well-known. "
            f"Number them 1-5, one per line."
        )
        system = "You write verified facts. Only include facts you are certain are true. One fact per line, numbered."
        raw = _generate(prompt, temperature=0.7, max_tokens=600, system=system)
        if not raw:
            return None
        facts = []
        for line in raw.split("\n"):
            line = line.strip().lstrip("*- ")
            if not line:
                continue
            if line[0].isdigit() and (". " in line[:4] or ") " in line[:4]):
                clean = line.split(". ", 1)[-1].split(") ", 1)[-1].strip()
                if clean and len(clean) > 10:
                    facts.append(clean.rstrip(".") + ".")
        return facts[:5] if len(facts) >= 3 else None
    except Exception as e:
        print(f"  LLM error: {e}")
        return None
