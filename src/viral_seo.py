"""Algorithm-cracking SEO engine — curiosity gap titles, viral descriptions, smart tags."""

import random

CHANNEL_NAME = "Dingdong"
CHANNEL_HANDLE = "@dingdong"

# Curiosity gap title templates proven to boost CTR 2-5x
TITLE_TEMPLATES = {
    "negative_hooks": [
        "{hook} {topic}",
        "This {topic} Will Ruin Your Day",
        "The Dark Truth About {topic} Nobody Tells You",
        "Why {topic} Is Worse Than You Think",
        "This {topic} Fact Will Haunt You",
        "The Dark Side Of {topic} Revealed",
        "{topic} — The Truth They Hide",
        "What They Don't Tell You About {topic}",
        "This {topic} Reality Check Hits Hard",
    ],
    "satisfying": [
        "Oddly Satisfying: {topic} 🎯",
        "This {topic} Is So Satisfying To Watch",
        "The Most Satisfying {topic} You'll See Today",
        "Watch This {topic} If You Need To Relax 🧘",
        "Oddly Satisfying {topic} — Pure ASMR Vibes",
        "This {topic} Will Satisfy Your Brain 🧠",
        "Can't Stop Watching This {topic}",
        "DIY {topic} — You Need To Try This",
        "Satisfying {topic} That Feels Illegal To Watch",
    ],
    "challenges": [
        "Can You Complete This {topic} Challenge? ⚡",
        "99% Fail This {topic} Challenge. Can You Beat It?",
        "This {topic} Challenge Looks Easy. It's Not.",
        "Try Not To Fail This {topic} Challenge 🏆",
        "The {topic} Challenge That Breaks Everyone",
        "{hook} {topic} Challenge — Are You Game?",
        "This {topic} Stunt Will Blow Your Mind 🤯",
        "Only 1% Can Win This {topic} Challenge",
    ],
    "things_they_dont_teach": [
        "{hook} {topic} Truth #shorts",
        "This {topic} Truth Will Change How You See Everything",
        "Nobody Teaches You This About {topic}",
        "The {topic} Truth They Hide From You",
        "Why Nobody Tells You This About {topic}",
        "The Harsh Truth About {topic} Nobody Talks About",
        "This {topic} Fact Will Open Your Eyes",
        "{hook} {topic} — Watch Till The End",
    ],
    "facts": [
        "This {topic} Fact Will Ruin Your Day 😱",
        "Why {topic} Scientists Are Hiding This From You",
        "The {topic} Fact That 99% Of People Get Wrong",
        "This {topic} Discovery Changes Everything We Know",
        "I Can't Believe This {topic} Fact Is Real",
        "What They Don't Tell You About {topic}",
        "The {topic} Secret They Don't Want You To Know",
        "This {topic} Fact Just Broke My Brain 🧠",
        "How Is This {topic} Fact Even Possible?",
        "Stop Believing These {topic} Lies ❌",
    ],
    "what_if": [
        "What If {scenario}? (You Won't Believe What Happens)",
        "If {scenario}, Here's What Would Actually Happen",
        "What If {scenario}? The Answer Changes Everything",
        "Imagine If {scenario} 🫢 Mind-Blowing",
        "What If {scenario}? Science Says This Would Happen",
    ],
    "how_it_works": [
        "How {topic} Actually Works (It's Not What You Think)",
        "The Real Way {topic} Works Explained In 30 Seconds",
        "How {topic} Works — No One Explains It Like This",
        "This Is How {topic} Actually Works 🤯",
        "The Secret Behind How {topic} Works Revealed",
    ],
    "riddles": [
        "Only 1% Can Solve This Riddle 🤔 Can You?",
        "This Riddle Is Impossible — Try Not To Fail",
        "If You Solve This Riddle You're A Genius",
        "99% Of People Fail This Riddle. Try Your Luck",
        "This Riddle Has A Twist Nobody Sees Coming",
        "Can You Beat This Riddle? (99% Fail Rate)",
    ],
    "would_you_rather": [
        "Would You Rather {a} Or {b}? Comment Below 👇",
        "Your Answer Says Everything About You 🫢",
        "Choose Wisely: {a} vs {b} 👀",
        "This Choice Is Impossible — {a} Or {b}?",
        "The Way You Answer Reveals Your Personality",
    ],
    "psychology": [
        "Your Brain Is Lying To You About {hack}",
        "The {hack} Psychology Trick They Use On You",
        "Why Your Brain Does {hack} (Psychologists Explain)",
        "This {hack} Hack Changes How You See Everything",
        "Psychology Says You Do {hack} Without Realizing",
    ],
    "life_hacks": [
        "This {hack} Hack Will Save You Hours ⏰",
        "You've Been Doing {hack} Wrong Your Whole Life",
        "This {hack} Trick Is Genius — Why Didn't I Know This?",
        "The {hack} Hack That Changes Everything 🔥",
        "Stop Doing {hack} The Hard Way. Try This Instead",
    ],
    "history_minute": [
        "They Didn't Teach You This In History Class 📚",
        "This Historical Event Changes How You See {topic}",
        "The {topic} Story They Don't Want In Textbooks",
        "History Fact: {topic} — Most People Don't Know",
        "This Day In History Changed Everything Forever",
    ],
    "urban_legends": [
        "You've Been Told {legend} Is Real. It's Not.",
        "The Truth About {legend} Will Shock You",
        "Everyone Believes {legend}. Here's The Real Story",
        "Why {legend} Is Actually FAKE (Debunked)",
        "The {legend} Myth vs Reality — It's Not Close",
    ],
    "coincidences": [
        "The Craziest Coincidence You'll Hear Today 🫢",
        "This Coincidence Sounds Fake But It's 100% Real",
        "What Are The Odds? This {topic} Coincidence Is Insane",
        "You Won't Believe This {topic} Coincidence Actually Happened",
    ],
    "unsolved_mysteries": [
        "This {topic} Mystery Has NO Explanation 🔍",
        "Decades Later, {topic} Still Remains Unsolved",
        "The {topic} Case That Baffles Investigators To This Day",
        "This {topic} Disappearance Has No Answers",
    ],
    "movie_trivia": [
        "This {movie} Secret Was Hidden For Years 🎬",
        "What They Hid From You About {movie}",
        "The {movie} Scene That Almost Didn't Make The Cut",
        "This {movie} Fact Changes How You See The Film",
    ],
    "animal_kingdom": [
        "This {animal} Fact Will Make You Reconsider Everything",
        "The {animal} Truth Nobody Talks About 🐾",
        "Why {animal} Is More Incredible Than You Think",
        "This {animal} Fact Is Scientifically Impossible",
    ],
    "space_wonders": [
        "NASA Doesn't Want You To Know This About {topic}",
        "This {topic} Fact Breaks The Laws Of Physics 🌌",
        "What They're Not Telling You About {topic}",
        "The {topic} Discovery That Changes Astronomy Forever",
    ],
    "box_office": [
        "This {movie} Made HOW Much Money? 💰",
        "The {movie} Box Office Numbers Are Insane",
        "How {movie} Broke Every Box Office Record",
        "This {movie} Profit Margin Is Unbelievable",
    ],
    "story": [
        "{title} — You Won't Believe What Happens Next",
        "Chapter {chapter}: {title} (Mind-Blowing Ending)",
        "This {title} Story Changes Everything 🔥",
        "The {title} Secret Nobody Talks About",
        "{title} — Watch Till The End ⚠️",
    ],
}

