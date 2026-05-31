"""Content bank: stores pre-generated scripts in repo, auto-refills via LLM.
Ensures no content repetition by tracking used items and filtering during refill."""

import json, random, re
from pathlib import Path
from src.script_generator import _generate

BANK_DIR = Path(__file__).parent / "bank"

REFILL_PROMPTS = {
    "facts": (
        "Generate 8 surprising true facts about {niche}. "
        "All facts must be 100%% accurate. Never repeat facts from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Number them 1-8, one per line."
    ),
    "what_if": (
        "Give me 6 imaginative 'What If' scenarios for kids. "
        "Never repeat scenarios from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format each as:\n"
        "SCENARIO: what if ...\n"
        "EXPLANATION: a short fun explanation of what would happen\n"
        "Make them creative, magical, and fun. No scary content."
    ),
    "how_it_works": (
        "Give me 6 different everyday objects and explain how each works in 2-3 simple sentences. "
        "Never repeat topics from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "TOPIC: [object name]\n"
        "EXPLANATION: [how it works in 2-3 sentences]\n\n"
        "Make each explanation clear and correct. Choose common household objects."
    ),
    "riddles": (
        "Write a {rtype} riddle. Never repeat riddles from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "RIDDLE: [the riddle question]\n"
        "ANSWER: [short answer]\n"
        "EXPLANATION: [one sentence explanation]\n"
        "Make it clever but solvable. Suitable for all ages."
    ),
    "would_you_rather": (
        "Write a 'Would You Rather' question about {cat}. "
        "Never repeat options from this avoid list:"
        "\n---\n{avoid}\n---\n"
        "Format exactly:\n"
        "OPTION_A: [first option, ~3-8 words]\n"
        "OPTION_B: [second option, ~3-8 words]\n"
        "Make both options fun, imaginative, and suitable for all ages. "
        "Both options should be equally desirable so it's a real choice."
    ),
}

NICHES = [
    "space", "animals", "history", "science", "psychology",
    "human body", "ocean", "technology", "brain", "nature", "physics",
    "food", "music", "sports", "weather", "dinosaurs", "inventions", "math",
]

FACT_HOOKS = [
    "Did you know?", "This will blow your mind...",
    "Most people don't know this...", "Here's something crazy:",
    "Wait till you hear this:", "This fact is unbelievable:",
    "You won't believe this:", "Mind-blowing fact:",
]

IMAGE_PROMPT_FACT = "cinematic illustration: {keywords}, atmospheric lighting, 9:16 vertical, highly detailed, moody"
IMAGE_PROMPT_WHATIF = "whimsical children's book illustration: {scenario}, colorful magical dreamlike, wide shot, 9:16 vertical, vibrant pastels, soft lighting"
IMAGE_PROMPT_HOW = "cinematic close-up illustration: {topic}, detailed technical cross-section view, clean lighting, educational style, 9:16 vertical"
IMAGE_PROMPT_RIDDLE = "mysterious cinematic scene: {riddle}, dark moody lighting, question marks, 9:16 vertical, intrigue"
IMAGE_PROMPT_RIDDLE_ANSWER = "cinematic reveal scene: {answer}, bright warm lighting, discovery moment, 9:16 vertical"

RIDDLE_TYPES = [
    "logic", "wordplay", "math", "lateral thinking", "observation",
    "classic", "nature", "science", "everyday", "animal",
]

WYR_CATEGORIES = [
    "food", "travel", "money", "superpowers", "animals", "silly",
    "everyday", "nature", "sports", "school", "technology",
]


def _bank_path(mode: str) -> Path:
    return BANK_DIR / f"{mode}.json"


def _read_bank(mode: str) -> dict:
    path = _bank_path(mode)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"entries": [], "used": [], "min_before_refill": 5, "refill_target": 40}


def _write_bank(mode: str, data: dict):
    path = _bank_path(mode)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _mark_used(mode: str, entry: dict):
    data = _read_bank(mode)
    if "used" not in data:
        data["used"] = []
    used = data["used"]
    if mode == "facts":
        for f in entry.get("facts", []):
            n = _normalize(f)
            if n not in used:
                used.append(n)
    elif mode == "what_if":
        for s in entry.get("scenarios", []):
            n = _normalize(s)
            if n not in used:
                used.append(n)
    elif mode == "how_it_works":
        for t in entry.get("topics", []):
            n = _normalize(t)
            if n not in used:
                used.append(n)
    elif mode == "riddles":
        n = _normalize(entry.get("riddle", ""))
        if n and n not in used:
            used.append(n)
    elif mode == "would_you_rather":
        for opt in [entry.get("option_a", ""), entry.get("option_b", "")]:
            n = _normalize(opt)
            if n and n not in used:
                used.append(n)
    data["used"] = used
    _write_bank(mode, data)


