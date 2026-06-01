"""Oddly Satisfying & DIY — satisfying visuals, restoration, cleaning, organization, and DIY projects."""

import random
import bank_manager

SATISFYING_HOOKS = [
    "This is so satisfying to watch:",
    "You won't believe how satisfying this is:",
    "Oddly satisfying content you didn't know you needed:",
    "Watch till the end. Trust us, it's worth it:",
    "There's something about this that just feels right:",
    "Can't stop watching. This is pure satisfaction:",
    "Oddly satisfying and oddly addictive:",
    "This will satisfy a part of your brain you forgot existed:",
    "The most satisfying thing you'll see today:",
    "DIY magic — watch and learn:",
]

SATISFYING_POOL = [
    ("Kinetic sand cutting", "Watch perfectly layered kinetic sand get sliced cleanly with a precision knife. Each cut leaves a satisfying clean edge.", "satisfying"),
    ("Pressure washing a driveway", "A filthy concrete driveway gets completely transformed by a pressure washer. The dirt dissolves in satisfying stripes.", "cleaning"),
    ("Paint mixing in slow motion", "Two colors of paint collide and swirl together in slow motion. The marbling pattern is mesmerizing.", "satisfying"),
    ("Restoring a rusty knife", "A blade caked in decades of rust gets sanded, polished, and restored to a mirror shine. Before and after is unreal.", "restoration"),
    ("Soap cutting", "A giant block of colorful handmade soap gets sliced into perfect cubes with a wire cutter. Smooth and flawless.", "satisfying"),
    ("Organizing a messy drawer", "A chaotic junk drawer gets sorted into neat compartments with dividers and labels. Pure organization porn.", "organization"),
    ("Slime stretching", "A massive batch of colorful slime gets stretched, folded, and poked. The sounds and textures are oddly addictive.", "satisfying"),
    ("Deep cleaning a carpet", "Years of stains and dirt get extracted from a carpet with hot water and a cleaning machine. The dirty water is shocking.", "cleaning"),
    ("Folding fitted sheets perfectly", "Watch the impossible become possible as a fitted sheet gets folded into a perfect rectangle. It's witchcraft.", "organization"),
    ("Melting and pouring metal", "Molten metal at 2000°F gets poured into a mold. The glow and flow are hypnotic.", "satisfying"),
    ("Restoring an old photograph", "A faded, torn 100-year-old photo gets digitally restored and printed. The detail recovered is incredible.", "restoration"),
    ("Cutting perfect fruit slices", "A sharp knife glides through a watermelon creating identical perfect slices every time. No waste.", "satisfying"),
    ("Polish a dirty car headlight", "A yellowed, foggy car headlight gets sanded and polished back to crystal clear. The difference is night and day.", "cleaning"),
    ("Building a mini zen garden", "A small tray filled with sand gets raked into perfect concentric patterns. Tiny rocks placed with tweezers.", "diy"),
    ("Unboxing and assembling IKEA furniture", "A pile of boards and screws transforms into a beautiful piece of furniture in time-lapse. Pure satisfaction.", "diy"),
    ("Color sorting M&Ms", "Hundreds of M&Ms get sorted by color into separate jars. The rainbow gradient is visually perfect.", "organization"),
    ("Sharpening a dull axe", "A worn axe head gets ground, whetstoned, and polished to a razor edge. It shaves hair by the end.", "restoration"),
    ("Pouring molten chocolate", "Silky melted chocolate gets poured over a perfectly shaped mold. The smooth flow is mesmerizing.", "satisfying"),
    ("Cleaning a burnt pan", "A pan covered in black burnt residue gets brought back to life with baking soda and elbow grease. Mirror finish.", "cleaning"),
    ("Tying dye on a white shirt", "A plain white shirt gets folded, tied, and dipped in vibrant colors. The reveal is a stunning pattern.", "diy"),
    ("Slicing a geode open", "A rough rock gets cut open with a diamond saw to reveal stunning crystal formations inside. Nature's art.", "satisfying"),
    ("Making slime from scratch", "Glue, activator, and color mix together in a bowl and transform into stretchy, satisfying slime. Simple DIY.", "diy"),
    ("Restoring a vintage watch", "A broken, rusted heirloom watch gets disassembled, cleaned, and reassembled. It ticks again after decades.", "restoration"),
    ("Squeezing blackheads", "Satisfying extraction video — clogged pores get cleared with careful pressure. Weirdly addictive to watch.", "cleaning"),
    ("Cutting perfect cubes of cheese", "A wire cutter glides through a block of cheese creating identical cubes. Every slice is precise.", "satisfying"),
    ("Organizing a fridge", "A messy fridge gets emptied, cleaned, and restocked with everything in labeled bins and clear containers.", "organization"),
]

