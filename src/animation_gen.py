"""AI Animation generator — takes a user prompt, generates narration + frame prompts."""

import sys, random
from src.script_generator import _generate

FRAME_TEMPLATES = [
    "{subject}, {style}, wide shot, dynamic angle, cinematic lighting",
    "{subject}, {style}, close-up view, detailed, dramatic shadows",
    "{subject}, {style}, side angle, motion blur, action pose",
    "{subject}, {style}, overhead view, scenic background, vibrant",
    "{subject}, {style}, low angle, heroic perspective, epic mood",
    "{subject}, {style}, macro detail, textures, soft focus background",
    "{subject}, {style}, night scene, glowing atmosphere, magical",
    "{subject}, {style}, golden hour lighting, warm tones, peaceful",
    "{subject}, {style}, extreme close-up, intense detail, sharp",
    "{subject}, {style}, bird's eye view, landscape setting, expansive",
]

NARRATION_FALLBACKS = [
    "Watch in awe as nature reveals its most incredible creation. Every detail tells a story of beauty and wonder.",
    "This is absolutely mesmerizing. The way light dances across the scene creates a truly magical atmosphere.",
    "Prepare to be amazed by this stunning display. Every moment is more breathtaking than the last.",
    "Nature at its finest. The beauty you're about to witness is truly one of a kind and unforgettable.",
    "Get ready for an incredible sight. This is something you have to see to believe — absolutely stunning.",
]

STYLE_FALLBACKS = [
    "digital art, vibrant colors, cinematic lighting",
    "oil painting, rich textures, warm tones",
    "watercolor, soft pastels, dreamy atmosphere",
    "cinematic, photorealistic, dramatic lighting",
    "fantasy art, glowing effects, magical mood",
]


def _try_generate(prompt, temperature=0.8, max_tokens=200, system=""):
    try:
        return _generate(prompt, temperature=temperature, max_tokens=max_tokens, system=system)
    except Exception as e:
        print(f"  LLM unavailable ({e}), using fallback")
        return ""


def generate_animation_script(user_prompt: str, num_frames: int = 6) -> dict:
    print(f"  Generating animation script for: {user_prompt}")

    raw = _try_generate(
        f"Write a short, engaging 20-25 second narration script about: {user_prompt}. "
        "The script should describe what's happening in the scene in a fun, vivid way. "
        "Make it feel like a nature documentary narrator. 30-50 words max. "
        "Return ONLY the script text.",
        temperature=0.8, max_tokens=200,
        system="You write short, vivid documentary-style narration scripts.",
    )
    narration = raw.strip() if raw else random.choice(NARRATION_FALLBACKS)

    style = _try_generate(
        f"Describe an art style for a beautiful AI animation of: {user_prompt}. "
        "Examples: 'digital art, vibrant colors, pixar style', 'oil painting, rich textures, classic art', "
        "'cyberpunk neon, futuristic, glowing', 'watercolor, soft pastels, dreamy', 'cinematic, photorealistic, dramatic lighting'. "
        "Return ONLY the style description, 3-6 words.",
        temperature=0.7, max_tokens=50,
        system="You suggest visual art styles for AI image generation.",
    )
    if not style:
        style = random.choice(STYLE_FALLBACKS)
    style = style.strip().strip('"').strip("'")

    frame_prompts = []
    templates = random.sample(FRAME_TEMPLATES, min(num_frames, len(FRAME_TEMPLATES)))
    for i, tmpl in enumerate(templates):
        frame_prompts.append(tmpl.format(subject=user_prompt, style=style))

    title_parts = user_prompt.split()
    title = " ".join(title_parts[:8]).title()

    return {
        "title": title,
        "subject": user_prompt,
        "style": style,
        "narration": narration,
        "frame_prompts": frame_prompts,
        "tts_script": narration,
    }


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "a duck swimming in a pond"
    result = generate_animation_script(prompt)
    print(f"\nTitle: {result['title']}")
    print(f"Style: {result['style']}")
    print(f"Narration: {result['narration']}")
    print(f"Frames: {len(result['frame_prompts'])}")
    for i, fp in enumerate(result['frame_prompts']):
        print(f"  {i+1}. {fp}")