def _avoid_sample(mode: str, max_items: int = 30) -> str:
    data = _read_bank(mode)
    used = data.get("used", [])
    if not used:
        return "none yet"
    sample = random.sample(used, min(max_items, len(used)))
    return "\n".join(f"- {item}" for item in sample)


def _is_duplicate(mode: str, items: list[str], data: dict) -> bool:
    used = set(data.get("used", []))
    for item in items:
        if _normalize(item) in used:
            return True
    return False


def pick(mode: str) -> dict | None:
    data = _read_bank(mode)
    if data["entries"]:
        entry = data["entries"].pop(0)
        _write_bank(mode, data)
        _mark_used(mode, entry)
        return entry
    return None


def count(mode: str) -> int:
    return len(_read_bank(mode)["entries"])


def needs_refill(mode: str) -> bool:
    data = _read_bank(mode)
    return len(data["entries"]) <= data["min_before_refill"]


def refill(mode: str, force_count: int | None = None):
    try:
        data = _read_bank(mode)
        target = force_count or data["refill_target"]
        existing = len(data["entries"])
        need = target - existing
        if need <= 0:
            return

        print(f"  Bank refill: generating {need} new {mode} entries...")

        if mode == "facts":
            new_entries = _refill_facts(need)
        elif mode == "what_if":
            new_entries = _refill_what_if(need)
        elif mode == "how_it_works":
            new_entries = _refill_how_it_works(need)
        elif mode == "riddles":
            new_entries = _refill_riddles(need)
        elif mode == "would_you_rather":
            new_entries = _refill_wyr(need)
        else:
            return

        data["entries"].extend(new_entries)
        _write_bank(mode, data)
        print(f"  Bank refilled: {len(data['entries'])} {mode} entries total")
    except Exception as e:
        print(f"  Bank refill failed (non-critical): {e}")


