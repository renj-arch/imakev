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
    "The Great Fire of London in 1666 started in a baker's shop on Pudding Lane and destroyed over 13,000 houses. Incredibly, only six deaths were recorded. The disaster led to brick buildings and modern fire insurance.",
    "In 1947, engineers found a moth trapped in the Harvard Mark II computer. They taped it in the logbook calling it the 'first actual case of bug being found.' That's how we got the term computer bug.",
    "Cleopatra lived closer to the invention of the iPhone than to the building of the Great Pyramid. The pyramid was built around 2560 BC, while Cleopatra was born in 69 BC. The iPhone launched in 2007.",
    "The shortest war in history was the Anglo-Zanzibar War of 1896. It lasted only 38 minutes. The British Navy bombarded the palace until surrender was declared almost immediately.",
    "Oxford University began teaching in 1096, over 300 years before the Aztec Empire was founded in 1428. When Oxford was already centuries old, the Aztecs were just building their capital Tenochtitlan.",
    "In 1814, a massive beer vat burst at the Meux Brewery in London, releasing over 323,000 gallons of beer. The wave killed eight people. Parliament ruled it an Act of God.",
    "The Dancing Plague of 1518 saw hundreds of people in Strasbourg dance uncontrollably for days. Some danced until they collapsed from exhaustion or heart attacks. The cause remains unknown.",
    "Napoleon once faced his most embarrassing defeat from rabbits. He ordered a rabbit hunt, but the rabbits charged at him instead of running away. He was forced to flee from the swarm.",
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
            f"Write a short engaging YouTube Shorts script about a fascinating event in {niche}. "
            f"Make it surprising, conversational, and hook in the first 3 seconds. "
            f"Focus on a single specific historical event or fact. "
            f"40-80 words max. Return ONLY the script text."
        )
        system = "You write verified historical facts. Only include events you are certain are accurate. Make it engaging for short-form video."
        raw = _generate(prompt, temperature=0.8, max_tokens=400, system=system)
        if raw and len(raw) > 30:
            return raw.strip()
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
