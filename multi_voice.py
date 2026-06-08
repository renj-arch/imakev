"""
Multi-voice narration-to-scene pipeline.
Parses scripts with 🎙️ speaker markers, generates varied frames per voice segment,
inserts child (Think) interjections and final acknowledgment.
"""
import os, re, json, hashlib, argparse, random
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator, SKETCH_TECHNIQUES
from src.narration_to_sketch import _describe_scene

CACHE_FILE = "output/.mv_cache.json"

# Voice configurations with personality roles
VOICES = {
    "Ding":  {"name": "Ding", "role": "Storykeeper", "color": (60, 140, 220), "icon": "~"},
    "Dong":  {"name": "Dong", "role": "Reflector", "color": (200, 100, 180), "icon": "~"},
    "Think": {"name": "Think", "role": "Curious", "color": (255, 200, 60), "icon": "?"},
}

# Mapping from script labels to voice keys
SPEAKER_MAP = {
    "Narrator": "Ding",
    "Voice 1":  "Ding",
    "Voice 2":  "Dong",
    "Voice 3":  "Dong",
    "Think":    "Think",
    "Child":    "Think",
    "Kid":      "Think",
}

# Generic child interjection templates (no family references — just a curious voice)
THINK_QUESTIONS = [
    "Why is that important?",
    "What happened next?",
    "How do you know that?",
    "Was that real?",
    "Could it happen again?",
    "Do you think they were scared?",
    "Can I ask something?",
    "I have a question.",
    "Wait — I don't understand.",
    "But how?",
    "Tell me more about that part.",
    "How long did that take?",
    "Why did that happen?",
    "What does that mean?",
    "Is that true?",
    "How is that possible?",
    "What would you have done?",
    "Could someone have stopped it?",
    "I want to know more.",
    "Did anyone see it coming?",
    "How did they know what to do?",
    "What happened after that?",
    "Why is that so hard to believe?",
    "What does that feel like?",
    "How do we know about it now?",
]

# Extract key nouns from story text for context-aware questions
STOP_WORDS = {"the", "a", "an", "is", "was", "are", "were", "be", "been",
              "have", "has", "had", "do", "does", "did", "will", "would",
              "could", "should", "may", "might", "can", "shall", "it", "its",
              "this", "that", "these", "those", "i", "you", "he", "she",
              "they", "we", "my", "your", "his", "her", "our", "their",
              "me", "him", "us", "them", "and", "but", "or", "not", "no",
              "all", "each", "every", "some", "any", "none", "who", "what",
              "where", "when", "why", "how", "which", "of", "in", "on",
              "at", "to", "for", "with", "by", "from", "as", "into",
              "through", "during", "before", "after", "above", "below",
              "between", "out", "off", "over", "under", "again", "then",
              "once", "here", "there", "more", "most", "other", "such",
              "very", "just", "also", "because", "if", "than"}


