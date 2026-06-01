"""Fast-paced challenges & stunts — dares, skill tests, and physical challenges."""

import random
import bank_manager

CHALLENGE_HOOKS = [
    "Think you can do this? Watch till the end:",
    "99% of people fail this challenge. Can you?",
    "This challenge looks easy. It's not:",
    "How far would YOU get? Be honest:",
    "Most people give up before the end. Prove us wrong:",
    "This stunt requires serious skill. Ready?",
    "Warning: this challenge is harder than it looks:",
    "You vs the challenge. Let's see who wins:",
    "Only 1% can complete all of these. You?",
    "Think you're tough? Try these challenges:",
    "Don't try this at home. But watch and learn:",
    "This challenge separates the pros from the amateurs:",
]

CHALLENGES_POOL = [
    ("Hold your breath for 30 seconds", "Take a deep breath and hold it. Most people tap out at 20 seconds. Your lungs will burn.", "Tapped out at 22 seconds", "lung capacity", "medium"),
    ("Balance a book on your head for 1 minute", "Place a hardcover book on your crown and walk in a straight line. Sounds easy until you try it.", "Dropped it at 35 seconds", "balance", "easy"),
    ("Stack 6 coins and pull the bottom one out", "Stack 6 quarters perfectly, then flick the bottom one out without toppling the rest. Steady hands only.", "Tower fell on the third attempt", "dexterity", "medium"),
    ("Keep a balloon in the air for 30 seconds", "No hands. Use only your head, knees, and feet. The floor is lava — and it's game over if the balloon touches it.", "Lasted 18 seconds", "coordination", "easy"),
    ("Eat a spoonful of cinnamon without drinking water", "One heaping spoonful. No water for 30 seconds. Your mouth will feel like a desert. 99% fail this.", "Coughing fit at 12 seconds", "pain tolerance", "hard"),
    ("Stand on one foot for 2 minutes with eyes closed", "Arms at your sides. Eyes shut. One foot off the ground. Your body will start swaying uncontrollably.", "Fell at 47 seconds", "balance", "medium"),
    ("Dunk a basketball 3 times in a row", "On a regulation hoop. No rim hangs. Three clean dunks. If you're under 6 feet tall, good luck.", "Got it on the fifth try", "vertical jump", "hard"),
    ("Solve a Rubik's cube in under 2 minutes", "Scramble it yourself first. Then solve it. Under 2 minutes or it doesn't count. Beginners take 5+ minutes.", "Completed at 1:48", "speed", "hard"),
    ("Don't blink for 60 seconds", "Stare straight ahead. No blinking. Your eyes will start burning at 15 seconds. Tears by 30.", "Broke at 23 seconds", "willpower", "easy"),
    ("Catch a falling ruler with one hand", "Have someone hold a ruler vertically and drop it. Catch it between your thumb and finger before it falls through. Average reaction: misses by 4 inches.", "Caught it on the third drop", "reflexes", "easy"),
    ("Flip a water bottle and land it upright", "Fill a bottle 1/3 full. Flip it in the air. Land it upright on the table. It's harder than the internet made it look.", "Landed on the 7th try", "precision", "easy"),
    ("Whistle a full song without stopping for breath", "Pick any song. Whistle the whole thing in one breath. Most people run out of air in 10 seconds.", "Ran out of breath at 'Happy Birthday' chorus", "breath control", "medium"),
    ("Walk a straight line heel-to-toe for 20 steps", "One foot directly in front of the other. 20 steps without wobbling. The sobriety test is harder when you're sober.", "Wobbled at step 14", "balance", "medium"),
    ("Keep a straight face while getting tickled for 30 seconds", "Have someone tickle your ribs. Don't laugh, smile, or flinch. 30 seconds is an eternity.", "Laughed at 8 seconds", "self control", "hard"),
    ("Type 'The quick brown fox jumps over the lazy dog' backwards in under 30 seconds", "Without looking at the keyboard. Every letter in reverse. Your muscle memory will fight you the whole way.", "Completed at 27 seconds with 3 mistakes", "typing skill", "medium"),
    ("Stand up from a seated position without using your hands", "Sit on the floor with legs crossed. Stand up. Hands must stay off the ground the entire time.", "Used a hand at second attempt", "core strength", "medium"),
    ("Balance a pencil on your nose for 10 seconds", "Place a pencil horizontally on the bridge of your nose. Tilt your head back slightly. Don't let it fall.", "Dropped at 6 seconds", "balance", "easy"),
    ("Eat 3 saltine crackers in 60 seconds without water", "Saltines only. No water. Your mouth will turn into a desert paste. Most people can't finish 2.", "Choked on the second cracker", "grit", "hard"),
    ("Do 20 pushups in 30 seconds", "Proper form. Chest to the floor. 20 in 30 seconds is a pace most people can't maintain past 12.", "Made it to 15", "endurance", "medium"),
    ("Recite the alphabet backwards in 15 seconds", "Z to A. No pauses. No mistakes. Your brain has only ever gone forward — reversing it is surprisingly hard.", "Stumbled at W at 12 seconds", "mental agility", "medium"),
    ("Keep a note spinning on your finger for 20 seconds", "A dollar bill or any paper note. Spin it like a basketball on your fingertip. 20 seconds without dropping.", "Dropped at 14 seconds", "dexterity", "medium"),
    ("Chug a can of soda in 10 seconds", "Full 12oz can. 10 seconds. The carbonation will fight back. Don't burp until after.", "Finished at 8 seconds with a massive burp", "speed", "medium"),
    ("Touch your nose with your tongue", "Simple test of tongue length. Most people can only reach their upper lip. If you can touch your nose, you're in the 10%.", "Missed by 1 centimeter", "flexibility", "easy"),
    ("Do a wall sit for 90 seconds", "Back flat against the wall, knees at 90 degrees. 90 seconds feels like 10 minutes when your thighs are on fire.", "Gave up at 62 seconds", "leg strength", "hard"),
    ("Snap your fingers with both hands at the same time", "Both hands. One snap. Same exact moment. Your brain struggles to coordinate both hands simultaneously.", "Achieved on the 12th attempt", "coordination", "medium"),
    ("Keep a hula hoop going for 30 seconds", "Around your waist. No hands. 30 seconds without the hoop dropping. Adults are worse at this than kids.", "Dropped at 22 seconds", "rhythm", "medium"),
]

