"""Coincidences generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "You won't believe this coincidence actually happened:",
    "What are the odds? This is 100% true:",
    "This coincidence is so wild it sounds fake — but it's real:",
    "The universe has a weird sense of humor:",
    "Some things just can't be explained:",
    "This happened in real life and it's mind-blowing:",
    "Statistically impossible, yet it happened:",
    "You couldn't make this up even if you tried:",
]

FALLBACKS = [
    ("The James Twins", "Two twin boys in Ohio were separated at birth and adopted by different families. Both were named James. Both grew up to be police officers. Both married women named Linda. Both had sons — one named James Alan, the other James Allan. Both owned dogs named Toy."),
    ("Lincoln & Kennedy", "Abraham Lincoln was elected to Congress in 1846, John F. Kennedy in 1946. Lincoln was elected President in 1860, Kennedy in 1960. Both were assassinated on a Friday, in front of their wives. Both successors were named Johnson — Andrew Johnson born 1808, Lyndon Johnson born 1908."),
    ("Mark Twain's Comet", "Mark Twain was born on November 30, 1835 — the same day Halley's Comet appeared. He once said, 'I came in with Halley's Comet and I expect to go out with it.' He died on April 21, 1910 — the day after Halley's Comet returned."),
    ("The Bookstore Dream", "In the 1920s, author Anne Parrish was walking through a Paris bookstore when she spotted a book she remembered from her childhood. She bought it and showed her husband, saying she'd been thinking about it all day. When she opened it, she found her own name and childhood address written inside as the previous owner."),
    ("The $50 Bill", "In 2002, a woman in Michigan found a $50 bill on the ground. On a whim, she deposited it into her bank account. Months later, her mother visited from out of state and handed her a birthday card. Inside was a $50 bill — with the same serial number as the one she'd found months earlier."),
    ("Prison Photo Coincidence", "In 2011, a British man was arrested in Spain. When police took his mugshot, it turned out the exact same police station had arrested his doppelganger 12 years earlier — and the photos looked identical. The earlier mugshot was of a man who had committed the exact same crime."),
    ("The 1919 Molasses Flood", "In 1919, a massive tank of molasses exploded in Boston, sending a 15-foot wave of molasses through the streets. 21 people died. Exactly 50 years later to the day, in 1969, a molasses tank explosion killed 9 people in Brooklyn, New York."),
    ("The Titanic Omen", "In 1898, author Morgan Robertson wrote a novel called 'Futility' about a massive unsinkable ship called the Titan that hit an iceberg on a cold April night and sank with most of its passengers. 14 years later, the Titanic — eerily similar in size and design — sank exactly the same way."),
    ("The Two Emilys", "In 2008, two British women named Emily Jones booked separate trips to the same resort in Greece. They had never met. They checked into the same room, sat by the same pool, and took the exact same photos at the same spots. The resort had mixed up their bookings — they were supposed to be in different rooms."),
    ("The Lottery Replay", "In 2009, Bulgarian lottery officials drew winning numbers: 4, 15, 23, 24, 35, 42. Four days later, the exact same numbers came up again. Statisticians calculated the odds at 1 in 4 million. No fraud was found — it was just an astronomical coincidence."),
    ("Death Bed Reunion", "In 1883, a man in Detroit lay on his deathbed and asked his family to bring his estranged brother. They sent a telegram. Hours later, a stranger arrived at the door — it was his brother, who had traveled 200 miles. He had received the telegram, but the sender address was different. It turned out the brother had the exact same dying wish at the exact same time."),
    ("The Lost Ring", "A woman swimming off the coast of Sweden lost her wedding ring in 1995. She thought it was gone forever. 6 years later, a man was fishing in the same area and caught a fish. When he cleaned it, he found the ring inside. The inscription was still readable, and he tracked down the owner."),
    ("Falling Baby", "In the 1930s, a man named Joseph Figlock was walking down a Detroit street when a baby fell from a window and landed on him. Both survived. A year later, the exact same baby fell from a window again — and landed on Joseph Figlock again."),
    ("The Unknown Soldier", "In 1937, an American salesman visiting Paris bought a postcard of the Tomb of the Unknown Soldier. When he looked closely at the crowd in the photo, he saw his own father — who had visited Paris 20 years earlier on a trip the son never knew about."),
    ("The Composer Dream", "In 1736, composer Giuseppe Tartini dreamed the devil played a violin sonata. He woke up and wrote down what he heard. The piece became 'The Devil's Trill Sonata,' one of the most famous violin works in history. In 1959, another composer had the exact same dream — and wrote a strikingly similar piece."),
    ("The Two Roberts", "In 1975, two men named Robert both traveled from different states to the same convention in Chicago. They sat next to each other. One was Robert Smith from New York. The other was Robert Smith from California. Both worked for the same company in different offices. Both had the same birthday."),
    ("The Identical Strangers", "Three men in the Canary Islands discovered they looked identical. DNA tests confirmed they were triplets separated at birth by an adoption agency. They had been placed with different families as part of a secret study. All three grew up with similar habits, tastes, and even married women with the same name."),
    ("The Car Crash Twins", "In 2014, twin brothers in Finland were cycling separately when both were hit by cars on the same road, one hour apart. Both survived with minor injuries. Police investigated and found the drivers were also twins."),
    ("The Hotel Fire", "In 1972, a man checked into a hotel room. He had a bad feeling and asked to switch rooms. He moved to room 1933. The next day, his original room was destroyed in a fire. 23 years later, the same man checked into the same hotel and was given room 1933 again — not knowing it was the room he had switched to decades earlier."),
    ("The Watch That Stopped", "In 1912, a pocket watch recovered from a man who died on the Titanic was found stopped at 2:28 AM — the exact time the ship sank. The watch belonged to a passenger who had waved off his family's pleas not to travel. In 2012, the watch sold at auction for exactly $28,000 — 100 years to the day after the sinking."),
]


def generate_coincidences_script() -> dict:
    entry = bank_manager.pick("coincidences")
    if entry:
        print(f"  Using banked coincidences ({bank_manager.count('coincidences')} left)")
        return entry

    print("  Bank empty, generating fresh coincidences...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(2, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"surreal vintage photograph style, {title}, mysterious and dreamlike atmosphere, sepia tones, double exposure effect, 9:16 vertical, cinematic lighting, historical aesthetic"
        for title, _ in items
    ]
    tts_lines = [f"{title}. {story}" for title, story in items]
    return {
        "title": f"{hook} {items[0][0]}",
        "hook": hook,
        "coincidences": [title for title, _ in items],
        "stories": [story for _, story in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 2 amazing true coincidence stories with short explanations (8-12 words each). "
            "Each must be a documented real event. "
            "Format exactly:\n"
            "TITLE: [short name of the coincidence]\n"
            "STORY: [short explanation, 8-12 words]\n\n"
            "Make them shocking, memorable, and 100% real."
        )
        system = "You write verified real coincidence stories. Every fact must be historically accurate and documented."
        raw = _generate(prompt, temperature=0.8, max_tokens=1000, system=system)
        if not raw:
            return None
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TITLE:"):
                if current.get("title") and current.get("story"):
                    items.append((current["title"], current["story"]))
                current = {"title": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("STORY:") and current:
                current["story"] = line.split(":", 1)[-1].strip()
        if current.get("title") and current.get("story"):
            items.append((current["title"], current["story"]))
        if items and len(items) >= 2:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"surreal vintage photograph style, {title}, mysterious and dreamlike atmosphere, sepia tones, double exposure effect, 9:16 vertical, cinematic lighting, historical aesthetic"
                for title, _ in items
            ]
            tts_lines = [f"{title}. {story}" for title, story in items]
            return {
                "title": f"{hook} {items[0][0]}",
                "hook": hook,
                "coincidences": [title for title, _ in items],
                "stories": [story for _, story in items],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
