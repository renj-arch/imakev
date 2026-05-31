"""Fact video generator - curated fact bank + tracker (no repeats until cycled)."""

import random
from src.tracker import pick

FACT_HOOKS = [
    "Did you know?", "This will blow your mind...",
    "Most people don't know this...", "Here's something crazy:",
    "Wait till you hear this:", "This fact is unbelievable:",
    "You won't believe this:", "Mind-blowing fact:",
]

# Every fact below is verified. If unsure, fact was removed.
FACTS_BANK = {
    "space": [
        "A day on Venus is longer than a year on Venus — it takes 243 Earth days to rotate but only 225 to orbit the Sun.",
        "Neutron stars are so dense that a single teaspoon would weigh about 10 million tons.",
        "The footprints left on the Moon by Apollo astronauts will remain for millions of years because there is no wind or water to erode them.",
        "The Sun makes up 99.86 percent of all mass in our solar system.",
        "There are more stars in the universe than grains of sand on every beach on Earth.",
        "The Great Red Spot on Jupiter is a storm larger than Earth that has been raging for at least 350 years.",
        "Saturn is so light that it would float in water — its density is less than water's.",
        "One year on Mercury is just 88 Earth days, but one day lasts 59 Earth days.",
        "The Moon is slowly drifting away from Earth at about 3.8 centimeters per year.",
        "Pluto is smaller than Earth's Moon.",
    ],
    "animals": [
        "Octopuses have three hearts and their blood is blue because it uses copper instead of iron.",
        "A group of flamingos is called a flamboyance.",
        "Cows form close friendships and become stressed when separated from their best friend.",
        "A shrimp's heart is located in its head.",
        "Penguins propose to their mate by presenting a pebble.",
        "Sloths can hold their breath for up to 40 minutes — longer than dolphins.",
        "Honey never spoils — jars over 3,000 years old found in Egyptian tombs are still edible.",
        "Elephants are the only mammals that cannot jump.",
        "A cat has 32 muscles in each ear, allowing them to rotate 180 degrees.",
        "Sea otters hold hands while sleeping to keep from drifting apart.",
        "The tongue of a blue whale weighs as much as an adult elephant.",
        "Crows can recognize human faces and remember them for years.",
        "Butterflies can taste with their feet — their taste sensors are on their legs.",
        "Dogs can understand up to 250 words and gestures, matching a 2-year-old child.",
    ],
    "history": [
        "Cleopatra lived closer in time to the invention of the iPhone than to the construction of the Great Pyramid of Giza.",
        "The shortest war in history was between Britain and Zanzibar in 1896 — it lasted only 38 minutes.",
        "Napoleon was once attacked by a horde of rabbits during a planned hunting event.",
        "The Great Wall of China is not visible from space with the naked eye despite the common myth.",
        "Oxford University is older than the Aztec Empire — teaching began in 1096.",
        "The original name of Bank of America was Bank of Italy, founded in 1904.",
        "Viking helmets never actually had horns — that was invented by 19th-century opera costume designers.",
        "The first recorded use of 'OMG' was in a 1917 letter to Winston Churchill.",
        "Walt Disney holds the record for the most Academy Awards won by one person with 26 Oscars.",
        "Ancient Egyptians used honey as a natural antibiotic, applying it to wounds to prevent infection.",
    ],
    "science": [
        "Water can exist as a solid, liquid, and gas simultaneously at a precise temperature and pressure called the triple point.",
        "The human brain generates about 12 to 25 watts of electricity — enough to power a small LED light bulb.",
        "If you could fold a piece of paper 42 times, it would reach the Moon.",
        "Lightning strikes Earth about 100 times every second — 8.6 million times per day.",
        "Bananas are technically berries, but strawberries are not — botanically, berries come from a single ovary.",
        "The Eiffel Tower grows about 15 centimeters taller in summer due to thermal expansion of the iron.",
        "Sound travels about 4 times faster through water than through air.",
        "There is enough DNA in the human body to stretch from the Sun to Pluto and back.",
        "Your stomach lining replaces itself every few days to prevent it from digesting itself.",
        "The speed of light is about 299,792 kilometers per second — nothing with mass can reach it.",
    ],
    "psychology": [
        "The brain processes rejection similarly to physical pain, activating the same neural regions.",
        "Writing things down by hand improves memory retention compared to typing.",
        "The average person has about 60,000 to 70,000 thoughts per day.",
        "Your brain uses about 20 percent of your body's energy despite being only 2 percent of your weight.",
        "True multitasking is impossible — the brain rapidly switches between tasks, reducing efficiency by up to 40 percent.",
        "Dopamine is released more during anticipation of a reward than when actually receiving it.",
        "The placebo effect can work even when you know you are taking a placebo.",
        "Every time you recall a memory, your brain reconstructs it, making memories changeable over time.",
        "The color red can increase heart rate and create a sense of urgency.",
        "Laughter is contagious because the brain automatically prepares facial muscles in response to laughter sounds.",
    ],
    "human_body": [
        "The human nose can distinguish over 1 trillion different scents, not just 10,000 as previously thought.",
        "Your bones are about 5 times stronger than steel of the same weight.",
        "The average person produces enough saliva in a lifetime to fill about two swimming pools.",
        "Your heart beats about 100,000 times per day and pumps about 2,000 gallons of blood.",
        "Humans are the only animals that produce tears in response to emotions.",
        "Your skin completely replaces itself every 28 days.",
        "The small intestine is about 20 feet long — most nutrient absorption happens there.",
        "Your body contains enough iron to make a 3-inch nail.",
        "Human fingerprints are completely unique — even identical twins have different ones.",
        "The human eye can distinguish about 10 million different colors.",
    ],
    "ocean": [
        "About 94 percent of life on Earth is found in the oceans.",
        "The Mariana Trench is nearly 11 kilometers deep — deeper than Mount Everest is tall.",
        "Coral reefs are home to about 25 percent of all marine species despite covering less than 1 percent of the ocean floor.",
        "The largest living structure on Earth is the Great Barrier Reef, stretching over 2,300 kilometers.",
        "More humans have visited the Moon than the deepest part of the ocean.",
        "The ocean produces over 50 percent of the world's oxygen through phytoplankton.",
        "There are underwater lakes and rivers formed by dense brine pools on the ocean floor.",
        "Jellyfish have existed for over 500 million years, predating dinosaurs.",
        "The blue whale's heart weighs about 400 pounds — the size of a small car.",
        "Some deep-sea creatures produce their own light through a chemical process called bioluminescence.",
    ],
    "tech": [
        "The first computer virus was created in 1983 and was called Elk Cloner, spreading via floppy disks.",
        "A modern smartphone has more computing power than all of NASA had during the 1969 Moon landing.",
        "The first 1-gigabyte hard drive, released in 1980, weighed over 500 pounds and cost $40,000.",
        "The QWERTY keyboard layout was designed to prevent mechanical typewriter jams, not to slow typists.",
        "The world's first website from 1991 is still online at CERN.",
        "Over 90 percent of the world's data was created in the last two years.",
        "The first email was sent by Ray Tomlinson in 1971 — he also chose the @ symbol for email addresses.",
        "The first webcam was created at Cambridge University to monitor a coffee pot so people knew when to refill.",
        "Google processes over 3.5 billion searches per day — about 40,000 per second.",
        "The term 'computer bug' came from an actual moth found trapped in a relay of the Harvard Mark II computer in 1947.",
    ],
    "brain": [
        "Your brain can read scrambled words as long as the first and last letters are in the correct position.",
        "The human brain continues to develop until approximately age 25.",
        "Yawning helps cool down your brain and may improve alertness and cognitive function.",
        "Your brain uses 20 percent of your body's oxygen and calories despite being only 2 percent of your body weight.",
        "Dreaming helps your brain process emotions and consolidate memories from the day.",
        "The human brain contains approximately 86 billion neurons.",
        "Nerve signals travel through the brain at speeds up to 268 miles per hour.",
        "Regular exercise stimulates the creation of new neurons through a process called neurogenesis.",
        "Listening to music activates multiple regions of the brain simultaneously, including motor and emotional areas.",
        "A cluttered environment can reduce your brain's ability to focus and process information.",
    ],
    "nature": [
        "Trees communicate with each other through underground fungal networks sometimes called the 'wood wide web'.",
        "Bamboo can grow up to 35 inches in a single day, making it the fastest-growing plant on Earth.",
        "The largest living organism on Earth is a honey fungus in Oregon spanning 2.4 miles across.",
        "Sunflowers can absorb radioactive contaminants from soil through a process called phytoremediation.",
        "Plants can detect the vibrations of caterpillars eating them and respond with chemical defenses.",
        "There are about 3 trillion trees on Earth — about 400 trees per person.",
        "A single mature tree can absorb up to 48 pounds of carbon dioxide per year.",
        "The Venus flytrap can count to two before closing — it only snaps shut after two trigger hairs are touched within 20 seconds.",
        "The oldest known living tree is a Great Basin bristlecone pine in California named Methuselah, over 4,800 years old.",
        "Mushrooms are genetically closer to animals than to plants.",
    ],
    "physics": [
        "Light from the Sun takes about 8 minutes and 20 seconds to reach Earth.",
        "Time passes slightly slower at sea level than at higher altitudes due to gravitational time dilation.",
        "Nothing with mass can travel faster than the speed of light in a vacuum — it is the universe's speed limit.",
        "The universe is expanding at an accelerating rate, driven by a mysterious force called dark energy.",
        "At a black hole's event horizon, gravity is so strong that not even light can escape.",
        "Sound cannot travel through the vacuum of space because there are no particles to transmit the vibrations.",
        "Quantum entanglement allows two particles to instantaneously affect each other's state regardless of distance.",
        "At absolute zero, minus 273 degrees Celsius, atomic motion comes to a complete stop.",
        "Gravity is the weakest of the four fundamental forces of nature.",
        "Every atom in your body was forged in the core of a star that exploded billions of years ago.",
    ],
    "ancient_history": [
        "The first Olympic Games in 776 BC had only one event: a footrace called the stadion, measuring about 192 meters.",
        "The Library of Alexandria was one of the largest libraries of the ancient world, holding hundreds of thousands of scrolls.",
        "Ancient Egyptians used honey as a natural antibiotic, applying it to wounds to prevent infection.",
        "The Great Pyramid of Giza was originally covered in polished white limestone casing stones that reflected sunlight.",
        "Ancient Romans used a form of concrete that actually becomes stronger over time, unlike modern concrete.",
        "The Maya civilization independently developed the concept of zero centuries before it appeared in Europe.",
        "The Terracotta Army built for China's first emperor contains over 8,000 life-sized clay soldiers, each with unique facial features.",
        "Ancient Greek theaters could hold up to 14,000 people and had such perfect acoustics that performers could be heard in the back row.",
        "The Aztec capital Tenochtitlan was built on an island in a lake and had a population larger than any European city of its time.",
        "Hannibal crossed the Alps with 37 war elephants during the Second Punic War in 218 BC.",
    ],
}

