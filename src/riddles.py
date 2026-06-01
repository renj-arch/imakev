"""Riddle generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "Can you solve this riddle?", "Here's a riddle for you:",
    "Think you're smart? Try this:", "Test your brain with this riddle:",
    "Only 1 in 10 can solve this:", "Here's a tricky one:",
]

RIDDLE_TYPES = [
    "logic", "wordplay", "math", "lateral thinking", "observation",
    "classic", "nature", "science", "everyday", "animal",
]


def generate_riddle_script() -> dict:
    entry = bank_manager.pick("riddles")
    if entry:
        print(f"  Using banked riddle ({bank_manager.count('riddles')} left)")
        return entry

    print("  Bank empty, generating fresh riddle...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    selected = random.sample(FALLBACKS, min(3, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    tts_parts = [f"Riddle {i+1}: {r[0]} The answer is {r[1]}. {r[2]}" for i, r in enumerate(selected)]
    return {
        "title": f"Can You Solve These Riddles?",
        "hook": hook,
        "riddle": f"{selected[0][0]} And here's another: {selected[1][0] if len(selected) > 1 else ''}",
        "answer": selected[0][1],
        "explanation": selected[0][2],
        "image_prompt_riddle": f"mysterious cinematic scene: {selected[0][0][:80]}, dark moody lighting, question marks, 9:16 vertical, intrigue",
        "image_prompt_answer": f"cinematic reveal scene: {selected[0][1][:80]}, bright warm lighting, discovery moment, 9:16 vertical",
        "tts_script": f"{hook} {' '.join(tts_parts)}",
    }


FALLBACKS = [
    ("What has keys but can't open locks?", "A piano", "A piano has keys that make music, not open doors."),
    ("What gets wetter the more it dries?", "A towel", "A towel dries you off, but in doing so it gets wet itself."),
    ("What can travel around the world while staying in a corner?", "A stamp", "A stamp sits in the corner of an envelope but travels everywhere."),
    ("What has a head and a tail but no body?", "A coin", "A coin has a heads side and a tails side, but no body."),
    ("What has cities but no houses, forests but no trees?", "A map", "A map shows cities and forests as symbols, not real ones."),
    ("What can you break even if you never pick it up?", "A promise", "Promises are broken by not keeping them, not by physical force."),
    ("What goes up but never comes down?", "Your age", "Age only increases with time, it never decreases."),
    ("What building has the most stories?", "The library", "Libraries are filled with books, each telling a story."),
    ("What has many teeth but can't bite?", "A comb", "A comb has teeth for detangling hair, not for biting."),
    ("What invention lets you look right through a wall?", "A window", "Windows are see-through panels set into walls."),
    ("If you drop me I'll crack, but smile at me and I'll smile back. What am I?", "A mirror", "A mirror cracks when dropped and reflects your smile back at you."),
    ("What can fill a room but takes up no space?", "Light", "Light illuminates a room without occupying physical space."),
    ("What has words but never speaks?", "A book", "Books contain words on pages but cannot speak aloud."),
    ("What is always in front of you but can't be seen?", "The future", "The future lies ahead of you but is invisible."),
    ("What can you catch but not throw?", "A cold", "You catch a cold virus, but you can't physically throw it."),
    ("What gets sharper the more you use it?", "Your brain", "The more you use your brain to think, the sharper it becomes."),
    ("What sleeps when you eat and wakes when you drink?", "Fire", "Fire goes dormant when you add fuel and flares up with air."),
    ("What has one eye but can't see?", "A needle", "A needle has an eye for thread but cannot see."),
    ("What comes once in a minute, twice in a moment, but never in a thousand years?", "The letter M", "The letter M appears once in 'minute', twice in 'moment', and not in 'thousand years'."),
    ("What is full of holes but still holds water?", "A sponge", "A sponge has many holes but absorbs and holds water."),
    ("What starts with T, ends with T, and has T in it?", "A teapot", "A teapot starts with T, ends with T, and has tea (T) inside it."),
    ("What can run but never walks?", "A river", "A river flows (runs) continuously but doesn't have legs to walk."),
    ("What has four wheels and flies?", "A garbage truck", "A garbage truck has four wheels and flies (insects) are attracted to it."),
    ("What belongs to you but others use it more than you?", "Your name", "Other people say and use your name more than you do."),
    ("What can you keep after giving to someone?", "Your word", "You can give your word (promise) and still keep it yourself."),
]


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Write 3 clever riddles. Format each exactly:\n"
            "RIDDLE: [the riddle question]\n"
            "ANSWER: [short answer]\n"
            "EXPLANATION: [one sentence explanation]\n\n"
            "Make them clever but solvable. Suitable for all ages."
        )
        system = "You write clever riddles suitable for all ages."
        raw = _generate(prompt, temperature=0.8, max_tokens=600, system=system)
        if not raw:
            return None
        riddle = answer = explanation = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("RIDDLE:"):
                riddle = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("ANSWER:"):
                answer = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[-1].strip()
        if riddle and answer:
            hook = random.choice(HOOKS)
            return {
                "title": f"Can You Solve This Riddle?",
                "hook": hook,
                "riddle": riddle,
                "answer": answer,
                "explanation": explanation or f"The answer is {answer}.",
                "image_prompt_riddle": f"mysterious cinematic scene: {riddle[:80]}, dark moody lighting, question marks, 9:16 vertical, intrigue",
                "image_prompt_answer": f"cinematic reveal scene: {answer[:80]}, bright warm lighting, discovery moment, 9:16 vertical",
                "tts_script": f"{hook} {riddle} The answer is {answer}. {explanation or f'The answer is {answer}.'}",
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
