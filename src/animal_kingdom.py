"""Animal Kingdom generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "Nature is absolutely mind-blowing:",
    "You won't believe what this animal can do:",
    "Mother Nature has some incredible secrets:",
    "This animal fact sounds fake but it's true:",
    "The animal kingdom never stops surprising us:",
    "Evolution created something truly amazing:",
    "You need to see what this creature is capable of:",
    "Most people don't know this about animals:",
]

FALLBACKS = [
    ("Octopus Has Three Hearts", "An octopus has three hearts. Two pump blood to the gills, and one pumps it to the rest of the body. When an octopus swims, the heart that pumps to the body actually stops beating. That's why octopuses prefer crawling — swimming exhausts them."),
    ("Axolotl Can Regrow Its Brain", "The axolotl, a Mexican salamander, can regenerate entire limbs, parts of its brain, and even its spinal cord. It can regrow the same limb up to 5 times perfectly. Scientists study axolotls because they hold the key to human tissue regeneration."),
    ("Mantis Shrimp Has the Most Complex Eyes", "The mantis shrimp has 16 color-receptive cones in its eyes. Humans have 3. It can see ultraviolet, infrared, and polarized light. It also has the fastest punch in the animal kingdom — faster than a bullet, strong enough to break aquarium glass."),
    ("Crows Hold Grudges", "Crows remember human faces for years. If you wrong a crow, it will remember you and warn other crows. Studies show crows teach their children which humans to avoid. They can also use tools, solve puzzles, and hold funerals for their dead."),
    ("Tardigrades Can Survive Space", "Tardigrades, also called water bears, can survive in outer space. They can withstand extreme temperatures from -272°C to 150°C, radiation, dehydration, and even the vacuum of space. They enter a state called cryptobiosis and can come back to life decades later."),
    ("Honeybees Can Recognize Faces", "Honeybees can recognize human faces. They use a process called configural processing — the same way humans recognize faces. They can also count to four, understand zero, and communicate the location of flowers through the 'waggle dance'."),
    ("Dolphins Have Names", "Dolphins give each other names. Each dolphin develops a unique signature whistle within the first year of life. They call each other by name and can remember the whistles of dolphins they haven't seen for 20 years."),
    ("Elephants Can Hear With Their Feet", "Elephants can detect seismic vibrations through their feet. They have special sensory cells in their toes and soles that pick up low-frequency rumbles from up to 20 miles away. They also use infrasound to communicate across vast distances."),
    ("Pistol Shrimp Creates Bubbles Hotter Than the Sun", "The pistol shrimp snaps its claw so fast that it creates a cavitation bubble that reaches 4,700°C — hotter than the surface of the Sun. The bubble collapses with a sound louder than a gunshot, stunning or killing prey. The entire event lasts microseconds."),
    ("Sea Otters Hold Hands While Sleeping", "Sea otters hold hands while sleeping to avoid drifting apart. They wrap themselves in kelp or hold paws with other otters They also have the thickest fur of any mammal — up to 1 million hairs per square inch — because they have no blubber."),
    ("Cows Have Best Friends", "Studies show cows form close friendships and become stressed when separated from their best friend. Their heart rate increases and cortisol levels rise when isolated. Cows also moo in distinct accents depending on their region and social group."),
    ("Immortal Jellyfish Can Live Forever", "The Turritopsis dohrnii jellyfish is biologically immortal. When it gets injured or stressed, it reverts to its juvenile polyp stage and grows again. It can theoretically repeat this cycle forever, making it the only known immortal animal."),
    ("Hummingbirds Are the Only Birds That Fly Backward", "Hummingbirds are the only birds that can fly backward, forward, and hover in place. They beat their wings up to 80 times per second. Their heart rate can reach 1,260 beats per minute, and they must eat every 10-15 minutes to survive."),
    ("Sloths Only Poop Once a Week", "Sloths only defecate once a week. They climb down from the trees specifically to do it, which is when they are most vulnerable to predators. Losing 30% of their body weight in one bowel movement is normal for a sloth."),
    ("Koalas Have Human-like Fingerprints", "Koalas have fingerprints that are nearly identical to human fingerprints. They are so similar that even under an electron microscope, experts have difficulty distinguishing koala prints from human ones. They are the only non-primate animals with true fingerprints."),
    ("Penguins Propose With a Pebble", "Male penguins search for the smoothest, most perfect pebble and present it to a female as a proposal. If she accepts, she places the pebble in their nest. Some males will travel hundreds of meters to find the ideal pebble."),
    ("Butterflies Taste With Their Feet", "Butterflies have taste sensors on their feet. When they land on a leaf or flower, they taste it instantly with their feet to determine if it's suitable for laying eggs. They can detect sugar concentrations as low as 0.01%."),
    ("Cheetahs Can't Roar", "Cheetahs are the only big cats that cannot roar — they chirp like birds instead. They purr, meow, and make a high-pitched chirping sound used to communicate with cubs. Despite being the fastest land animal cheetahs are actually closer to small cats than big ones."),
    ("Rats Laugh When Tickled", "Rats produce ultrasonic vocalizations when tickled — essentially laughter. Humans can't hear it without special equipment. They also seek out being tickled and will return to the hands of researchers who tickle them. Rats are the only non-primate animals known to laugh."),
    ("Greenland Shark Lives 500 Years", "The Greenland shark is the longest-living vertebrate on Earth, with a lifespan of up to 500 years. They don't reach sexual maturity until age 150. One shark born in the 1500s would still be alive today, swimming the Arctic oceans."),
]


def generate_animal_kingdom_script() -> dict:
    entry = bank_manager.pick("animal_kingdom")
    if entry:
        print(f"  Using banked animal facts ({bank_manager.count('animal_kingdom')} left)")
        return entry

    print("  Bank empty, generating fresh animal facts...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(4, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"National Geographic wildlife photography, {title}, stunning animal portrait, golden hour lighting, 9:16 vertical, hyper-realistic, nature documentary style"
        for title, _ in items
    ]
    tts_lines = [f"{title}. {story}" for title, story in items]
    return {
        "title": f"{hook} {items[0][0]}",
        "hook": hook,
        "animal_facts": [title for title, _ in items],
        "stories": [story for _, story in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 4 incredible animal facts with short explanations (12-15 words each). "
            "Each must be a verified documented fact about a real animal. "
            "Format exactly:\n"
            "ANIMAL: [name of animal and the surprising fact headline]\n"
            "FACT: [short explanation, 8-12 words]\n\n"
            "Make them mind-blowing, accurate, and fascinating."
        )
        system = "You write verified true animal facts. Every detail must be scientifically accurate and documented in research."
        raw = _generate(prompt, temperature=0.7, max_tokens=1000, system=system)
        if not raw:
            return None
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("ANIMAL:"):
                if current.get("animal") and current.get("fact"):
                    items.append((current["animal"], current["fact"]))
                current = {"animal": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("FACT:") and current:
                current["fact"] = line.split(":", 1)[-1].strip()
        if current.get("animal") and current.get("fact"):
            items.append((current["animal"], current["fact"]))
        if items and len(items) >= 3:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"National Geographic wildlife photography, {animal}, stunning animal portrait, golden hour lighting, 9:16 vertical, hyper-realistic, nature documentary style"
                for animal, _ in items
            ]
            tts_lines = [f"{animal}. {fact}" for animal, fact in items]
            return {
                "title": f"{hook} {items[0][0]}",
                "hook": hook,
                "animal_facts": [animal for animal, _ in items],
                "stories": [fact for _, fact in items],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
