"""
Dictionary sketch generator — creates a unique visual for every English word
that doesn't already have a dedicated draw method.
Each word gets a deterministic procedural sketch (hash-based polygon).
"""
import os, sys, json, re, hashlib, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw
from src.sketch_generator import SketchGenerator
from src.dynamic_scene import ELEMENT_DEFS
from src.concept_extractor import CONCEPTS

# Words already covered by existing concept→draw method mappings
COVERED_WORDS = set()
for concept in ELEMENT_DEFS:
    COVERED_WORDS.add(concept)
    COVERED_WORDS.add(concept.replace("_", " "))
for concept, keywords in CONCEPTS.items():
    for kw in keywords:
        COVERED_WORDS.add(kw.lower())
        if " " in kw:
            COVERED_WORDS.add(kw.replace(" ", "_"))

# Function words to skip (articles, prepositions, pronouns, conjunctions, etc.)
FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "so", "as", "at", "by", "for",
    "in", "of", "on", "to", "up", "with", "is", "was", "are", "were", "been",
    "be", "being", "have", "has", "had", "do", "does", "did", "it", "its",
    "this", "that", "these", "those", "i", "me", "my", "we", "our", "you",
    "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "not", "nor", "only", "own", "same", "than", "too", "very",
    "just", "also", "well", "now", "then", "here", "there", "from", "into",
    "over", "under", "down", "between", "through", "during", "before", "after",
    "above", "below", "about", "along", "among", "around", "behind", "beyond",
    "within", "without", "against", "around", "because", "until", "while",
    "am", "may", "might", "can", "could", "shall", "should", "will", "would",
    "must", "ought", "shall", "let", "get", "got", "say", "said", "see",
    "make", "made", "know", "think", "take", "come", "want", "use", "find",
    "give", "tell", "work", "call", "try", "ask", "need", "feel", "become",
    "leave", "put", "mean", "keep", "let", "begin", "seem", "help", "show",
    "hear", "play", "run", "move", "live", "believe", "hold", "bring",
    "happen", "write", "provide", "sit", "stand", "lose", "pay", "meet",
    "include", "continue", "set", "learn", "change", "lead", "understand",
    "watch", "follow", "stop", "create", "speak", "read", "allow", "add",
    "spend", "grow", "open", "walk", "win", "teach", "offer", "remember",
    "consider", "appear", "buy", "serve", "die", "send", "build", "stay",
    "fall", "cut", "reach", "kill", "remain", "suggest", "raise", "pass",
    "sell", "require", "report", "decide", "pull", "carry", "expect",
    "develop", "produce", "rest", "drive", "break", "receive", "agree",
    "support", "explain", "hope", "supply", "watch", "beat", "wait",
    "correct", "practice", "record", "design", "post", "cause", "effect",
    "result", "reason", "return", "answer", "start", "finish", "form",
    "increase", "decrease", "respect", "wonder", "question", "order",
    "demand", "supply", "struggle", "matter", "mind", "sense", "force",
    "spirit", "nature", "power", "value", "beauty", "truth", "strength",
    "view", "top", "back", "right", "left", "front", "side", "end",
    "way", "time", "year", "day", "week", "month", "hour", "minute",
    "second", "morning", "evening", "night", "today", "tomorrow",
    "kind", "sort", "type", "part", "piece", "hand", "head", "eye",
    "face", "body", "life", "death", "love", "hate", "fear", "joy",
    "hope", "peace", "war", "world", "earth", "ground", "land",
    "water", "air", "fire", "sun", "moon", "star", "sky", "sea",
    "city", "town", "home", "house", "room", "door", "window",
    "table", "chair", "bed", "book", "word", "letter", "name",
    "man", "woman", "child", "boy", "girl", "friend", "family",
    "father", "mother", "brother", "sister", "son", "daughter",
    "king", "queen", "lord", "lady", "god", "angel", "devil",
    "thing", "place", "point", "case", "group", "number", "level",
    "line", "lot", "set", "bit", "rate", "score", "test", "act",
    "age", "area", "band", "bar", "base", "bill", "bit", "block",
    "board", "bond", "box", "branch", "budget", "cap", "card",
    "care", "case", "cash", "cast", "cause", "cent", "chain",
    "chance", "change", "charge", "check", "claim", "class",
    "clean", "clear", "close", "club", "code", "college",
    "color", "column", "commission", "committee", "community",
    "company", "compare", "competition", "condition", "conference",
    "congress", "connection", "conservation", "conservative",
    "consideration", "constitution", "construction", "consumer",
    "contact", "contest", "context", "contract", "contribution",
    "control", "convention", "conversation", "conviction",
    "cooperation", "copy", "corner", "corporation", "correct",
    "cost", "county", "couple", "course", "court", "cousin",
    "cover", "crack", "craft", "crash", "cream", "creation",
    "creature", "credit", "crew", "crime", "crisis", "criterion",
    "criticism", "crop", "cross", "crowd", "cry", "culture",
    "cup", "current", "curve", "customer", "cycle", "daily",
    "damage", "dance", "danger", "data", "daughter", "dawn",
    "deal", "dear", "death", "debate", "debt", "decade",
    "decision", "declaration", "deep", "defense", "deficit",
    "definition", "degree", "delay", "delivery", "demand",
    "democracy", "demonstration", "department", "departure",
    "dependence", "deposit", "depression", "depth", "deputy",
    "description", "desert", "design", "designer", "desire",
    "desk", "despair", "destination", "destiny", "destruction",
    "detail", "detection", "development", "device", "devil",
    "diet", "difference", "difficulty", "dimension", "dinner",
    "direction", "director", "directory", "dirt", "disability",
    "disaster", "discipline", "discount", "discovery",
    "discrimination", "discussion", "disease", "disgust",
    "dish", "dismissal", "display", "dispute", "distance",
    "distinction", "distribution", "district", "disturbance",
    "diversity", "division", "doctor", "document", "dollar",
    "domain", "donation", "doubt", "draft", "drag", "drain",
    "drama", "drawing", "dream", "dress", "drink", "drive",
    "driver", "drop", "drug", "dry", "duration", "dust",
    "duty", "dynamics", "eagle", "ear", "earnings", "ease",
    "east", "edge", "edition", "editor", "education", "effect",
    "efficiency", "effort", "egg", "election", "element",
    "elite", "email", "emergence", "emergency", "emission",
    "emotion", "emphasis", "empire", "employee", "employer",
    "employment", "encounter", "encouragement", "enemy",
    "energy", "enforcement", "engagement", "engine", "engineer",
    "enterprise", "entertainment", "enthusiasm", "entrance",
    "entry", "environment", "episode", "equality", "equation",
    "equipment", "era", "error", "essay", "establishment",
    "estate", "estimate", "evaluation", "evening", "event",
    "evidence", "evil", "evolution", "examination", "example",
    "exchange", "excitement", "executive", "exercise",
    "exhibition", "existence", "expansion", "expedition",
    "expense", "experiment", "expert", "expertise", "explanation",
    "exploration", "explosion", "export", "exposure", "extension",
    "extent", "extreme", "fabric", "facility", "factor",
    "factory", "faculty", "failure", "faith", "fame", "familiar",
    "fan", "fantasy", "fare", "fashion", "fat", "fate",
    "father", "fault", "favor", "favorite", "fear", "feature",
    "federal", "fee", "feedback", "feeling", "female", "fence",
    "festival", "fiction", "field", "fifteen", "fighting",
    "figure", "file", "fill", "film", "final", "finance",
    "finding", "finger", "fire", "firm", "fish", "fishing",
    "fitness", "fix", "flag", "flame", "flash", "flat", "fleet",
    "flesh", "flight", "flood", "floor", "flow", "flower",
    "fluid", "focus", "folk", "food", "foot", "football",
    "force", "forecast", "foreign", "forest", "form", "format",
    "formation", "formula", "fortune", "forum", "foundation",
    "founder", "fraction", "frame", "framework", "freedom",
    "frequency", "friend", "friendship", "front", "fruit",
    "fuel", "fun", "function", "fund", "funding", "funeral",
    "furniture", "future", "gain", "galaxy", "gallery", "gap",
    "garage", "garden", "gas", "gate", "gathering", "gaze",
    "gear", "gene", "general", "generation", "genius", "genre",
    "gentleman", "gesture", "giant", "gift", "glance", "glass",
    "glimpse", "goal", "god", "gold", "golf", "good", "government",
}

