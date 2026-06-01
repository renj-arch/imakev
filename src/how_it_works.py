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
    ("A Zipper", "A zipper seems simple but it's brilliant engineering. Each tooth has a hook and a hollow. The slider forces them together at the perfect angle. Pull down and a wedge splits them apart. 15 interlocking teeth per inch — every single one has to line up perfectly or it jams. Over 200 million zippers are produced every day worldwide, yet most people never think about how they work."),
    ("A Microwave", "Your microwave shoots radio waves at 2.4 billion cycles per second. That frequency is precise — it excites water molecules into vibration. Friction from vibrating water heats your food from the inside. Metal reflects these waves, which is why forks spark and aluminum foil is dangerous. The door has a mesh screen with holes smaller than the wavelength, so microwaves bounce back while you can see through it."),
    ("A Toilet", "The toilet hasn't changed in 150 years. When you flush, a valve drops and water rushes from the tank into the bowl. That creates a siphon — the same physics that let you steal gas from a car. The siphon pulls everything out. Then the tank refills, the valve floats up, and it's ready again. Every flush uses about 1.6 gallons — that's nearly 5,000 gallons per person per year."),
    ("A Lock and Key", "Inside every lock are spring-loaded pins of different heights. Insert the wrong key and pins block the cylinder. The right key pushes every pin to exactly the shear line. With all pins aligned, the cylinder rotates. Master keys exist because some locks have extra shear lines for multiple keys. Some high-security locks use magnetic or laser-cut keys that are nearly impossible to pick."),
    ("A Camera", "Light enters through a curved glass lens that bends rays to a single point. The shutter opens for milliseconds — at 1/4000th of a second it's faster than a hummingbird wing. Light hits millions of photodiodes on the sensor. Each converts photons to electrons. That array of charges becomes your digital photo. A typical smartphone camera has 12 million of these tiny sensors in a space smaller than your thumbnail."),
    ("A Battery", "Two different metals in acid — that's all a battery is. One metal wants to give away electrons. The other wants to take them. Connect a wire and electrons flow. The chemical reaction keeps pushing until one metal dissolves completely. That's why batteries die. Rechargeables reverse the reaction with external power. A lithium-ion phone battery contains enough energy to launch a small object 100 feet in the air."),
    ("A Refrigerator", "Your fridge moves heat, it doesn't create cold. Liquid refrigerant evaporates inside the freezer, absorbing heat. Temperature drops. The compressor squeezes the gas back into liquid outside, dumping that heat into your kitchen. That's why the back feels warm. It's a heat pump working in reverse. The average fridge runs about 4,000 hours per year, costing around $70 in electricity annually."),
    ("An Escalator", "A massive motor at the top turns a chain loop that pulls steps in a continuous circle. Every step has wheels on two tracks. At the top and bottom, tracks flatten so steps become level — you can step on safely. There are 57 moving parts per step. Over 90 billion people ride escalators every year. The world's longest escalator system is in Hong Kong, stretching over 800 meters."),
    ("A Smoke Detector", "Inside is a tiny speck of americium-241, a radioactive element. It ionizes air between two electrodes, creating a small current. Smoke particles disrupt that current, triggering the alarm. Americium has a half-life of 432 years. That tiny speck will keep ionizing for centuries. Every smoke detector contains less radiation than you'd get from a chest X-ray, and it's completely sealed so it's safe."),
    ("A Vacuum Cleaner", "A motor spins a fan at 30,000 RPM, pushing air out the back. That creates low pressure inside. Higher atmospheric pressure outside pushes air — and dirt — into the nozzle. The dirt hits a cyclonic separator spinning at 200 mph. Centrifugal force throws particles against walls. Filters catch what's left. The first vacuum cleaner was so large it had to be pulled by horses through the streets."),
    ("An Umbrella", "A sliding mechanism on the central shaft pushes hinged ribs outward. When fully opened, the fabric stretches into a dome shape. That dome deflects rain by redirecting airflow over the surface. The curved top also handles wind — if wind gets underneath, the umbrella inverts instead of breaking. The word umbrella comes from the Latin word umbra, meaning shade — it was originally designed for sun protection."),
    ("A Bicycle", "Your legs push pedals in a circle. That turns a chainring connected to the rear wheel by a chain. Gear ratios multiply your force — a small gear in front with a large gear in back gives you climbing power. The wheels are gyroscopes. Above 8 mph, gyroscopic stability keeps you upright. A bicycle is the most efficient human-powered vehicle on Earth — you burn less energy per mile than walking."),
    ("A Compass", "Earth's core is molten iron spinning at 1,000 mph, creating a magnetic field. Your compass needle is a tiny magnetized sliver of iron. It aligns with Earth's field lines, always pointing magnetic north. True north is different — by up to 20 degrees depending where you are. Maps adjust for this difference, which is called magnetic declination. Without compasses, global navigation as we know it wouldn't exist."),
    ("A Fluorescent Light", "The tube contains mercury vapor and argon gas. Electricity excites mercury atoms, making them emit ultraviolet light. UV is invisible. So the inside is coated with phosphor — a powder that absorbs UV and glows visible white. That's fluorescence. LED works completely differently — electrons passing through a semiconductor release light directly. Fluorescent lights last about 10 times longer than traditional incandescent bulbs."),
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
            "Give me 1 fascinating everyday thing/phenomenon and explain how it works in 5-7 detailed sentences (150-180 words total). "
            "Choose something people encounter daily but don't understand. Be surprising and engaging. Add interesting statistics or historical facts. "
            "Format exactly:\n"
            "TOPIC: [Name of the thing, formatted as a curiosity title like 'How A Zipper Actually Works' or 'Why Ice Sticks To Your Fingers']\n"
            "EXPLANATION: [5-7 sentence detailed explanation, 150-180 words]"
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