"""Viral SEO: titles, descriptions, tags, hashtags optimized for YouTube Shorts."""

import random

TRENDING_HASHTAGS = [
    "#shorts", "#viralshorts", "#trending", "#fyp", "#foryou",
    "#aifilm", "#aicinema", "#cinematic", "#neon", "#cyberpunk",
    "#cat", "#cats", "#rescue", "#storytime", "#animation",
    "#dreamcore", "#surreal", "#nightcity", "#aiart", "#midjourney",
]

HOOK_PHRASES = [
    "You won't believe what happens next",
    "This AI film will blow your mind",
    "Wait for the ending",
    "The most insane AI video you'll see today",
    "What happens in this neon city will shock you",
    "This is what AI dreams look like",
    "Subscribe for more cinematic stories",
    "Comment your favorite scene",
    "Like if you love AI cinema",
    "Share with someone who needs to see this",
]

def generate_title(chapter: int, story_title: str) -> str:
    templates = [
        f"Chapter {chapter}: {story_title} 🔥 | AI Cinematic Short Film",
        f"{story_title} - Chapter {chapter} (AI Cinematic) 🎬",
        f"AI Generated: {story_title} | Chapter {chapter} {random.choice(TRENDING_HASHTAGS)}",
        f"Mind-Blowing AI Film - Chapter {chapter}: {story_title}",
        f"Chapter {chapter}: {story_title} - An AI Story {random.choice(['🌆', '🔥', '⚡', '🎥'])}",
    ]
    return random.choice(templates)


def generate_description(chapter: int, story_title: str, script: str, video_url: str = "") -> str:
    hook = random.choice(HOOK_PHRASES)
    tags_list = " ".join(random.sample(TRENDING_HASHTAGS, min(8, len(TRENDING_HASHTAGS))))

    return (
        f"{hook}! 🚀\n\n"
        f"Chapter {chapter}: {story_title}\n\n"
        f"{script[:200]}...\n\n"
        f"🤖 Created with AI (Pollinations.ai + edge-tts + Python)\n"
        f"📺 Subscribe for daily chapters: https://youtube.com/@yourchannel\n\n"
        f"💬 Comment: What should happen in Chapter {chapter + 1}?\n"
        f"🔔 Turn on notifications for the next episode!\n\n"
        f"{tags_list}\n\n"
        f"#aicinema #shortfilm #aigenerated #neoncity #chapter{chapter}"
    )


def generate_tags(chapter: int, story_title: str) -> list[str]:
    base = [
        "ai film", "cinematic", "short film", "ai generated", "neon city",
        f"chapter {chapter}", story_title, "ai movie", "cinematic short",
        "viral video", "shorts", "ai animation", "cyberpunk", "dreamcore",
        "youtube shorts", "aifilm", "storytime", "aicinema",
    ]
    extra = random.sample([
        "cat story", "rescue mission", "ai art", "night city",
        "fyp", "foryoupage", "trending", "viralshorts",
    ], 5)
    return base + extra


def generate_hashtags(count: int = 12) -> str:
    selected = random.sample(TRENDING_HASHTAGS, min(count, len(TRENDING_HASHTAGS)))
    return " ".join(selected)


def get_comment_prompt() -> str:
    prompts = [
        "What should happen next? 👇",
        "Which scene was your favorite? 💬",
        "Rate this video 1-10 in the comments! ⭐",
        "Subscribe for Chapter X tomorrow! 🔔",
        "Share this with a friend who loves AI 🤖",
        "Comment your theory about the cat villain! 🐱",
    ]
    return random.choice(prompts)