OUTPUT_DIR = "output/elem_dict"


def generate_sketch(word: str, output_dir: str, seed_base=42):
    """Generate a unique procedural sketch for a word."""
    word_clean = re.sub(r'[^a-z0-9]', '_', word.lower())[:30]
    out_path = os.path.join(output_dir, f"elem_{word_clean}.png")
    if os.path.exists(out_path):
        return out_path

    # Create a seed from the word hash
    word_hash = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
    seed = seed_base + word_hash

    gen = SketchGenerator(128, 128, seed)
    gen.canvas = Image.new('RGB', (128, 128), (25, 25, 40))
    draw = ImageDraw.Draw(gen.canvas)

    # Element with the word as type — will hit procedural engine fallback
    elem = {"type": word.lower(), "x": 0.5, "y": 0.5, "scale": 3.0}
    gen._render_element(draw, elem)

    gen.canvas.save(out_path)
    return out_path


def generate_all(
    word_list_path="output/common_words.txt",
    max_words=2000,
    output_dir=OUTPUT_DIR,
    force=False,
):
    """Generate sketches for all uncovered words in the dictionary."""
    os.makedirs(output_dir, exist_ok=True)

    with open(word_list_path, "r") as f:
        words = [w.strip().lower() for w in f.readlines() if w.strip()]

    print(f"Loaded {len(words)} words")
    print(f"Words already covered by existing sketches: {len(COVERED_WORDS)}")

    # Filter to uncovered words that are concrete-looking (not function words)
    uncovered = [
        w for w in words
        if w not in COVERED_WORDS
        and w not in FUNCTION_WORDS
        and len(w) >= 4
        and re.match(r'^[a-z]+$', w)
    ]
    print(f"Uncovered: {len(uncovered)} (generating first {min(max_words, len(uncovered))})")

    manifest = {}
    count = 0
    errors = 0

    for word in uncovered[:max_words]:
        try:
            out_path = generate_sketch(word, output_dir)
            word_clean = re.sub(r'[^a-z0-9]', '_', word.lower())[:30]
            size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            manifest[word] = {"file": f"elem_{word_clean}.png", "size": size}
            count += 1
            if count % 200 == 0:
                print(f"  ... {count} done ({errors} errors)")
        except Exception as e:
            errors += 1
            if errors < 5:
                print(f"  ERROR: {word} -> {e}")

    # Save manifest
    manifest_path = os.path.join(output_dir, "dict_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone: {count} sketches generated, {errors} errors")
    print(f"Manifest: {manifest_path}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dictionary sketches for uncovered words")
    parser.add_argument("--words", type=str, default="output/common_words.txt",
                       help="Word list file (one per line)")
    parser.add_argument("--max", type=int, default=2000,
                       help="Maximum number of sketches to generate")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR,
                       help="Output directory")
    parser.add_argument("--force", action="store_true",
                       help="Regenerate even if file exists")
    args = parser.parse_args()

    generate_all(
        word_list_path=args.words,
        max_words=args.max,
        output_dir=args.output,
        force=args.force,
    )
