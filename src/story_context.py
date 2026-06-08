"""Story Context Analyzer — extracts the big picture from a full script.
Analyzes the entire story to determine theme, key elements, and setting,
so per-segment rendering stays coherent and relevant.
"""
import re
from collections import Counter
from src.concept_extractor import extract_concepts, detect_bg_type, infer_scene_type


# Words that should NEVER produce literal visual elements (metaphorical/abstract)
METAPHOR_WORDS = {
    "see", "saw", "seen", "look", "looks", "looking", "watch", "watched",
    "moment", "moments", "time", "thought", "thoughts", "heavy", "strange",
    "unsettling", "wonder", "curious", "curiosity", "imagine", "imagination",
    "remember", "memory", "memories", "history", "story", "stories",
    "believe", "feeling", "feel", "felt", "hope", "hopes", "hoping",
    "know", "knows", "known", "understand", "understood",
    "end", "ending", "begin", "beginning", "start", "started",
    "change", "changed", "changing", "world", "life", "death",
    "page", "chapter", "part", "piece", "thing", "everything",
    "nothing", "something", "anyone", "someone", "nobody",
}


def filter_literal_concepts(concepts: dict, text: str) -> dict:
    """Remove concepts triggered by metaphorical/abstract word usage."""
    tl = text.lower()
    filtered = {}
    for concept, count in concepts.items():
        # Check if ALL keyword matches for this concept are metaphorical
        keywords = _get_concept_keywords(concept)
        literal_matches = 0
        for kw in keywords:
            if " " in kw:
                if kw in tl and kw.split()[0] not in METAPHOR_WORDS:
                    literal_matches += 1
            else:
                if re.search(r'\b' + re.escape(kw) + r'\b', tl):
                    if kw not in METAPHOR_WORDS:
                        literal_matches += 1
        if literal_matches > 0:
            filtered[concept] = count
    return filtered


# Cache for concept keywords (lazy-loaded from concept_extractor)
_CONCEPT_KEYWORDS_CACHE = None


def _get_concept_keywords(concept_name: str) -> list:
    global _CONCEPT_KEYWORDS_CACHE
    if _CONCEPT_KEYWORDS_CACHE is None:
        from src.concept_extractor import CONCEPTS
        _CONCEPT_KEYWORDS_CACHE = CONCEPTS
    return _CONCEPT_KEYWORDS_CACHE.get(concept_name, [])


def analyze_story(segments: list) -> dict:
    """Analyze full story to extract context for scene generation.
    
    Returns:
        Dict with theme, key_elements, bg_type, mood_arc, narrator
    """
    full_text = " ".join(
        s["text"] for s in segments 
        if isinstance(s, dict) and "text" in s
    )
    
    # Extract all concepts from full story
    raw_concepts = extract_concepts(full_text)
    concepts = filter_literal_concepts(raw_concepts, full_text)
    
    # Top 5 key elements (the story's main subjects)
    sorted_concepts = sorted(concepts.items(), key=lambda x: -x[1])
    key_elements = [c for c, _ in sorted_concepts[:7]]
    
    # Theme
    theme = infer_scene_type(concepts)
    
    # Background type
    bg_type = detect_bg_type(concepts)
    
    # Detect if story has strong concrete subjects
    has_concrete_subject = bool(key_elements) and any(
        c not in ("human", "crown", "book", "clock", "question", "infinity")
        for c in key_elements
    )
    
    return {
        "theme": theme,
        "key_elements": key_elements,
        "all_concepts": concepts,
        "bg_type": bg_type,
        "has_concrete_subject": has_concrete_subject,
        "full_text": full_text,
    }


def get_segment_concepts(segment_text: str, story_context: dict) -> dict:
    """Get concepts for a specific segment, filtered by story context.
    
    Only returns concepts that are:
    1. Relevant to the segment's text (literal, not metaphorical)
    2. Among the story's key themes (or strongly present in this segment)
    """
    raw = extract_concepts(segment_text)
    literal = filter_literal_concepts(raw, segment_text)
    
    key = story_context["key_elements"]
    
    # If segment has zero literal concepts matching story themes,
    # use the top story elements instead
    relevant = {c: v for c, v in literal.items() if c in key}
    
    if not relevant and story_context["has_concrete_subject"]:
        return {c: 1 for c in key[:3]}
    
    if not relevant:
        return literal
    
    return relevant
