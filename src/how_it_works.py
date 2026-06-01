"""How Things Work — Zack D. Films style: single curious topic, deep explanation."""

import random
from pathlib import Path
import bank_manager

HOOKS = [
    "How does this actually work?",
    "You'll never guess how this works.",
    "The way this works will surprise you.",
    "You use it every day. Here's what nobody tells you.",
    "This is how it actually works.",
    "There's a reason this works the way it does.",
]

FALLBACKS = [
    ("A Zipper", "Each zipper tooth has a tiny hook and hollow. The slider forces them together at the perfect angle, then a wedge splits them apart. Over 200 million zippers are made daily, yet almost nobody knows how they work."),
    ("A Microwave", "Your microwave fires radio waves at 2.4 billion cycles per second, precisely tuned to vibrate water molecules. The friction heats your food from inside out. That's why metal sparks — it reflects the waves instead of absorbing them."),
    ("A Toilet", "When you flush, water rushes from the tank into the bowl, creating a siphon that pulls everything out. The tank refills, a valve floats up, and it's ready again. The design hasn't changed in 150 years."),
    ("A Lock and Key", "Inside every lock, spring-loaded pins of different heights block the cylinder. The right key pushes every pin to exactly the right height, letting the cylinder rotate. Master keys work because some locks have extra shear lines."),
    ("A Camera", "Light enters through a curved lens and hits millions of photodiodes on the sensor. Each one converts photons to electrons. That array of charges becomes your photo. Smartphone sensors pack 12 million of these in an area smaller than your thumbnail."),
    ("A Battery", "Two different metals in acid — that's all a battery is. One metal gives electrons, the other takes them. Connect a wire and they flow. When one metal dissolves completely, the battery dies. Rechargeables just reverse the reaction."),
    ("A Refrigerator", "Your fridge doesn't create cold — it moves heat. Liquid refrigerant evaporates inside, absorbing heat. The compressor squeezes it back into liquid outside, dumping that heat into your kitchen. That's why the back feels warm."),
    ("An Escalator", "A motor at the top turns a chain that pulls steps in a circle. Every step has wheels on two tracks. At the top and bottom, the tracks flatten so you can step on safely. Over 90 billion people ride escalators every year."),
    ("A Smoke Detector", "Inside is a tiny speck of americium-241 that ionizes air between two electrodes, creating a small current. Smoke particles disrupt the current and trigger the alarm. That speck will keep working for centuries."),
    ("A Vacuum Cleaner", "A motor spins a fan at 30,000 RPM, pushing air out the back. That creates low pressure inside, and outside air pressure pushes dirt into the nozzle. The first vacuum cleaner was so big it had to be pulled by horses."),
    ("An Umbrella", "A sliding mechanism pushes hinged ribs outward, stretching fabric into a dome that deflects rain. If wind gets underneath, the umbrella inverts instead of breaking. The word umbrella comes from the Latin word for shade."),
    ("A Bicycle", "Your pedals turn a chainring connected to the rear wheel. Gear ratios multiply your force. Above 8 mph, gyroscopic forces from the spinning wheels keep you upright. Bicycles are the most efficient vehicles ever invented."),
    ("A Compass", "Earth's molten iron core creates a magnetic field. Your compass needle aligns with it, pointing north. But true north and magnetic north differ by up to 20 degrees. Maps adjust for this — it's called magnetic declination."),
    ("A Fluorescent Light", "Electricity excites mercury atoms, making them emit ultraviolet light. A phosphor coating inside the tube absorbs the UV and glows white. LED works completely differently — electrons passing through a semiconductor release light directly."),
]

CURIOSITY_TOPICS = [
    "How To Open A Stuck Jar Lid",
    "Why Your Phone Battery Dies Faster In Cold",
    "How Airport Scanners Actually Work",
    "What Makes A Boomerang Come Back",
    "How A Penny Counter Works",
    "Why Plane Windows Have Tiny Holes",
    "How A Bar Code Scanner Reads Invisible Lines",
    "Why Ice Sticks To Your Fingers",
    "How A Bulletproof Vest Stops A Bullet",
    "What Happens Inside A Lava Lamp",
    "How Self-Darkening Welding Helmets Work",
    "Why Wet Floors Are Slippery",
    "How A Pinball Machine Launches The Ball",
    "Why Your Voice Sounds Different On Recording",
    "How A Parking Meter Knows You Left",
    "What Makes A Wine Glass Sing",
    "Why Static Electricity Builds Up In Winter",
    "How A Speeding Radar Catches You",
    "Why Some Plates Spin In A Microwave",
    "How A Touchscreen Knows Where You Touched",
]

IMAGE_PROMPT_TEMPLATE = "cinematic close-up detailed illustration: {topic}, cross-section view, dramatic lighting, photorealistic texture, highly detailed, educational, 9:16 vertical, dark background, professional rendering, curious fascinating style"


def generate_howitworks_script() -> dict:
    entry = bank_manager.pick("how_it_works")
    if entry:
        print(f"  Using banked how-it-works ({bank_manager.count('how_it_works')} left)")
        topic = entry.get("topics", [""])[0]
        explanation = entry.get("explanations", [""])[0]
        tts = entry.get("tts_script", "")
        # If tts_script is much longer than one topic's worth, rebuild it
        if tts.count(".") > 3 or len(tts) > 150:
            print(f"  Shortened bank entry to single topic: '{topic}'")
            entry["title"] = topic
            entry["topics"] = [topic]
            entry["explanations"] = [explanation]
            entry["image_prompts"] = [IMAGE_PROMPT_TEMPLATE.format(topic=topic)]
            entry["script"] = f"{topic}. {explanation}"
            entry["tts_script"] = f"{topic}. {explanation}"
        return entry

    print("  Bank empty, generating fresh...")
    result = _try_llm()
    if not result:
        print("  LLM unavailable, using fallback")
        result = _fallback()

    return result


def _fallback() -> dict:
    from_bank = random.choice(FALLBACKS + [(t, f"Here's something you didn't know about {t.lower()}.") for t in CURIOSITY_TOPICS])
    topic, explanation = from_bank
    return {
        "title": topic,
        "hook": random.choice(HOOKS),
        "topics": [topic],
        "explanations": [explanation],
        "image_prompts": [IMAGE_PROMPT_TEMPLATE.format(topic=topic)],
        "script": f"{topic}. {explanation}",
        "tts_script": f"{topic}. {explanation}",
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 1 fascinating everyday thing and explain how it works in 3-4 punchy sentences (50-70 words total). "
            "Make it surprising and clickable. One interesting fact or stat. "
            "Format exactly:\n"
            "TOPIC: [Short curiosity title like 'How A Zipper Actually Works']\n"
            "EXPLANATION: [3-4 sentences, 50-70 words, fast-paced]"
        )
        system = "You explain everyday things with surprising depth. Like Zack D. Films — curious, clear, engaging. Your explanations make people say 'I never knew that.'"
        raw = _generate(prompt, temperature=0.9, max_tokens=600, system=system)
        if not raw:
            return None
        topic = explanation = None
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                topic = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[-1].strip()
        if topic and explanation and len(explanation) > 30:
            return {
                "title": topic,
                "hook": random.choice(HOOKS),
                "topics": [topic],
                "explanations": [explanation],
                "image_prompts": [IMAGE_PROMPT_TEMPLATE.format(topic=topic)],
                "script": f"{topic}. {explanation}",
                "tts_script": f"{topic}. {explanation}",
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None