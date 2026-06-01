"""Box Office generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "You won't believe how much this movie earned:",
    "This box office record still stands today:",
    "The numbers behind this film are insane:",
    "This movie broke every record in Hollywood:",
    "Made on a tiny budget, earned millions:",
    "This film was predicted to flop but became a legend:",
    "The most profitable movie ever made:",
    "Hollywood didn't see this coming:",
]

FALLBACKS = [
    ("Avatar Is the Highest-Grossing Film", "Avatar (2009) earned $2.92 billion worldwide, making it the highest-grossing film of all time. It held the record for a decade until Avengers: Endgame briefly surpassed it in 2019. Avatar regained the title after a 2021 China re-release. Adjusted for inflation, Gone With the Wind still holds the all-time record."),
    ("The Blair Witch Project Made 4,000x Its Budget", "The Blair Witch Project (1999) was made for just $60,000. It earned $248 million worldwide — a return of 4,133 times its budget. It remains the most profitable film in history by budget-to-box-office ratio. It used a groundbreaking viral marketing campaign that convinced audiences it was real footage."),
    ("Avengers: Endgame Made $1 Billion in 5 Days", "Avengers: Endgame (2019) earned $1.2 billion in its opening weekend worldwide. It crossed $1 billion in just 5 days — the fastest any film has ever reached that milestone. It finished its run with $2.79 billion, briefly becoming the highest-grossing film ever."),
    ("The Biggest Box Office Bomb in History", "John Carter (2012) is considered the biggest box office bomb ever. It cost $350 million to make and market, but earned only $284 million worldwide. Disney lost an estimated $200 million on the film. Director Andrew Stanton later said the marketing failed to explain what the movie was about."),
    ("Paranormal Activity Cost $15,000, Earned $193 Million", "Paranormal Activity (2007) was made for only $15,000. It used a clever marketing strategy where audiences could 'demand' the film be shown in their city. It earned $193 million worldwide — a return of 12,867 times its budget. It launched a franchise that has earned over $890 million total."),
    ("Gone With the Wind Adjusted for Inflation", "Gone With the Wind (1939) earned $393 million in its original release. Adjusted for inflation, that's approximately $4.3 billion today — making it the highest-grossing film of all time when inflation is accounted for. It held the initial box office record for 25 years until Jaws surpassed it in 1975."),
    ("Mad Max Fury Road Made Back Its Budget in One Day", "Mad Max: Fury Road (2015) had a budget of $150 million. On opening weekend, it earned $45 million in the US alone. While it only made back $379 million worldwide, its insane practical stunts — almost no CGI — made it one of the most acclaimed action films ever. It won 6 Oscars."),
    ("Star Wars Saved 20th Century Fox", "In 1977, 20th Century Fox was on the verge of bankruptcy. The studio bet everything on Star Wars, which cost $11 million to make. It earned $775 million worldwide, saving the studio. George Lucas famously traded his director's fee for merchandise rights — a deal that made him billions."),
    ("The Dark Knight Missed $1 Billion by $2 Million", "The Dark Knight (2008) earned $997 million worldwide — just $3 million short of $1 billion. It was the highest-grossing film of that year and the fourth film ever to cross $500 million domestically. Heath Ledger's posthumous Oscar-winning performance as the Joker drove massive audience turnout."),
    ("Titanic Was Predicted to Be a Disaster", "Before release, Titanic (1997) was predicted to be the biggest flop in history. It cost $200 million — the most expensive film ever at the time. Instead, it earned $2.2 billion worldwide and held the all-time box office record for 12 years. James Cameron famously said: 'I'm not crazy — I'm just confident.'"),
    ("Spider-Man No Way Home Saved Theaters", "Spider-Man: No Way Home (2021) earned $1.9 billion during the COVID-19 pandemic. It was the first film to cross $1 billion since Star Wars: The Rise of Skywalker in 2019. Many theater chains were on the verge of closing permanently before this film's release brought audiences back."),
    ("The Lowest Budget Movie to Earn $1 Billion", "Jurassic Park (1993) was made for $63 million — one of the lowest budgets for any billion-dollar film. It earned $1.03 billion worldwide. The groundbreaking CGI dinosaurs were revolutionary. It remains one of the most profitable films ever, with a budget-to-box-office ratio of 16:1."),
    ("Marvel vs DC at the Box Office", "The Marvel Cinematic Universe has earned over $29 billion across 33 films. The DC Extended Universe has earned about $6 billion across 15 films. Avengers: Endgame alone earned more than the entire DCEU Snyder trilogy combined. The highest-grossing DC film is Aquaman at $1.15 billion."),
    ("The First Movie to Make $1 Billion", "Jurassic Park (1993) was the first film to reach $1 billion at the worldwide box office. It had earned $912 million by the end of its initial run, then crossed $1 billion after re-releases. Today, over 50 films have crossed the $1 billion mark, but 85% of them were released after 2010."),
    ("Harry Potter and the $7.7 Billion Franchise", "The Harry Potter film series earned $7.7 billion across 8 films — an average of $962 million per film. The most successful was Harry Potter and the Deathly Hallows Part 2 at $1.3 billion. The Fantastic Beasts spin-offs added another $1.8 billion, though with diminishing returns."),
    ("Indiana Jones 5 Lost Over $100 Million", "Indiana Jones and the Dial of Destiny (2023) cost $387 million to make and market. It earned only $384 million — a loss of over $100 million for Disney. It's one of the biggest bombs in history. Harrison Ford's final outing as Indy was praised critically but couldn't find an audience."),
    ("Animated Films That Surprised Everyone", "The Super Mario Bros Movie (2023) earned $1.36 billion — the highest-grossing video game adaptation ever. Frozen (2013) earned $1.28 billion, becoming the highest-grossing animated film at the time. Minions (2015) earned $1.16 billion despite receiving poor reviews from critics."),
    ("The Most Expensive Movie Ever Made", "Star Wars: The Force Awakens (2015) cost $447 million to make — the most expensive film ever when including marketing. Avengers: Endgame cost $356 million. Avatar: The Way of Water cost $350 million. Pirates of the Caribbean 3 cost $300 million. Most of these budgets went to CGI and actor salaries."),
    ("China's Box Office Is Now Bigger Than North America", "In 2020, China's box office surpassed North America for the first time. China earned $2.9 billion while North America earned $2.2 billion. The top-grossing film in China is The Battle at Lake Changjin at $913 million. Chinese films now regularly outperform Hollywood films in their domestic market."),
    ("The Movie That Never Made a Profit Despite $600M Box Office", "Despite earning $600 million worldwide, The Incredibles 2 (2018) had such a high budget and marketing cost that it took years to break even. Many blockbuster films with large budgets don't truly 'profit' from box office alone — merchandising, streaming rights, and TV licenses are where studios actually make money."),
]


def generate_box_office_script() -> dict:
    entry = bank_manager.pick("box_office")
    if entry:
        print(f"  Using banked box office facts ({bank_manager.count('box_office')} left)")
        return entry

    print("  Bank empty, generating fresh box office facts...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(4, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"vintage Hollywood movie poster, {title}, dramatic golden lighting, film strip border, 9:16 vertical, cinema marquee lights, retro box office aesthetic"
        for title, _ in items
    ]
    tts_lines = [f"{title}. {story}" for title, story in items]
    return {
        "title": f"{hook} {items[0][0]}",
        "hook": hook,
        "box_office_titles": [title for title, _ in items],
        "stories": [story for _, story in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 4 fascinating box office or movie earnings facts with short explanations (12-15 words each). "
            "Each must be a verified real fact about movie budgets, earnings, or records. "
            "Format exactly:\n"
            "TITLE: [short headline for the box office fact]\n"
            "FACT: [short explanation, 8-12 words]\n\n"
            "Include specific numbers, years, and comparisons."
        )
        system = "You write verified true box office facts. Every dollar amount and record must be accurate."
        raw = _generate(prompt, temperature=0.7, max_tokens=1000, system=system)
        if not raw:
            return None
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TITLE:"):
                if current.get("title") and current.get("fact"):
                    items.append((current["title"], current["fact"]))
                current = {"title": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("FACT:") and current:
                current["fact"] = line.split(":", 1)[-1].strip()
        if current.get("title") and current.get("fact"):
            items.append((current["title"], current["fact"]))
        if items and len(items) >= 3:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"vintage Hollywood movie poster, {title}, dramatic golden lighting, film strip border, 9:16 vertical, cinema marquee lights, retro box office aesthetic"
                for title, _ in items
            ]
            tts_lines = [f"{title}. {fact}" for title, fact in items]
            return {
                "title": f"{hook} {items[0][0]}",
                "hook": hook,
                "box_office_titles": [title for title, _ in items],
                "stories": [fact for _, fact in items],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