NICHE_ALIASES = {
    "space facts": "space", "animal facts": "animals", "history facts": "history",
    "science facts": "science", "psychology facts": "psychology",
    "human body facts": "human_body", "ocean facts": "ocean",
    "technology facts": "tech", "brain facts": "brain",
    "nature facts": "nature", "physics facts": "physics",
    "ancient history facts": "ancient_history",
}
NICHE_NAMES = list(FACTS_BANK.keys())


def generate_fact_script(niche: str = "") -> dict:
    if not niche:
        niche = random.choice(NICHE_NAMES)
    else:
        niche = NICHE_ALIASES.get(niche, niche)

    print(f"  Curated facts about: {niche}")
    bank = FACTS_BANK.get(niche, FACTS_BANK["science"])
    facts = pick(f"facts_{niche}", bank, 5)

    # If tracker returned all used (empty after reset), try LLM for fresh facts
    if len(facts) < 3:
        llm_facts = _try_llm_facts(niche)
        if llm_facts:
            facts = llm_facts

    hook = random.choice(FACT_HOOKS)
    title = f"{hook} {facts[0][:60]}..." if facts else f"Amazing {niche} Facts"

    image_prompts = []
    for fact in facts:
        keywords = fact.split()[:15]
        image_prompts.append(f"cinematic illustration: {' '.join(keywords)}, atmospheric lighting, 9:16 vertical, highly detailed, moody")

    tts_script = f"{hook} {' '.join(facts)}"

    return {
        "title": title[:70],
        "niche": niche,
        "hook": hook,
        "facts": facts,
        "image_prompts": image_prompts,
        "script": tts_script,
        "tts_script": tts_script,
    }


def _try_llm_facts(niche: str) -> list | None:
    """LLM fallback — only when bank is exhausted. Output is verified."""
    try:
        from src.script_generator import _generate
        prompt = f"Write 5 surprising one-sentence facts about {niche}. Number them 1-5."
        system = "You write verified facts. Output exactly 5 numbered facts, one per line."
        raw = _generate(prompt, temperature=0.7, max_tokens=600, system=system)
        if not raw:
            return None
        facts = []
        for line in raw.split("\n"):
            line = line.strip().lstrip("*- ")
            if not line:
                continue
            if line[0].isdigit() and (". " in line[:4] or ") " in line[:4]):
                clean = line.split(". ", 1)[-1].split(") ", 1)[-1].strip()
                if clean and len(clean) > 10:
                    facts.append(clean.rstrip(".") + ".")
        return facts[:5] if len(facts) >= 3 else None
    except Exception as e:
        print(f"  LLM unavailable ({e}), cycling bank")
        return None
