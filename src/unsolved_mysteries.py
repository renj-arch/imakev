"""Unsolved Mysteries generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "This mystery has never been solved:",
    "Decades later, we still don't know what happened:",
    "The case went cold and no one knows why:",
    "This real mystery has no explanation:",
    "Investigators are still baffled by this one:",
    "To this day, no one has the answers:",
    "This unsolved case will keep you up at night:",
    "What really happened? The truth was never found:",
]

FALLBACKS = [
    ("DB Cooper", "In 1971, a man calling himself Dan Cooper hijacked a Boeing 727, collected $200,000 in ransom, then parachuted out over the Pacific Northwest. Despite an massive FBI investigation spanning 50 years, his identity and fate remain unknown. The only clue: his black clip-on tie and $5,800 in found ransom money."),
    ("The Zodiac Killer", "Between 1968 and 1974, the Zodiac killer murdered at least 5 people in Northern California. He taunted police with cryptic letters and ciphers, some never solved. Despite being the most famous unsolved serial killer case in US history, his identity is still unknown. A 2021 breakthrough claimed to crack one cipher, but the killer was never caught."),
    ("Amelia Earhart", "In 1937, famed aviator Amelia Earhart vanished over the Pacific Ocean while attempting to fly around the world. Despite the largest search in naval history, no trace of her plane was ever found. Theories range from crashing into the ocean to being captured by Japanese forces on a remote island."),
    ("The Black Dahlia", "In 1947, aspiring actress Elizabeth Short was found murdered in Los Angeles, her body cut in half and drained of blood. The case became a media sensation, but despite hundreds of suspects and confessions, the killer was never identified. The case remains one of Hollywood's most infamous unsolved murders."),
    ("Jack the Ripper", "In 1888, a serial killer murdered at least 5 women in London's Whitechapel district. He mutilated his victims with surgical precision and sent taunting letters to police. Despite one of history's largest manhunts, Jack the Ripper was never caught and his identity remains a mystery."),
    ("The Mary Celeste", "In 1872, the merchant ship Mary Celeste was found adrift in the Atlantic Ocean. The ship was fully intact with supplies untouched, food on the table, and the crew's personal belongings still aboard. But all 7 crew members and the captain's family had vanished without a trace. They were never found."),
    ("The Roanoke Colony", "In 1587, 115 English settlers landed on Roanoke Island off the coast of North Carolina. Three years later, a supply ship returned to find the colony completely abandoned. The only clue was the word 'CROATOAN' carved into a tree. No trace of the settlers was ever found."),
    ("The Tamam Shud Case", "In 1948, an unidentified man was found dead on Somerton Park beach in Australia. In his pocket was a scrap of paper reading 'Tamám Shud' — Persian for 'it is finished.' The paper was torn from a rare book of poetry, and inside the book was an unbreakable code. The man's identity and the code remain unsolved to this day."),
    ("The Hinterkaifeck Murders", "In 1922, six people were murdered with a mattock on a remote German farm. Days earlier, the family had reported strange footprints in the snow, a newspaper no one bought, and voices in the attic. The killer lived in the house for days before the murders. No one was ever convicted."),
    ("The Somerton Man", "Same as the Tamam Shud case — in 1948, a well-dressed man was found dead on an Australian beach. He had no ID, all clothing tags were removed, and he carried a hidden pocket sewn into his trousers. Despite exhuming his body in 2021 for DNA testing, his identity is still debated."),
    ("The Lead Masks Case", "In 1966, two Brazilian engineers were found dead on a hilltop wearing lead masks. Next to them was a notebook with cryptic instructions about positioning and timing. The cause of death was never determined, and the purpose of the lead masks remains unknown."),
    ("Flight 370", "In 2014, Malaysia Airlines Flight 370 disappeared with 239 people on board while flying from Kuala Lumpur to Beijing. Despite the largest search in aviation history covering 120,000 square kilometers of ocean floor, the plane's main wreckage was never found. Theories range from pilot suicide to hijacking to mechanical failure."),
    ("The Sodder Children", "On Christmas Eve 1945, a fire destroyed the Sodder family home in West Virginia. Five of the ten children were missing and presumed dead, but no remains were ever found. Evidence suggested the fire was arson, and years later, a photo surfaced showing one of the children alive. Their fate is still unknown."),
    ("The Yuba County Five", "In 1978, five men with mild intellectual disabilities drove into the Plumas National Forest in California. Their car was found abandoned and running. Four of the men were found dead miles away under bizarre circumstances — one was miles from the car, another died of exposure near a closed resort they could have taken shelter in."),
    ("Elisa Lam", "In 2013, 21-year-old Elisa Lam was found dead in a water tank on the roof of the Cecil Hotel in Los Angeles. Surveillance footage showed her acting erratically in an elevator, pressing buttons, and talking to someone not visible. How she got to the locked roof and into the tank remains unexplained."),
    ("The Dyatlov Pass Incident", "In 1959, nine experienced hikers died mysteriously in the Ural Mountains. Their tent was cut open from inside, and they fled into the freezing snow without proper clothing. Some had bizarre injuries — a missing tongue, cracked ribs with no external bruising, and traces of radiation. The official cause remains 'an unknown compelling force.'"),
    ("The Tamarind Sea Mystery", "In 2012, a sailing dinghy was found drifting off the coast of India with a half-eaten meal and a still-running engine. The three men aboard, all experienced sailors, had vanished without a trace. Their GPS showed the boat circling for hours before being found. No bodies were ever recovered."),
    ("The Springfield Three", "In 1992, three women — 47-year-old Suzie Streeter, her 18-year-old daughter Stacy, and friend Sherrill Levitt — vanished from their Springfield, Missouri home. Their purses, keys, and cars were left behind. Only a broken porch light suggested anything was wrong. They have never been found."),
    ("The Circleville Letters", "Starting in 1976, an anonymous letter writer terrorized residents of Circleville, Ohio. The letters revealed intimate details about people's lives and threatened violence. One man was convicted, but the letters continued even after he was imprisoned. The true author was never identified."),
    ("The Boy in the Box", "In 1957, the body of a young boy was found in a cardboard box in Philadelphia. He was clean, neatly dressed, and freshly bathed — suggesting someone loved him. Despite decades of investigation, thousands of tips, and a DNA exhumation in 2021, his identity and killer remain unknown."),
]


def generate_unsolved_mysteries_script() -> dict:
    entry = bank_manager.pick("unsolved_mysteries")
    if entry:
        print(f"  Using banked unsolved mysteries ({bank_manager.count('unsolved_mysteries')} left)")
        return entry

    print("  Bank empty, generating fresh unsolved mysteries...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(3, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"dark mysterious cinematic photograph, {title}, vintage crime scene photography style, dramatic shadows, film grain, 9:16 vertical, haunting atmosphere, noir aesthetic"
        for title, _ in items
    ]
    tts_lines = [f"{title}. {story}" for title, story in items]
    return {
        "title": f"{hook} {items[0][0]}",
        "hook": hook,
        "mysteries": [title for title, _ in items],
        "stories": [story for _, story in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 3 famous unsolved mysteries or cold cases. "
            "Each must be a real, documented case. "
            "Format exactly:\n"
            "CASE: [name of the mystery/case]\n"
            "STORY: [3-4 sentences telling what happened, key facts, dates, and why it remains unsolved]\n\n"
            "Make them fascinating, chilling, and accurate."
        )
        system = "You write about real unsolved mysteries and cold cases. Every detail must be factually accurate and documented."
        raw = _generate(prompt, temperature=0.8, max_tokens=1100, system=system)
        if not raw:
            return None
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("CASE:"):
                if current.get("case") and current.get("story"):
                    items.append((current["case"], current["story"]))
                current = {"case": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("STORY:") and current:
                current["story"] = line.split(":", 1)[-1].strip()
        if current.get("case") and current.get("story"):
            items.append((current["case"], current["story"]))
        if items and len(items) >= 2:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"dark mysterious cinematic photograph, {case}, vintage crime scene photography style, dramatic shadows, film grain, 9:16 vertical, haunting atmosphere, noir aesthetic"
                for case, _ in items
            ]
            tts_lines = [f"{case}. {story}" for case, story in items]
            return {
                "title": f"{hook} {items[0][0]}",
                "hook": hook,
                "mysteries": [case for case, _ in items],
                "stories": [story for _, story in items],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