def extract_story_keywords(text: str, max_words=10) -> list[str]:
    """Extract meaningful nouns/keywords from story text."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    freq = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    # Filter out common verbs/adjectives that make bad question subjects
    bad_subjects = {"imagine", "survived", "survive", "become", "became",
                    "began", "begun", "taken", "took", "known", "knew",
                    "shown", "showed", "grown", "grew", "meant", "meant",
                    "found", "kept", "felt", "left", "lost", "told",
                    "given", "gave", "gone", "went", "seen", "seen",
                    "heard", "held", "kept", "said", "made", "tried",
                    "lived", "lives", "living", "died", "dying", "dead",
                    "coming", "going", "being", "having", "doing",
                    "looking", "finding", "keeping", "taking", "giving",
                    "walking", "standing", "sitting", "running", "moving",
                    "wanted", "wants", "wanting", "needed", "needs",
                    "knowing", "thinking", "feeling", "believing",
                    "trying", "asking", "telling", "showing", "calling",
                    "started", "starts", "starting", "ended", "ends",
                    "ending", "changed", "changes", "changing",
                    "followed", "follows", "following", "crossed",
                    "crosses", "crossing", "retreated", "retreats",
                    "retreating", "spread", "spreading", "disappeared",
                    "disappears", "disappearing", "shrank", "shrinking",
                    "roamed", "roams", "roaming", "notice", "noticed",
                    "noticing", "inherited", "inherits", "inheriting",
                    "remained", "remains", "remaining", "walks", "walked",
                    "record", "recorded", "recording", "marks", "marked",
                    "marking", "continued", "continues", "continuing",
                    "vanished", "vanishes", "vanishing", "stopped",
                    "stops", "stopping", "remembers", "remembering",
                    "remembered", "knows", "understood", "understand",
                    "understanding", "sudden", "slowly", "familiar",
                    "ordinary", "ancient", "enormous", "brutal",
                    "frozen", "endless", "heavy", "strange", "obvious",
                    "single", "final", "cold", "hundreds", "thousands",
                    "eventually", "completely", "simply", "perhaps",
                    "almost", "yet", "still", "another", "different",
                    "small", "smaller", "tiny", "enormous", "huge",
                    "slightly", "exactly", "nothing", "something",
                    "everything", "always", "never", "together"}
    filtered = [(w, c) for w, c in sorted_words if w not in bad_subjects]
    if not filtered:
        filtered = sorted_words[:5]
    return [w for w, _ in filtered[:max_words]]


def generate_context_question(story_text: str, keywords: list[str],
                               used_questions: set) -> str:
    """Generate a story-aware child question using extracted keywords."""
    templates = [
        "Why did the {}...?",
        "How did the {}...?",
        "What happened to the {}?",
        "Was the {} real?",
        "Could the {} have been saved?",
        "How big was the {}?",
        "Where did the {} go?",
        "Did anyone see the {}?",
        "What does the {} look like?",
        "Why is the {} important?",
    ]
    rng = random.Random(hash(story_text[:100]))
    # Filter keywords not yet used in questions
    fresh = [k for k in keywords if k not in str(used_questions).lower()]
    if not fresh:
        fresh = keywords
    for _ in range(20):
        kw = rng.choice(fresh)
        tmpl = rng.choice(templates)
        q = tmpl.format(kw).capitalize()
        if q not in used_questions:
            used_questions.add(q)
            return q
    # Fallback to generic
    q = rng.choice(THINK_QUESTIONS)
    if q not in used_questions:
        used_questions.add(q)
    return q

# Visual style per voice
VOICE_STYLES = {
    "Ding":  {"border": (60, 140, 220), "bar_color": (10, 30, 60), "icon": "~"},
    "Dong":  {"border": (200, 100, 180), "bar_color": (50, 20, 40), "icon": "~"},
    "Think": {"border": (255, 200, 60), "bar_color": (50, 40, 10), "icon": "?"},
}

# Character portrait thumbnails
CHAR_PORTRAITS = {}
for _v in ["ding", "dong", "think"]:
    _p = os.path.join("output", f"char_{_v}.png")
    if os.path.exists(_p):
        CHAR_PORTRAITS[_v.capitalize()] = Image.open(_p).convert("RGBA")

# Camera angle configs for visual variety
CAMERA_ANGLES = [
    {"angle": "wide", "zoom": 1.0, "desc": "wide shot"},
    {"angle": "medium", "zoom": 1.1, "desc": "medium shot"},
    {"angle": "closeup", "zoom": 1.4, "desc": "close-up"},
    {"angle": "overhead", "zoom": 0.9, "desc": "overhead view"},
    {"angle": "low_angle", "zoom": 1.2, "desc": "low angle"},
]

STYLES = [
    {"tag": "[Epic twilight] ", "mood": "epic", "bg_hint": "sunset", "camera": "wide", "zoom": 1.0},
    {"tag": "[Dramatic night] ", "mood": "dramatic", "bg_hint": "night", "camera": "closeup", "zoom": 1.4},
    {"tag": "[Somber dawn] ", "mood": "somber", "bg_hint": "dawn", "camera": "medium", "zoom": 1.1},
    {"tag": "[Grand sunset] ", "mood": "epic", "bg_hint": "sunset", "camera": "low_angle", "zoom": 1.2},
    {"tag": "[Mysterious moonlight] ", "mood": "mysterious", "bg_hint": "night", "camera": "overhead", "zoom": 0.9},
    {"tag": "[Hopeful golden] ", "mood": "hopeful", "bg_hint": "sunset", "camera": "wide", "zoom": 1.0},
    {"tag": "[Intense overcast] ", "mood": "dramatic", "bg_hint": "overcast", "camera": "closeup", "zoom": 1.3},
    {"tag": "[Quiet evening] ", "mood": "peaceful", "bg_hint": "indoor", "camera": "medium", "zoom": 1.0},
]


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs("output", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def parse_script(text: str) -> list[dict]:
    """Parse 🎙️ VoiceName: format into segments."""
    segments = []
    # Normalize line endings
    text = text.replace("\r\n", "\n")
    # Split by 🎙️ markers
    pattern = r'🎙️\s*([^:\n]+):\s*\n'
    parts = re.split(pattern, text)
    # parts[0] is anything before first marker (usually empty)
    # then alternating: speaker, text, speaker, text, ...
    for i in range(1, len(parts), 2):
        if i + 1 >= len(parts):
            break
        raw_speaker = parts[i].strip()
        raw_text = parts[i + 1].strip()
        if not raw_text:
            continue
        # Map speaker label to voice key
        voice_key = SPEAKER_MAP.get(raw_speaker, raw_speaker)
        if voice_key not in VOICES:
            voice_key = "Ding"  # fallback
        segments.append({"voice": voice_key, "speaker": raw_speaker, "text": raw_text})
    return segments


def smart_parse(text: str) -> list[dict]:
    """Parse raw story text without voice markers.
    
    The engine automatically:
    - Splits text into natural segments (paragraph-based, merging short lines)
    - Classifies each segment as Narration (Ding) or Reflection (Dong)
    - Uses linguistic heuristics + context alternation
    """
    text = text.replace("\r\n", "\n")
    
    # Remove title line
    lines = text.split("\n")
    title = None
    non_empty = [l for l in lines if l.strip()]
    if non_empty:
        first = non_empty[0].strip()
        if len(first.split()) <= 5 and not first.endswith((".", "!", "?")):
            title = first
            text = "\n".join(lines[lines.index(first) + 1:])
    
    # Split by blank lines into paragraphs first
    paragraphs = re.split(r'\n\n+', text.strip())
    
    segments = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Within a paragraph, merge short lines into larger chunks
        lines = para.split("\n")
        lines = [l.strip() for l in lines if l.strip()]
        
        chunks = []
        current = []
        for line in lines:
            word_count = len(line.split())
            # If this line is short and continues the same thought, merge
            if word_count <= 12 and current:
                current.append(line)
            elif word_count <= 12 and not current:
                current.append(line)
            else:
                if current:
                    chunks.append(" ".join(current))
                    current = []
                chunks.append(line)
        if current:
            chunks.append(" ".join(current))
        
        # Further group very short chunks with nearby ones
        merged = []
        for chunk in chunks:
            if merged and len(chunk.split()) <= 8 and len(merged[-1].split()) <= 12:
                merged[-1] = merged[-1] + " " + chunk
            else:
                merged.append(chunk)
        
        for chunk in merged:
            chunk = chunk.strip()
            if chunk:
                segments.append({"text": chunk})
    
    # If too many segments, merge adjacent same-voice candidates
    if len(segments) > 40:
        merged = []
        for seg in segments:
            if merged and len(seg["text"].split()) <= 10 and len(merged[-1]["text"].split()) <= 15:
                merged[-1]["text"] = merged[-1]["text"] + " " + seg["text"]
            else:
                merged.append(seg)
        segments = merged
    
    return segments, title


def classify_voice(segment: dict, prev_voice=None) -> str:
    """Classify a text segment as narration (Ding) or reflection (Dong).
    
    Uses multiple signals:
    - Length and sentence count
    - Linguistic patterns (tense, phrasing, punctuation)
    - Content keywords
    - Alternation preference to keep a natural back-and-forth rhythm
    """
    text = segment["text"].strip()
    words = text.split()
    word_count = len(words)
    sentences = re.split(r'[.!?]+\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sent_count = len(sentences)
    
    # Strong narration signals (factual storytelling) — checked first
    # Past tense narrative about events
    if re.search(r'(was|were|had been|had|did|could|would)\s', text, re.IGNORECASE):
        # Check if it's describing events or making a philosophical point
        if re.search(r'(years ago|roamed|lived|survived|crossed|retreated|spread|disappeared|'
                     r'began|remained|walked|stood|fired|dragged|passed|fallen|vanished)', 
                     text, re.IGNORECASE):
            return "Ding"
    
    # Specific historical/factual content
    if re.search(r'(thousands of|millions of|hundreds of) (years|miles|people)', text, re.IGNORECASE):
        return "Ding"
    if re.search(r'(in |on |at |during |across |through |over |under )', text, re.IGNORECASE):
        # But only if it's describing something specific
        if word_count >= 6 and not re.match(r'^(and yet|that\'s|it\'s)', text, re.IGNORECASE):
            return "Ding"
    
    # Strong reflection signals
    if re.search(r'\.{4,}', text):
        return "Dong"  # Long ellipsis = pensive reflection
    
    if re.search(r'^(that\'s|that is|it\'s|it is|this is)', text, re.IGNORECASE):
        return "Dong"
    if re.search(r'^(and yet|but yet|yet|still,|but still)', text, re.IGNORECASE):
        return "Dong"
    if re.search(r'^(perhaps|maybe|almost|exactly|indeed|surely|certainly)', text, re.IGNORECASE):
        return "Dong"
    if re.search(r'^(not |no one|no |never |nothing )', text, re.IGNORECASE):
        # Check if it's continuing a narration
        if word_count <= 12:
            return "Dong"
    if re.search(r'^(the )?(unsettling|strange|saddest|hardest|heaviest|weirdest)', 
                 text, re.IGNORECASE):
        return "Dong"
    if re.search(r'(heavier|worse|better|stranger|sadder) than', text, re.IGNORECASE):
        return "Dong"
    if re.search(r'(almost )?(worse|better|stranger)', text, re.IGNORECASE):
        return "Dong"
    if re.search(r'^(imagine|wonder|curious|strange thing|funny thing)', text, re.IGNORECASE):
        return "Dong"
    
    # Very short segments with present tense tend to be reflection
    if word_count <= 6 and sent_count <= 1:
        if re.search(r'(is|are|doesn\'t|don\'t|can\'t|won\'t|will|shall)', text, re.IGNORECASE):
            return "Dong"
        # "The last.", "Gone.", "Exactly." — short reflective
        return "Dong"
    
    # Short reflective patterns (7-15 words, single sentence)
    if word_count <= 15 and sent_count <= 1:
        if re.search(r'(heavy thought|strange part|that\'s|it\'s|here\'s)', text, re.IGNORECASE):
            return "Dong"
        if re.search(r'(not because|because their|that\'s what|that is what)', text, re.IGNORECASE):
            return "Dong"
        if re.search(r'^and (yet|eventually|so|then)', text, re.IGNORECASE):
            return "Dong"
    
    # Long factual segments with multiple sentences
    if word_count > 30 or sent_count >= 3:
        return "Ding"
    
    # Medium segments: use alternation for natural rhythm
    if prev_voice:
        return "Dong" if prev_voice == "Ding" else "Ding"
    
    return "Ding"


def insert_smart_child(segments: list[dict], density=0.3) -> list[dict]:
    """Insert child questions at natural pause points.
    
    Places Think questions sparingly — only after key reflective moments
    or major narrative transitions, never more than a few per story.
    """
    result = []
    q_idx = 0
    used_questions = set()
    
    full_text = " ".join(s["text"] for s in segments)
    keywords = extract_story_keywords(full_text)
    
    # Determine max inserts based on story length
    total_segments = len([s for s in segments if s["voice"] in ("Ding", "Dong")])
    max_inserts = max(1, min(int(total_segments * density * 0.4), 6))
    inserted = 0
    
    # Identify natural insertion points: after major narration or reflection
    insertion_candidates = []
    for i, seg in enumerate(segments):
        text_lower = seg["text"].lower()
        
        # After reflection with emotional weight
        if seg["voice"] == "Dong" and any(w in text_lower for w in [
            "heavy thought", "unsettling", "strange part", "worse than",
            "never know", "almost worse", "not because", "simply turns",
            "doesn't stop", "ending around"
        ]):
            insertion_candidates.append(i)
        
        # After key narration moments
        if seg["voice"] == "Ding" and any(w in text_lower for w in [
            "imagine", "never know", "ended", "final group",
            "last of", "had vanished", "gone.", "disappeared",
            "last mammoth", "one final"
        ]):
            insertion_candidates.append(i)
    
    # Prioritize first few candidates spaced evenly
    if insertion_candidates:
        step = max(1, len(insertion_candidates) // max_inserts)
        chosen = insertion_candidates[::step][:max_inserts]
    else:
        # Fallback: pick evenly spaced
        step = max(1, total_segments // (max_inserts + 1))
        chosen = []
        count = 0
        for i, seg in enumerate(segments):
            if seg["voice"] in ("Ding", "Dong"):
                count += 1
                if count % step == 0 and len(chosen) < max_inserts:
                    chosen.append(i)
    
    for i, seg in enumerate(segments):
        result.append(seg)
        if i in chosen and inserted < max_inserts:
            if keywords:
                q = generate_context_question(seg["text"], keywords, used_questions)
            else:
                q = THINK_QUESTIONS[q_idx % len(THINK_QUESTIONS)]
                q_idx += 1
            result.append({"voice": "Think", "speaker": "Think",
                          "text": q, "auto_inserted": True})
            inserted += 1
    
    return result


def child_acknowledgment(segments: list[dict]) -> list[dict]:
    """Append child acknowledgment at the end."""
    full_text = " ".join(s["text"] for s in segments if s["voice"] in ("Ding", "Dong"))
    keywords = extract_story_keywords(full_text, max_words=5)
    kw = keywords[0] if keywords else "story"

    ack_text = (
        "I liked the story.\n"
        "I didn't understand all of it.\n"
        "But I think I understood the end."
    )
    segments.append({"voice": "Think", "speaker": "Think", "text": ack_text,
                    "auto_inserted": True})
    outro_templates = [
        f"I hope the {kw} was okay in the end.",
        f"I wonder what happened to the {kw} afterward.",
        f"I'll remember the {kw} for a long time.",
        f"Do you think the {kw} is still out there somewhere?",
    ]
    rng = random.Random(hash(full_text[-200:]))
    outro = rng.choice(outro_templates)
    segments.append({"voice": "Think", "speaker": "Think", "text": outro,
                    "auto_inserted": True})
    return segments


def generate_multi_voice(
    script_text: str,
    width=720,
    height=1280,
    seed=42,
    output_dir="output/mv_frames",
    font_path=None,
    child_density=0.4,
    add_child=True,
    smart=False,
    hand_drawn=True,
):
    """Generate scene frames from a multi-voice script.
    
    If smart=True, engine auto-parses raw text without markers:
    - Segments paragraphs, classifies voice (narration vs reflection)
    - Inserts child questions at natural pause points
    - Uses concept extraction for intelligent illustration
    """
    os.makedirs(output_dir, exist_ok=True)
    cache = load_cache()

    # Parse and expand script
    if smart:
        segments, title = smart_parse(script_text)
        print(f"Smart parsing: {len(segments)} segments extracted")
        if title:
            print(f"Title: {title}")
        # Classify each segment's voice
        prev = None
        for seg in segments:
            seg["voice"] = classify_voice(seg, prev)
            seg["speaker"] = "Narrator" if seg["voice"] == "Ding" else "Reflector"
            prev = seg["voice"]
        
        if add_child:
            segments = insert_smart_child(segments, child_density)
            segments = child_acknowledgment(segments)
    else:
        segments = parse_script(script_text)
        if not segments:
            print("No segments parsed from script.")
            return []

        if add_child:
            segments = insert_child_interjections(segments, child_density)
            segments = child_acknowledgment(segments)

    # Analyze full story for context-aware scene generation
    from src.story_context import analyze_story
    story_context = analyze_story(segments)
    if story_context["key_elements"]:
        print(f"Story context: {', '.join(story_context['key_elements'][:5])}")
        print(f"Theme: {story_context['theme']} | Setting: {story_context['bg_type']}")

    print(f"Generated {len(segments)} segments:")
    for i, seg in enumerate(segments):
        short = seg["text"][:60].replace("\n", " ")
        icon = VOICES.get(seg["voice"], {}).get("icon", "")
        tag = seg.get("auto_inserted", False) and " [auto]" or ""
        print(f"  [{i+1}] {seg['voice']}: {short}...{tag}")

    frames = []
    scene_descs = []
    has_comments = any(seg["voice"] == "Think" for seg in segments)
    if has_comments:
        os.makedirs(os.path.join(output_dir, "comments"), exist_ok=True)
    for i, seg in enumerate(segments):
        voice = seg["voice"]
        voice_info = VOICES.get(voice, VOICES["Ding"])
        style = STYLES[i % len(STYLES)]

        # Use segment text as the scene narration
        scene_text = seg["text"]
        modified_text = style["tag"] + scene_text

        cache_key = hashlib.md5(
            (modified_text + str(seed) + str(width) + str(height) + str(voice) + 
             str(story_context.get("key_elements", "")) + style.get("camera", "medium")).encode()
        ).hexdigest()
        cached = cache.get(cache_key)

        if cached and os.path.exists(cached):
            print(f"  [{i+1}/{len(segments)}] CACHED -> {cached}")
            img = Image.open(cached).convert("RGB")
            scene_descs.append({})  # no _camera data for cached
        else:
            print(f"  [{i+1}/{len(segments)}] {voice} ({style['mood']}) [{style.get('camera','medium')}]...")
            scene_desc = _describe_scene(modified_text, story_context=story_context, voice=voice, camera=style.get("camera", "medium"))
            # Apply style overrides
            bg = scene_desc.get("bg", {})
            if style["bg_hint"] == "night":
                bg["colors"] = [[2, 2, 18], [8, 5, 25], [15, 10, 35]]
            elif style["bg_hint"] == "sunset":
                bg["colors"] = [[80, 40, 30], [180, 100, 60], [200, 160, 120]]
            elif style["bg_hint"] == "dawn":
                bg["colors"] = [[60, 50, 80], [120, 100, 140], [180, 170, 190]]
            elif style["bg_hint"] == "overcast":
                bg["colors"] = [[60, 60, 70], [80, 80, 90], [100, 100, 110]]
            elif style["bg_hint"] == "indoor":
                bg["colors"] = [[30, 25, 20], [50, 40, 35], [80, 70, 60]]
            scene_desc["mood"] = style["mood"]
            scene_desc["bg"] = bg
            scene_desc["camera"] = style.get("camera", "medium")
            
            # Add per-element rotation to some elements for variety
            elements = scene_desc.get("elements", [])
            cam_rng = random.Random(hash(modified_text) & 0xFFFFFFFF)
            for elem in elements:
                if cam_rng.random() < 0.3 and elem.get("type") not in ("circle", "text"):
                    elem["rotation"] = cam_rng.choice([-15, -10, -5, 5, 10, 15, 180])
                # Add subtle shadow to foreground elements
                if elem.get("z_order", 2) >= 2 and cam_rng.random() < 0.4:
                    elem["shadow"] = True

            gen = SketchGenerator(width, height, seed + i, hand_drawn=hand_drawn)
            # Per-segment sketch technique from visual treatment
            sketch_tech = scene_desc.get("_sketch", "pencil" if hand_drawn else "none")
            if isinstance(hand_drawn, str):
                sketch_tech = hand_drawn
            if sketch_tech != "none":
                gen.technique = SKETCH_TECHNIQUES.get(sketch_tech, SKETCH_TECHNIQUES["pencil"])
                gen.paper_color = tuple(gen.technique["paper_tint"])
            img = gen.render_scene(scene_desc)
            scene_descs.append(scene_desc)

        # Bake text into frame directly (reliable, no ffmpeg drawtext dependency)
        img = add_voice_overlay(img, seg["voice"], seg["text"], font_path, bake_text=True)

        out_path = os.path.join(output_dir, f"seg_{i+1:03d}.png")
        img.save(out_path)
        frames.append((out_path, seg))

        # Generate comment pop images for Think segments
        if seg["voice"] == "Think" and has_comments:
            _generate_comment_pop(seg["text"], voice_info, i, output_dir, width, height)

        print(f"    -> {out_path}")

    # Save manifest with camera/effects metadata
    manifest = {
        "total_segments": len(segments),
        "width": width,
        "height": height,
        "fps": 24,
        "segments": [
            {
                "frame": f"seg_{i+1:03d}.png",
                "voice": seg["voice"],
                "speaker": seg["speaker"],
                "text": seg["text"],
                "auto_inserted": seg.get("auto_inserted", False),
                "duration_frames": 5 * 24,
                "camera": STYLES[i % len(STYLES)].get("camera", "medium"),
                "mood": STYLES[i % len(STYLES)]["mood"],
                "_camera": scene_descs[i].get("_camera", {}) if i < len(scene_descs) else {},
            }
            for i, seg in enumerate(segments)
        ],
    }
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path}")
    print(f"Total: {len(segments)} segments -> {output_dir}/")

    return frames


def add_voice_overlay(img: Image.Image, voice_key: str, text: str,
                      font_path=None, bake_text=True) -> Image.Image:
    """Add subtitle bar with voice indicator, colored border, and character portrait.
    
    When bake_text=False, only draws the voice indicator bar + subtitle background
    without the text — ffmpeg drawtext handles animated subtitles instead.
    """
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    vstyle = VOICE_STYLES.get(voice_key, VOICE_STYLES["Ding"])
    voice_info = VOICES.get(voice_key, VOICES["Ding"])
    icon = voice_info["icon"]

    # Colored left border strip
    strip_w = int(w * 0.015)
    draw.rectangle([0, 0, strip_w, h], fill=vstyle["border"] + (180,))

    # Top voice indicator bar with character portrait
    bar_h = int(h * 0.055)
    draw.rectangle([0, 0, w, bar_h], fill=vstyle["bar_color"] + (200,))

    font = None
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, int(bar_h * 0.45))
        except Exception:
            pass

    # Character portrait thumbnail
    portrait = CHAR_PORTRAITS.get(voice_key)
    if portrait:
        thumb_size = int(bar_h * 0.8)
        thumb = portrait.resize((thumb_size, thumb_size), Image.LANCZOS)
        # Circular mask
        mask = Image.new("L", (thumb_size, thumb_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, thumb_size, thumb_size], fill=255)
        portrait_x = int(bar_h * 0.1)
        portrait_y = int(bar_h * 0.1)
        img.paste(thumb, (portrait_x, portrait_y), mask)
        label_x = portrait_x + thumb_size + int(bar_h * 0.2)
    else:
        label_x = 12

    # Voice name + role
    label = f"{icon} {voice_key} ({voice_info['role']})"
    draw.text((label_x, int(bar_h * 0.15)), label, fill=(255, 255, 255, 230), font=font)

    # Bottom subtitle bar background (always drawn for visual consistency)
    sub_h = int(h * 0.13)
    draw.rectangle([0, h - sub_h, w, h], fill=(0, 0, 0, 160))

    if not bake_text:
        return img

    # Split text into lines and draw
    max_chars = 55
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        for word in words:
            if not lines or len(lines[-1] + " " + word) > max_chars:
                lines.append(word)
            else:
                lines[-1] += " " + word
        lines.append("")
    lines = [l for l in lines if l]

    line_h = int(sub_h * 0.28)
    start_y = h - sub_h + (sub_h - len(lines) * line_h) // 2
    for j, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        draw.text((tx, start_y + j * line_h), line, fill=(255, 255, 255, 230), font=font)

    return img


def _generate_comment_pop(text: str, voice_info: dict, seg_idx: int,
                          output_dir: str, width: int, height: int):
    """Generate a speech-bubble overlay PNG for Think segment comments."""
    from PIL import Image, ImageDraw, ImageFont
    bubble_w, bubble_h = int(width * 0.6), int(height * 0.12)
    bubble = Image.new("RGBA", (bubble_w + 20, bubble_h + 30), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubble, "RGBA")
    bx, by = 10, 10
    color = voice_info.get("color", (255, 200, 60))
    # Rounded rectangle bubble
    draw.rounded_rectangle([bx, by, bx + bubble_w, by + bubble_h],
                           radius=12, fill=color + (220,), outline=(255, 255, 255, 60), width=2)
    # Tail triangle at bottom-left
    tail = [(bx + 20, by + bubble_h), (bx + 10, by + bubble_h + 18), (bx + 35, by + bubble_h)]
    draw.polygon(tail, fill=color + (220,))
    # Text
    short = text[:80].replace("\n", " ")
    font = None
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        pass
    # Word wrap inside bubble
    max_chars = 25
    lines = []
    for word in short.split():
        if not lines or len(lines[-1] + " " + word) > max_chars:
            lines.append(word)
        else:
            lines[-1] += " " + word
    line_h = 22
    text_y = by + (bubble_h - len(lines) * line_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = bx + (bubble_w - tw) // 2
        draw.text((tx, text_y), line, fill=(0, 0, 0, 220), font=font)
        text_y += line_h
    # Place at right-center of frame
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ox = width - bubble_w - 30
    oy = int(height * 0.35)
    overlay.paste(bubble, (ox, oy), bubble)
    out_path = os.path.join(output_dir, "comments", f"comment_{seg_idx+1:03d}.png")
    overlay.save(out_path)
    return out_path


def assemble_video(output_dir="output/mv_frames", output_video="output/mv_video.mp4"):
    manifest_path = os.path.join(output_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print("No manifest found. Run with --generate first.")
        return
    manifest = json.load(open(manifest_path))
    w, h = manifest["width"], manifest["height"]
    fps = manifest.get("fps", 24)
    w = manifest.get("width", 720)
    h = manifest.get("height", 1280)

    # Simple concat assembly — text is already baked into frames
    concat_path = os.path.join(output_dir, "concat.txt")
    segments = manifest["segments"]
    with open(concat_path, "w") as f:
        for i, seg in enumerate(segments):
            fp = os.path.join(output_dir, seg["frame"]).replace("\\", "/")
            duration = seg.get("duration_frames", 120) / fps
            f.write(f"file '{fp}'\n")
            f.write(f"duration {duration:.2f}\n")
        # Last file must be written again WITHOUT duration for concat demuxer
        last_fp = os.path.join(output_dir, segments[-1]["frame"]).replace("\\", "/")
        f.write(f"file '{last_fp}'\n")

    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        output_video
    ]

    print(f"Running: ffmpeg -y -f concat -safe 0 -i concat.txt -c:v libx264 ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Video saved: {output_video}")
    else:
        print(f"ffmpeg failed (code {result.returncode})")
        print(f"stderr: {result.stderr[:500]}")
        print("Try running the command manually with the concat.txt file.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-voice narration scene generator")
    parser.add_argument("--text", "-t", type=str, help="Narration script text")
    parser.add_argument("--file", "-f", type=str, help="Read script from file")
    parser.add_argument("--width", "-w", type=int, default=720)
    parser.add_argument("--height", "-H", type=int, default=1280)
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--output", "-o", type=str, default="output/mv_frames")
    parser.add_argument("--no-child", action="store_true",
                       help="Skip child interjections and acknowledgment")
    parser.add_argument("--child-density", type=float, default=0.4,
                       help="How often child questions appear (0-1)")
    parser.add_argument("--smart", action="store_true",
                       help="Smart mode: raw text without markers — engine figures out voices")
    parser.add_argument("--no-hand-drawn", action="store_true",
                       help="Disable hand-drawn sketch style (clean digital look)")
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--video", type=str, default="output/mv_video.mp4")
    args = parser.parse_args()

    if args.assemble:
        assemble_video(args.output, args.video)
        exit(0)

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = input("Paste your multi-voice script (Ctrl+Z then Enter to finish):\n")

    generate_multi_voice(
        script_text=text,
        width=args.width,
        height=args.height,
        seed=args.seed,
        output_dir=args.output,
        add_child=not args.no_child,
        child_density=args.child_density,
        smart=args.smart,
        hand_drawn=not args.no_hand_drawn,
    )
