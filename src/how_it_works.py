"""How Things Work — LLM every run for fresh topics. Bank is offline fallback only."""

import random

HOOKS = [
    "Ever wondered how this works?", "Here's how it actually works.",
    "You use it every day. But how does it work?", "Let me explain how this works.",
]

FALLBACKS = [
    ("a zipper", "A zipper works using interlocking teeth. The slider forces teeth together, locking hook into hollow. Pulling down splits them apart."),
    ("a microwave", "A microwave shoots waves at 2.4 gigahertz that excite water molecules in food, making them vibrate and create friction heat."),
    ("a lock and key", "Spring-loaded pins block the cylinder. The correct key pushes pins to the right height so the cylinder can rotate and unlock."),
    ("a battery", "Two different metals separated by electrolyte. When connected, chemical reaction sends electrons through the wire = electricity."),
    ("a camera", "Light enters through the lens. The shutter opens briefly to let light hit the sensor, converting photons into a digital image."),
    ("a refrigerator", "Liquid refrigerant evaporates inside absorbing heat. A compressor squeezes it back to liquid outside, releasing the heat."),
    ("an escalator", "A motor turns a chain loop that pulls steps in a circle. Wheels on two tracks flatten at ends so you can step on and off."),
    ("a toilet", "Flushing opens a valve. Water rushes from tank to bowl creating a siphon that pulls everything out. The tank then refills."),
    ("a ceiling fan", "Spinning blades at an angle push air downward for wind chill. Reversing circulates warm trapped air back down."),
    ("a smoke detector", "A tiny radioactive source ionizes air between electrodes. Smoke particles disrupt the current, triggering the alarm."),
    ("a vacuum cleaner", "A motor spins a fan that sucks air in, creating low pressure. Outside air pushes in carrying dirt. Filters trap particles."),
    ("an umbrella", "A sliding mechanism pushes metal ribs outward, stretching fabric into a dome. The curved shape deflects rain and wind."),
    ("a bicycle", "Pedals turn a chainring that drives the rear wheel through a chain. Gears change the ratio for speed or climbing."),
    ("a compass", "A small magnetized needle aligns with Earth's magnetic field, always pointing north. The housing lets you orient yourself."),
    ("a fluorescent light", "Electricity excites mercury vapor, emitting UV light. UV hits a phosphor coating inside the tube, which glows visible white."),
]

IMAGE_PROMPT_TEMPLATE = "cinematic close-up illustration: {topic}, detailed technical cross-section view, clean lighting, educational style, 9:16 vertical"


def generate_howitworks_script() -> dict:
    topics = _try_llm()
    if not topics:
        print("  LLM unavailable, using fallback")
        topics = random.sample(FALLBACKS, min(4, len(FALLBACKS)))

    hook = random.choice(HOOKS)
    title = f"{hook} {topics[0][0].capitalize()}"
    image_prompts = [IMAGE_PROMPT_TEMPLATE.format(topic=t) for t, _ in topics]
    tts_lines = [e for _, e in topics]

    return {
        "title": title[:70],
        "hook": hook,
        "topics": [t for t, _ in topics],
        "explanations": [e for _, e in topics],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> list | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 4 different everyday objects and explain how each works in 2-3 simple sentences. "
            "Format exactly:\n"
            "TOPIC: [object name]\n"
            "EXPLANATION: [how it works in 2-3 sentences]\n\n"
            "Make each explanation clear and correct. Choose common household objects."
        )
        system = "You explain how everyday things work in simple, accurate terms."
        raw = _generate(prompt, temperature=0.8, max_tokens=800, system=system)
        if not raw:
            return None
        topics = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                if current.get("topic") and current.get("explanation"):
                    topics.append((current["topic"], current["explanation"]))
                current = {"topic": line.split(":", 1)[-1].strip().lower()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("topic") and current.get("explanation"):
            topics.append((current["topic"], current["explanation"]))
        return topics[:4] if len(topics) >= 2 else None
    except Exception as e:
        print(f"  LLM error: {e}")
        return None