DESCRIPTION_TEMPLATES = {
    "negative_hooks": [
        "{hook}\n\nDark truths you weren't ready for. Which one hit you the hardest?",
        "{hook}\n\nThese uncomfortable truths will change how you see everything. Comment your thoughts below.",
    ],
    "satisfying": [
        "{hook}\n\nSit back, relax, and enjoy these oddly satisfying visuals. Which one was your favorite?",
        "{hook}\n\nDIY projects, satisfying restorations, and oddly calming visuals. Comment your favorite!",
    ],
    "challenges": [
        "{hook}\n\nThink you can handle these challenges? Try them yourself and comment how far you got!",
        "{hook}\n\nWatch till the end — these challenges are harder than they look. Let us know your score in the comments!",
    ],
    "things_they_dont_teach": [
        "{hook}\n\nWatch till the end — these hard truths will change how you see everything.\n\nComment which one hit you hardest! 👇",
        "{hook}\n\nHere are some hard truths they don't teach you in school. Let us know your thoughts in the comments!",
    ],
    "facts": [
        "This {topic} fact will change how you see everything. Watch till the end — it gets wild.\n\n{hashtags}",
        "Most people don't know this about {topic}. Here's the truth they're hiding.\n\nComment what you think! 👇\n\n{hashtags}",
    ],
    "what_if": [
        "What if {scenario}? The answer might surprise you. Let us know what you'd do in the comments!\n\n{hashtags}",
    ],
    "riddles": [
        "Think you're smart? Try solving this riddle. 99% of people get it wrong.\n\nDrop your answer in the comments! ⬇️\n\n{hashtags}",
    ],
    "would_you_rather": [
        "Would you rather {a} or {b}? Your choice says more about you than you think.\n\nComment which one! 👇\n\n{hashtags}",
    ],
    "story": [
        "Chapter {chapter}: {title}\n\nWatch this cinematic story — the ending will surprise you.\n\nComment what you think! 👇\n\n{hashtags}",
    ],
}

