"""Keyword extraction engine — extracts precise, high-intent keywords from content data for SEO."""

import re
import random

STOP_WORDS = {
    "a", "an", "the", "is", "it", "of", "in", "on", "to", "for", "and",
    "or", "but", "at", "by", "with", "from", "as", "was", "are", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "just", "very", "too", "so", "up", "out", "off", "over", "all",
    "any", "each", "every", "no", "not", "only", "own", "same", "than",
    "that", "this", "these", "those", "what", "which", "who", "how",
    "when", "where", "why", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "some", "such", "more",
    "most", "other", "else", "like", "get", "got", "make", "made", "take",
    "took", "see", "saw", "know", "knew", "think", "thought", "come",
    "came", "give", "gave", "find", "found", "tell", "told", "become",
    "became", "leave", "left", "feel", "felt", "put", "set", "bring",
    "brought", "begin", "began", "keep", "kept", "hold", "held", "write",
    "wrote", "stand", "stood", "hear", "heard", "let", "mean", "meant",
    "set", "meet", "met", "run", "ran", "pay", "paid", "sit", "sat",
    "speak", "spoke", "lie", "lay", "lead", "led", "read", "grow", "grew",
    "lose", "lost", "fall", "fell", "send", "sent", "build", "built",
    "understand", "draw", "drew", "break", "broke", "spend", "spent",
    "cut", "rise", "rose", "drive", "drove", "buy", "bought", "wear",
    "wore", "choose", "chose", "seek", "sought", "throw", "threw",
    "catch", "caught", "reveal", "shows", "showed", "shown", "called",
    "known", "following", "using", "looking", "trying", "giving",
    "making", "taking", "getting",
}

MODE_KEYWORDS = {
    "facts": ["did you know", "fun facts", "interesting facts", "mind blowing", "trivia", "random facts", "amazing facts", "fact video", "educational", "learning"],
    "challenges": ["challenge", "try not to", "dare", "stunt", "competition", "can you", "hardest challenge", "extreme challenge", "fail", "win"],
    "satisfying": ["satisfying", "oddly satisfying", "asmr", "relaxing", "satisfying video", "restoration", "cleaning", "diy", "calming", "mesmerizing"],
    "negative_hooks": ["dark truth", "reality check", "uncomfortable truth", "psychology facts", "deep thoughts", "mind blowing truth", "sad truth", "eye opening", "harsh reality"],
    "things_they_dont_teach": ["life lessons", "wisdom", "hard truth", "life advice", "school didn't teach", "adulting", "reality", "success tips", "life hacks", "self improvement"],
    "psychology": ["psychology", "mind tricks", "brain hacks", "psychology facts", "human behavior", "mind games", "mental health", "self improvement", "manipulation"],
    "life_hacks": ["life hacks", "tips and tricks", "diy", "useful tips", "clever", "how to", "productivity", "home hacks", "kitchen hacks"],
    "history_minute": ["history", "history facts", "did you know history", "world history", "historical events", "ancient history", "on this day", "war history"],
    "urban_legends": ["urban legends", "creepy", "scary stories", "true story", "myths debunked", "paranormal", "unsolved mystery", "creepy facts"],
    "coincidences": ["coincidence", "crazy coincidence", "true story", "unbelievable", "fate", "luck", "strange but true", "amazing story"],
    "unsolved_mysteries": ["unsolved mystery", "cold case", "true crime", "mystery", "creepy", "unsolved", "disappearance", "baffling"],
    "movie_trivia": ["movie trivia", "behind the scenes", "movie facts", "hollywood secrets", "film facts", "cinema", "movie magic"],
    "animal_kingdom": ["animals", "animal facts", "wildlife", "nature", "cute animals", "amazing animals", "pet", "safari", "ocean animals"],
    "space_wonders": ["space", "nasa", "astronomy", "universe", "space facts", "planet", "galaxy", "science", "cosmos", "solar system"],
    "box_office": ["box office", "movie earnings", "hollywood", "highest grossing", "movie records", "film industry", "blockbuster"],
    "what_if": ["what if", "imagine", "scenario", "what would happen", "curiosity", "science fiction", "hypothetical"],
    "how_it_works": ["how it works", "explained", "science", "engineering", "how things work", "educational", "mechanism"],
    "riddles": ["riddle", "brain teaser", "puzzle", "iq test", "riddle answer", "challenge", "logic puzzle", "think"],
    "would_you_rather": ["would you rather", "this or that", "choice", "pick one", "fun questions", "decision", "personality test"],
    "story": ["story", "cinematic", "animation", "ai story", "chapter", "series", "drama"],
    "try_this": ["try this", "brain hack", "illusion", "mind trick", "optical illusion", "brain teaser", "visual trick", "psychology experiment", "mind game"],
}

