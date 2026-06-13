"""Narrative-to-multi-scene pipeline — splits narration into composed scenes with camera directives."""
import re, random
from src.creative_composer import compose_creative_scene
from src.concept_extractor import extract_concepts, detect_mood

SHOT_KEYWORDS = {
    "wide":   ["came", "arrived", "then", "in the", "there was", "this is", "once",
               "far away", "distant", "landscape", "vast", "wide", "panorama"],
    "closeup":["eyes", "face", "expression", "look", "stare", "gaze", "whisper",
               "whispered", "silent", "quiet", "noticed", "saw", "watched"],
    "action": ["pounce", "jump", "run", "chase", "catch", "attack", "strike",
               "pounced", "jumped", "ran", "chased", "caught", "attacked"],
    "medium": [],  # default
}

NIGHT_KEYWORDS = ["night", "dark", "moon", "shadow", "evening", "dusk", "starlight",
                   "torch", "firelight", "campfire", "feast", "dinner", "settlement"]


def detect_shot_type(text: str) -> str:
    """Determine the best camera shot type for a sentence."""
    tl = text.lower()
    for shot_type, keywords in SHOT_KEYWORDS.items():
        for kw in keywords:
            if kw in tl:
                return shot_type
    return "medium"


def detect_is_night(text: str, mood: str) -> bool:
    """Check if scene should be night/dark themed."""
    tl = text.lower()
    for kw in NIGHT_KEYWORDS:
        if kw in tl:
            return True
    if mood in ("mysterious", "cautious", "sneaky"):
        return True
    return False


def narration_to_scenes(narration_text: str, rng: random.Random = None) -> list[dict]:
    """Split narration into individual scenes with camera directives.
    
    Returns a list of scene dicts ready for rendering.
    """
    if rng is None:
        rng = random.Random()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', narration_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    scenes = []
    for i, sentence in enumerate(sentences):
        is_last = (i == len(sentences) - 1)

        scene = compose_creative_scene(sentence, rng)
        if not scene:
            continue

        # Detect shot type
        shot = detect_shot_type(sentence)

        # Detect mood (already set by composer, but may need override)
        mood = scene.get("mood") or detect_mood(sentence)
        if not mood:
            mood = "neutral"
        scene["mood"] = mood

        # Night detection
        is_night = detect_is_night(sentence, mood)
        scene["is_night"] = is_night

        # Camera directive
        camera_zoom = 1.0
        if shot == "closeup":
            camera_zoom = 1.8
        elif shot == "action":
            camera_zoom = 1.3
        elif shot == "wide":
            camera_zoom = 0.8

        scene["camera"] = {
            "shot": shot,
            "zoom": camera_zoom,
            "zoom_target": [0.5, 0.4],  # center, upper-third
        }

        scene["narration"] = sentence
        scenes.append(scene)

    return scenes
