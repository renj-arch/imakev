"""Urban Legends generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "You've heard this story. But here's what really happened:",
    "Everyone knows this urban legend. Almost none of it is true:",
    "The scariest story you've heard? It's not what you think:",
    "You probably believe this urban legend. Here's the truth:",
    "This famous story is completely made up. Here's the real origin:",
    "Before the internet, this story terrified everyone:",
    "You've been told this since childhood. Let me ruin it with facts:",
    "This urban legend gave generations nightmares. Was it real?",
]

FALLBACKS = [
    ("Bloody Mary", "Say Bloody Mary three times in front of a mirror and a ghostly woman appears. The legend has terrified children at sleepovers for decades.", "The legend likely originated from 16th century Queen Mary I. The modern version spread in the 1970s as a harmless dare game inspired by mirror-gazing superstitions."),
    ("The Hook", "A couple parked at Lover's Lane hears a radio warning about an escaped convict with a hook for a hand. Later they find a bloody hook dangling from the car door handle.", "The story first appeared in 1950s teen folklore magazines. No real incident has ever matched the details."),
    ("Killer in the Backseat", "A woman driving home notices a car flashing its headlights at her. Frightened, she races home. The driver tells her a man was hiding in her backseat with a knife.", "This legend may trace to a real 1964 crime. The 'friendly flasher' variant now appears in driver's safety courses as a real warning."),
    ("The Babysitter", "A babysitter receives creepy calls asking 'Have you checked the children?' The police say the calls are coming from inside the house.", "This story appeared in a 1960s horror anthology. No real case matches the exact scenario, but it became one of the most retold urban legends."),
    ("Alligators in the Sewers", "NYC's sewers teem with alligators flushed as babies, feeding on rats in the dark tunnels below the city.", "The myth started in the 1930s when a few small alligators were found in sewers — almost certainly dumped by owners. Sewers are too cold for breeding."),
    ("The Vanishing Hitchhiker", "A driver picks up a hitchhiker on a lonely road. The hitchhiker gives an address then vanishes from the car. The address belongs to someone who died years ago.", "This is one of the oldest urban legends, dating to the 1800s. Versions exist in dozens of cultures worldwide."),
    ("Spider Bite", "A woman bitten by a spider on vacation goes to the doctor, who finds hundreds of baby spiders crawling out of the wound.", "Medically impossible — spider eggs cannot survive in human tissue. The story originated from a 1990s chain email."),
    ("The Kidney Heist", "A businessman wakes up in a bathtub of ice with a note: 'Call 911. You've had a kidney removed.'", "No verified case exists. Kidney transplants require tissue matching and medical infrastructure. The story spread via late-90s chain emails."),
    ("The Crying Boy", "A painting of a crying boy is blamed for causing house fires across England. The painting is always found intact on the wall.", "In 1985 a UK newspaper claimed firefighters found the print untouched in fires. The real explanation: it was mass-produced, so it appeared in many homes — confirmation bias."),
    ("The Licked Hand", "A girl staying home alone puts her hand down for her dog to lick. In the morning the dog is dead and a message reads: 'Humans can lick too.'", "This story appeared in a 1992 horror fiction collection. No police report of this event exists anywhere."),
]


def generate_urban_legend_script() -> dict:
    entry = bank_manager.pick("urban_legends")
    if entry:
        print(f"  Using banked urban legend ({bank_manager.count('urban_legends')} left)")
        return entry

    print("  Bank empty, generating fresh urban legend...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    legend, myth, truth = random.choice(FALLBACKS)
    hook = random.choice(HOOKS)
    image_prompts = [
        f"dark cinematic horror scene: {legend}, foggy night, creepy atmosphere, vintage style, 9:16 vertical, moody lighting, shadows",
        f"bright cinematic reveal scene: {legend}, warm sunlight, documentary style, clean, 9:16 vertical, educational",
    ]
    script = f"{hook} {legend}. {myth} But here's the truth: {truth}"
    return {
        "title": f"Urban Legend: {legend}",
        "hook": hook,
        "legend": legend,
        "myth": myth,
        "truth": truth,
        "image_prompts": image_prompts,
        "script": script,
        "tts_script": script,
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Write a short YouTube Shorts script about a famous urban legend. "
            "First tell the spooky version, then reveal the real origin. "
            "Format exactly:\n"
            "LEGEND: [name of the urban legend]\n"
            "MYTH: [the spooky story version in 2-3 sentences]\n"
            "TRUTH: [the real origin in 2-3 sentences]\n\n"
            "Make it engaging and surprising. Suitable for all ages."
        )
        system = "You write about real urban legends. Always distinguish myth from fact. Keep it family-friendly."
        raw = _generate(prompt, temperature=0.8, max_tokens=800, system=system)
        if not raw:
            return None
        legend = ""
        myth = ""
        truth = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("LEGEND:"):
                legend = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("MYTH:"):
                myth = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("TRUTH:"):
                truth = line.split(":", 1)[-1].strip()
        if legend and myth and truth:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"dark cinematic horror scene: {legend}, foggy night, creepy atmosphere, vintage style, 9:16 vertical, moody lighting, shadows",
                f"bright cinematic reveal scene: {legend}, warm sunlight, documentary style, clean, 9:16 vertical, educational",
            ]
            script = f"{hook} {legend}. {myth} But here's the truth: {truth}"
            return {
                "title": f"Urban Legend: {legend}",
                "hook": hook,
                "legend": legend,
                "myth": myth,
                "truth": truth,
                "image_prompts": image_prompts,
                "script": script,
                "tts_script": script,
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