ENGAGEMENT_TEMPLATES = [
    "Comment what you think! 👇",
    "Which side are you on? Drop your answer! ⬇️",
    "I read every comment — tell me your thoughts! 💬",
    "Share this with someone who needs to see it 🔄",
    "Save this for later 📌",
    "Follow for more mind-blowing content! 🔔",
]


def generate_viral_title(mode: str, data: dict) -> str:
    templates = TITLE_TEMPLATES.get(mode, ["{hook} {topic} #shorts"])
    template = random.choice(templates)

    topic_map = {
        "facts": lambda d: d.get("niche", "mind-blowing"),
        "what_if": lambda d: d.get("scenarios", ["it"])[0] if d.get("scenarios") else "it",
        "how_it_works": lambda d: d.get("topics", ["it"])[0] if d.get("topics") else "it",
        "psychology": lambda d: d.get("hacks", ["it"])[0] if d.get("hacks") else "your brain",
        "life_hacks": lambda d: d.get("hacks", ["it"])[0] if d.get("hacks") else "this",
        "history_minute": lambda d: d.get("niche", "history"),
        "urban_legends": lambda d: d.get("legend", "this story"),
        "coincidences": lambda d: d.get("coincidences", ["this"])[0] if d.get("coincidences") else "this",
        "unsolved_mysteries": lambda d: d.get("mysteries", ["this"])[0] if d.get("mysteries") else "this",
        "movie_trivia": lambda d: d.get("trivia_titles", ["this movie"])[0] if d.get("trivia_titles") else "this movie",
        "animal_kingdom": lambda d: d.get("animal_facts", ["this animal"])[0] if d.get("animal_facts") else "this animal",
        "space_wonders": lambda d: d.get("space_facts", ["this"])[0] if d.get("space_facts") else "space",
        "box_office": lambda d: d.get("box_office_titles", ["this movie"])[0] if d.get("box_office_titles") else "this movie",
        "story": lambda d: d.get("title", "this story"),
        "things_they_dont_teach": lambda d: d.get("topics", ["hard truth"])[0] if d.get("topics") else "hard truth",
        "challenges": lambda d: d.get("challenges", [{"title": "this"}])[0]["title"] if d.get("challenges") else "this",
        "satisfying": lambda d: d.get("topics", ["this"])[0] if d.get("topics") else "this",
        "negative_hooks": lambda d: d.get("topics", ["truth"])[0] if d.get("topics") else "truth",
    }

    get_topic = topic_map.get(mode, lambda d: "")
    topic = get_topic(data)
    template = template.replace("{hook}", data.get("hook", ""))
    template = template.replace("{topic}", topic)
    template = template.replace("{scenario}", data.get("scenarios", ["it"])[0] if data.get("scenarios") else "it")
    template = template.replace("{hack}", data.get("hacks", ["it"])[0] if data.get("hacks") else "this")
    template = template.replace("{legend}", data.get("legend", "this story"))
    template = template.replace("{movie}", data.get("trivia_titles", ["this movie"])[0] if data.get("trivia_titles") else "this movie")
    template = template.replace("{animal}", data.get("animal_facts", ["this animal"])[0] if data.get("animal_facts") else "this animal")
    template = template.replace("{a}", data.get("option_a", "Option A"))
    template = template.replace("{b}", data.get("option_b", "Option B"))
    template = template.replace("{chapter}", str(data.get("chapter", "1")))
    template = template.replace("{title}", data.get("title", "this story"))

    if len(template) > 90:
        template = template[:87] + "..."

    return template


