"""Kid-friendly SEO for 'Pajama Explorers' — no AI mentions, gentle engagement."""

import random

HASHTAGS = [
    "#shorts", "#kidsshorts", "#bedtimestory", "#storyforkids",
    "#kidsstory", "#fairytale", "#imagination", "#magic",
    "#kidsvideo", "#storytime", "#pajamaexplorers", "#adventure",
    "#dreams", "#childrensstory", "#reading", "#bedtime",
]

TITLE_TEMPLATES = [
    "Pajama Explorers: {} ✨",
    "Chapter {}: {} 🌙",
    "The Midnight Flight 🛏️ Chapter {}: {}",
    "Pajama Explorers - Chapter {}: {}",
    "✨ Chapter {}: {}",
]

DESC_HOOKS = [
    "A new dream awaits the Pajama Explorers!",
    "Where will the magic beds fly tonight?",
    "Mia, Leo, and Sam are off on another adventure!",
    "The Pajama Explorers discover a new magical world!",
    "Ember the fox leads the way to somewhere incredible!",
]

def generate_title(chapter: int, story_title: str) -> str:
    name = story_title.split(":", 1)[-1].strip() if ":" in story_title else story_title
    t = random.choice(TITLE_TEMPLATES)
    if t.count("{}") == 2:
        return t.format(chapter, name)
    return t.format(name)


def generate_description(chapter: int, story_title: str, script: str, hashtags: str = "", video_url: str = "") -> str:
    hook = random.choice(DESC_HOOKS)
    return (
        f"{hook}\n\n"
        f"⭐ Chapter {chapter}: {story_title}\n\n"
        f"{script[:200]}...\n\n"
        f"Subscribe for more Pajama Explorer adventures! 🌙\n"
        f"💬 What dream world should they visit next?\n\n"
        f"{hashtags}"
    )


def generate_tags(chapter: int, story_title: str) -> list[str]:
    return [
        "pajama explorers", "kids story", "bedtime story",
        f"chapter {chapter}", story_title,
        "magical adventure", "kids shorts", "imagination",
        "dreams", "fairytale", "childrens story",
    ] + random.sample([
        "fox", "magic bed", "adventure", "kids entertainment", "story for kids",
    ], 3)


def generate_hashtags(count: int = 8) -> str:
    selected = random.sample(HASHTAGS, min(count, len(HASHTAGS)))
    return " ".join(selected)


def get_comment_prompt() -> str:
    prompts = [
        "What dream world should they visit next? 🌙",
        "Which Pajama Explorer is your favorite? 💬",
        "Where would YOUR bed fly? Tell us! ✨",
        "Subscribe for the next adventure! 🔔",
        "Draw the dream world and share it! 🎨",
    ]
    return random.choice(prompts)
