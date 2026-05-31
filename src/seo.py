"""Viral SEO: titles, descriptions, tags — optimized for YouTube Shorts, no AI mentions."""

import random

TRENDING_HASHTAGS = [
    "#shorts", "#viralshorts", "#trending", "#fyp", "#foryou",
    "#cinematic", "#cyberpunk", "#neon",
    "#cat", "#cats", "#storytime", "#animation",
    "#dreamcore", "#surreal", "#nightcity",
    "#shortfilm", "#cinematography", "#viralvideo", "#fypシ",
    "#scifi", "#dystopian", "#megacity", "#rain",
]

HOOK_PHRASES = [
    "You won't believe what happens next",
    "Wait for the ending",
    "This will blow your mind",
    "Subscribe for more stories",
    "Comment your favorite scene",
    "Like if you love cinematic stories",
    "Share with someone who needs to see this",
]

def generate_title(chapter: int, story_title: str) -> str:
    templates = [
        f"Chapter {chapter}: {story_title} 🔥",
        f"{story_title} - Chapter {chapter} 🎬",
        f"TO BE CONTINUED... Chapter {chapter}: {story_title}",
        f"Chapter {chapter}: {story_title} 🌆",
        f"THE STORY CONTINUES - Chapter {chapter}: {story_title}",
        f"⚠️ Chapter {chapter}: {story_title} (Watch Till End)",
    ]
    return random.choice(templates)


def generate_description(chapter: int, story_title: str, script: str, hashtags: str = "", video_url: str = "") -> str:
    hook = random.choice(HOOK_PHRASES)
    return (
        f"{hook}! 🚀\n\n"
        f"Chapter {chapter}: {story_title}\n\n"
        f"{script[:200]}...\n\n"
        f"📺 Subscribe for Chapter {chapter + 1}!\n"
        f"🔔 Turn on notifications!\n\n"
        f"💬 What happens in Chapter {chapter + 1}?\n"
        f"👍 Like if you re-watched (be honest 👀)\n"
        f"🔁 Share with someone who loves cinematic stories\n\n"
        f"{hashtags}"
    )


def generate_tags(chapter: int, story_title: str) -> list[str]:
    return [
        "cinematic", "short film", "neon city",
        f"chapter {chapter}", story_title, "cinematic short",
        "viral video", "shorts", "cyberpunk", "dreamcore",
        "youtube shorts", "storytime", "shorts video",
    ] + random.sample([
        "cat story", "night city", "fyp", "foryoupage", "trending",
    ], 3)


def generate_hashtags(count: int = 12) -> str:
    selected = random.sample(TRENDING_HASHTAGS, min(count, len(TRENDING_HASHTAGS)))
    return " ".join(selected)


def get_comment_prompt() -> str:
    prompts = [
        "What should happen next? 👇",
        "Which scene was your favorite? 💬",
        "Rate this video 1-10 in the comments! ⭐",
        "Subscribe for Chapter X tomorrow! 🔔",
        "Share this with a friend!",
        "Comment your theory about the cat villain! 🐱",
    ]
    return random.choice(prompts)