CATEGORIES = ["balance", "dexterity", "endurance", "speed", "willpower", "coordination", "reflexes", "strength"]

IMAGE_STYLES = [
    "cinematic action shot, {challenge}, dramatic lighting, fast-paced motion blur, 9:16 vertical, intense atmosphere, adrenaline",
    "dynamic sports photography, {challenge}, sweat and determination, dramatic shadows, 9:16 vertical, energy and movement",
    "close-up intense moment, {challenge}, extreme focus, dramatic lighting, 9:16 vertical, gritty realistic style",
    "cinematic challenge moment, {challenge}, countdown timer overlay, neon lights, 9:16 vertical, high energy urban vibe",
    "dramatic slow-motion capture, {challenge}, peak action moment, motion blur background, 9:16 vertical, cinematic color grading",
]


def generate_challenges_script() -> dict:
    entry = bank_manager.pick("challenges")
    if entry:
        print(f"  Using banked challenges ({bank_manager.count('challenges')} left)")
        return entry

    print("  Bank empty, generating fresh challenges...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(CHALLENGES_POOL, min(5, len(CHALLENGES_POOL)))
    hook = random.choice(CHALLENGE_HOOKS)
    challenges = []
    image_prompts = []
    tts_lines = []
    for title, desc, _, _, _ in items:
        challenges.append({"title": title, "description": desc})
        kw = title.lower().replace(" ", "_")[:50]
        style = random.choice(IMAGE_STYLES)
        image_prompts.append(style.format(challenge=kw))
        tts_lines.append(f"{title}. {desc}")
    return {
        "title": f"Can You Do This? {items[0][0][:50]}",
        "hook": hook,
        "challenges": [{"title": t, "description": d} for t, d, _, _, _ in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": f"{hook} {' '.join(tts_lines)}",
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 5 fun physical challenges or stunts that someone can attempt. "
            "Each should be a specific, measurable challenge (e.g., 'Hold your breath for 30 seconds', "
            "'Balance a book on your head for 1 minute'). "
            "Mix easy, medium, and hard difficulties. "
            "Format exactly:\n"
            "CHALLENGE: [short name of the challenge, 3-8 words]\n"
            "DESCRIPTION: [one punchy sentence explaining what to do and why it's hard]\n\n"
            "Make each one feel like a dare."
        )
        system = "You write fun, engaging physical challenges and stunts for short-form video content. Be creative and specific."
        raw = _generate(prompt, temperature=0.9, max_tokens=700, system=system)
        if not raw:
            return None
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
        if current.get("title") and current.get("description"):
            challenges.append(current)
        if challenges and len(challenges) >= 3:
            hook = random.choice(CHALLENGE_HOOKS)
            image_prompts = []
            for c in challenges:
                kw = c["title"].lower().replace(" ", "_")[:50]
                image_prompts.append(random.choice(IMAGE_STYLES).format(challenge=kw))
            tts_lines = [f"{c['title']}. {c['description']}" for c in challenges]
            return {
                "title": f"Can You Do This? {challenges[0]['title'][:50]}",
                "hook": hook,
                "challenges": challenges,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": f"{hook} {' '.join(tts_lines)}",
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
