"""What If? generator — tracker-driven, no repeats, LLM fallback when bank exhausted."""

import random
from src.tracker import pick

HOOKS = ["What if...", "Imagine if...", "What would happen if...", "Picture this:", "Have you ever wondered..."]

SCENARIOS = [
    ("cats could talk", "If cats could talk, they'd probably just ask for treats all day. But they'd also tell us the best hiding spots and warn us when it's about to rain!"),
    ("trees grew candy", "If trees grew candy, lollipops would grow on branches like fruit, and chocolate bars would fall when ripe."),
    ("rain was lemonade", "If rain was lemonade, every puddle would be a drink. We'd open our mouths and catch a cold sweet drink from the sky!"),
    ("our shadows had minds of their own", "If shadows had their own minds, yours might dance when you stand still, wave at other shadows, or refuse to follow you if you're being naughty."),
    ("the Moon was made of cheese", "If the Moon was cheese, astronauts would pack crackers instead of space food. Mice would be the best space explorers."),
    ("we could breathe underwater", "If we could breathe underwater, the ocean would be our second home with coral gardens and fish for neighbors."),
    ("pets could drive tiny cars", "If pets could drive, dogs would take themselves to the park, cats would drive to sunny windowsills, and hamsters would race tiny cars through tubes."),
    ("books could read themselves aloud", "If books could read themselves, bedtime stories would come alive with voices. Your bookshelf would hum with tales."),
    ("clouds were made of cotton candy", "If clouds were cotton candy, we'd climb tall ladders and take big fluffy bites from the sky. Rain would be sweet syrup."),
    ("plants could sing", "If plants could sing, gardens would be nature's concerts. Flowers would hum in the morning, trees would create forest symphonies."),
    ("we could jump as high as kangaroos", "If we could jump like kangaroos, we'd bounce to school instead of walking. Basketball would have hoops on skyscrapers."),
    ("the floor was a trampoline", "If the floor was a trampoline, walking would be bouncing. Every step would be a little jump, and going upstairs would be the most fun ever."),
    ("we had tails", "If humans had tails, we'd wag them when happy, hide them when scared, and express feelings without words."),
    ("feelings changed the weather", "If feelings controlled weather, a happy thought would bring sunshine, a sad thought would make it rain, and laughter would create rainbows."),
    ("paintings could move", "If paintings could move, museum halls would come alive with dancing figures, drifting ships, and fluttering birds frozen in time."),
    ("toys came to life at night", "If toys came to life at night, your bedroom would become a tiny city where action heroes guard your socks and teddy bears hold council meetings."),
    ("we could talk to animals", "If we could talk to animals, we'd learn their secrets: where squirrels hide the best acorns, what birds gossip about, and why cats judge us silently."),
    ("food could grant temporary powers", "If broccoli gave you super strength and ice cream made you run faster, dinner would be a strategic choice for tomorrow's adventures."),
    ("laughter was contagious like a cold", "If laughter was contagious like a cold, comedy clubs would be the most dangerous places on Earth. One joke could start an epidemic of giggles across the world."),
    ("we could rewind time like a video", "If we could rewind time like a video, every mistake would be fixable. You could un-spill milk, un-trip over your own feet, and eat the same cookie twice."),
    ("houses could walk", "If houses could walk, you could wake up in the mountains and sleep by the beach. Your house would be your best travel companion."),
    ("dreams were mini movies you could share", "If dreams were movies you could share, you'd watch your friend's flying dream and they'd watch your talking pizza dream. Sleepovers would be cinema night."),
    ("the internet was a physical place", "If the internet was a physical place, you'd walk through hallways of cat videos, take boats on seas of music, and climb mountains of memes."),
    ("everyone had a personal cloud", "If clouds followed you everywhere, you'd have shade on sunny days, a raincloud for your plants, and a fluff to cushion falls. Clouds would need names like pets."),
    ("maps showed smells instead of roads", "If maps showed smells, you'd navigate by following the scent of fresh bread, find the park by its grass aroma, and locate your home by mom's cooking."),
    ("the dark was just a different color", "If darkness was just another color, night would feel like blue velvet. Shadows would be deep purple, and the space under your bed would be warm indigo."),
    ("our dreams grew into plants", "If dreams grew into plants when we woke up, gardens would be full of flying trees, chocolate flowers, and clouds that bloom from happy thoughts."),
    ("parallel universes were in bubbles", "If every choice created a parallel universe in a floating bubble, the sky would be filled with shimmering alternate worlds where you chose the other ice cream flavor."),
    ("music tasted like food", "If you could taste music, happy songs would taste like birthday cake, sad songs like dark chocolate, and classical music like fancy cheese with grapes."),
    ("the wind carried messages", "If the wind carried private messages from your friends, you'd stand outside waiting for breezes full of secrets and jokes carried from across town."),
    ("mirrors showed you in other universes", "If mirrors showed your parallel self, you'd wave at the version of you who chose different breakfast, wore different socks, and maybe had a pet dragon."),
    ("gravity had an off switch", "If you could turn off gravity in your room, you'd do homework floating upside down, sleep on the ceiling, and your toys would orbit you like tiny planets."),
    ("your reflection could step out", "If your reflection could step out of the mirror, you'd have a best friend who looks exactly like you but has their own style, favorite color, and probably better jokes."),
    ("buildings were alive", "If buildings were alive, skyscrapers would stretch in the morning, schools would blush when you graffiti them, and your house would hug you when you come home."),
    ("words glowed when spoken", "If words glowed when spoken, whispers would be soft sparkles, songs would light up rooms, and 'I love you' would shine brighter than a thousand stars."),
    ("rainbows were solid bridges", "If rainbows were solid bridges, you could walk across the sky. The view from the top would be spectacular, but you'd have to walk down the other side."),
    ("memories were stored in jars", "If memories were stored in jars on shelves, you could revisit your first birthday, rewatch yesterday's funny moment, and lend happy memories to sad friends."),
    ("the moon was a giant nightlight", "If the moon was a giant dimmable nightlight, you could brighten it on scary nights and dim it for sleepovers under the stars."),
    ("pockets were bottomless", "If every pocket led to a secret dimension, you could pull out toys, snacks, and books on demand. But you'd lose your keys forever in there."),
    ("laughter grew flowers", "If every laugh planted a flower seed, the world would be a garden of tulips from giggles, roses from chuckles, and daisies from snorts."),
    ("you could fold space like paper", "If you could fold space like paper, you'd step from your bedroom to the Amazon in one step. Geography class would need origami skills."),
    ("the ocean was a giant aquarium you could walk through", "If the ocean floor had glass tunnels everywhere, you'd walk to school past coral reefs, wave at octopuses, and have whales as commute buddies."),
]

IMAGE_PROMPT_TEMPLATE = "whimsical children's book illustration: {scenario}, colorful magical dreamlike, wide shot, 9:16 vertical, vibrant pastels, soft lighting"


def generate_what_if_script() -> dict:
    scenarios = pick("what_if", [(s, e) for s, e in SCENARIOS], 4)
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