def generate_viral_description(mode: str, data: dict, script: str = "") -> str:
    desc_templates = DESCRIPTION_TEMPLATES.get(mode, [
        "{hook}\n\nWatch till the end — you won't believe what happens.\n\nComment what you think! 👇\n\n{hashtags}"
    ])
    template = random.choice(desc_templates)
    template = template.replace("{topic}", data.get("niche", "this"))
    template = template.replace("{scenario}", data.get("scenarios", ["it"])[0] if data.get("scenarios") else "it")
    template = template.replace("{a}", data.get("option_a", ""))
    template = template.replace("{b}", data.get("option_b", ""))
    template = template.replace("{hook}", data.get("hook", ""))
    template = template.replace("{chapter}", str(data.get("chapter", "1")))
    template = template.replace("{title}", data.get("title", "this story"))

    # Add script preview
    if script:
        preview = script[:150].strip()
        if len(preview) >= 150:
            preview += "..."
        template += f"\n\n{preview}"

    # Add engagement prompt
    template += f"\n\n{random.choice(ENGAGEMENT_TEMPLATES)}"

    # Link to channel
    template += f"\n\n🔗 {CHANNEL_HANDLE}"

    engagement_prompt = random.choice([
        "What do you think? I read every comment! 💬",
        "Drop a 🔥 if you learned something new!",
        "Save this for later and share with a friend! 📌",
        "Follow for daily content like this! 🚀",
        "Comment your thoughts below! 👇",
    ])
    template += f"\n\n{engagement_prompt}"

    return template


def generate_viral_tags(mode: str, data: dict) -> list[str]:
    base_tags = {
        "facts": ["shorts", "facts", "mindblowing", "didyouknow", "interestingfacts", "trivia", "education", "learning", "funfacts", "factshorts", "amazingfacts", "youtubeshorts"],
        "what_if": ["shorts", "whatif", "imagination", "curiosity", "kids", "fun", "creative", "wonder", "whatifscenarios", "youtubeshorts"],
        "how_it_works": ["shorts", "howitworks", "science", "engineering", "education", "explained", "howthingswork", "diy", "learning", "youtubeshorts"],
        "riddles": ["shorts", "riddle", "brainteaser", "puzzle", "challenge", "iqtest", "riddles", "brain", "think", "youtubeshorts"],
        "would_you_rather": ["shorts", "wouldyourather", "choose", "fun", "challenge", "decision", "poll", "funny", "youtubeshorts"],
        "psychology": ["shorts", "psychology", "brainhacks", "mindtricks", "psychologyfacts", "humanbehavior", "mentalhealth", "selfimprovement", "youtubeshorts"],
        "life_hacks": ["shorts", "lifehacks", "hacks", "tips", "diy", "clever", "savetime", "lifehack", "usefultips", "youtubeshorts"],
        "history_minute": ["shorts", "history", "historyfacts", "didyouknow", "historical", "education", "learning", "oneminutehistory", "youtubeshorts"],
        "urban_legends": ["shorts", "urbanlegends", "creepy", "myths", "debunked", "truth", "scary", "legends", "youtubeshorts"],
        "coincidences": ["shorts", "coincidences", "truestories", "amazing", "unbelievable", "facts", "mindblown", "youtubeshorts"],
        "unsolved_mysteries": ["shorts", "unsolvedmysteries", "mystery", "truecrime", "coldcase", "creepy", "unsolved", "mysterious", "youtubeshorts"],
        "movie_trivia": ["shorts", "movietrivia", "behindthescenes", "hollywood", "moviefacts", "cinema", "filmmaking", "youtubeshorts"],
        "animal_kingdom": ["shorts", "animals", "animalfacts", "nature", "wildlife", "amazinganimals", "didyouknow", "naturelovers", "youtubeshorts"],
        "space_wonders": ["shorts", "space", "astronomy", "nasa", "universe", "spacefacts", "science", "cosmos", "galaxy", "youtubeshorts"],
        "box_office": ["shorts", "boxoffice", "movies", "hollywood", "moviefacts", "earnings", "filmmaking", "movierecords", "youtubeshorts"],
        "story": ["shorts", "story", "cinematic", "animation", "ai", "chapter", "series", "episode", "storytime", "youtubeshorts"],
        "things_they_dont_teach": ["shorts", "hardtruths", "lifelessons", "wisdom", "realitycheck", "adulting", "lifetips", "truth", "mindset", "youtubeshorts"],
        "challenges": ["shorts", "challenge", "stunts", "dare", "fail", "try", "competition", "funny", "youtubeshorts", "viral"],
        "satisfying": ["shorts", "satisfying", "oddlysatisfying", "diy", "restoration", "cleaning", "asmr", "relaxing", "satisfyingvideo", "youtubeshorts"],
        "negative_hooks": ["shorts", "darktruths", "realitycheck", "uncomfortabletruths", "psychology", "mindblown", "truth", "deeptheory", "youtubeshorts"],
    }

    tags = base_tags.get(mode, ["shorts", "youtubeshorts", mode])[:]

    # Add topic-specific tags from data
    if "niche" in data and data["niche"]:
        tags.append(data["niche"].lower().replace(" ", ""))
    if mode == "facts" and "facts" in data:
        for f in data["facts"][:1]:
            words = f.split()[:3]
            tags.append("".join(words).lower()[:30])
    if mode == "riddles":
        tags.append("solvetheriddle")
        tags.append("riddleanswer")
    if mode == "would_you_rather":
        tags.append("chooseyourpath")

    # Deduplicate and limit to 30 (YouTube max is 500 chars total)
    seen = set()
    unique_tags = []
    for tag in tags:
        t = tag.lower().strip()
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)

    return unique_tags[:30]


