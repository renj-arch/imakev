"""Negative Hooks — shocking, dark, brutal truths that grab attention through negative curiosity gap."""

import random
import bank_manager
from src.high_retention import retention_tts

NEGATIVE_HOOKS = [
    "This will ruin your day:",
    "Here's something dark you need to hear:",
    "This fact will haunt you:",
    "You're not ready for this truth:",
    "The darker side of things you didn't know:",
    "This will change how you see everything — not in a good way:",
    "Warning: this is disturbing:",
    "You can't unlearn this:",
    "The truth nobody wants to admit:",
    "This kept me up at night:",
    "Reality check incoming:",
    "This is what they don't want you to know:",
]

NEGATIVE_POOL = [
    ("Your phone is listening to you", "Advertisers don't need to hear you. They track your location, your typing speed, your scrolling patterns, and who you message. They know you better than your therapist."),
    ("Most of your memories are fake", "Every time you recall a memory, your brain rewrites it. After 10 years, your oldest memories are more fiction than fact. You're nostalgic for things that never happened."),
    ("You'll die without ever knowing your full potential", "Most people use less than 5% of their actual capabilities. The rest is locked behind fear, comfort, and the slow erosion of ambition that happens with age."),
    ("Your friends don't care about you as much as you think", "The average person has 3 close friends. After 30, that number drops to 1. Most people in your phone wouldn't notice if you disappeared for a month."),
    ("The food industry is poisoning you slowly", "Ultra-processed food makes up 60% of the average diet. These foods are engineered to be addictive, not nutritious. The companies know. They don't care."),
    ("You're going to run out of time", "The average human lives about 4,000 weeks. By age 40, you've already used half. Most people spend 90% of that time working, sleeping, or scrolling. What are you doing with yours?"),
    ("Your job will replace you without a second thought", "Companies have no loyalty. They will lay you off the moment the spreadsheet says it's profitable. You are a line item. Nothing more."),
    ("The water you drink contains plastic", "Microplastics have been found in 90% of bottled water and tap water worldwide. You're ingesting about a credit card's worth of plastic every week. The long-term effects are unknown."),
    ("You're being manipulated by algorithms", "Every app you use is designed to keep you hooked. The goal isn't to help you. It's to monetize your attention. You're not the customer. You're the product."),
    ("The happiest moments of your life are already behind you", "Research shows happiness peaks at age 23 for most people. After that, responsibilities, health issues, and the weight of reality slowly drag it down."),
    ("Nobody is coming to save you", "No knight, no lottery win, no lucky break. If your life is going to change, you're the only one who can do it. Waiting is a trap."),
    ("You'll probably die from something preventable", "Heart disease, cancer, diabetes — the top killers are all lifestyle-related. You know what you should be doing. You just won't do it until it's too late."),
    ("Your children will face a harder world", "Climate change, economic instability, AI replacing jobs. The world your kids inherit will be more difficult, more expensive, and more uncertain than the one you grew up in."),
    ("You are not special", "Billions of people have lived and died without leaving a trace. The universe doesn't care about you. You have to create your own meaning."),
    ("Social media is making you miserable", "Every like, comment, and notification triggers a dopamine hit. Then it fades. You're stuck in a loop of craving and disappointment. It's designed that way."),
    ("The news is designed to scare you", "Fear keeps you watching. If it bleeds, it leads. The news doesn't report what's important. It reports what will keep you terrified and tuned in."),
    ("You'll never read all the books you want to", "The average person reads 12 books a year. There are over 130 million books in existence. Even if you read one a week for 50 years, you'll barely scratch the surface."),
    ("Your body is slowly falling apart", "After 25, your collagen production drops 1% every year. Your metabolism slows. Your joints wear down. You're slowly decaying and there's nothing you can do to stop it completely."),
    ("Everything you own will eventually be trash", "Your clothes, your furniture, your phone, your car. In 50 years, almost everything you own will be in a landfill. You spend your life accumulating things that will outlive you as garbage."),
    ("Most people die with regrets", "The top deathbed regrets: working too hard, not spending time with loved ones, not expressing feelings, not pursuing dreams. Most people know this and still do nothing about it."),
    ("You're not as honest as you think", "Studies show the average person lies 1-2 times per day. Most lies are small and social. But the person you lie to most often is yourself."),
    ("Your pet will break your heart", "The average dog lives 10-13 years. The average cat lives 12-18 years. You will almost certainly outlive your pet. You know this when you get them. It doesn't make it easier."),
    ("The people who can help you won't", "When you're struggling, most people will offer thoughts and prayers. Very few will offer real help. Everyone is too busy with their own life to care about yours."),
    ("You're addicted to dopamine and you don't know it", "Your phone, social media, junk food, porn, video games — all engineered to give you cheap dopamine. Your ability to delay gratification is gone. You're an addict in denial."),
    ("The education system failed you", "School taught you to memorize, obey, and pass tests. It didn't teach you about taxes, investing, relationships, mental health, or how to think critically. You were set up for a life of labor, not a life of freedom."),
    ("Success is mostly luck", "Hard work matters. But being born in the right country, to the right family, at the right time, with the right genetics — that's luck. And it matters more than effort."),
    ("You're going to forget most of your life", "By age 60, you'll remember less than 10% of your life in detail. Your child's first steps, your wedding day, your favorite vacation — they'll all fade into vague impressions."),
    ("The people you love will die", "Everyone you love will die. You will watch some of them go. The grief will reshape you. And then you will die too. This is the contract of being alive."),
]

