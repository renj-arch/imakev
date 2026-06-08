"""Brain — scene composer. Uses trained model to generate scenes from narration."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from src.brain.models import get_brain
from src.brain.dataset import record_scene
from src.rules_engine import apply_rules, feedback as rules_feedback
import re

# Camera presets (same as generate_cat_video.py)
CAM_LONG = {"x":0, "y":0, "w":1, "h":1}
CAM_MED = {"x":0.12, "y":0, "w":0.76, "h":1}
CAM_CU = {"x":0.32, "y":0.05, "w":0.36, "h":0.95}
CAM_ECU = {"x":0.4, "y":0.1, "w":0.2, "h":0.85}
CAM_HIGH = {"x":0, "y":0, "w":1, "h":0.65}
ZOOM_IN = {"type": "zoom_in"}
PAN_UP = {"type": "pan_up"}

MOOD_KEYWORDS = {
    "peaceful": ["peace","calm","quiet","gentle","slow","serene","tranquil","harmony","soft","warm"],
    "dramatic": ["war","battle","fought","anger","fierce","storm","chaos","destruction","crash","violent"],
    "hopeful": ["hope","future","dream","discover","new","beginning","rise","build","create","born"],
    "mysterious": ["mystery","unknown","strange","ancient","hidden","secret","shadow","dark","night"],
    "sad": ["sad","lost","alone","empty","grief","fall","collapse","die","death","abandon"],
    "playful": ["play","fun","joy","happy","love","cute","funny","smile","laugh","dance"],
}


def detect_mood(narration):
    """Detect mood from narration text based on keyword matching."""
    text = narration.lower()
    scores = {}
    for mood, words in MOOD_KEYWORDS.items():
        scores[mood] = sum(1 for w in words if w in text)
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "peaceful"


def detect_camera(narration, element_count):
    """Pick camera shot based on narration and element count."""
    text = narration.lower()
    if any(w in text for w in ["close","detail","small","tiny","face","eye","hand"]):
        return CAM_CU if element_count <= 3 else CAM_ECU if element_count <= 2 else CAM_MED
    if any(w in text for w in ["wide","vast","landscape","city","crowd","many","all","world"]):
        return CAM_LONG
    if element_count <= 2:
        return CAM_CU
    if element_count >= 5:
        return CAM_LONG
    return CAM_MED


def generate_scene(narration, mood=None, seed=None):
    """Generate a full scene composition from narration text using the trained brain."""
    if mood is None:
        mood = detect_mood(narration)

    brain = get_brain()
    elements = brain.predict_elements(narration, mood=mood)

    if not elements:
        # Fallback: basic scene
        elements = [
            {"type": "sun", "x": 0.88, "y": 0.12, "scale": 3.0},
            {"type": "cloud", "x": 0.3, "y": 0.18, "scale": 2.5},
            {"type": "tree", "x": 0.2, "y": 0.78, "scale": 3.0},
            {"type": "tree", "x": 0.8, "y": 0.78, "scale": 3.0},
        ]

    # Strip internal fields
    clean = []
    for e in elements:
        clean.append({
            "type": e["type"],
            "x": e.get("x", 0.5),
            "y": e.get("y", 0.7),
            "scale": e.get("scale", 2.5),
        })
    elements = clean

    # Apply rules engine constraints
    elements = apply_rules([dict(e) for e in elements])

    camera = detect_camera(narration, len(elements))
    duration = 3.0 if len(elements) <= 3 else 3.5

    # Record this generation as a training example
    record_scene(narration, elements, mood=mood, source="brain_generated")

    # Determine background colors from mood
    if mood == "dramatic":
        colors = [[100,90,80],[140,120,100]]
        ground = [100,70,50]
    elif mood == "sad":
        colors = [[150,170,190],[170,190,210]]
        ground = [80,100,80]
    elif mood == "hopeful":
        colors = [[180,200,230],[140,180,220]]
        ground = [60,130,60]
    elif mood == "playful":
        colors = [[200,220,240],[180,200,220]]
        ground = [80,160,80]
    elif mood == "mysterious":
        colors = [[80,70,90],[50,40,60]]
        ground = [40,35,40]
    else:
        colors = [[140,180,220],[100,160,200]]
        ground = [60,130,60]

    scene = {
        "narration": narration,
        "mood": mood,
        "duration": duration,
        "camera": camera,
        "elements": elements,
        "bg": {"colors": colors, "ground": ground, "horizon": 0.55},
    }
    return scene


def process_feedback(text, element_type=None):
    """Give feedback to both rules engine and brain model."""
    action = rules_feedback(text, element_type)
    if action and element_type:
        brain = get_brain()
        if "scale_max" in action.lower() or "reduced" in action.lower():
            import re
            m = re.search(r'[\d.]+', action)
            if m:
                brain.learn_from_feedback(element_type, {"scale_max": float(m.group())})
        if "y" in action.lower():
            brain.learn_from_feedback(element_type, {"y_min": 0.05})
    return action