def _refill_facts(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        niche = random.choice(NICHES)
        avoid = _avoid_sample("facts")
        prompt = REFILL_PROMPTS["facts"].format(niche=niche, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You write verified facts. Only include facts you are certain are true. One fact per line, numbered.")
        except Exception as e:
            print(f"  LLM error (facts): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        facts = []
        for line in raw.split("\n"):
            line = line.strip().lstrip("*- ")
            if not line or len(line) < 15:
                continue
            if (line[0].isdigit() and (". " in line[:4] or ") " in line[:4])):
                clean = line.split(". ", 1)[-1].split(") ", 1)[-1].strip()
                if clean and len(clean) > 10:
                    facts.append(clean.rstrip(".") + ".")

        if len(facts) >= 3 and not _is_duplicate("facts", facts, _read_bank("facts")):
            hook = random.choice(FACT_HOOKS)
            image_prompts = [
                IMAGE_PROMPT_FACT.format(keywords=" ".join(f.split()[:12]))
                for f in facts
            ]
            tts_script = f"{hook} {' '.join(facts)}"
            entry = {
                "title": f"{hook} {facts[0][:60]}...",
                "niche": niche,
                "hook": hook,
                "facts": facts,
                "image_prompts": image_prompts,
                "script": tts_script,
                "tts_script": tts_script,
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_what_if(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("what_if")
        prompt = REFILL_PROMPTS["what_if"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.9, max_tokens=800,
                            system="You write creative 'What If' scenarios for children's videos.")
        except Exception as e:
            print(f"  LLM error (what_if): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        scenarios = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("SCENARIO:"):
                if current.get("scenario") and current.get("explanation"):
                    scenarios.append((current["scenario"], current["explanation"]))
                current = {"scenario": line.split(":", 1)[-1].strip().lower()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("scenario") and current.get("explanation"):
            scenarios.append((current["scenario"], current["explanation"]))

        scenario_texts = [s for s, _ in scenarios]
        if len(scenarios) >= 3 and not _is_duplicate("what_if", scenario_texts, _read_bank("what_if")):
            hook = random.choice(FACT_HOOKS)
            image_prompts = [
                IMAGE_PROMPT_WHATIF.format(scenario=s)
                for s, _ in scenarios
            ]
            tts_lines = [f"{hook} {s}. {e}" for s, e in scenarios]
            entry = {
                "title": f"{hook} {scenarios[0][0]}",
                "hook": hook,
                "scenarios": [s for s, _ in scenarios],
                "explanations": [e for _, e in scenarios],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_how_it_works(need: int) -> list:
    entries = []
    attempts = 0
    while len(entries) < need and attempts < need * 5:
        avoid = _avoid_sample("how_it_works")
        prompt = REFILL_PROMPTS["how_it_works"].format(avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=800,
                            system="You explain how everyday things work in simple, accurate terms.")
        except Exception as e:
            print(f"  LLM error (how_it_works): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue

        topics = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("TOPIC:"):
                if current.get("topic") and current.get("explanation"):
                    topics.append((current["topic"], current["explanation"]))
                current = {"topic": line.split(":", 1)[-1].strip().lower()}
            elif line.upper().startswith("EXPLANATION:") and current:
                current["explanation"] = line.split(":", 1)[-1].strip()
        if current.get("topic") and current.get("explanation"):
            topics.append((current["topic"], current["explanation"]))

        topic_texts = [t for t, _ in topics]
        if len(topics) >= 3 and not _is_duplicate("how_it_works", topic_texts, _read_bank("how_it_works")):
            hook = random.choice([
                "Ever wondered how this works?", "Here's how it actually works.",
                "You use it every day. But how does it work?", "Let me explain how this works.",
            ])
            image_prompts = [
                IMAGE_PROMPT_HOW.format(topic=t)
                for t, _ in topics
            ]
            tts_lines = [e for _, e in topics]
            entry = {
                "title": f"{hook} {topics[0][0].capitalize()}",
                "hook": hook,
                "topics": [t for t, _ in topics],
                "explanations": [e for _, e in topics],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
            entries.append(entry)
        attempts += 1

    return entries


def _refill_riddles(need: int) -> list:
    entries = []
    attempts = 0
    hooks = [
        "Can you solve this riddle?", "Here's a riddle for you:",
        "Think you're smart? Try this:", "Test your brain with this riddle:",
        "Only 1 in 10 can solve this:", "Here's a tricky one:",
    ]
    while len(entries) < need and attempts < need * 5:
        rtype = random.choice(RIDDLE_TYPES)
        avoid = _avoid_sample("riddles")
        prompt = REFILL_PROMPTS["riddles"].format(rtype=rtype, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.8, max_tokens=300,
                            system="You write clever riddles suitable for all ages.")
        except Exception as e:
            print(f"  LLM error (riddles): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        riddle = answer = explanation = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("RIDDLE:"):
                riddle = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("ANSWER:"):
                answer = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[-1].strip()
        if riddle and answer and not _is_duplicate("riddles", [riddle], _read_bank("riddles")):
            hook = random.choice(hooks)
            entry = {
                "title": "Can You Solve This Riddle?",
                "hook": hook,
                "riddle": riddle,
                "answer": answer,
                "explanation": explanation or f"The answer is {answer}.",
                "image_prompt_riddle": IMAGE_PROMPT_RIDDLE.format(riddle=riddle[:80]),
                "image_prompt_answer": IMAGE_PROMPT_RIDDLE_ANSWER.format(answer=answer[:80]),
                "tts_script": f"{hook} {riddle} Pause and think about it. The answer is... {answer}. {explanation or f'The answer is {answer}.'}",
            }
            entries.append(entry)
        attempts += 1
    return entries


def _refill_wyr(need: int) -> list:
    entries = []
    attempts = 0
    hooks = [
        "Would you rather...", "Choose wisely:", "Which one would you pick?",
        "Hard choice incoming:", "What would you do?", "Pick your side:",
    ]
    while len(entries) < need and attempts < need * 5:
        cat = random.choice(WYR_CATEGORIES)
        avoid = _avoid_sample("would_you_rather")
        prompt = REFILL_PROMPTS["would_you_rather"].format(cat=cat, avoid=avoid)
        try:
            raw = _generate(prompt, temperature=0.9, max_tokens=200,
                            system="You write fun 'Would You Rather' questions suitable for all ages.")
        except Exception as e:
            print(f"  LLM error (would_you_rather): {e}")
            attempts += 1
            continue
        if not raw:
            attempts += 1
            continue
        a = b = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("OPTION_A:") or line.upper().startswith("A)"):
                a = line.split(":", 1)[-1].split(")", 1)[-1].strip()
            elif line.upper().startswith("OPTION_B:") or line.upper().startswith("B)"):
                b = line.split(":", 1)[-1].split(")", 1)[-1].strip()
        if a and b and not _is_duplicate("would_you_rather", [a, b], _read_bank("would_you_rather")):
            hook = random.choice(hooks)
            entries.append({
                "title": "Would You Rather?",
                "hook": hook,
                "option_a": a,
                "option_b": b,
                "tts_script": f"{hook} {a} or {b}. Which one would you choose? Comment below!",
            })
        attempts += 1
    return entries


def ensure_refilled(mode: str):
    if needs_refill(mode):
        print(f"  {mode} bank low ({count(mode)} left), refilling...")
        refill(mode)
    else:
        print(f"  {mode} bank healthy ({count(mode)} entries)")