CATEGORIES = ["satisfying", "cleaning", "restoration", "organization", "diy"]

IMAGE_STYLES = [
    "macro close-up shot, {topic}, soft diffused lighting, satisfying textures, 9:16 vertical, clean minimalist aesthetic",
    "cinematic top-down view, {topic}, bright natural lighting, flat lay style, 9:16 vertical, vibrant colors, crisp details",
    "extreme close-up slow motion, {topic}, mesmerizing detail, smooth textures, 9:16 vertical, soft focus background",
    "bright clean studio photography, {topic}, perfect lighting, satisfying symmetry, 9:16 vertical, high contrast, sharp focus",
    "before and after split screen, {topic}, dramatic transformation, clean composition, 9:16 vertical, satisfying reveal",
]


def generate_satisfying_script() -> dict:
    entry = bank_manager.pick("satisfying")
    if entry:
        print(f"  Using banked satisfying ({bank_manager.count('satisfying')} left)")
        return entry

    print("  Bank empty, generating fresh satisfying content...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(SATISFYING_POOL, min(5, len(SATISFYING_POOL)))
    hook = random.choice(SATISFYING_HOOKS)
    topics = []
    image_prompts = []
    tts_lines = []
    for title, desc, _ in items:
        topics.append(title)
        kw = title.lower().replace(" ", "_")[:50]
        style = random.choice(IMAGE_STYLES)
        image_prompts.append(style.format(topic=kw))
        tts_lines.append(f"{title}. {desc}")
    return {
        "title": f"Oddly Satisfying: {items[0][0][:50]}",
        "hook": hook,
        "topics": topics,
        "descriptions": [d for _, d, _ in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": f"{hook} {' '.join(tts_lines)}",
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 5 oddly satisfying or DIY ideas for a short video. "
            "Mix of satisfying visuals (like cutting soap, mixing paint), "
            "restoration projects (like restoring rusty tools), "
            "cleaning transformations, and organization tips. "
            "Format exactly:\n"
            "TOPIC: [short name, 3-6 words]\n"
            "DESCRIPTION: [one punchy sentence describing the satisfying process]\n\n"
            "Make each one feel calming and visually satisfying."
        )
        system = "You write about oddly satisfying content, DIY projects, restorations, and cleaning transformations. Be descriptive and visual."
        raw = _generate(prompt, temperature=0.9, max_tokens=600, system=system)
        if not raw:
            return None
        topics = []
        descriptions = []
        current = None
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                current = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("DESCRIPTION:") and current:
                descriptions.append(line.split(":", 1)[-1].strip())
                topics.append(current)
                current = None
        if topics and len(topics) >= 3:
            hook = random.choice(SATISFYING_HOOKS)
            image_prompts = []
            for t in topics:
                kw = t.lower().replace(" ", "_")[:50]
                image_prompts.append(random.choice(IMAGE_STYLES).format(topic=kw))
            tts_lines = [f"{t}. {d}" for t, d in zip(topics, descriptions)]
            return {
                "title": f"Oddly Satisfying: {topics[0][:50]}",
                "hook": hook,
                "topics": topics,
                "descriptions": descriptions,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": f"{hook} {' '.join(tts_lines)}",
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
