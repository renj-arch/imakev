"""Would You Rather — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "Would you rather...", "Choose wisely:", "Which one would you pick?",
    "Hard choice incoming:", "What would you do?", "Pick your side:",
]

CATEGORIES = [
    "food", "travel", "money", "superpowers", "animals", "silly",
    "everyday", "food", "nature", "sports", "school", "technology",
]


def generate_wyr_script() -> dict:
    entry = bank_manager.pick("would_you_rather")
    if entry:
        print(f"  Using banked WYR ({bank_manager.count('would_you_rather')} left)")
        return entry

    print("  Bank empty, generating fresh WYR...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    pair = random.choice(FALLBACKS)
    hook = random.choice(HOOKS)
    return {
        "title": "Would You Rather?",
        "hook": hook,
        "option_a": pair[0],
        "option_b": pair[1],
        "tts_script": f"{hook} {pair[0]} or {pair[1]}. Which one would you choose? Comment below!",
    }


FALLBACKS = [
    ("Have the ability to fly", "Be invisible"),
    ("Live in a treehouse", "Live in an underwater house"),
    ("Have a pet dinosaur", "Have a pet dragon"),
    ("Be able to talk to animals", "Speak every human language"),
    ("Never have to sleep", "Never have to eat"),
    ("Have unlimited pizza for life", "Have unlimited ice cream for life"),
    ("Be the funniest person in the room", "Be the smartest"),
    ("Explore outer space", "Explore the deep ocean"),
    ("Have super strength", "Have super speed"),
    ("Live without internet", "Live without TV"),
    ("Be able to time travel to the past", "Time travel to the future"),
    ("Have a rewind button for life", "Have a pause button"),
    ("Always win at board games", "Always win at video games"),
    ("Be a famous musician", "Be a famous athlete"),
    ("Have a personal chef", "Have a personal driver"),
    ("Visit every country", "Visit every planet"),
    ("Have fingers as long as your legs", "Have legs as long as your fingers"),
    ("Be able to teleport anywhere", "Be able to read minds"),
    ("Live in a castle", "Live on a spaceship"),
    ("Always be 10 minutes late", "Always be 10 minutes early"),
    ("Have a million dollars now", "Have 10 million dollars in 20 years"),
    ("Be the best player on a losing team", "Be the worst on a winning team"),
    ("Have a talking pet", "Have a pet that can shape-shift"),
    ("Only be able to whisper", "Only be able to shout"),
    ("Eat only sweet food forever", "Eat only savory food forever"),
    ("Have a bed that floats", "Have a bed that moves around your room"),
    ("Be able to grow any plant instantly", "Be able to fix any machine instantly"),
    ("Have a third eye", "Have a sixth finger"),
    ("Live in a world with no mirrors", "Live in a world with no windows"),
    ("Have an extra hour every day", "Have an extra day every week"),
]


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        cat = random.choice(CATEGORIES)
        prompt = (
            f"Write a 'Would You Rather' question about {cat}. "
            f"Format exactly:\n"
            f"OPTION_A: [first option, ~3-8 words]\n"
            f"OPTION_B: [second option, ~3-8 words]\n"
            f"Make both options fun, imaginative, and suitable for all ages. "
            f"Both options should be roughly equally desirable so it's a real choice."
        )
        system = "You write fun 'Would You Rather' questions suitable for all ages."
        raw = _generate(prompt, temperature=0.9, max_tokens=200, system=system)
        if not raw:
            return None
        a = b = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("OPTION_A:") or line.upper().startswith("A)"):
                a = line.split(":", 1)[-1].split(")", 1)[-1].strip()
            elif line.upper().startswith("OPTION_B:") or line.upper().startswith("B)"):
                b = line.split(":", 1)[-1].split(")", 1)[-1].strip()
        if a and b:
            hook = random.choice(HOOKS)
            return {
                "title": "Would You Rather?",
                "hook": hook,
                "option_a": a,
                "option_b": b,
                "tts_script": f"{hook} {a} or {b}. Which one would you choose? Comment below!",
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
