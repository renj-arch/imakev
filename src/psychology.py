"""Psychology hacks generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "Your brain is playing tricks on you...",
    "This psychology hack will change how you see people...",
    "Most people don't know this about their own brain...",
    "Here's why your brain does this:",
    "Psychology says:",
    "Your mind is more powerful than you think...",
    "This brain hack works instantly:",
    "The way you think is not what you think it is...",
]

FALLBACKS = [
    ("The Spotlight Effect", "You think everyone notices your mistakes. They don't. People are too busy thinking about themselves."),
    ("The Ben Franklin Effect", "If someone does you a favor, they will like you more — not less. The brain justifies helping by assuming they like you."),
    ("Loss Aversion", "Losing $10 hurts twice as much as finding $10 feels good. Your brain is wired to avoid loss more than seek gain."),
    ("The IKEA Effect", "You value things more when you build them yourself. That's why DIY projects feel so satisfying."),
    ("Mirroring", "People unconsciously copy body language of people they like. Try subtly mirroring someone — they'll feel connected to you."),
    ("The Halo Effect", "If someone is attractive, your brain assumes they're also smart and kind. One positive trait colors everything."),
    ("Choice Paradox", "Too many options make us unhappy. The brain prefers 3 choices over 30. Less is literally more."),
    ("Foot-in-the-Door", "If someone agrees to a small request, they're much more likely to agree to a bigger one later."),
    ("The Zeigarnik Effect", "Your brain remembers unfinished tasks better than completed ones. That's why cliffhangers are so effective."),
    ("Cognitive Dissonance", "When your actions don't match your beliefs, your brain changes the belief — not the behavior."),
    ("The Pratfall Effect", "Highly competent people become more likable when they make a small mistake. Perfection is actually off-putting."),
    ("Anchoring", "The first number you hear sets a mental anchor. That's why $99 feels much cheaper after seeing $199 first."),
    ("The Pygmalion Effect", "Expecting more from someone actually makes them perform better. High expectations create high results."),
    ("Reciprocity", "When someone gives you something, your brain feels an overwhelming urge to give back. It's automatic."),
    ("The Dunning-Kruger Effect", "Incompetent people overestimate their skills. Experts underestimate theirs. The more you know, the less confident you feel."),
]


def generate_psychology_script() -> dict:
    entry = bank_manager.pick("psychology")
    if entry:
        print(f"  Using banked psychology ({bank_manager.count('psychology')} left)")
        return entry

    print("  Bank empty, generating fresh psychology hacks...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    hacks = random.sample(FALLBACKS, min(2, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"cinematic surreal brain illustration: {h}, glowing neural connections, moody atmospheric lighting, 9:16 vertical, dark background with neon accents, highly detailed"
        for h, _ in hacks
    ]
    tts_lines = [f"{h}. {e}" for h, e in hacks]
    return {
        "title": f"Psychology Hack: {hacks[0][0]}",
        "hook": hook,
        "hacks": [h for h, _ in hacks],
        "explanations": [e for _, e in hacks],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 2 different psychology hacks or brain facts. "
            "Each should be a real psychological effect with a surprising explanation. "
            "Format exactly:\n"
            "HACK: [Name of the effect, 3-5 words]\n"
            "EXPLANATION: [1 short sentence, 8-12 words]\n\n"
            "Make each one feel like a secret about the human mind."
        )
        system = "You write about real psychology effects in simple, fascinating terms. Only include verified psychological phenomena."
        raw = _generate(prompt, temperature=0.8, max_tokens=800, system=system)
        if not raw:
            return None
        hacks = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("HACK:"):
                if current.get("hack") and current.get("explanation"):
                    hacks.append((current["hack"], current["explanation"]))
                current = {"hack": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("hack") and current.get("explanation"):
            hacks.append((current["hack"], current["explanation"]))
        if hacks and len(hacks) >= 2:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"cinematic surreal brain illustration: {h}, glowing neural connections, moody atmospheric lighting, 9:16 vertical, dark background with neon accents, highly detailed"
                for h, _ in hacks
            ]
            tts_lines = [f"{h}. {e}" for h, e in hacks]
            return {
                "title": f"Psychology Hack: {hacks[0][0]}",
                "hook": hook,
                "hacks": [h for h, _ in hacks],
                "explanations": [e for _, e in hacks],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