IMAGE_STYLES = [
    "dark cinematic scene, {topic}, moody lighting, deep shadows, 9:16 vertical, unsettling atmosphere, noir style",
    "disturbing surreal photograph, {topic}, dark色调, grainy texture, 9:16 vertical, uncomfortable mood, eerie lighting",
    "dark minimalist scene, {topic}, single harsh light source, deep contrast, 9:16 vertical, bleak atmosphere, cinematic shadow play",
    "gritty urban night photograph, {topic}, neon signs reflecting on wet pavement, 9:16 vertical, cyberpunk noir aesthetic, moody",
    "abandoned dark room, {topic}, dust particles in beam of light, 9:16 vertical, unsettling quiet, horror aesthetic, vignette",
]


def generate_negative_hooks_script() -> dict:
    entry = bank_manager.pick("negative_hooks")
    if entry:
        print(f"  Using banked negative hooks ({bank_manager.count('negative_hooks')} left)")
        return entry

    print("  Bank empty, generating fresh negative truths...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(NEGATIVE_POOL, min(5, len(NEGATIVE_POOL)))
    hook = random.choice(NEGATIVE_HOOKS)
    topics = []
    truths = []
    image_prompts = []
    for title, desc in items:
        topics.append(title)
        truths.append(desc)
        kw = title.lower().replace(" ", "_")[:50]
        style = random.choice(IMAGE_STYLES)
        image_prompts.append(style.format(topic=kw))
    tts_lines = [f"{t}. {d}" for t, d in items]
    items_data = [{"title": t, "description": d} for t, d in items]
    return {
        "title": f"Dark Truth: {items[0][0][:50]}",
        "hook": hook,
        "topics": topics,
        "truths": truths,
        "image_prompts": image_prompts,
        "script": retention_tts(items_data, "negative_hooks", hook),
        "tts_script": retention_tts(items_data, "negative_hooks", hook),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 5 dark, shocking truths or uncomfortable realities. "
            "Each should be a brutal fact about life, society, human nature, or the future. "
            "The tone: unsettling but factual. Make people think. "
            "Format exactly:\n"
            "TRUTH: [short shocking headline, 3-8 words]\n"
            "EXPLANATION: [one punchy sentence explaining why it's dark or unsettling]\n\n"
            "Make each one feel like a cold dose of reality."
        )
        system = "You write dark, uncomfortable truths about life, society, human nature, and reality. Be brutally honest. Make people think."
        raw = _generate(prompt, temperature=0.9, max_tokens=600, system=system)
        if not raw:
            return None
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
        if topics and len(topics) >= 3:
            hook = random.choice(NEGATIVE_HOOKS)
            image_prompts = []
            for t in topics:
                kw = t.lower().replace(" ", "_")[:50]
                image_prompts.append(random.choice(IMAGE_STYLES).format(topic=kw))
            items_data = [{"title": t, "description": d} for t, d in zip(topics, truths)]
            return {
                "title": f"Dark Truth: {topics[0][:50]}",
                "hook": hook,
                "topics": topics,
                "truths": truths,
                "image_prompts": image_prompts,
                "script": retention_tts(items_data, "negative_hooks", hook),
                "tts_script": retention_tts(items_data, "negative_hooks", hook),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
