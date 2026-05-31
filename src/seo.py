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

def generate_hashtags(count: int = 12) -> str:
    selected = random.sample(TRENDING_HASHTAGS, min(count, len(TRENDING_HASHTAGS)))
    return " ".join(selected)


def get_comment_prompt() -> str:
    prompts = [
        "What should happen next? 👇",
        "Which scene was your favorite? 💬",
        "Rate this video 1-10 in the comments! ⭐",
        "Subscribe for Chapter X tomorrow! 🔔",
        "Share this with a friend! 🤖",
        "Comment your theory about the cat villain! 🐱",
    ]
    return random.choice(prompts)
