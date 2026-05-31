"""What If? generator — imaginative kid-friendly scenarios with Pollinations visuals + TTS."""

import random

HOOKS = [
    "What if...", "Imagine if...", "What would happen if...",
    "Picture this:", "Have you ever wondered...",
]

SCENARIOS = [
    ("cats could talk", "If cats could talk, they'd probably just ask for treats all day. But they'd also tell us the best hiding spots and warn us when it's about to rain!"),
    ("trees grew candy", "If trees grew candy, we'd never run out of sweets. Lollipops would grow on branches like fruit, and chocolate bars would fall when they're ripe. Dentists would be very busy!"),
    ("rain was lemonade", "If rain was lemonade, every puddle would be a drink. We'd open our mouths and catch a cold, sweet drink from the sky! Umbrellas would need to be cups too."),
    ("our shadows had minds of their own", "If shadows had their own minds, yours might dance when you stand still, wave at other shadows, or refuse to follow you if you're being naughty. You'd never feel alone!"),
    ("the Moon was made of cheese", "If the Moon was cheese, astronauts would pack crackers instead of space food. Mice would be the best space explorers, and every night we'd look up at a giant glowing pizza in the sky."),
    ("we could breathe underwater", "If we could breathe underwater, the ocean would be our second home. We'd have underwater cities with coral gardens, fish for neighbors, and the深海 would become our biggest playground."),
    ("pets could drive tiny cars", "If pets could drive, dogs would take themselves to the park, cats would drive to sunny windowsills, and hamsters would race tiny cars through tubes. Traffic jams would be adorable."),
    ("books could read themselves aloud", "If books could read themselves, bedtime stories would come alive with voices. Your bookshelf would hum with tales, and you could close your eyes and just listen to any adventure you want."),
    ("clouds were made of cotton candy", "If clouds were cotton candy, we'd climb tall ladders and take big fluffy bites from the sky. Rain would be sweet syrup, and after a storm, the world would smell like a carnival."),
    ("plants could sing", "If plants could sing, gardens would be nature's concerts. Flowers would hum in the morning, trees would create forest symphonies, and your houseplant would sing a little song when you water it."),
    ("we could jump as high as kangaroos", "If we could jump like kangaroos, we'd bounce to school instead of walking. Basketball would have hoops on skyscrapers, and playgrounds would have trampoline lanes everywhere."),
    ("the floor was a trampoline", "If the floor was a trampoline, walking would be bouncing. Every step would be a little jump, going upstairs would be the most fun ever, and you'd never want to sit still."),
    ("we had tails", "If humans had tails, we'd wag them when happy, hide them when scared, and express feelings without words. Chairs would need tail holes, and pants would have a totally new design."),
    ("feelings changed the weather", "If feelings controlled weather, a happy thought would bring sunshine, a sad thought would make it rain, and laughter would create rainbows. The sky would always show how the world is feeling."),
]

IMAGE_PROMPT_TEMPLATE = "whimsical children's book illustration: {scenario}, colorful magical dreamlike, wide shot, 9:16 vertical, vibrant pastels, soft lighting, wonder and curiosity"


def generate_what_if_script() -> dict:
    scenarios = random.sample(SCENARIOS, min(4, len(SCENARIOS)))
    hook = random.choice(HOOKS)

    title = f"{hook} {scenarios[0][0]}"
    image_prompts = []
    tts_lines = []

    for scenario, explanation in scenarios:
        image_prompts.append(IMAGE_PROMPT_TEMPLATE.format(scenario=scenario))
        tts_lines.append(f"{hook} {scenario}. {explanation}")

    return {
        "title": title[:70],
        "hook": hook,
        "scenarios": [s[0] for s in scenarios],
        "explanations": [s[1] for s in scenarios],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }
