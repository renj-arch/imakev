"""Content bank: stores pre-generated scripts in repo, auto-refills via LLM.
Ensures no content repetition by tracking used items and filtering during refill."""

import json, random, re
from pathlib import Path
from src.script_generator import _generate

BANK_DIR = Path(__file__).parent / "bank"

REFILL_PROMPTS = {
    "facts": (
        "Generate 8 surprising true facts about {niche}. "
        "All facts must be 100%% accurate. Never repeat facts from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Number them 1-8, one per line."
    ),
    "what_if": (
        "Give me 6 imaginative 'What If' scenarios for kids. "
        "Never repeat scenarios from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format each as:\n"
        "SCENARIO: what if ...\n"
        "EXPLANATION: a short fun explanation of what would happen\n"
        "Make them creative, magical, and fun. No scary content."
    ),
    "how_it_works": (
        "Give me 6 different everyday objects and explain how each works in 2-3 simple sentences. "
        "Never repeat topics from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TOPIC: [object name]\n"
        "EXPLANATION: [how it works in 2-3 sentences]\n\n"
        "Make each explanation clear and correct. Choose common household objects."
    ),
    "riddles": (
        "Write a {rtype} riddle. Never repeat riddles from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "RIDDLE: [the riddle question]\n"
        "ANSWER: [short answer]\n"
        "EXPLANATION: [one sentence explanation]\n"
        "Make it clever but solvable. Suitable for all ages."
    ),
    "would_you_rather": (
        "Write a 'Would You Rather' question about {cat}. "
        "Never repeat options from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "OPTION_A: [first option, ~3-8 words]\n"
        "OPTION_B: [second option, ~3-8 words]\n"
        "Make both options fun, imaginative, and suitable for all ages. "
        "Both options should be equally desirable so it's a real choice."
    ),
    "history_minute": (
        "Write a short YouTube Shorts script about a fascinating yet lesser-known historical event. "
        "Never repeat events from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Make it surprising, conversational, and hook in the first 3 seconds. "
        "Focus on a single specific historical event or fact. "
        "40-80 words max. Return ONLY the script text."
    ),
    "psychology": (
        "Give me 6 different psychology hacks or brain facts. "
        "Each should be a real psychological effect with a surprising explanation. "
        "Never repeat hacks from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "HACK: [Name of the effect]\n"
        "EXPLANATION: [1-2 sentence explanation of how it works]\n\n"
        "Make each one feel like a secret about the human mind."
    ),
    "life_hacks": (
        "Give me 6 useful life hacks or clever everyday tips. "
        "Each must be practical, surprising, and actually work. "
        "Never repeat hacks from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "HACK: [short name of the hack]\n"
        "EXPLANATION: [1-2 sentence how to do it and why it works]\n\n"
        "Make them simple, clever, and immediately usable."
    ),
    "urban_legends": (
        "Write a short YouTube Shorts script about a famous urban legend. "
        "First tell the spooky version, then reveal the real origin. "
        "Never repeat legends from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "LEGEND: [name of the urban legend]\n"
        "MYTH: [the spooky story version in 2-3 sentences]\n"
        "TRUTH: [the real origin in 2-3 sentences]\n\n"
        "Make it engaging and surprising. Suitable for all ages."
    ),
    "coincidences": (
        "Give me 3 amazing true coincidence stories. Each must be a documented real event. "
        "Never repeat stories from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TITLE: [short name of the coincidence]\n"
        "STORY: [3-4 sentences telling what happened with specific details and dates]\n\n"
        "Make them shocking, memorable, and 100% real."
    ),
    "unsolved_mysteries": (
        "Give me 3 famous unsolved mysteries or cold cases. Each must be a real, documented case. "
        "Never repeat cases from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "CASE: [name of the mystery/case]\n"
        "STORY: [3-4 sentences telling what happened, key facts, dates, and why it remains unsolved]\n\n"
        "Make them fascinating, chilling, and accurate."
    ),
    "movie_trivia": (
        "Give me 3 true behind-the-scenes movie trivia facts. Each must be a verified real fact from a well-known movie. "
        "Never repeat trivia from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "MOVIE: [movie title and the trivia headline]\n"
        "TRIVIA: [3-4 sentences explaining the real behind-the-scenes story]\n\n"
        "Make them fascinating, surprising, and 100% factual."
    ),
    "animal_kingdom": (
        "Give me 3 incredible animal facts. Each must be a verified documented fact about a real animal. "
        "Never repeat facts from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "ANIMAL: [name of animal and the surprising fact headline]\n"
        "FACT: [3-4 sentences explaining the fact with specific details]\n\n"
        "Make them mind-blowing, accurate, and fascinating."
    ),
    "space_wonders": (
        "Give me 3 incredible space and astronomy facts. Each must be a verified documented fact from NASA or research. "
        "Never repeat facts from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TITLE: [short headline for the space fact]\n"
        "FACT: [3-4 sentences explaining the fact with specific numbers and details]\n\n"
        "Make them mind-blowing, accurate, and fascinating."
    ),
    "box_office": (
        "Give me 3 fascinating box office or movie earnings facts. Each must be a verified real fact. "
        "Never repeat facts from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TITLE: [short headline for the box office fact]\n"
        "FACT: [3-4 sentences explaining with specific dollar amounts and details]\n\n"
        "Include specific numbers, years, and comparisons."
    ),
    "negative_hooks": (
        "Give me 5 dark, shocking truths or uncomfortable realities. "
        "Each should be a brutal fact about life, society, human nature, or the future. "
        "The tone: unsettling but factual. Make people think. "
        "Never repeat truths from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TRUTH: [short shocking headline, 3-8 words]\n"
        "EXPLANATION: [one punchy sentence explaining why it's dark]\n\n"
        "Make each one feel like a cold dose of reality."
    ),
    "satisfying": (
        "Give me 5 oddly satisfying or DIY ideas for a short video. "
        "Mix of satisfying visuals (like cutting soap, mixing paint), "
        "restoration projects (like restoring rusty tools), "
        "cleaning transformations, and organization tips. "
        "Never repeat topics from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TOPIC: [short name, 3-6 words]\n"
        "DESCRIPTION: [one punchy sentence describing the satisfying process]\n\n"
        "Make each one feel calming and visually satisfying."
    ),
    "challenges": (
        "Give me 5 different fun physical challenges or stunts to attempt. "
        "Each should be specific and measurable (e.g., 'Hold your breath for 30 seconds'). "
        "Mix easy, medium, and hard difficulties. "
        "Never repeat challenges from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "CHALLENGE: [short name, 3-8 words]\n"
        "DESCRIPTION: [one punchy sentence explaining what to do and why it's hard]\n"
        "RESULT: [what typically happens when people try]\n"
        "SKILL: [balance/dexterity/endurance/speed/willpower/strength]\n"
        "DIFFICULTY: [easy/medium/hard]\n\n"
        "Make each one feel like a dare."
    ),
    "try_this": (
        "Give me 1 interactive brain hack or visual illusion. "
        "The viewer must experience the effect in real time. "
        "Never repeat tricks from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "HOOK: [direct command, first 2 seconds]\n"
        "SETUP: [what the brain is doing, 3-5s]\n"
        "ACTION: [countdown or instruction]\n"
        "REVEAL: [what they just experienced]\n"
        "EXPLANATION: [one punchy line, 5-8s]\n"
        "PROMPT: [one line summary for the end]\n"
        "IMAGE: [short visual description for the image]\n\n"
        "Make it feel like a magic trick. The viewer must do something."
    ),
}

NICHES = [
    "space", "animals", "history", "science", "psychology",
    "human body", "ocean", "technology", "brain", "nature", "physics",
    "food", "music", "sports", "weather", "dinosaurs", "inventions", "math",
]

FACT_HOOKS = [
    "Did you know?", "This will blow your mind...",
    "Most people don't know this...", "Here's something crazy:",
    "Wait till you hear this:", "This fact is unbelievable:",
    "You won't believe this:", "Mind-blowing fact:",
]

IMAGE_PROMPT_FACT = "cinematic illustration: {keywords}, atmospheric lighting, 9:16 vertical, highly detailed, moody"
IMAGE_PROMPT_WHATIF = "whimsical children's book illustration: {scenario}, colorful magical dreamlike, wide shot, 9:16 vertical, vibrant pastels, soft lighting"
IMAGE_PROMPT_HOW = "cinematic close-up illustration: {topic}, detailed technical cross-section view, clean lighting, educational style, 9:16 vertical"
IMAGE_PROMPT_RIDDLE = "mysterious cinematic scene: {riddle}, dark moody lighting, question marks, 9:16 vertical, intrigue"
IMAGE_PROMPT_RIDDLE_ANSWER = "cinematic reveal scene: {answer}, bright warm lighting, discovery moment, 9:16 vertical"
IMAGE_PROMPT_HISTORY = "vintage historical photograph style: {topic}, sepia tones, dramatic lighting, 9:16 vertical, weathered texture, cinematic"
IMAGE_PROMPT_PSYCHOLOGY = "cinematic surreal brain illustration: {hack}, glowing neural connections, moody atmospheric lighting, 9:16 vertical, dark background with neon accents, highly detailed"
IMAGE_PROMPT_LIFE_HACKS = "clean bright flat lay photography: {hack}, household objects arranged neatly, top down view, natural lighting, minimalist, 9:16 vertical, white background"
IMAGE_PROMPT_URBAN_LEGENDS_MYTH = "dark cinematic horror scene: {legend}, foggy night, creepy atmosphere, vintage style, 9:16 vertical, moody lighting, shadows"
IMAGE_PROMPT_URBAN_LEGENDS_TRUTH = "bright cinematic reveal scene: {legend}, warm sunlight, documentary style, clean, 9:16 vertical, educational"
IMAGE_PROMPT_COINCIDENCES = "surreal vintage photograph style, {title}, mysterious dreamlike atmosphere, sepia tones, double exposure effect, 9:16 vertical, cinematic lighting, historical aesthetic"
IMAGE_PROMPT_UNSOLVED = "dark mysterious cinematic photograph, {title}, vintage crime scene style, dramatic shadows, film grain, 9:16 vertical, haunting atmosphere, noir aesthetic"
IMAGE_PROMPT_MOVIE_TRIVIA = "cinematic movie poster style, {title}, dramatic lighting, film grain, 9:16 vertical, Hollywood golden hour, vintage movie set photography"
IMAGE_PROMPT_ANIMAL_KINGDOM = "National Geographic wildlife photography, {title}, stunning animal portrait, golden hour lighting, 9:16 vertical, hyper-realistic, nature documentary style"
IMAGE_PROMPT_SPACE_WONDERS = "NASA deep space photograph, {title}, stunning nebula and stars, cosmic colors, 9:16 vertical, ultra-detailed space photography, James Webb Space Telescope style"
IMAGE_PROMPT_BOX_OFFICE = "vintage Hollywood movie poster, {title}, dramatic golden lighting, film strip border, 9:16 vertical, cinema marquee lights, retro box office aesthetic"
IMAGE_PROMPT_CHALLENGES = "cinematic action shot, {challenge}, dramatic lighting, fast-paced motion blur, 9:16 vertical, intense atmosphere, adrenaline"
IMAGE_PROMPT_SATISFYING = "macro close-up shot, {topic}, soft diffused lighting, satisfying textures, 9:16 vertical, clean minimalist aesthetic, vibrant colors"
IMAGE_PROMPT_NEGATIVE = "dark cinematic scene, {topic}, moody lighting, deep shadows, 9:16 vertical, unsettling atmosphere, noir style"
IMAGE_PROMPT_TRY_THIS = "minimalist brain illusion, {hook}, 9:16 vertical, high contrast, surreal, optical illusion style, clean background"

RIDDLE_TYPES = [
    "logic", "wordplay", "math", "lateral thinking", "observation",
    "classic", "nature", "science", "everyday", "animal",
]

HISTORY_HOOKS = [
    "Did you know this happened?", "History is full of surprises:",
    "You won't believe what happened in history:", "This historical event will shock you:",
    "Here's a history lesson you didn't get in school:", "Mind-blowing history fact:",
    "Most people don't know this about history:", "Wait till you hear this history story:",
]

HISTORY_NICHES = [
    "ancient civilizations", "world wars", "medieval history", "famous inventors",
    "explorers", "ancient rome", "ancient egypt", "industrial revolution",
    "renaissance", "american history", "asian history", "scientific discoveries",
]

WYR_CATEGORIES = [
    "food", "travel", "money", "superpowers", "animals", "silly",
    "everyday", "nature", "sports", "school", "technology",
]

PSYCHOLOGY_HOOKS = [
    "Your brain is playing tricks on you...",
    "This psychology hack will change how you see people...",
    "Most people don't know this about their own brain...",
    "Here's why your brain does this:",
    "Psychology says:",
    "Your mind is more powerful than you think...",
    "This brain hack works instantly:",
    "The way you think is not what you think it is...",
]

PSYCHOLOGY_FALLBACKS = [
    ("The Spotlight Effect", "You think everyone notices your mistakes. They don't. People are too busy thinking about themselves."),
    ("The Ben Franklin Effect", "If someone does you a favor, they will like you more — not less. The brain justifies helping by assuming they like you."),
    ("Loss Aversion", "Losing $10 hurts twice as much as finding $10 feels good. Your brain is wired to avoid loss more than seek gain."),
    ("The IKEA Effect", "You value things more when you build them yourself. That's why DIY projects feel so satisfying."),
    ("Mirroring", "People unconsciously copy body language of people they like. Try subtly mirroring someone — they'll feel connected to you."),
    ("The Halo Effect", "If someone is attractive, your brain assumes they're also smart and kind. One positive trait colors everything."),
    ("Choice Paradox", "Too many options make us unhappy. The brain prefers 3 choices over 30. Less is literally more."),
    ("Foot-in-the-Door", "If someone agrees to a small request, they're much more likely to agree to a bigger one later."),
    ("The Zeigarnik Effect", "Your brain remembers unfinished tasks better than completed ones. That's why cliffhangers are so effective."),
    ("Cognitive Dissonance", "When your actions don't match your beliefs, your brain changes the belief — not the behavior."),
    ("The Pratfall Effect", "Highly competent people become more likable when they make a small mistake. Perfection is actually off-putting."),
    ("Anchoring", "The first number you hear sets a mental anchor. That's why $99 feels much cheaper after seeing $199 first."),
    ("The Pygmalion Effect", "Expecting more from someone actually makes them perform better. High expectations create high results."),
    ("Reciprocity", "When someone gives you something, your brain feels an overwhelming urge to give back. It's automatic."),
    ("The Dunning-Kruger Effect", "Incompetent people overestimate their skills. Experts underestimate theirs. The more you know, the less confident you feel."),
]

LIFE_HACKS_HOOKS = [
    "This life hack will save you time every day:",
    "Here's a hack you wish you knew sooner:",
    "Stop doing this the hard way. Try this instead:",
    "This simple trick changes everything:",
    "Most people don't know this hack:",
    "Here's a life hack that actually works:",
    "You've been doing this wrong your whole life:",
    "This one trick makes everything easier:",
]

LIFE_HACKS_FALLBACKS = [
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

URBAN_LEGENDS_HOOKS = [
    "You've heard this story. But here's what really happened:",
    "This urban legend gave generations nightmares. Was it real?",
    "Everyone knows this story. Almost none of it is true:",
    "The scariest story you've heard? It's not what you think:",
    "You probably believe this urban legend. Here's the truth:",
    "This famous story is completely made up. Here's the real origin:",
    "Before the internet, this story terrified everyone. Then the truth came out:",
    "You've been told this spooky story since childhood. Let me ruin it with facts:",
]

COINCIDENCES_HOOKS = [
    "You won't believe this coincidence actually happened:",
    "What are the odds? This is 100% true:",
    "This coincidence is so wild it sounds fake but it's real:",
    "The universe has a weird sense of humor:",
    "Some things just can't be explained:",
    "Statistically impossible, yet it happened:",
    "You couldn't make this up even if you tried:",
]

UNSOLVED_HOOKS = [
    "This mystery has never been solved:",
    "Decades later, we still don't know what happened:",
    "The case went cold and no one knows why:",
    "This real mystery has no explanation:",
    "Investigators are still baffled by this one:",
    "To this day, no one has the answers:",
    "This unsolved case will keep you up at night:",
]

MOVIE_TRIVIA_HOOKS = [
    "You won't believe what happened behind the scenes:",
    "This movie secret was hidden for years:",
    "Most people don't know this about their favorite movie:",
    "This famous scene almost didn't make the cut:",
    "The real story behind this movie moment is incredible:",
    "Hollywood kept this secret quiet for decades:",
    "This movie fact sounds fake but it's 100% true:",
]

ANIMAL_KINGDOM_HOOKS = [
    "Nature is absolutely mind-blowing:",
    "You won't believe what this animal can do:",
    "Mother Nature has some incredible secrets:",
    "This animal fact sounds fake but it's true:",
    "The animal kingdom never stops surprising us:",
    "Evolution created something truly amazing:",
    "Most people don't know this about animals:",
]

SPACE_WONDERS_HOOKS = [
    "The universe is bigger than you can imagine:",
    "This space fact will blow your mind:",
    "Space is weirder than science fiction:",
    "NASA confirms this incredible space fact:",
    "Looking at the stars is looking into the past:",
    "The cosmos has secrets we're only beginning to understand:",
]

BOX_OFFICE_HOOKS = [
    "You won't believe how much this movie earned:",
    "This box office record still stands today:",
    "The numbers behind this film are insane:",
    "This movie broke every record in Hollywood:",
    "Made on a tiny budget, earned millions:",
    "The most profitable movie ever made:",
    "Hollywood didn't see this coming:",
]

CHALLENGES_HOOKS = [
    "Think you can do this? Watch till the end:",
    "99% of people fail this challenge. Can you?",
    "This challenge looks easy. It's not:",
    "How far would YOU get? Be honest:",
    "Only 1% can complete all of these. You?",
    "This challenge separates the pros from the amateurs:",
    "Most people give up before the end. Prove us wrong:",
    "This stunt requires serious skill. Ready?",
]

TRY_THIS_HOOKS = [
    "Try this right now. Don't look away:",
    "Your brain is lying to you. Try this:",
    "This trick works on everyone. Ready?",
    "Try this 5-second brain hack:",
    "You won't believe what happens. Try it:",
    "This illusion breaks your brain. Watch:",
    "Ready to hack your own brain?",
    "Try this and feel your brain break:",
]

SATISFYING_HOOKS = [
    "This is so satisfying to watch:",
    "You won't believe how satisfying this is:",
    "Oddly satisfying content you didn't know you needed:",
    "Watch till the end. Trust us, it's worth it:",
    "There's something about this that just feels right:",
    "Can't stop watching. This is pure satisfaction:",
    "Oddly satisfying and oddly addictive:",
    "The most satisfying thing you'll see today:",
]

NEGATIVE_HOOKS = [
    "This will ruin your day:",
    "Here's something dark you need to hear:",
    "This fact will haunt you:",
    "You're not ready for this truth:",
    "The darker side of things you didn't know:",
    "This will change how you see everything — not in a good way:",
    "Warning: this is disturbing:",
    "You can't unlearn this:",
    "Reality check incoming:",
]

URBAN_LEGENDS_FALLBACKS = [
    ("Bloody Mary", "Say Bloody Mary three times in front of a mirror and a ghostly woman appears to attack you. The legend has terrified children at sleepovers for decades.", "The legend likely originated from 16th century Queen Mary I. The modern version spread in the 1970s as a harmless dare game, inspired by mirror-gazing superstitions."),
    ("The Hook", "A couple parked at Lover's Lane hears a radio warning about an escaped convict with a hook for a hand. They drive away scared, and later find a bloody hook dangling from the car door handle.", "The story first appeared in 1950s teen folklore magazines. No real incident has ever matched the details, but it became the classic cautionary tale about teenage rebellion."),
    ("Killer in the Backseat", "A woman driving home notices a car flashing its headlights at her repeatedly. Frightened, she races home. The driver follows her, then tells her a man was hiding in her backseat with a knife.", "This legend may trace to a real 1964 crime where a woman found a man in her backseat. The 'friendly flasher' variant appears in driver's safety courses as a real warning."),
    ("The Babysitter", "A babysitter receives creepy phone calls asking 'Have you checked the children?' She calls the police and learns the calls are coming from inside the house. The killer is upstairs.", "This story first appeared in a 1960s horror anthology. No real case has ever matched this exact scenario, but it became one of the most retold urban legends in American folklore."),
    ("Alligators in the Sewers", "New York City's sewers are infested with alligators that were flushed down toilets as babies and grew in the darkness feeding on rats and garbage.", "The myth started in the 1930s when a few small alligators were found in NYC sewers. They were almost certainly dumped by owners, not from a breeding population. Sewers are too cold for them to survive."),
    ("The Vanishing Hitchhiker", "A driver picks up a hitchhiker on a lonely road. The hitchhiker gives an address, then mysteriously vanishes from the car. The driver later finds out the person died years ago.", "This is one of the oldest urban legends dating back to the 1800s. Versions exist in dozens of cultures. The modern version spread during the 1950s car culture boom."),
    ("Microwaved Pet", "An elderly woman tries to dry her wet poodle by putting it in the microwave. The pet explodes, killing it instantly.", "This grotesque story appeared in a 1970s book but was entirely fabricated. No documented case of anyone microwaving a pet has ever been found. It became a warning about modern technology."),
    ("Spider Bite", "A woman is bitten by a spider while on vacation. The bite swells and when she goes to the doctor, hundreds of baby spiders crawl out of the wound.", "Medically impossible. Spider eggs cannot survive inside human tissue and spider venom doesn't work this way. The story originates from a 1990s chain email."),
    ("The Kidney Heist", "A businessman travels abroad, wakes up in a bathtub of ice with a note saying 'Call 911. You've had one of your kidneys removed.'", "No verified case of a single kidney being stolen surgically has ever been documented. The story spread via chain emails in the late 1990s. Kidney transplants require tissue matching and medical infrastructure."),
    ("The Clown Statue", "A family buys a creepy clown statue from an antique store. It keeps appearing in different rooms. They later learn it was never a statue — it was a man playing dead.", "This story gained traction on early internet forums in the 2000s. It's a variation of the 'living statue' trope found in horror fiction dating back to the 1800s."),
    ("Car Headlights Game", "Teens drive to a remote road at night and stop. They turn off the car. The legend says if you count to three and turn the headlights back on, you'll see a ghost in the beam.", "This is a modern campfire story that spread through social media. No paranormal sightings have been verified, but teens still try it. The fear comes from anticipation and darkness."),
    ("The Licked Hand", "A girl staying home alone feels safe with her dog. She puts her hand down for the dog to lick. In the morning, she finds the dog dead and a message in blood: 'Humans can lick too.'", "This story appeared in a 1992 horror fiction collection. It was written as fiction but spread as a true story through forwarded emails. No police report of this event exists."),
    ("Room for One More", "A taxi driver picks up a passenger. The passenger gets out at a cemetery. The driver looks back and the passenger is gone. Later he finds out the passenger was a person who died exactly one year ago.", "This is a global folklore motif dating back centuries. Versions exist in Japanese, Mexican, and European cultures. It's a classic ghost story, not a real event."),
    ("The Crying Boy", "A painting of a crying boy is blamed for causing fires in homes across England in the 1980s. Every house that burned down had the painting intact on the wall.", "In 1985, a UK newspaper claimed firefighters found the print untouched in numerous fires. The real explanation: the print was mass-produced, so it appeared in many homes. Confirmation bias created the legend."),
    ("Deadly Pizza Topping", "A man orders pizza, eats it, and dies. Police trace it to a specific topping that was laced with poison by a disgruntled employee.", "No verified case of a poisoned pizza killing a customer has ever been documented. This urban legend likely stems from general food safety fears and has been debunked by multiple food safety agencies."),
]


def _bank_path(mode: str) -> Path:
    return BANK_DIR / f"{mode}.json"


def _read_bank(mode: str) -> dict:
    path = _bank_path(mode)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"entries": [], "used": [], "min_before_refill": 5, "refill_target": 40}


def _write_bank(mode: str, data: dict):
    path = _bank_path(mode)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _mark_used(mode: str, entry: dict):
    data = _read_bank(mode)
    if "used" not in data:
        data["used"] = []
    used = data["used"]
    if mode == "facts":
        for f in entry.get("facts", []):
            n = _normalize(f)
            if n not in used:
                used.append(n)
    elif mode == "what_if":
        for s in entry.get("scenarios", []):
            n = _normalize(s)
            if n not in used:
                used.append(n)
    elif mode == "how_it_works":
        for t in entry.get("topics", []):
            n = _normalize(t)
            if n not in used:
                used.append(n)
    elif mode == "riddles":
        n = _normalize(entry.get("riddle", ""))
        if n and n not in used:
            used.append(n)
    elif mode == "would_you_rather":
        for opt in [entry.get("option_a", ""), entry.get("option_b", "")]:
            n = _normalize(opt)
            if n and n not in used:
                used.append(n)
    elif mode == "history_minute":
        n = _normalize(entry.get("script", ""))
        if n and n not in used:
            used.append(n)
    elif mode == "psychology":
        for h in entry.get("hacks", []):
            n = _normalize(h)
            if n and n not in used:
                used.append(n)
    elif mode == "life_hacks":
        for h in entry.get("hacks", []):
            n = _normalize(h)
            if n and n not in used:
                used.append(n)
    elif mode == "urban_legends":
        n = _normalize(entry.get("legend", ""))
        if n and n not in used:
            used.append(n)
    elif mode == "coincidences":
        for c in entry.get("coincidences", []):
            n = _normalize(c)
            if n and n not in used:
                used.append(n)
    elif mode == "unsolved_mysteries":
        for m in entry.get("mysteries", []):
            n = _normalize(m)
            if n and n not in used:
                used.append(n)
    elif mode == "movie_trivia":
        for t in entry.get("trivia_titles", []):
            n = _normalize(t)
            if n and n not in used:
                used.append(n)
    elif mode == "animal_kingdom":
        for f in entry.get("animal_facts", []):
            n = _normalize(f)
            if n and n not in used:
                used.append(n)
    elif mode == "space_wonders":
        for f in entry.get("space_facts", []):
            n = _normalize(f)
            if n and n not in used:
                used.append(n)
    elif mode == "box_office":
        for f in entry.get("box_office_titles", []):
            n = _normalize(f)
            if n and n not in used:
                used.append(n)
    elif mode == "challenges":
        for c in entry.get("challenges", []):
            n = _normalize(c.get("title", ""))
            if n and n not in used:
                used.append(n)
    elif mode == "satisfying":
        for t in entry.get("topics", []):
            n = _normalize(t)
            if n and n not in used:
                used.append(n)
    elif mode == "negative_hooks":
        for t in entry.get("topics", []):
            n = _normalize(t)
            if n and n not in used:
                used.append(n)
    elif mode == "try_this":
        n = _normalize(entry.get("hook", ""))
        if n and n not in used:
            used.append(n)
    data["used"] = used
    _write_bank(mode, data)


def _avoid_sample(mode: str, max_items: int = 30) -> str:
    data = _read_bank(mode)
    used = data.get("used", [])
    if not used:
        return "none yet"
    sample = random.sample(used, min(max_items, len(used)))
    return "\n".join(f"- {item}" for item in sample)


def _is_duplicate(mode: str, items: list[str], data: dict) -> bool:
    used = set(data.get("used", []))
    for item in items:
        if _normalize(item) in used:
            return True
    return False


def pick(mode: str) -> dict | None:
    data = _read_bank(mode)
    entries = data.get("entries", [])
    if not entries:
        return None
    entry = entries.pop(0)
    data["entries"] = entries
    _mark_used(mode, entry)
    _write_bank(mode, data)
    return entry


def count(mode: str) -> int:
    return len(_read_bank(mode)["entries"])


def needs_refill(mode: str) -> bool:
    data = _read_bank(mode)
    return len(data["entries"]) <= data["min_before_refill"]


def refill(mode: str, force_count: int | None = None):
    try:
        data = _read_bank(mode)
        target = force_count or data["refill_target"]
        existing = len(data["entries"])
        need = target - existing
        if need <= 0:
            return

        print(f"  Bank refill: generating {need} new {mode} entries...")

        if mode == "facts":
            new_entries = _refill_facts(need)
        elif mode == "what_if":
            new_entries = _refill_what_if(need)
        elif mode == "how_it_works":
            new_entries = _refill_how_it_works(need)
        elif mode == "riddles":
            new_entries = _refill_riddles(need)
        elif mode == "would_you_rather":
            new_entries = _refill_wyr(need)
        elif mode == "history_minute":
            new_entries = _refill_history(need)
        elif mode == "psychology":
            new_entries = _refill_psychology(need)
        elif mode == "life_hacks":
            new_entries = _refill_life_hacks(need)
        elif mode == "urban_legends":
            new_entries = _refill_urban_legends(need)
        elif mode == "coincidences":
            new_entries = _refill_3item("coincidences", need, COINCIDENCES_HOOKS, "coincidences", IMAGE_PROMPT_COINCIDENCES)
        elif mode == "unsolved_mysteries":
            new_entries = _refill_3item("unsolved_mysteries", need, UNSOLVED_HOOKS, "mysteries", IMAGE_PROMPT_UNSOLVED)
        elif mode == "movie_trivia":
            new_entries = _refill_3item("movie_trivia", need, MOVIE_TRIVIA_HOOKS, "trivia_titles", IMAGE_PROMPT_MOVIE_TRIVIA)
        elif mode == "animal_kingdom":
            new_entries = _refill_3item("animal_kingdom", need, ANIMAL_KINGDOM_HOOKS, "animal_facts", IMAGE_PROMPT_ANIMAL_KINGDOM)
        elif mode == "space_wonders":
            new_entries = _refill_3item("space_wonders", need, SPACE_WONDERS_HOOKS, "space_facts", IMAGE_PROMPT_SPACE_WONDERS)
        elif mode == "box_office":
            new_entries = _refill_3item("box_office", need, BOX_OFFICE_HOOKS, "box_office_titles", IMAGE_PROMPT_BOX_OFFICE)
        elif mode == "challenges":
            new_entries = _refill_challenges(need)
        elif mode == "satisfying":
            new_entries = _refill_satisfying(need)
        elif mode == "negative_hooks":
            new_entries = _refill_negative_hooks(need)
        elif mode == "try_this":
            new_entries = _refill_try_this(need)
        else:
            return

        data["entries"].extend(new_entries)
        _write_bank(mode, data)
        print(f"  Bank refilled: {len(data['entries'])} {mode} entries total")
    except Exception as e:
        print(f"  Bank refill failed (non-critical): {e}")


