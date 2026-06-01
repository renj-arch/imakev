"""Things They Don't Teach You — adult truths about money, dating, career, health, life."""

import random
import bank_manager

HOOKS = [
    "Nobody teaches you this in school:",
    "They don't want you to know this:",
    "Here's what they don't teach you:",
    "School never told you this:",
    "The one thing nobody teaches you:",
    "This is kept from you for a reason:",
    "What they don't teach you about life:",
]

FALLBACKS = [
    ("Negotiate salary or get scammed", "Your first employer will pay you the minimum they think you'll accept. The only raise that matters is the one you negotiate before you accept the offer."),
    ("Credit cards are designed to trap you", "Banks want you to carry a balance. That's how they make money. Pay in full every month or you're paying 25% interest on things you already bought."),
    ("Your degree doesn't matter", "Nobody cares about your GPA after your first job. Skills and network matter more than any piece of paper."),
    ("Taxes are optional if you're rich", "The wealthy don't pay income tax. They borrow against assets and the loan isn't taxable. You pay more because you work for a paycheck."),
    ("Your boss is not your friend", "Companies will replace you the moment you stop being useful. Loyalty to a corporation is a one-way street. Look out for yourself first."),
    ("Marriage is a financial contract", "People call it romance but the legal system treats it as a merger of assets. Know the financial implications before you sign."),
    ("Rent is throwing money away slowly", "Your landlord is building equity with your payment every month. The system is designed to keep you renting while they own."),
    ("The health industry profits from sick people", "There's no money in curing you. The money is in managing symptoms with prescriptions you take forever. Follow the profit."),
    ("Inflation is a hidden tax on the poor", "The government prints money and your savings lose value. The rich own assets that go up. You hold cash that goes down. Every time."),
    ("Nobody is coming to save you", "No government program, no inheritance, no lucky break. The only person who can fix your life is you. Stop waiting and start moving."),
    ("College is an expensive filter", "The content is free online. You pay for the piece of paper that signals to employers you can finish something. That's it."),
    ("Your network is your net worth", "The most successful people aren't the smartest. They know the right people. Your social skills determine your income more than your IQ."),
    ("Comparison is the thief of joy", "Social media shows you everyone's highlight reel while you compare it to your behind-the-scenes. Quit scrolling and focus on your own path."),
    ("The middle class is disappearing", "The gap between rich and poor is widening. If you're not actively building wealth, you're falling behind. Savings accounts don't cut it."),
    ("Jobs are not secure anymore", "The concept of a 40-year career at one company is dead. You are a freelancer with a single client. Always have an exit plan."),
    ("Your habits determine your future", "Small daily actions compound into massive results over time. The person you are tomorrow is built by what you do today."),
    ("Fear keeps you poor and small", "Every decision made from fear keeps you stuck. The biggest risks pay the biggest rewards. Calculated risk is the only way forward."),
    ("Time is your only non-renewable resource", "You can make more money. You can't make more time. Stop trading your time for money and start building assets that work while you sleep."),
    ("Dopamine is controlling your life", "Social media, porn, junk food, video games. Your brain is being hijacked by cheap dopamine. The ability to delay gratification is the single biggest predictor of success."),
    ("Most people are sleepwalking through life", "Wake up, work, consume, sleep, repeat. Break the cycle. The system is designed to keep you comfortable and compliant."),
]

IMAGE_STYLES = [
    "dark cinematic street photography, abandoned classroom, moody lighting, {topic}, 9:16 vertical, urban decay aesthetic",
    "cinematic neon noir, dark alley with glowing signs, {topic}, mysterious atmosphere, 9:16 vertical, rainy cyberpunk vibe",
    "dramatic minimalist scene, {topic}, single light source, deep shadows, 9:16 vertical, fine art photography style",
    "dark academia aesthetic, {topic}, vintage library, candlelight, moody atmosphere, 9:16 vertical, intellectual vibe",
    "cinematic dark office, {topic}, corporate atmosphere, dramatic shadows, 9:16 vertical, noir style",
]


def generate_things_script() -> dict:
    entry = bank_manager.pick("things_they_dont_teach")
    if entry:
        return entry

    print("  Generating fresh truths...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(5, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = []
    keywords_list = []
    for t, e in items:
        kw = t.lower().replace(" ", "_")[:50]
        keywords_list.append(kw)
        style = random.choice(IMAGE_STYLES)
        image_prompts.append(style.format(topic=kw))
    tts_lines = [f"{t}. {e}" for t, e in items]
    return {
        "title": f"Things They Don't Teach You: {items[0][0][:50]}",
        "hook": hook,
        "topics": [t for t, _ in items],
        "truths": [e for _, e in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": f"{hook} {' '.join(tts_lines)}",
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 5 hard truths about life that schools don't teach. "
            "Topics: money, relationships, career, health, society, psychology. "
            "Each must be a controversial but factual adult truth. Sharp and memorable. "
            "Format exactly:\n"
            "TRUTH: [The headline, 4-8 words]\n"
            "EXPLANATION: [One punchy sentence, 12-18 words]\n\n"
            "Make each one feel like a secret that most people never figure out."
        )
        system = "You write uncomfortable truths about life, money, relationships, and society. Be sharp, factual, and memorable. Suitable for mature audiences."
        raw = _generate(prompt, temperature=0.9, max_tokens=800, system=system)
        if not raw:
            return None
        topics = []
        truths = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TRUTH:"):
                if current.get("topic") and current.get("truth"):
                    topics.append(current["topic"])
                    truths.append(current["truth"])
                current = {"topic": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["truth"] = line.split(":", 1)[-1].strip()
        if current.get("topic") and current.get("truth"):
            topics.append(current["topic"])
            truths.append(current["truth"])
        if topics and len(topics) >= 4:
            hook = random.choice(HOOKS)
            image_prompts = []
            for t in topics:
                kw = t.lower().replace(" ", "_")[:50]
                image_prompts.append(random.choice(IMAGE_STYLES).format(topic=kw))
            tts_lines = [f"{t}. {e}" for t, e in zip(topics, truths)]
            return {
                "title": f"Things They Don't Teach You: {topics[0][:50]}",
                "hook": hook,
                "topics": topics,
                "truths": truths,
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": f"{hook} {' '.join(tts_lines)}",
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
