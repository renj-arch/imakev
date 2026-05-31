"""Fact video generator - creates short fact-based videos."""

import random

FACT_NICHES = [
    "space facts", "animal facts", "history facts", "science facts",
    "psychology facts", "nature facts", "technology facts", "human body facts",
    "ocean facts", "physics facts", "ancient history facts", "brain facts",
]

FACT_HOOKS = [
    "Did you know?", "This will blow your mind...",
    "Most people don't know this...", "Here's something crazy:",
    "Wait till you hear this:", "This fact is unbelievable:",
    "You won't believe this:", "Mind-blowing fact:",
]

FALLBACK_FACTS = {
    "space facts": [
        "A day on Venus is longer than a year on Venus.",
        "Neutron stars can spin 600 times per second.",
        "There is a giant cloud of water floating in space that contains 140 trillion times the water of Earth's oceans.",
        "The footprints on the Moon will stay there for millions of years because there is no wind or water to erode them.",
        "The largest known asteroid, Ceres, makes up about 40 percent of the asteroid belt's total mass.",
        "The Sun makes up 99.86 percent of the total mass of our solar system.",
        "One day on Pluto lasts about 6.4 Earth days.",
        "There are more stars in the universe than grains of sand on all of Earth's beaches.",
        "A year on Mercury is just 88 Earth days long.",
        "The Great Red Spot on Jupiter is a storm that has been raging for over 350 years.",
        "Space is completely silent because sound waves need a medium to travel through.",
        "The hottest planet in our solar system is Venus, not Mercury.",
        "Titan, one of Saturn's moons, has methane lakes and rivers on its surface.",
        "Astronauts can grow up to 3 percent taller in space due to spinal decompression.",
    ],
    "animal facts": [
        "Octopuses have three hearts and blue blood.",
        "A group of flamingos is called a flamboyance.",
        "Cows have best friends and get stressed when separated from them.",
        "A shrimp's heart is located in its head.",
        "Penguins propose to their mates with a pebble.",
        "Sloths can hold their breath longer than dolphins can.",
        "Honey never spoils and has been found edible in ancient Egyptian tombs.",
        "Dogs can understand up to 250 words and gestures.",
        "Butterflies can taste with their feet.",
        "Elephants are the only mammals that cannot jump.",
        "A cat has 32 muscles in each ear.",
        "Sea otters hold hands while sleeping to avoid drifting apart.",
        "The tongue of a blue whale weighs as much as an adult elephant.",
        "Crows can recognize human faces and hold grudges.",
    ],
    "history facts": [
        "Cleopatra lived closer in time to the invention of the iPhone than to the construction of the Great Pyramid.",
        "The shortest war in history lasted only 38 minutes between Britain and Zanzibar in 1896.",
        "Napoleon was once attacked by a horde of bunnies.",
        "Ancient Romans used crushed mouse brains as toothpaste.",
        "The Great Wall of China is not visible from space with the naked eye.",
        "The entire world's population could fit inside Los Angeles if everyone stood shoulder to shoulder.",
        "Oxford University is older than the Aztec Empire.",
        "The original name of Bank of America was Bank of Italy.",
        "In medieval France, people used to pay for items with salt.",
        "Walt Disney holds the record for the most Academy Awards won by an individual.",
        "The first recorded use of 'OMG' was in a 1917 letter to Winston Churchill.",
        "Viking helmets never actually had horns.",
    ],
    "science facts": [
        "Water can boil and freeze at the same time at the triple point.",
        "The human brain generates enough electricity to power a small LED light bulb.",
        "A single teaspoon of honey contains DNA from over 300 different flowering plants.",
        "If you fold a piece of paper 42 times, it would reach the Moon.",
        "Lightning strikes the Earth about 100 times every second.",
        "The speed of light is about 299,792 kilometers per second.",
        "Your stomach produces a new layer of mucus every two weeks to prevent digesting itself.",
        "Bananas are technically berries, but strawberries are not.",
        "The Eiffel Tower grows taller in summer by about 15 centimeters due to thermal expansion.",
        "There is enough DNA in the human body to stretch from the Sun to Pluto and back.",
        "Sound travels about 4 times faster in water than in air.",
        "A single bolt of lightning contains enough energy to toast 100,000 slices of bread.",
    ],
    "psychology facts": [
        "The brain treats rejection similarly to physical pain.",
        "People are more likely to remember things when they write them down by hand.",
        "The average person has about 70,000 thoughts per day.",
        "Your brain uses about 20 percent of your body's oxygen and calories.",
        "Multitasking is actually just rapid task-switching and reduces productivity by up to 40 percent.",
        "Dopamine is released more during the anticipation of a reward than the reward itself.",
        "The placebo effect works even when you know it's a placebo.",
        "Memories are reconstructed every time you recall them, making them changeable.",
        "The color red can increase your heart rate and create a sense of urgency.",
        "People with low self-esteem often unconsciously sabotage themselves.",
        "Laughing is contagious because the brain automatically responds to laughter sounds.",
        "Your brain can process images in as little as 13 milliseconds.",
    ],
    "human body facts": [
        "Your nose can remember over 50,000 different scents.",
        "The human eye can distinguish about 10 million different colors.",
        "Your bones are about 5 times stronger than steel of the same weight.",
        "The average person produces enough saliva in a lifetime to fill two swimming pools.",
        "Your heart beats about 100,000 times per day and pumps 2,000 gallons of blood.",
        "Humans are the only animals that produce emotional tears.",
        "Your skin renews itself completely every 28 days.",
        "The small intestine is about 20 feet long.",
        "Your body contains enough iron to make a 3-inch nail.",
        "Humans are the only primates that cannot also breathe and swallow simultaneously.",
        "Your fingerprints are completely unique, even identical twins have different ones.",
        "The human body contains about 37 trillion cells.",
    ],
    "ocean facts": [
        "About 94 percent of life on Earth is aquatic.",
        "The Mariana Trench is deeper than Mount Everest is tall.",
        "Coral reefs are home to about 25 percent of all marine species.",
        "The largest living structure on Earth is the Great Barrier Reef.",
        "More people have been to the Moon than to the deepest part of the ocean.",
        "The ocean produces over half of the world's oxygen.",
        "There are underwater lakes and rivers on the ocean floor.",
        "Jellyfish have been around for over 500 million years.",
        "The blue whale's heart is the size of a small car.",
        "Some deep-sea creatures produce their own light through bioluminescence.",
        "The ocean absorbs about 30 percent of the carbon dioxide produced by humans.",
        "Underwater volcanoes produce about 75 percent of all new oceanic crust.",
    ],
    "technology facts": [
        "The first computer virus was created in 1983 and was called the 'Elk Cloner'.",
        "More computing power exists in a modern smartphone than in all of NASA in 1969.",
        "The first 1GB hard drive weighed over 500 pounds and cost $40,000.",
        "The QWERTY keyboard layout was designed to slow typists down.",
        "The world's first website is still online and was published in 1991.",
        "Over 90 percent of the world's data was created in the last two years.",
        "The average person spends over 6 hours per day looking at screens.",
        "The first email was sent by Ray Tomlinson in 1971.",
        "The '@' symbol was chosen for email addresses because it was rarely used.",
        "The first webcam was created to monitor a coffee pot at Cambridge University.",
        "Google processes over 3.5 billion searches per day.",
        "The term 'bug' in programming came from an actual moth found in a computer relay.",
    ],
    "brain facts": [
        "Your brain can read scrambled words as long as the first and last letters are correct.",
        "The brain continues to develop until about age 25.",
        "Yawning cools down your brain and improves alertness.",
        "Your brain uses 20 percent of your body's energy despite being only 2 percent of your weight.",
        "Dreaming may help your brain process emotions and memories.",
        "The brain has about 86 billion neurons.",
        "Information travels through neurons at about 268 miles per hour.",
        "Your brain produces enough electricity to power a small light bulb.",
        "Being in a messy room can actually reduce your brain's ability to focus.",
        "Exercise creates new neurons in the brain, a process called neurogenesis.",
        "Music activates multiple areas of the brain simultaneously.",
        "Your brain can't actually multitask and just switches between tasks rapidly.",
    ],
    "nature facts": [
        "Trees can communicate with each other through underground fungal networks.",
        "The Amazon rainforest produces 20 percent of the world's oxygen.",
        "Bamboo can grow up to 35 inches in a single day.",
        "The largest organism on Earth is a honey fungus in Oregon spanning 2.4 miles.",
        "Sunflowers can absorb radioactive contaminants from soil.",
        "Plants can 'hear' themselves being eaten and respond defensively.",
        "There are about 3 trillion trees on Earth.",
        "The Venus flytrap can count to two before closing on its prey.",
        "A single mature tree can absorb up to 48 pounds of carbon dioxide per year.",
        "Dandelions have been used in traditional medicine for centuries.",
        "The world's oldest living tree is over 5,000 years old.",
        "Mushrooms are more closely related to animals than to plants.",
    ],
    "physics facts": [
        "Light takes about 8 minutes to travel from the Sun to Earth.",
        "Time passes slightly slower at sea level than on a mountain top due to gravity.",
        "Quantum particles can exist in multiple places at the same time.",
        "Nothing can travel faster than the speed of light in a vacuum.",
        "The universe is expanding faster now than it was in the past.",
        "Black holes can warp spacetime so much that time stops at the event horizon.",
        "Sound cannot travel through a vacuum because there are no particles to vibrate.",
        "Entanglement allows two particles to instantly affect each other regardless of distance.",
        "At absolute zero, atoms stop moving entirely.",
        "Gravity is the weakest of the four fundamental forces.",
        "The double-slit experiment shows that light behaves as both a particle and a wave.",
        "Every atom in your body was forged in a star billions of years ago.",
    ],
}


def generate_fact_script(niche: str = "") -> dict:
    if not niche:
        niche = random.choice(FACT_NICHES)

    print(f"  Generating fact script about: {niche}")

    # Try LLM first, fall back to hardcoded bank
    facts = _try_llm(niche)
    if not facts:
        facts = _fallback_facts(niche)

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


def _try_llm(niche: str) -> list[str] | None:
    try:
        from src.script_generator import _generate
        prompt = f"Write 5 surprising one-sentence facts about {niche}. Number them 1-5. Make each fact unexpected and easy to understand."
        system = "You write engaging short facts for social media. Output exactly 5 numbered facts, one per line."
        raw = _generate(prompt, temperature=0.8, max_tokens=600, system=system)
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
        if len(facts) >= 3:
            return facts[:5]
    except Exception as e:
        print(f"  LLM unavailable ({e}), using fallback")
    return None


def _fallback_facts(niche: str) -> list[str]:
    bank = FALLBACK_FACTS.get(niche)
    if not bank or len(bank) < 5:
        bank = FALLBACK_FACTS.get("science facts", [])
    return random.sample(bank, min(5, len(bank)))
