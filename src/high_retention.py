"""High-retention scripting engine — hooks, pattern interrupts, curiosity gaps, and pacing."""

import random

OPENING_BOMBS = [
    "Here's something most people won't tell you:",
    "Pay attention. This changes everything:",
    "Stop scrolling. This one's different:",
    "You need to hear this:",
    "This is going to change how you see things:",
    "Don't scroll past this. Trust me:",
    "I'm about to blow your mind:",
    "This is the most important thing you'll hear today:",
    "Ready? Because this hits different:",
    "Listen carefully. This matters:",
]

PATTERN_INTERRUPTS = [
    "But here's the thing:",
    "Wait. It gets worse:",
    "Here's where it gets interesting:",
    "But that's not the crazy part:",
    "Here's what nobody tells you:",
    "Think about that for a second:",
    "But here's the twist:",
    "This is where it gets wild:",
    "Pause and think about that:",
    "Now here's the part they don't want you to know:",
]

CLOSING_PUNCHES = [
    "Think about that.",
    "Let that sink in.",
    "That's the reality.",
    "Now you know.",
    "Doesn't that make you think?",
    "That's the truth they don't teach you.",
    "Pass this on to someone who needs to hear it.",
    "That's just how it is.",
    "Now you see the bigger picture.",
    "That hit different, didn't it?",
]

COUNTDOWNS = ["3... 2... 1...", "Ready? Here we go:", "Countdown: 3, 2, 1 — go:", "In 3, 2, 1...",]

CURIOSITY_BUILDERS = [
    "The reason will surprise you.",
    "You won't believe why.",
    "Most people get this wrong.",
    "And the reason is not what you think.",
    "Wait till you hear the explanation.",
    "The science behind this is wild.",
]

ITEM_OPENERS = [
    "First up:",
    "Number one:",
    "Starting with:",
    "Here's the first one:",
    "Kicking off with:",
]

ITEM_TRANSITIONS = [
    "Next up:",
    "Moving on:",
    "Number {n}:",
    "Here's another one:",
    "This next one is wild:",
    "Coming in at #{n}:",
    "Here's the next truth:",
]

RETENTION_PATTERNS = {
    "challenges": {
        "intro": [
            "Think you're tough? Let's test that.",
            "99% of people fail at least one of these. Let's see how you do:",
            "I'm about to give you 5 challenges. Be honest — how many can you do?",
            "These challenges look easy. They're not. Ready?",
        ],
        "mid_roll": [
            "Still think you can do all of these?",
            "That one was harder than it looked, right?",
            "Okay, this next one separates the pros:",
            "Most people tap out by this point. Let's see:",
            "This is where it gets real:",
        ],
        "outro": [
            "How many did you get right? Comment your score.",
            "Be honest — which one would you fail first?",
            "Share this with someone who needs to prove themselves.",
            "If you made it this far, you're tougher than most.",
        ],
    },
    "satisfying": {
        "intro": [
            "You didn't know you needed this. But trust me, you do:",
            "Sit back. Relax. This is pure satisfaction:",
            "Your brain is about to feel very, very good:",
            "There's something about watching these that just feels right:",
        ],
        "mid_roll": [
            "Admit it — that was satisfying.",
            "Tell me that didn't feel good to watch.",
            "Okay, this next one is even better:",
            "The satisfaction level just keeps going up:",
        ],
        "outro": [
            "Which one was your favorite? Comment below.",
            "If you need more of this, subscribe. You know you want to.",
            "That's it. Now go watch it again — I won't judge.",
        ],
    },
    "negative_hooks": {
        "intro": [
            "I'm about to ruin your day. Ready?",
            "You're not ready for what I'm about to tell you:",
            "This is going to sit with you for a while:",
            "If you're easily disturbed, look away. If not, listen up:",
        ],
        "mid_roll": [
            "Still with me? Good. Because it gets darker:",
            "Think that was bad? Wait for this one:",
            "This next one will really mess with your head:",
            "I told you this would be uncomfortable. And it gets worse:",
        ],
        "outro": [
            "Which one hit you the hardest? Comment honestly.",
            "I warned you. Now share this with someone who needs a reality check.",
            "Follow for more uncomfortable truths. You know you need them.",
        ],
    },
}


def retention_script(items: list[dict], mode: str, hook: str = "") -> str:
    patterns = RETENTION_PATTERNS.get(mode, {
        "intro": ["Check this out:"],
        "mid_roll": ["Next up:"],
        "outro": ["Comment your thoughts."],
    })

    intro = random.choice(patterns["intro"])
    mid = random.choice(patterns["mid_roll"])
    outro = random.choice(patterns["outro"])

    parts = [f"{hook} {intro}"]

    titles = []
    for i, item in enumerate(items):
        if isinstance(item, dict):
            titles.append(item.get("title", item.get("topic", str(item))))
        else:
            titles.append(str(item))

    n = len(titles)
    for i, title in enumerate(titles):
        if i == 0:
            parts.append(f"{title}.")
        elif i == n - 1:
            parts.append(f"And finally — {title}.")
        elif i == n // 2:
            parts.append(f"{mid} {title}.")
        else:
            parts.append(f"{title}.")

    parts.append(outro)
    return " ".join(parts)


def retention_tts(items: list[dict], mode: str, hook: str = "") -> str:
    patterns = RETENTION_PATTERNS.get(mode, {
        "intro": ["Check this out:"],
        "mid_roll": ["Next up:"],
        "outro": ["Comment your thoughts."],
    })

    intro = random.choice(patterns["intro"])
    mid = random.choice(patterns["mid_roll"])
    outro = random.choice(patterns["outro"])

    parts = [f"{hook} {intro}"]

    for i, item in enumerate(items):
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            title = item.get("title", item.get("topic", ""))
            desc = item.get("description", item.get("truth", item.get("explanation", "")))
            text = f"{title}. {desc}" if desc else title
            parts.append(text)
        if i < len(items) - 1 and i == len(items) // 2 - 1:
            parts.append(random.choice(PATTERN_INTERRUPTS))

    parts.append(outro)
    return ". ".join(parts)


def hook_with_bait(hook: str) -> str:
    bait = random.choice(OPENING_BOMBS)
    return f"{bait} {hook}"
