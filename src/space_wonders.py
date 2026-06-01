"""Space Wonders generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "The universe is bigger than you can imagine:",
    "This space fact will blow your mind:",
    "What happens out there is beyond belief:",
    "Space is weirder than science fiction:",
    "NASA confirms this incredible space fact:",
    "Looking at the stars is looking into the past:",
    "The cosmos has secrets we're only beginning to understand:",
    "This is what happens when you look up:",
]

FALLBACKS = [
    ("A Year on Venus Is Shorter Than a Day", "Venus takes 225 Earth days to orbit the Sun but 243 Earth days to rotate once. This means a day on Venus is longer than its year. To make things stranger, Venus rotates backward — the Sun rises in the west and sets in the east."),
    ("There Are More Stars Than Grains of Sand", "Scientists estimate there are about 100 billion galaxies in the observable universe. Each galaxy contains roughly 100 billion stars. That's 10,000,000,000,000,000,000,000 stars — more than all the grains of sand on every beach on Earth."),
    ("Neutron Stars Are Insanely Dense", "A neutron star is the collapsed core of a massive star. It's about 20 km across but contains more mass than the Sun. One teaspoon of neutron star material would weigh 10 million tons — about the same as every human on Earth combined."),
    ("Saturn Would Float in Water", "Saturn is the least dense planet in our solar system. Its density is 0.687 g/cm³, while water is 1 g/cm³. If you could find a bathtub big enough, Saturn would actually float. Bonus: Jupiter is 5 times denser and would sink immediately."),
    ("The Moon Is Drifting Away", "The Moon moves about 3.8 cm away from Earth every year. When it formed 4.5 billion years ago, it was 20 times closer. In 50 billion years, the Moon will take 47 days to orbit Earth instead of 27. One day on Earth will last 1,000 hours."),
    ("There's a Giant Diamond in Space", "In 2004, astronomers discovered a white dwarf star named BPM 37093, nicknamed Lucy. The star is essentially a giant diamond — a crystallized carbon sphere 4,000 km across. It weighs 10 billion trillion trillion carats. It's the largest diamond ever found."),
    ("The Sun Makes 99.86% of All Mass", "The Sun contains 99.86% of all mass in our solar system. All planets, moons, asteroids, comets, and dust combined make up only 0.14%. The Sun is so massive that 1.3 million Earths could fit inside it."),
    ("One Day on Mercury Is 59 Earth Days", "Mercury rotates extremely slowly — one full rotation takes 59 Earth days. But it orbits the Sun in only 88 days. This means from sunrise to sunrise on Mercury, a full day-night cycle takes 176 Earth days."),
    ("The Largest Storm in the Solar System", "Jupiter's Great Red Spot is a storm larger than Earth that has been raging for at least 400 years. It's about 16,000 km wide — 1.3 times Earth's diameter. Winds inside reach 640 km/h. Scientists don't know why it hasn't dissipated."),
    ("Pluto Has Ice Mountains Higher Than the Rockies", "Pluto, once the ninth planet, has water ice mountains that rise 6,500 meters above the surface — taller than the Rocky Mountains. The ice is harder than rock at Pluto's freezing temperatures of -230°C. The mountains are made of frozen water, not rock."),
    ("A Day on Earth Was Once Only 6 Hours", "When the Moon first formed 4.5 billion years ago, Earth rotated much faster. A day was only 6 hours long. The Moon's gravity has been slowing Earth's rotation for billions of years. In the time of dinosaurs, a day was 23 hours."),
    ("There Are 10 Million Billion Billion Ants vs 1 Billion Trillion Stars", "For every ant on Earth, there are 10,000 stars. For every grain of sand, there are 10,000 stars. For every second of all human history, 100 stars are born. The universe is so vast that numbers become meaningless."),
    ("The Coldest Place in the Universe Is on Earth", "In 2003, scientists at MIT created a Bose-Einstein condensate that reached 0.5 nanokelvin — half a billionth of a degree above absolute zero. That's colder than the Boomerang Nebula, the coldest known natural place in the universe at 1 Kelvin."),
    ("A Spoonful of a Black Hole Weighs Mountains", "A black hole's density is theoretically infinite. But using the Schwarzschild radius, a black hole the size of a golf ball would contain the mass of Mount Everest. A black hole the size of a tennis ball would have the mass of Earth."),
    ("Uranus Rolls Sideways", "Most planets spin like tops, tilted slightly. Uranus is tilted 98 degrees — it essentially rolls around the Sun on its side. Scientists believe a massive collision with an Earth-sized object knocked it over 4 billion years ago."),
    ("The Andromeda Galaxy Is Headed Our Way", "The Andromeda Galaxy is moving toward the Milky Way at 400,000 km/h. In about 4.5 billion years, the two galaxies will collide. Despite the name, stars are so far apart that no star collisions are expected. The night sky will look spectacular."),
    ("Olympus Mons Is 2.5 Times Taller Than Everest", "Mars is home to Olympus Mons, the largest volcano in the solar system. It stands 21.9 km tall — 2.5 times Mount Everest's height. Its base is the size of Arizona. The volcano is so wide that from its peak, you wouldn't see the edge — it curves beyond the horizon."),
    ("There's a Giant Hexagon on Saturn", "Saturn's north pole has a persistent hexagonal cloud pattern about 32,000 km across. Each side is longer than Earth's diameter. First spotted by Voyager in 1981, the hexagon is a standing wave pattern in Saturn's atmosphere. No other planet has anything like it."),
    ("The Solar System Has a Tail", "The solar system moves through space at 828,000 km/h. Behind it stretches a comet-like tail called the heliotail, made of charged particles. It extends trillions of kilometers behind us. IBEX satellite mapped it in 2013."),
    ("What If the Moon Disappeared", "If the Moon suddenly vanished, Earth's rotation would slowly change. Days would eventually become 12 hours long. Without the Moon's gravitational pull, Earth's tilt could shift from 23.5° to 45°, causing extreme seasons and mass extinction. Tides would shrink by 75%."),
]


def generate_space_wonders_script() -> dict:
    entry = bank_manager.pick("space_wonders")
    if entry:
        print(f"  Using banked space facts ({bank_manager.count('space_wonders')} left)")
        return entry

    print("  Bank empty, generating fresh space facts...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(4, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"NASA deep space photograph, {title}, stunning nebula and stars, cosmic colors, 9:16 vertical, ultra-detailed space photography, James Webb Space Telescope style"
        for title, _ in items
    ]
    tts_lines = [f"{title}. {story}" for title, story in items]
    return {
        "title": f"{hook} {items[0][0]}",
        "hook": hook,
        "space_facts": [title for title, _ in items],
        "stories": [story for _, story in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 4 incredible space and astronomy facts with short explanations (12-15 words each). "
            "Each must be a verified documented fact from NASA or astronomy research. "
            "Format exactly:\n"
            "TITLE: [short headline for the space fact]\n"
            "FACT: [short explanation, 8-12 words]\n\n"
            "Make them mind-blowing, accurate, and fascinating."
        )
        system = "You write verified true space facts. Every detail must be scientifically accurate from NASA or astronomy research."
        raw = _generate(prompt, temperature=0.7, max_tokens=1000, system=system)
        if not raw:
            return None
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TITLE:"):
                if current.get("title") and current.get("fact"):
                    items.append((current["title"], current["fact"]))
                current = {"title": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("FACT:") and current:
                current["fact"] = line.split(":", 1)[-1].strip()
        if current.get("title") and current.get("fact"):
            items.append((current["title"], current["fact"]))
        if items and len(items) >= 3:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"NASA deep space photograph, {title}, stunning nebula and stars, cosmic colors, 9:16 vertical, ultra-detailed space photography, James Webb Space Telescope style"
                for title, _ in items
            ]
            tts_lines = [f"{title}. {fact}" for title, fact in items]
            return {
                "title": f"{hook} {items[0][0]}",
                "hook": hook,
                "space_facts": [title for title, _ in items],
                "stories": [fact for _, fact in items],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
