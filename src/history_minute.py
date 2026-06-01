"""History Minute generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HISTORY_HOOKS = [
    "Did you know this happened?", "History is full of surprises:",
    "You won't believe what happened in history:", "This historical event will shock you:",
    "Here's a history lesson you didn't get in school:", "Mind-blowing history fact:",
    "Most people don't know this about history:", "Wait till you hear this history story:",
]

NICHE_NAMES = [
    "ancient civilizations", "world wars", "medieval history", "famous inventors",
    "explorers", "ancient rome", "ancient egypt", "industrial revolution",
    "renaissance", "american history", "asian history", "scientific discoveries",
]

FALLBACK_SCRIPTS = [
    "The Great Fire of London in 1666 started in a baker's shop and destroyed 13,000 houses but only killed six people. That's when they started building with brick instead of wood.",
    "In 1947, engineers found a moth trapped in the Harvard Mark II computer and called it the 'first actual bug.' That's where the term computer bug comes from.",
    "Cleopatra lived closer to the iPhone than to the Great Pyramid. The pyramid was already 2,400 years old when she was born. Mind blowing.",
    "The shortest war ever was the Anglo-Zanzibar War of 1896. It lasted just 38 minutes. The British bombarded the palace and won almost instantly.",
    "Oxford University started teaching in 1096, over 300 years before the Aztec Empire even existed. It's the oldest university in the English-speaking world.",
    "In 1814, a beer vat burst in London releasing 323,000 gallons of beer. The flood killed eight people. Parliament called it an Act of God.",
    "The Dancing Plague of 1518 made hundreds of people in Strasbourg dance nonstop for days. Some danced until they died. Cause? Still unknown.",
    "Napoleon once lost a battle to rabbits. He organized a rabbit hunt but the rabbits charged at him instead of running. He had to flee.",
]

IMAGE_STYLES = [
    "vintage historical photograph style: {topic}, sepia tones, dramatic lighting, 9:16 vertical, weathered texture",
    "cinematic historical reenactment: {topic}, epic wide shot, period accurate, dramatic sky, 9:16 vertical, highly detailed",
    "oil painting historical scene: {topic}, classical painting style, rich colors, dramatic chiaroscuro, 9:16 vertical, masterpiece",
    "dramatic historical illustration: {topic}, detailed artwork, moody atmosphere, authentic period setting, 9:16 vertical",
]


def generate_history_script() -> dict:
    entry = bank_manager.pick("history_minute")
    if entry:
        print(f"  Using banked history ({bank_manager.count('history_minute')} left)")
        return entry

    print("  Bank empty, generating fresh history...")
    niche = random.choice(NICHE_NAMES)
    print(f"  Generating history about: {niche}")

    script = _try_llm(niche)
    if not script:
        print("  LLM unavailable, using fallback bank")
        script = random.choice(FALLBACK_SCRIPTS)

    hook = random.choice(HISTORY_HOOKS)
    topic = script.split(".")[0].strip()
    title = f"{hook} {topic[:60]}..." if topic else f"Amazing {niche} History"

    keywords = script.split()[:15]
    image_prompt = random.choice(IMAGE_STYLES).format(topic=" ".join(keywords))

    tts_script = f"{hook} {script}"

    return {
        "title": title[:70],
        "niche": niche,
        "hook": hook,
        "script": script,
        "image_prompt": image_prompt,
        "tts_script": tts_script,
    }


def _try_llm(niche: str) -> str | None:
    try:
        from src.script_generator import _generate
        prompt = (
            f"Write an engaging YouTube Shorts script about a fascinating event in {niche}. "
            f"Make it surprising, conversational, and hook in the first 3 seconds. "
            f"Focus on a single specific historical event or fact. "
            f"40-60 words max — short and punchy. Include one surprising detail. Return ONLY the script text."
        )
        system = "You write verified historical facts. Only include events you are certain are accurate. Make it engaging for short-form video."
        raw = _generate(prompt, temperature=0.8, max_tokens=400, system=system)
        if raw and len(raw) > 30:
            return raw.strip()
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
