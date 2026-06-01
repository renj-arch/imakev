"""Life hacks generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "This life hack will save you time every day:",
    "Here's a hack you wish you knew sooner:",
    "Stop doing this the hard way. Try this instead:",
    "This simple trick changes everything:",
    "Most people don't know this hack:",
    "Here's a life hack that actually works:",
    "You've been doing this wrong your whole life:",
    "This one trick makes everything easier:",
]

FALLBACKS = [
    ("Peel garlic in 10 seconds", "Put garlic cloves in a metal bowl, cover with another bowl, and shake hard for 10 seconds. The skin falls right off."),
    ("Untie knots with a fork", "Stick a fork into the knot and twist. The tines separate the strands and the knot loosens instantly."),
    ("Keep bananas fresh longer", "Wrap the stem of the banana bunch in plastic wrap. It traps the ethylene gas and slows ripening by days."),
    ("Find wall studs with a magnet", "Run a magnet along the wall until it sticks to a screw or nail. That's where the stud is."),
    ("Never lose a sock again", "Safety pin socks together before washing. They stay paired through the entire laundry cycle."),
    ("Make your phone charger last", "Wrap a spring from an old pen around the base of the charging cable. It prevents the wire from fraying at the stress point."),
    ("Remove a stripped screw", "Place a rubber band between the screwdriver and the screw head. The extra grip lets you turn it out."),
    ("Keep chip bags closed", "Fold the top of the bag down in triangles, then flip it over. The tension holds it shut without a clip."),
    ("Cool drinks faster", "Wrap a wet paper towel around the bottle and put it in the freezer. The evaporative cooling works in 15 minutes instead of an hour."),
    ("Remove permanent marker", "Draw over the marker stain with a dry erase marker, then wipe both off together. The solvents lift the permanent ink."),
    ("Prevent tears when cutting onions", "Chew gum while chopping. The chewing forces you to breathe through your mouth, bypassing the eye-irritating fumes."),
    ("Open a jar with tape", "Wrap duct tape around the lid in opposite directions, leaving two tails to pull. The leverage makes any jar open easily."),
    ("Double your headphone battery", "Store wireless earbuds in the case upside down. The contacts don't connect, so they stop trickle charging and last longer."),
    ("Zipper fix with a pencil", "Rub pencil graphite along the teeth of a stuck zipper. The graphite acts as a dry lubricant and it glides smoothly."),
    ("Keep cables tangle-free", "Fold cables in thirds, loop a twist tie around the middle. They stay coiled and never tangle in your bag."),
    ("Remove price stickers cleanly", "Heat the sticker with a hairdryer for 30 seconds. The adhesive softens and it peels off without residue."),
    ("Boost Wi-Fi with foil", "Place a curved piece of aluminum foil behind your router. It reflects the signal forward and can double range in one direction."),
    ("Fix a wobbly table", "Dip a toothpick in wood glue and hammer it into the loose joint. Snap off the excess. The table becomes rock solid."),
    ("Keep ice cream soft", "Store ice cream in a ziplock bag inside the carton. The bag prevents ice crystals from forming so it stays scoopable."),
    ("Get more juice from lemons", "Microwave the lemon for 15 seconds before squeezing. The heat breaks down membranes and releases twice the juice."),
]


def generate_life_hacks_script() -> dict:
    entry = bank_manager.pick("life_hacks")
    if entry:
        print(f"  Using banked life hacks ({bank_manager.count('life_hacks')} left)")
        return entry

    print("  Bank empty, generating fresh life hacks...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    hacks = random.sample(FALLBACKS, min(2, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"clean bright flat lay photography: {h}, household objects arranged neatly, top down view, natural lighting, minimalist, 9:16 vertical, white background"
        for h, _ in hacks
    ]
    tts_lines = [f"{h}. {e}" for h, e in hacks]
    return {
        "title": f"{hook} {hacks[0][0]}",
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
            "Give me 2 useful life hacks. "
            "Each must be practical, surprising, and actually work. "
            "Format exactly:\n"
            "HACK: [short name, 3-5 words]\n"
            "EXPLANATION: [one short sentence, 8-12 words]\n\n"
            "Make them simple, clever, and immediately usable."
        )
        system = "You write practical, clever life hacks that actually work. Each hack must be safe, simple, and useful."
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
                f"clean bright flat lay photography: {h}, household objects arranged neatly, top down view, natural lighting, minimalist, 9:16 vertical, white background"
                for h, _ in hacks
            ]
            tts_lines = [f"{h}. {e}" for h, e in hacks]
            return {
                "title": f"{hook} {hacks[0][0]}",
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