def generate_viral_hashtags(mode: str, count: int = 6) -> str:
    mode_hashtags = {
        "facts": ["#facts", "#shorts", "#didyouknow", "#mindblown", "#trivia", "#learning"],
        "what_if": ["#whatif", "#shorts", "#imagination", "#curiosity", "#wonder", "#fun"],
        "how_it_works": ["#howitworks", "#shorts", "#science", "#explained", "#engineering", "#diy"],
        "riddles": ["#riddle", "#shorts", "#brainteaser", "#puzzle", "#challenge", "#think"],
        "would_you_rather": ["#wouldyourather", "#shorts", "#choose", "#fun", "#challenge", "#poll"],
        "psychology": ["#psychology", "#shorts", "#brainhacks", "#mindtricks", "#psychologyfacts", "#mindblown"],
        "life_hacks": ["#lifehacks", "#shorts", "#hacks", "#tips", "#diy", "#clever"],
        "history_minute": ["#history", "#shorts", "#historyfacts", "#didyouknow", "#learning", "#oneminutehistory"],
        "urban_legends": ["#urbanlegends", "#shorts", "#myths", "#debunked", "#truth", "#creepy"],
        "coincidences": ["#coincidences", "#shorts", "#truestories", "#amazing", "#mindblown", "#unbelievable"],
        "unsolved_mysteries": ["#unsolvedmysteries", "#shorts", "#mystery", "#truecrime", "#coldcase", "#creepy"],
        "movie_trivia": ["#movietrivia", "#shorts", "#behindthescenes", "#hollywood", "#moviefacts", "#movies"],
        "animal_kingdom": ["#animals", "#shorts", "#animalfacts", "#nature", "#wildlife", "#didyouknow"],
        "space_wonders": ["#space", "#shorts", "#astronomy", "#nasa", "#universe", "#spacefacts"],
        "box_office": ["#boxoffice", "#shorts", "#movies", "#hollywood", "#moviefacts", "#records"],
        "things_they_dont_teach": ["#hardtruths", "#shorts", "#lifelessons", "#wisdom", "#realitycheck", "#mindset"],
        "challenges": ["#challenge", "#shorts", "#stunts", "#dare", "#tryit", "#viral", "#fail"],
        "satisfying": ["#satisfying", "#shorts", "#oddlysatisfying", "#diy", "#restoration", "#asmr", "#relaxing"],
        "negative_hooks": ["#darktruths", "#shorts", "#realitycheck", "#uncomfortable", "#truthhurts", "#deep", "#mindblowing"],
    }

    selected = mode_hashtags.get(mode, ["#shorts", mode, "#youtubeshorts"])
    random.shuffle(selected)
    return " ".join(selected[:count])