CATEGORY_MAP = {
    "facts": "education",
    "challenges": "entertainment",
    "satisfying": "entertainment",
    "negative_hooks": "education",
    "things_they_dont_teach": "education",
    "psychology": "education",
    "life_hacks": "howto",
    "history_minute": "education",
    "urban_legends": "entertainment",
    "coincidences": "entertainment",
    "unsolved_mysteries": "entertainment",
    "movie_trivia": "entertainment",
    "animal_kingdom": "education",
    "space_wonders": "education",
    "box_office": "entertainment",
    "what_if": "entertainment",
    "how_it_works": "education",
    "riddles": "entertainment",
    "would_you_rather": "entertainment",
    "story": "entertainment",
    "try_this": "education",
}


def extract_keywords(text: str, max_words: int = 20) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    bigrams = []
    words_list = filtered
    for i in range(len(words_list) - 1):
        bigram = f"{words_list[i]} {words_list[i+1]}"
        if len(bigram) > 5:
            bigrams.append(bigram)
    bigram_freq = {}
    for b in bigrams:
        bigram_freq[b] = bigram_freq.get(b, 0) + 1
    sorted_bigrams = sorted(bigram_freq.items(), key=lambda x: -x[1])
    result = [w for w, _ in sorted_bigrams[:max_words//2]]
    result += [w for w, _ in sorted_words[:max_words//2]]
    seen = set()
    unique = []
    for item in result:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:max_words]


def generate_keyword_tags(mode: str, data: dict) -> list[str]:
    tags = []
    mode_base = MODE_KEYWORDS.get(mode, [mode])
    tags.extend(mode_base)
    text_pool = []
    for key in ["script", "tts_script", "title"]:
        val = data.get(key, "")
        if val:
            text_pool.append(val)
    for key in ["topics", "facts", "truths", "hacks", "challenges"]:
        items = data.get(key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str):
                    text_pool.append(item)
                elif isinstance(item, dict):
                    text_pool.append(item.get("title", ""))
                    text_pool.append(item.get("description", ""))
    combined = " ".join(text_pool)
    extracted = extract_keywords(combined, max_words=10)
    tags.extend(extracted)
    if "niche" in data and data["niche"]:
        tags.append(data["niche"].lower().replace(" ", ""))
    seen = set()
    unique = []
    for tag in tags:
        t = tag.lower().strip()
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:30]


def generate_audience_tags(mode: str) -> list[str]:
    audience_map = {
        "facts": ["curious minds", "trivia lovers", "fact enthusiasts", "lifelong learners"],
        "challenges": ["thrill seekers", "competitive", "daredevils", "adventure lovers"],
        "satisfying": ["relaxation seekers", "asmr fans", "neat freaks", "visual lovers"],
        "negative_hooks": ["deep thinkers", "reality seekers", "philosophy", "self aware"],
        "things_they_dont_teach": ["self improvers", "life learners", "wisdom seekers", "ambitious"],
        "psychology": ["mind explorers", "self awareness", "psychology fans", "behavior analysts"],
        "life_hacks": ["home improvers", "life hackers", "productivity", "clever people"],
        "history_minute": ["history buffs", "past explorers", "history lovers", "fact seekers"],
        "urban_legends": ["mystery lovers", "creepy fans", "skeptics", "story lovers"],
        "coincidences": ["believers in fate", "story lovers", "amazed people", "curious"],
        "unsolved_mysteries": ["true crime fans", "mystery solvers", "detectives", "cold case"],
        "movie_trivia": ["movie buffs", "film lovers", "cinema fans", "hollywood"],
        "animal_kingdom": ["animal lovers", "nature fans", "pet owners", "wildlife"],
        "space_wonders": ["space enthusiasts", "astronomy fans", "science lovers", "nasa"],
        "box_office": ["movie fans", "box office trackers", "film industry", "cinema"],
        "what_if": ["imaginative", "curious kids", "dreamers", "what if scenario"],
        "how_it_works": ["curious engineers", "how stuff works", "diy learners", "science"],
        "riddles": ["puzzle solvers", "brain game lovers", "iq challenge", "smart"],
        "would_you_rather": ["decision lovers", "fun seekers", "game players", "social"],
        "story": ["story lovers", "cinematic fans", "fiction", "drama"],
        "try_this": ["brain hack fans", "illusion lovers", "psychology curious", "mind game players"],
    }
    return audience_map.get(mode, ["general audience"])


def get_youtube_category(mode: str) -> str:
    return CATEGORY_MAP.get(mode, "entertainment")