def _refill_facts(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        niche = random.choice(NICHES)
        avoid = _avoid_sample("facts")
        prompt = REFILL_PROMPTS["facts"].format(niche=niche, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You write verified facts. Only include facts you are certain are true. One fact per line, numbered.")
        except Exception as e:
            print(f"  LLM error (facts): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        facts = []
        for line in raw.split("\n"):
            line = line.strip().lstrip("*- ")
            if not line or len(line) < 15:
                continue
            if (line[0].isdigit() and (". " in line[:4] or ") " in line[:4])):
                clean = line.split(". ", 1)[-1].split(") ", 1)[-1].strip()
                if clean and len(clean) > 10:
                    facts.append(clean.rstrip(".") + ".")

        if len(facts) >= 3 and not _is_duplicate("facts", facts, _read_bank("facts")):
            hook = random.choice(FACT_HOOKS)
            image_prompts = [
                IMAGE_PROMPT_FACT.format(keywords=" ".join(f.split()[:12]))
                for f in facts
            ]
            tts_script = f"{hook} {' '.join(facts)}"
            entry = {
                "title": f"{hook} {facts[0][:60]}...",
                "niche": niche,
                "hook": hook,
                "facts": facts,
                "image_prompts": image_prompts,
                "script": tts_script,
                "tts_script": tts_script,
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_what_if(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("what_if")
        prompt = REFILL_PROMPTS["what_if"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.9, max_tokens=800,
                            system="You write creative 'What If' scenarios for children's videos.")
        except Exception as e:
            print(f"  LLM error (what_if): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        scenarios = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("SCENARIO:"):
                if current.get("scenario") and current.get("explanation"):
                    scenarios.append((current["scenario"], current["explanation"]))
                current = {"scenario": line.split(":", 1)[-1].strip().lower()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("scenario") and current.get("explanation"):
            scenarios.append((current["scenario"], current["explanation"]))

        scenario_texts = [s for s, _ in scenarios]
        if len(scenarios) >= 3 and not _is_duplicate("what_if", scenario_texts, _read_bank("what_if")):
            hook = random.choice(FACT_HOOKS)
            image_prompts = [
                IMAGE_PROMPT_WHATIF.format(scenario=s)
                for s, _ in scenarios
            ]
            tts_lines = [f"{hook} {s}. {e}" for s, e in scenarios]
            entry = {
                "title": f"{hook} {scenarios[0][0]}",
                "hook": hook,
                "scenarios": [s for s, _ in scenarios],
                "explanations": [e for _, e in scenarios],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_how_it_works(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("how_it_works")
        prompt = REFILL_PROMPTS["how_it_works"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You explain how everyday things work in simple, accurate terms.")
        except Exception as e:
            print(f"  LLM error (how_it_works): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        topics = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                if current.get("topic") and current.get("explanation"):
                    topics.append((current["topic"], current["explanation"]))
                current = {"topic": line.split(":", 1)[-1].strip().lower()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("topic") and current.get("explanation"):
            topics.append((current["topic"], current["explanation"]))

        topic_texts = [t for t, _ in topics]
        if len(topics) >= 3 and not _is_duplicate("how_it_works", topic_texts, _read_bank("how_it_works")):
            hook = random.choice([
                "Ever wondered how this works?", "Here's how it actually works.",
                "You use it every day. But how does it work?", "Let me explain how this works.",
            ])
            image_prompts = [
                IMAGE_PROMPT_HOW.format(topic=t)
                for t, _ in topics
            ]
            tts_lines = [e for _, e in topics]
            entry = {
                "title": f"{hook} {topics[0][0].capitalize()}",
                "hook": hook,
                "topics": [t for t, _ in topics],
                "explanations": [e for _, e in topics],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_riddles(need: int) -> list:
    entries = []
    attempts = 0
    hooks = [
        "Can you solve this riddle?", "Here's a riddle for you:",
        "Think you're smart? Try this:", "Test your brain with this riddle:",
        "Only 1 in 10 can solve this:", "Here's a tricky one:",
    ]
    while len(entries) < need and attempts < need * 5:
        rtype = random.choice(RIDDLE_TYPES)
        avoid = _avoid_sample("riddles")
        prompt = REFILL_PROMPTS["riddles"].format(rtype=rtype, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=300,
                            system="You write clever riddles suitable for all ages.")
        except Exception as e:
            print(f"  LLM error (riddles): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        riddle = answer = explanation = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("RIDDLE:"):
                riddle = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("ANSWER:"):
                answer = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[-1].strip()
        if riddle and answer and not _is_duplicate("riddles", [riddle], _read_bank("riddles")):
            hook = random.choice(hooks)
            entry = {
                "title": "Can You Solve This Riddle?",
                "hook": hook,
                "riddle": riddle,
                "answer": answer,
                "explanation": explanation or f"The answer is {answer}.",
                "image_prompt_riddle": IMAGE_PROMPT_RIDDLE.format(riddle=riddle[:80]),
                "image_prompt_answer": IMAGE_PROMPT_RIDDLE_ANSWER.format(answer=answer[:80]),
                "tts_script": f"{hook} {riddle} Pause and think about it. The answer is... {answer}. {explanation or f'The answer is {answer}.'}",
            }
            entries.append(entry)
        attempts += 1
    return entries


def _refill_wyr(need: int) -> list:
    entries = []
    attempts = 0
    hooks = [
        "Would you rather...", "Choose wisely:", "Which one would you pick?",
        "Hard choice incoming:", "What would you do?", "Pick your side:",
    ]
    while len(entries) < need and attempts < need * 5:
        cat = random.choice(WYR_CATEGORIES)
        avoid = _avoid_sample("would_you_rather")
        prompt = REFILL_PROMPTS["would_you_rather"].format(cat=cat, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.9, max_tokens=200,
                            system="You write fun 'Would You Rather' questions suitable for all ages.")
        except Exception as e:
            print(f"  LLM error (would_you_rather): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        a = b = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("OPTION_A:") or line.upper().startswith("A)"):
                a = line.split(":", 1)[-1].split(")", 1)[-1].strip()
            elif line.upper().startswith("OPTION_B:") or line.upper().startswith("B)"):
                b = line.split(":", 1)[-1].split(")", 1)[-1].strip()
        if a and b and not _is_duplicate("would_you_rather", [a, b], _read_bank("would_you_rather")):
            hook = random.choice(hooks)
            entries.append({
                "title": "Would You Rather?",
                "hook": hook,
                "option_a": a,
                "option_b": b,
                "tts_script": f"{hook} {a} or {b}. Which one would you choose? Comment below!",
            })
        attempts += 1
    return entries


def _refill_history(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        niche = random.choice(HISTORY_NICHES)
        avoid = _avoid_sample("history_minute")
        prompt = REFILL_PROMPTS["history_minute"].format(niche=niche, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=400,
                            system="You write verified historical facts. Only include events you are certain are accurate. Make it engaging for short-form video.")
        except Exception as e:
            print(f"  LLM error (history): {e}")
            attempts += 1
            continue
        if not raw or len(raw) < 30:
            attempts += 1
            continue

        script = raw.strip()
        if not _is_duplicate("history_minute", [script], _read_bank("history_minute")):
            hook = random.choice(HISTORY_HOOKS)
            topic = script.split(".")[0].strip()
            keywords = " ".join(script.split()[:15])
            image_prompt = IMAGE_PROMPT_HISTORY.format(topic=keywords)
            tts_script = f"{hook} {script}"
            entry = {
                "title": f"{hook} {topic[:60]}...",
                "niche": niche,
                "hook": hook,
                "script": script,
                "image_prompt": image_prompt,
                "tts_script": tts_script,
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_psychology(need: int) -> list:
    entries = []
    attempts = 0
    hooks = PSYCHOLOGY_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("psychology")
        prompt = REFILL_PROMPTS["psychology"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You write about real psychology effects in simple, fascinating terms. Only include verified psychological phenomena.")
        except Exception as e:
            print(f"  LLM error (psychology): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

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

        hack_texts = [h for h, _ in hacks]
        if len(hacks) >= 3 and not _is_duplicate("psychology", hack_texts, _read_bank("psychology")):
            hook = random.choice(hooks)
            image_prompts = [
                IMAGE_PROMPT_PSYCHOLOGY.format(hack=h)
                for h, _ in hacks
            ]
            tts_lines = [f"{h}. {e}" for h, e in hacks]
            entry = {
                "title": f"Psychology Hack: {hacks[0][0]}",
                "hook": hook,
                "hacks": [h for h, _ in hacks],
                "explanations": [e for _, e in hacks],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_life_hacks(need: int) -> list:
    entries = []
    attempts = 0
    hooks = LIFE_HACKS_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("life_hacks")
        prompt = REFILL_PROMPTS["life_hacks"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You write practical, clever life hacks that actually work. Each hack must be safe, simple, and useful.")
        except Exception as e:
            print(f"  LLM error (life_hacks): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

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

        hack_texts = [h for h, _ in hacks]
        if len(hacks) >= 3 and not _is_duplicate("life_hacks", hack_texts, _read_bank("life_hacks")):
            hook = random.choice(hooks)
            image_prompts = [
                IMAGE_PROMPT_LIFE_HACKS.format(hack=h)
                for h, _ in hacks
            ]
            tts_lines = [f"{h}. {e}" for h, e in hacks]
            entry = {
                "title": f"{hook} {hacks[0][0]}",
                "hook": hook,
                "hacks": [h for h, _ in hacks],
                "explanations": [e for _, e in hacks],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_urban_legends(need: int) -> list:
    entries = []
    attempts = 0
    hooks = URBAN_LEGENDS_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("urban_legends")
        prompt = REFILL_PROMPTS["urban_legends"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You write about real urban legends. Always distinguish myth from fact. Keep it family-friendly.")
        except Exception as e:
            print(f"  LLM error (urban_legends): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

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

        if legend and myth and truth and not _is_duplicate("urban_legends", [legend], _read_bank("urban_legends")):
            hook = random.choice(hooks)
            image_prompts = [
                IMAGE_PROMPT_URBAN_LEGENDS_MYTH.format(legend=legend),
                IMAGE_PROMPT_URBAN_LEGENDS_TRUTH.format(legend=legend),
            ]
            entry = {
                "title": f"Urban Legend: {legend}",
                "hook": hook,
                "legend": legend,
                "myth": myth,
                "truth": truth,
                "image_prompts": image_prompts,
                "script": f"{hook} {legend}. {myth} But here's the truth: {truth}",
                "tts_script": f"{hook} {legend}. {myth} But here's the truth: {truth}",
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_3item(mode: str, need: int, hooks: list, list_key: str, img_prompt: str) -> list:
    """Generic refill for 3-item-per-entry modes (coincidences, unsolved, trivia, etc)."""
    entries = []
    attempts = 0
    title_keys = {"coincidences": "TITLE", "unsolved_mysteries": "CASE", "movie_trivia": "MOVIE", "animal_kingdom": "ANIMAL", "space_wonders": "TITLE", "box_office": "TITLE"}
    story_keys = {"coincidences": "STORY", "unsolved_mysteries": "STORY", "movie_trivia": "TRIVIA", "animal_kingdom": "FACT", "space_wonders": "FACT", "box_office": "FACT"}
    tk = title_keys[mode]
    sk = story_keys[mode]
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample(mode)
        prompt = REFILL_PROMPTS[mode].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=1000,
                            system="You write verified true content. Every detail must be accurate and documented.")
        except Exception as e:
            print(f"  LLM error ({mode}): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith(tk + ":"):
                if current.get("title") and current.get("story"):
                    items.append((current["title"], current["story"]))
                current = {"title": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith(sk + ":") and current:
                current["story"] = line.split(":", 1)[-1].strip()
        if current.get("title") and current.get("story"):
            items.append((current["title"], current["story"]))
        titles = [i[0] for i in items]
        if len(items) >= 3 and not _is_duplicate(mode, titles, _read_bank(mode)):
            hook = random.choice(hooks)
            stories = [i[1] for i in items]
            image_prompts = [img_prompt.format(title=t) for t in titles]
            tts_lines = [f"{t}. {s}" for t, s in items]
            entry = {
                "title": f"{hook} {titles[0]}",
                "hook": hook,
                list_key: titles,
                "stories": stories,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1
    return entries


def _refill_negative_hooks(need: int) -> list:
    entries = []
    attempts = 0
    hooks = NEGATIVE_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("negative_hooks")
        prompt = REFILL_PROMPTS["negative_hooks"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.9, max_tokens=600,
                            system="You write dark, uncomfortable truths about life, society, human nature, and reality. Be brutally honest.")
        except Exception as e:
            print(f"  LLM error (negative_hooks): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        topics = []
        truths = []
        current = None
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TRUTH:"):
                current = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:") and current:
                truths.append(line.split(":", 1)[-1].strip())
                topics.append(current)
                current = None
        if len(topics) >= 3 and not _is_duplicate("negative_hooks", topics, _read_bank("negative_hooks")):
            hook = random.choice(hooks)
            image_prompts = [
                IMAGE_PROMPT_NEGATIVE.format(topic=t.lower().replace(" ", "_")[:50])
                for t in topics
            ]
            tts_lines = [f"{t}. {d}" for t, d in zip(topics, truths)]
            entry = {
                "title": f"Dark Truth: {topics[0][:50]}",
                "hook": hook,
                "topics": topics,
                "truths": truths,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": f"{hook} {' '.join(tts_lines)}",
            }
            entries.append(entry)
        attempts += 1
    return entries


def _refill_satisfying(need: int) -> list:
    entries = []
    attempts = 0
    hooks = SATISFYING_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("satisfying")
        prompt = REFILL_PROMPTS["satisfying"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=600,
                            system="You write about oddly satisfying content, DIY projects, restorations, and cleaning transformations. Be descriptive and visual.")
        except Exception as e:
            print(f"  LLM error (satisfying): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        topics = []
        descriptions = []
        current = None
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                current = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("DESCRIPTION:") and current:
                descriptions.append(line.split(":", 1)[-1].strip())
                topics.append(current)
                current = None

        if len(topics) >= 3 and not _is_duplicate("satisfying", topics, _read_bank("satisfying")):
            hook = random.choice(hooks)
            image_prompts = [
                IMAGE_PROMPT_SATISFYING.format(topic=t.lower().replace(" ", "_")[:50])
                for t in topics
            ]
            tts_lines = [f"{t}. {d}" for t, d in zip(topics, descriptions)]
            entry = {
                "title": f"Oddly Satisfying: {topics[0][:50]}",
                "hook": hook,
                "topics": topics,
                "descriptions": descriptions,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": f"{hook} {' '.join(tts_lines)}",
            }
            entries.append(entry)
        attempts += 1
    return entries


def _refill_challenges(need: int) -> list:
    entries = []
    attempts = 0
    hooks = CHALLENGES_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("challenges")
        prompt = REFILL_PROMPTS["challenges"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=700,
                            system="You write fun, engaging physical challenges and stunts for short-form video content.")
        except Exception as e:
            print(f"  LLM error (challenges): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        challenges = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("CHALLENGE:"):
                if current.get("title") and current.get("description"):
                    challenges.append(current)
                current = {"title": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("DESCRIPTION:") and current:
                current["description"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("RESULT:") and current:
                current["result"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("SKILL:") and current:
                current["skill"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("DIFFICULTY:") and current:
                current["difficulty"] = line.split(":", 1)[-1].strip()
        if current.get("title") and current.get("description"):
            challenges.append(current)

        titles = [c["title"] for c in challenges]
        if len(challenges) >= 3 and not _is_duplicate("challenges", titles, _read_bank("challenges")):
            hook = random.choice(hooks)
            image_prompts = [
                IMAGE_PROMPT_CHALLENGES.format(challenge=c["title"].lower().replace(" ", "_")[:50])
                for c in challenges
            ]
            tts_lines = [f"{c['title']}. {c['description']}" for c in challenges]
            entry = {
                "title": f"Can You Do This? {challenges[0]['title'][:50]}",
                "hook": hook,
                "challenges": challenges,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": f"{hook} {' '.join(tts_lines)}",
            }
            entries.append(entry)
        attempts += 1
    return entries


def _refill_try_this(need: int) -> list:
    entries = []
    attempts = 0
    hooks = TRY_THIS_HOOKS
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("try_this")
        prompt = REFILL_PROMPTS["try_this"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.9, max_tokens=300,
                            system="You write interactive brain hacks and visual illusions. Short, punchy, experiential.")
        except Exception as e:
            print(f"  LLM error (try_this): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        result = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("HOOK:"):
                result["hook"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("SETUP:"):
                result["setup"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("ACTION:"):
                result["action"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("REVEAL:"):
                result["reveal"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:"):
                result["explanation"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("PROMPT:"):
                result["prompt"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("IMAGE:"):
                result["image_style"] = line.split(":", 1)[-1].strip() + ", 9:16"
        if result.get("hook") and result.get("reveal") and not _is_duplicate("try_this", [result["hook"]], _read_bank("try_this")):
            result.setdefault("setup", "")
            result.setdefault("action", "")
            result.setdefault("explanation", "")
            result.setdefault("prompt", result["reveal"])
            result.setdefault("image_style", "minimal brain illusion, abstract, 9:16")
            entry = {
                "hook": result["hook"],
                "setup": result["setup"],
                "action": result["action"],
                "reveal": result["reveal"],
                "explanation": result["explanation"],
                "prompt": result["prompt"],
                "image_style": result["image_style"],
            }
            entries.append(entry)
        attempts += 1
    return entries


def ensure_refilled(mode: str):
    if needs_refill(mode):
        print(f"  {mode} bank low ({count(mode)} left), refilling...")
        refill(mode)
    else:
        print(f"  {mode} bank healthy ({count(mode)} entries)")
