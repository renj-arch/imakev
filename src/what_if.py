"""What If? — LLM every run for fresh ideas. Bank is offline fallback only."""

import random

HOOKS = ["What if...", "Imagine if...", "What would happen if...", "Picture this:", "Have you ever wondered..."]

FALLBACKS = [
    ("cats could talk", "If cats could talk, they'd probably just ask for treats all day."),
    ("trees grew candy", "If trees grew candy, lollipops would grow on branches like fruit."),
    ("rain was lemonade", "If rain was lemonade, every puddle would be a cold sweet drink."),
    ("we could breathe underwater", "The ocean would be our second home with coral gardens and fish for neighbors."),
    ("clouds were made of cotton candy", "We'd climb tall ladders and take big fluffy bites from the sky."),
    ("the floor was a trampoline", "Walking would be bouncing and going upstairs would be the most fun ever."),
    ("feelings changed the weather", "Happy thoughts would bring sunshine, laughter would create rainbows."),
    ("books could read themselves aloud", "Bedtime stories would come alive with voices and your bookshelf would hum."),
    ("pets could drive tiny cars", "Dogs would drive to the park, cats to sunny windowsills, hamsters would race."),
    ("we had tails", "We'd wag when happy, hide when scared, and express feelings without words."),
]

IMAGE_PROMPT_TEMPLATE = "whimsical children's book illustration: {scenario}, colorful magical dreamlike, wide shot, 9:16 vertical, vibrant pastels, soft lighting"


def generate_what_if_script() -> dict:
    scenarios = _try_llm()
    if not scenarios:
        print("  LLM unavailable, using fallback")
        scenarios = random.sample(FALLBACKS, min(4, len(FALLBACKS)))

    hook = random.choice(HOOKS)
    title = f"{hook} {scenarios[0][0]}"
    image_prompts = [IMAGE_PROMPT_TEMPLATE.format(scenario=s) for s, _ in scenarios]
    tts_lines = [f"{hook} {s}. {e}" for s, e in scenarios]

    return {
        "title": title[:70],
        "hook": hook,
        "scenarios": [s for s, _ in scenarios],
        "explanations": [e for _, e in scenarios],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> list | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 4 imaginative 'What If' scenarios for kids. "
            "Format each as:\n"
            "SCENARIO: what if ...\n"
            "EXPLANATION: a short fun explanation of what would happen\n"
            "Make them creative, magical, and fun. No scary content."
        )
        system = "You write creative 'What If' scenarios for children's videos."
        raw = _generate(prompt, temperature=0.9, max_tokens=800, system=system)
        if not raw:
            return None
        scenarios = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("SCENARIO:"):
                if current.get("scenario") and current.get("explanation"):
                    scenarios.append((current["scenario"], current["explanation"]))
                current = {"scenario": line.split(":", 1)[-1].strip().lower()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("scenario") and current.get("explanation"):
            scenarios.append((current["scenario"], current["explanation"]))
        return scenarios[:4] if len(scenarios) >= 2 else None
    except Exception as e:
        print(f"  LLM error: {e}")
        return None
