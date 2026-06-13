"""AI Director Module — turns sentences into cinematic visual beats.

Sits between narration and scene rendering. Instead of one scene per
sentence, the Director breaks each sentence into 3-8 micro-beats with
varied camera shots, character animations, tension-driven pacing, and
cinematic transitions.

Architecture:

  Sentence
    ↓
  Director.direct()
    ↓
  list[DirectorialBeat]  ← each beat is a "shot" in the scene
    ↓
  Director.beat_to_scene()
    ↓
  renderable scene dicts → animator → video
"""

import random, re, math
from dataclasses import dataclass, field, asdict
from typing import Optional

from src.concept_extractor import extract_concepts, detect_mood
from src.creative_composer import compose_creative_scene
from src.dynamic_scene import ELEMENT_DEFS


# ── Tension keyword maps ──

TENSION_HIGH: dict[str, dict] = {
    "suddenly":   {"boost": 3, "transition": "cut", "shake": 0.4},
    "danger":     {"boost": 4, "lighting": "shadow", "mood": "cautious", "shake": 0.2},
    "attack":     {"boost": 5, "transition": "cut", "animation": "run", "shake": 0.6, "camera": "handheld"},
    "pounce":     {"boost": 4, "transition": "cut", "animation": "run", "shake": 0.5},
    "chase":      {"boost": 4, "transition": "cut", "animation": "run", "camera": "pan_left"},
    "scream":     {"boost": 4, "transition": "cut", "mood": "surprised"},
    "storm":      {"boost": 3, "lighting": "dark", "shake": 0.4, "mood": "cautious"},
    "hunter":     {"boost": 3, "mood": "focused", "lighting": "shadow"},
    "fire":       {"boost": 2, "lighting": "firelight", "mood": "cautious"},
    "death":      {"boost": 4, "mood": "sad", "color_grade": "desaturated"},
    "explode":    {"boost": 5, "shake": 0.8, "camera": "handheld", "transition": "cut"},
    "crash":      {"boost": 4, "shake": 0.6, "transition": "cut"},
    "war":        {"boost": 4, "lighting": "dark", "mood": "angry"},
    "fight":      {"boost": 3, "camera": "handheld", "animation": "run"},
    "escape":     {"boost": 3, "animation": "run", "mood": "triumphant", "transition": "cut"},
    "dark":       {"boost": 1, "lighting": "shadow", "mood": "mysterious"},
    "shadow":     {"boost": 1, "lighting": "shadow", "mood": "mysterious"},
    "hunt":       {"boost": 3, "mood": "focused", "lighting": "shadow"},
    "trap":       {"boost": 3, "mood": "cautious", "camera": "closeup"},
    "ambush":     {"boost": 4, "mood": "sneaky", "camera": "silhouette", "transition": "cut"},
    "claw":       {"boost": 2, "animation": "swipe", "transition": "cut"},
    "snap":       {"boost": 2, "animation": "bite", "transition": "cut"},
    "growl":      {"boost": 2, "mood": "angry", "camera": "closeup"},
    "howl":       {"boost": 2, "mood": "sad", "camera": "wide"},
    "sneak":      {"boost": 1, "mood": "sneaky", "animation": "crouch"},
    "creep":      {"boost": 1, "mood": "sneaky", "animation": "crouch"},
}

TENSION_CALM: dict[str, dict] = {
    "rest":      {"mood": "tired", "animation": "sleep"},
    "sleep":     {"mood": "tired", "animation": "sleep", "camera": "closeup"},
    "play":      {"mood": "happy", "animation": "bounce"},
    "eat":       {"animation": "eat", "camera": "closeup"},
    "drink":     {"camera": "closeup", "animation": "eat"},
    "laugh":     {"mood": "happy", "camera": "closeup"},
    "smile":     {"mood": "happy"},
    "dance":     {"animation": "bounce", "mood": "happy"},
    "sing":      {"animation": "talk", "camera": "closeup"},
    "wait":      {"animation": "freeze", "camera": "slow_zoom", "visual_goal": "build suspense"},
    "watch":     {"camera": "closeup", "focus": "eyes", "animation": "freeze"},
    "stare":     {"camera": "extreme_closeup", "focus": "eyes", "animation": "freeze"},
    "listen":    {"camera": "closeup", "animation": "freeze", "focus": "ears"},
    "think":     {"camera": "closeup", "animation": "freeze", "visual_goal": "show reflection"},
    "walk":      {"animation": "walk", "camera": "medium"},
    "run":       {"animation": "run", "camera": "pan_left"},
    "jump":      {"animation": "pounce", "camera": "action"},
    "climb":     {"animation": "walk", "camera": "low_angle"},
    "crouch":    {"animation": "crouch", "mood": "sneaky"},
    "hide":      {"mood": "cautious", "animation": "freeze", "lighting": "shadow"},
    "notice":    {"camera": "closeup", "focus": "eyes", "animation": "freeze_then_step", "visual_goal": "discovery"},
    "realize":   {"camera": "closeup", "focus": "eyes", "visual_goal": "realization"},
    "approach":  {"animation": "walk", "camera": "dolly_in"},
    "retreat":   {"animation": "walk", "camera": "dolly_out", "direction": "backward"},
    "celebrate": {"mood": "triumphant", "animation": "bounce"},
    "victory":   {"mood": "triumphant", "animation": "proud_pose", "camera": "low_angle"},
}


# ── Shot type definitions ──

SHOT_DEFS: dict[str, dict] = {
    "extreme_wide":   {"zoom": 0.4, "desc": "Extreme wide - tiny subject in vast landscape"},
    "wide":           {"zoom": 0.7, "desc": "Wide shot - subject visible in environment"},
    "medium":         {"zoom": 1.0, "desc": "Medium shot - subject fills half the frame"},
    "medium_closeup": {"zoom": 1.3, "desc": "Medium close-up - subject from chest up"},
    "closeup":        {"zoom": 1.8, "desc": "Close-up - face fills frame"},
    "extreme_closeup": {"zoom": 2.5, "desc": "Extreme close-up - eyes or detail only"},
    "over_shoulder":  {"zoom": 1.4, "desc": "Over-the-shoulder - behind character looking at subject", "x_offset": 0.15},
    "top_down":       {"zoom": 0.9, "desc": "Top-down - bird's eye view", "y_base": 0.3},
    "silhouette":     {"zoom": 0.8, "desc": "Silhouette - character against bright background", "lighting": "silhouette"},
    "POV":            {"zoom": 1.1, "desc": "Point of view - through character's eyes"},
    "low_angle":      {"zoom": 1.0, "desc": "Low angle - looking up at subject", "y_base": 0.55},
    "high_angle":     {"zoom": 1.0, "desc": "High angle - looking down at subject", "y_base": 0.25},
    "dutch":          {"zoom": 1.2, "desc": "Dutch angle - tilted frame for unease", "shake": 0.1},
    "handheld":       {"zoom": 1.3, "desc": "Handheld - unstable camera for action", "shake": 0.3},
}

SHOT_TRANSITIONS: dict[str, str] = {
    "cut": "Hard cut - instant scene change",
    "dissolve": "Soft dissolve - 0.3s crossfade",
    "fade_in": "Fade from black",
    "fade_out": "Fade to black",
    "wipe_left": "Wipe left",
    "wipe_right": "Wipe right",
    "slide_left": "Slide left - scene pushes previous off",
    "slide_right": "Slide right",
}

ANIMATION_DEFS: dict[str, str] = {
    "idle": "Gentle sway, occasional blink",
    "blink": "Eye closure only",
    "walk": "Walk cycle with leg swing + vertical bounce",
    "run": "Fast walk cycle, more bounce",
    "freeze": "Complete stillness, no movement",
    "freeze_then_step": "Hold still, then one slow step forward",
    "turn_head": "Head rotates left or right",
    "look_left": "Eyes + head shift left, hold 2s",
    "look_right": "Eyes + head shift right, hold 2s",
    "crouch": "Lower body position, tense",
    "pounce": "Gather hind legs, spring forward",
    "swipe": "Front paw sweeps in arc",
    "bite": "Head lunges forward, mouth opens",
    "eat": "Head bobs down and up",
    "sleep": "Body still, gentle breathing",
    "bounce": "Up-down bobbing",
    "talk": "Mouth opens/closes rhythmically",
    "nod": "Head tilts down then up (yes)",
    "shake": "Head shakes side to side (no)",
    "point": "One front paw extends forward",
    "proud_pose": "Chest out, chin lifted, holds posture",
    "tail_swish": "Tail sweeps side to side",
    "ear_twitch": "Ears flick forward and back",
}

LIGHTING_DEFS: dict[str, dict] = {
    "day":        {"colors": [[200, 210, 230], [140, 160, 200]], "ground_color": [60, 90, 50]},
    "night":      {"colors": [[5, 3, 20], [15, 10, 40]], "ground_color": [15, 20, 30]},
    "dawn":       {"colors": [[240, 180, 120], [200, 140, 100]], "ground_color": [80, 70, 50]},
    "dusk":       {"colors": [[220, 120, 80], [160, 80, 60]], "ground_color": [60, 40, 30]},
    "firelight":  {"colors": [[220, 140, 60], [180, 80, 30]], "ground_color": [80, 50, 20]},
    "moonlight":  {"colors": [[60, 70, 100], [20, 30, 60]], "ground_color": [25, 30, 45]},
    "shadow":     {"colors": [[20, 18, 25], [10, 8, 15]], "ground_color": [12, 10, 18]},
    "silhouette": {"colors": [[180, 140, 80], [255, 180, 60]], "ground_color": [40, 30, 15]},
    "dark":       {"colors": [[8, 5, 18], [3, 2, 10]], "ground_color": [5, 4, 8]},
}


@dataclass
class DirectorialBeat:
    """A single visual beat (shot) in the narrative."""
    narrative_beat: str = ""
    visual_goal: str = "establish scene"
    camera: str = "medium"
    focus: str = "scene"
    animation: str = "idle"
    duration: float = 2.0
    characters: list[str] = field(default_factory=list)
    props: list[str] = field(default_factory=list)
    bg_type: str = "gradient"
    lighting: str = "day"
    tension_level: int = 0
    transition: str = "dissolve"
    camera_movement: str = "static"
    mood: str = "neutral"
    shake: float = 0.0
    color_grade: str = "normal"
    vignette: bool = False
    depth_of_field: str = "none"
    narration_excerpt: str = ""
    visual_directives: dict = field(default_factory=dict)
    narrative_phase: str = ""


class Director:
    """AI Director — converts a sentence or narrative into a sequence of cinematic shots."""

    def __init__(self, rng: random.Random = None, narrative_engine: Optional['NarrativeEngine'] = None):
        self.rng = rng or random.Random()
        self.narrative_engine = narrative_engine

    # ── Narrative-level direction (archetype-aware) ──

    def direct_from_narrative(self, narration_text: str) -> list[list[DirectorialBeat]]:
        """Direct an entire narrative using archetype detection.

        Returns list of beat sequences (one sequence per sentence group,
        same structure as direct_narration_to_beats).
        """
        from src.narrative_engines import NarrativeEngine
        engine = self.narrative_engine or NarrativeEngine(self.rng)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', narration_text.strip()) if s.strip()]
        full_text = narration_text

        archetype_probs = engine.detect_archetype_probs(full_text)
        archetype_beats = engine.structure_narrative(
            sentences, full_text=full_text, archetype_probs=archetype_probs
        )
        archetype = max(archetype_probs, key=archetype_probs.get)
        reveal_strategy = engine.get_reveal_strategy(archetype)

        # Group archetype beats by sentence for per-sentence sequences
        sentence_groups: list[list[ArchetypeBeat]] = [[]]
        for ab in archetype_beats:
            if len(sentence_groups[-1]) >= 1 and ab.beat_index > 0:
                pass  # continue same group
            # Map each archetype beat separately — each becomes a DirectorialBeat
            # But we want one Director beat per archetype beat, grouped by sentence
            if len(sentence_groups[-1]) < 1:
                sentence_groups[-1].append(ab)
            else:
                sentence_groups.append([ab])

        # Actually, each archetype beat already maps to one sentence.
        # Group them so each sentence's beats go together.
        sentence_groups = [[] for _ in sentences]
        for ab in archetype_beats:
            si = ab.beat_index
            sentence_groups[si].append(ab)

        char_types = {"cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
                      "monkey", "horse", "elephant", "mouse", "rat", "lion", "tiger",
                      "bird", "deer", "cow", "dinosaur", "dragon", "animal",
                      "wildcat", "wildcats"}

        result_sequences = []
        for sentence_idx, (sentence, group) in enumerate(zip(sentences, sentence_groups)):
            concepts = extract_concepts(sentence)
            mood = detect_mood(sentence)
            chars = [c for c in concepts if c in char_types]
            props = [c for c in concepts if c not in char_types and c != "none"]

            beat_seq: list[DirectorialBeat] = []
            for ab in group:
                db = DirectorialBeat(
                    narrative_beat=ab.goal,
                    visual_goal=ab.goal,
                    camera=ab.suggested_camera,
                    focus="character" if chars else "scene",
                    animation=ab.suggested_animation,
                    duration=max(1.0, 3.0 - ab.tension * 0.15),
                    characters=chars[:2],
                    props=props[:2],
                    lighting=ab.suggested_lighting,
                    tension_level=ab.tension,
                    transition="dissolve",
                    mood=ab.suggested_mood,
                    narration_excerpt=sentence,
                    narrative_phase=ab.phase,
                )
                beat_seq.append(db)

            # Run enrichment passes
            beat_seq = self._assign_animations(beat_seq, max(ab.tension for ab in group) if group else 5, mood)
            beat_seq = self._assign_transitions(beat_seq, sentence_idx, len(sentences))
            beat_seq = self._apply_motif_overrides(beat_seq, chars)
            beat_seq = self._fill_details(beat_seq, concepts)

            result_sequences.append(beat_seq)

        # ── Emotion Tracker pass ──
        story_state = None
        try:
            from src.emotion_tracker import EmotionTracker
            et = EmotionTracker(self.rng)
            story_state = et.initialize_state(narration_text)
            for i, (sentence, group) in enumerate(zip(sentences, sentence_groups)):
                concepts_for_char = extract_concepts(sentence)
                chars = [c for c in concepts_for_char if c in char_types]
                et.process_sentence(story_state, sentence, i,
                                    all_chars_in_sentence=chars)
        except ImportError:
            pass

        # ── Relationship Tracker pass ──
        rt = None
        try:
            from src.relationship_tracker import RelationshipTracker
            rt = RelationshipTracker(self.rng)
            if story_state is not None:
                for i, (sentence, group) in enumerate(zip(sentences, sentence_groups)):
                    concepts_for_char = extract_concepts(sentence)
                    chars = [c for c in concepts_for_char if c in char_types]
                    rt.process_sentence(story_state, sentence, i,
                                        chars_in_sentence=chars)
        except ImportError:
            pass

        # ── Concept-to-Visual translation pass ──
        try:
            from src.concept_visuals import ConceptVisualsTranslator
            cvt = ConceptVisualsTranslator(self.rng)
            # Collect unique phases from all beats
            all_phases: list[str] = []
            for seq in result_sequences:
                for beat in seq:
                    if beat.narrative_phase and beat.narrative_phase not in all_phases:
                        all_phases.append(beat.narrative_phase)
            phase_concept_map = cvt.get_phase_concepts(
                narration_text, archetype, all_phases, len(all_phases)
            )
            phase_to_concepts = dict(zip(all_phases, phase_concept_map)) if len(all_phases) == len(phase_concept_map) else {}
            for seq_idx, seq in enumerate(result_sequences):
                for beat in seq:
                    # Per-sentence concept detection (with intensities)
                    raw = cvt.detect_concepts(beat.narration_excerpt)
                    # Build intensity dict from all sources
                    concept_intensities: dict[str, float] = {}
                    for c, v in raw.items():
                        if v > 0.2:
                            concept_intensities[c] = v
                    # Blend with phase-level affinities (moderate weight)
                    if beat.narrative_phase in phase_to_concepts:
                        for pc in phase_to_concepts[beat.narrative_phase]:
                            existing = concept_intensities.get(pc, 0.0)
                            concept_intensities[pc] = max(existing, 0.35)
                    # Inject emotion-derived concepts from StoryState
                    if story_state is not None:
                        char_emotions = et.get_dominant_emotions(story_state, seq_idx)
                        for ch_key, emo_dict in char_emotions.items():
                            for dim, intensity in emo_dict.items():
                                if intensity > 0.3:
                                    existing = concept_intensities.get(dim, 0.0)
                                    concept_intensities[dim] = max(existing, intensity * 0.5)
                        # Inject relationship-derived concepts (lower weight)
                        if rt is not None:
                            rel_concepts = rt.get_relationship_concepts(story_state, beat.characters)
                            for rc in rel_concepts:
                                existing = concept_intensities.get(rc, 0.0)
                                concept_intensities[rc] = max(existing, 0.4)
                    directives = cvt.concepts_to_directives_weighted(concept_intensities)
                    # Compute symbolic elements from resolved concepts
                    active_names = list(concept_intensities.keys())
                    symbolic = cvt.get_symbolic_elements(active_names)
                    directives["symbolic_atmosphere"] = symbolic.get("atmosphere")
                    directives["symbolic_ground"] = symbolic.get("ground_elements", [])
                    beat.visual_directives = directives
        except ImportError:
            pass

        return result_sequences

    # ── Per-sentence direction ──

    def direct(self, sentence: str, scene_idx: int = 0,
               total_scenes: int = 1, previous_beats: list[DirectorialBeat] = None) -> list[DirectorialBeat]:
        """Direct a sentence into multiple visual beats.

        This is the main entry point. Returns 3-8 beats per sentence.
        """
        tl = sentence.lower()
        tension = self._detect_tension(tl)
        concepts = extract_concepts(sentence)
        mood = detect_mood(sentence)

        # 1. Break sentence into narrative beats
        beats = self._break_into_beats(sentence, concepts, mood, tension)

        # 2. Plan shots (camera types)
        beats = self._plan_shots(beats, tension, scene_idx, total_scenes)

        # 3. Assign animations
        beats = self._assign_animations(beats, tension, mood)

        # 4. Assign lighting
        beats = self._assign_lighting(beats, tension, mood, concepts)

        # 5. Assign transitions
        beats = self._assign_transitions(beats, scene_idx, total_scenes)

        # 6. Fill details
        beats = self._fill_details(beats, concepts)

        return beats

    # ── Tension detection ──

    def _detect_tension(self, tl: str) -> int:
        """Score tension level 0-10 from keywords."""
        score = 0
        for word, effects in TENSION_HIGH.items():
            if word in tl:
                score += effects.get("boost", 2)
        for word in ["silent", "quiet", "calm", "peaceful", "gentle", "soft", "slow"]:
            if word in tl:
                score = max(0, score - 1)
        return min(10, score)

    # ── Micro-beat engine ──

    def _break_into_beats(self, sentence: str, concepts: dict,
                          mood: str, tension: int) -> list[DirectorialBeat]:
        """Break a sentence into sequential narrative beats."""
        tl = sentence.lower()
        beats: list[DirectorialBeat] = []

        # Primary characters from concepts
        char_types = {"cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
                      "monkey", "horse", "elephant", "mouse", "rat", "lion", "tiger",
                      "bird", "deer", "cow", "dinosaur", "dragon", "animal",
                      "wildcat", "wildcats"}
        chars = [c for c in concepts if c in char_types]
        props = [c for c in concepts if c not in char_types and c != "none"]

        # Handle specific high-tension trigger words
        has_sudden = any(w in tl for w in ["suddenly", "all at once", "in an instant"])

        # Build beats from sentence structure:

        # Beat 1: Establishing shot (always)
        beats.append(DirectorialBeat(
            narrative_beat=f"Establish the scene",
            visual_goal="establish location",
            camera="extreme_wide" if tension < 3 else "wide",
            characters=chars[:1],
            props=[],
            mood="neutral",
            animation="freeze",
            narration_excerpt=sentence,
        ))

        # Look for specific action/event words that generate extra beats
        action_revealed = False

        # Process calm keywords
        for word, ef in TENSION_CALM.items():
            if word in tl:
                # Add a close-up or detail beat before the action
                if not action_revealed:
                    focus_map = {"wait": "eyes", "watch": "eyes", "notice": "target",
                                 "listen": "ears", "stare": "eyes"}
                    beats.append(DirectorialBeat(
                        narrative_beat=f"Focus on character {word}ing",
                        visual_goal=ef.get("visual_goal", f"show character {word}ing"),
                        camera=ef.get("camera", "closeup"),
                        focus=focus_map.get(word, "character"),
                        animation=ef.get("animation", "freeze"),
                        mood=ef.get("mood", mood or "neutral"),
                        narration_excerpt=sentence,
                    ))
                    action_revealed = True

                # Then show the action itself
                action_beats = {
                    "notice": DirectorialBeat(
                        narrative_beat="Eyes lock onto target",
                        visual_goal="discovery",
                        camera="extreme_closeup",
                        focus="eyes",
                        animation="freeze",
                        mood="focused",
                        duration=1.5,
                        narration_excerpt=sentence,
                    ),
                    "wait": DirectorialBeat(
                        narrative_beat="Time passes in silence",
                        visual_goal="build suspense",
                        camera="wide",
                        focus="character",
                        animation="freeze",
                        mood="cautious",
                        duration=2.0,
                        narration_excerpt=sentence,
                    ),
                    "walk": DirectorialBeat(
                        narrative_beat="Character moves forward",
                        visual_goal="show movement",
                        camera="medium",
                        focus="character",
                        animation="walk",
                        mood="focused",
                        duration=2.0,
                        narration_excerpt=sentence,
                    ),
                    "run": DirectorialBeat(
                        narrative_beat="Character breaks into a run",
                        visual_goal="show urgency",
                        camera="handheld",
                        focus="character",
                        animation="run",
                        shake=0.3,
                        duration=1.5,
                        narration_excerpt=sentence,
                    ),
                    "crouch": DirectorialBeat(
                        narrative_beat="Character lowers to the ground",
                        visual_goal="show stealth",
                        camera="closeup",
                        focus="character",
                        animation="crouch",
                        mood="sneaky",
                        duration=1.5,
                        narration_excerpt=sentence,
                    ),
                    "eat": DirectorialBeat(
                        narrative_beat="Character eats",
                        visual_goal="show consumption",
                        camera="closeup",
                        focus="mouth",
                        animation="eat",
                        duration=2.0,
                        narration_excerpt=sentence,
                    ),
                    "sleep": DirectorialBeat(
                        narrative_beat="Character rests",
                        visual_goal="show peace",
                        camera="closeup",
                        focus="face",
                        animation="sleep",
                        mood="tired",
                        duration=2.0,
                        narration_excerpt=sentence,
                    ),
                    "jump": DirectorialBeat(
                        narrative_beat="Character springs into the air",
                        visual_goal="show agility",
                        camera="action",
                        focus="character",
                        animation="pounce",
                        duration=1.0,
                        narration_excerpt=sentence,
                    ),
                }
                for action_word, beat in action_beats.items():
                    if action_word in tl and (word == action_word or
                                              (action_word in tl and word != action_word)):
                        if beat not in beats:  # avoid duplicates
                            beats.append(beat)
                        break
                break

        # High-tension beats
        if tension >= 5:
            shake_level = 0.3
            for word, ef in TENSION_HIGH.items():
                if word in tl:
                    shake_level = max(shake_level, ef.get("shake", 0))
                    if ef.get("animation") == "run":
                        beats.append(DirectorialBeat(
                            narrative_beat=f"Chaos erupts - {word}!",
                            visual_goal="shock",
                            camera=ef.get("camera", "handheld"),
                            focus="action",
                            animation="run",
                            shake=max(shake_level, 0.4),
                            duration=1.0,
                            mood=ef.get("mood", "surprised"),
                            narration_excerpt=sentence,
                            transition="cut",
                        ))
                    break

        # Fallback: if no action keyword matched, still add rich beats
        if len(beats) == 1 and chars:
            # We only have establishing shot, add more
            beats.append(DirectorialBeat(
                narrative_beat=f"Show {chars[0]} - full body",
                visual_goal="introduce character",
                camera="wide",
                focus=chars[0],
                animation="idle",
                characters=chars[:1],
                mood=mood or "neutral",
                narration_excerpt=sentence,
            ))
            # Detail beat
            detail_focus = {"cat": "eyes", "dog": "ears", "human": "face",
                           "rat": "whiskers", "mouse": "whiskers", "bird": "wings"}
            focus_part = detail_focus.get(chars[0], "face")
            beats.append(DirectorialBeat(
                narrative_beat=f"Focus on {chars[0]} {focus_part}",
                visual_goal=f"show character detail",
                camera="closeup",
                focus=focus_part,
                animation="freeze",
                characters=chars[:1],
                mood=mood or "neutral",
                duration=1.5,
                narration_excerpt=sentence,
            ))
            # Environment beat if props available
            if props:
                beats.append(DirectorialBeat(
                    narrative_beat=f"Show environment detail",
                    visual_goal="establish context",
                    camera="medium",
                    focus=props[0],
                    animation="freeze",
                    props=props[:1],
                    duration=1.5,
                    narration_excerpt=sentence,
                ))
        elif len(beats) == 2 and chars:
            # Has establishing + action, add reaction/detail
            beats.append(DirectorialBeat(
                narrative_beat=f"Subtle {chars[0]} reaction",
                visual_goal="show character emotion",
                camera="closeup",
                focus="face",
                animation="freeze",
                characters=chars[:1],
                mood=mood or "neutral",
                duration=1.5,
                narration_excerpt=sentence,
            ))

        # Final beat: reveal / reaction
        if tension >= 5 or has_sudden:
            beats.append(DirectorialBeat(
                narrative_beat="Reaction to events",
                visual_goal="show consequence",
                camera="closeup",
                focus="character" if chars else "scene",
                animation="freeze",
                mood=mood or "cautious",
                duration=1.5,
                narration_excerpt=sentence,
            ))

        # Cap at 8 beats
        return beats[:8]

    # ── Shot planning ──

    def _plan_shots(self, beats: list[DirectorialBeat], tension: int,
                    scene_idx: int, total_scenes: int) -> list[DirectorialBeat]:
        """Assign varied camera shots to each beat."""
        # Cinematic shot patterns
        if tension >= 7:
            pattern = ["wide", "handheld", "closeup", "dutch", "extreme_closeup", "handheld"]
        elif tension >= 4:
            pattern = ["wide", "medium", "closeup", "silhouette", "closeup"]
        else:
            pattern = ["extreme_wide", "wide", "medium", "closeup", "medium"]

        for i, beat in enumerate(beats):
            if beat.camera in ("extreme_wide", "wide", "medium", "closeup", "handheld", "silhouette", "dutch", "extreme_closeup"):
                continue  # already explicitly set
            # Cycle through pattern
            cam = pattern[i % len(pattern)]
            beat.camera = cam

            # Adjust duration based on tension
            if tension >= 5:
                beat.duration = max(0.8, beat.duration * 0.7)  # faster cuts
            else:
                beat.duration = max(1.2, beat.duration)

        return beats

    # ── Animation assignment ──

    def _assign_animations(self, beats: list[DirectorialBeat],
                           tension: int, mood: str) -> list[DirectorialBeat]:
        """Assign character animations per beat."""
        for beat in beats:
            if beat.animation == "idle":
                if tension >= 5:
                    beat.animation = "freeze"
                elif mood in ("sneaky", "cautious"):
                    beat.animation = "crouch"
                elif mood in ("happy", "triumphant"):
                    beat.animation = "bounce"
            if beat.animation == "freeze" and tension >= 6:
                beat.camera_movement = "slow_zoom"
        return beats

    # ── Lighting assignment ──

    def _assign_lighting(self, beats: list[DirectorialBeat], tension: int,
                         mood: str, concepts: dict) -> list[DirectorialBeat]:
        """Assign lighting per beat based on tension, mood, time."""
        for beat in beats:
            if beat.lighting == "silhouette" or beat.camera == "silhouette":
                beat.lighting = "silhouette"
                beat.bg_type = "silhouette"
                continue

            lighting = "day"
            # Check for night words in concepts
            for night_word in ["night", "moon", "dark", "evening", "shadow", "starlight",
                               "moonlight", "dusk", "midnight"]:
                if night_word in concepts:
                    lighting = "night"
                    break

            if mood in ("mysterious", "cautious", "sneaky"):
                lighting = "shadow"
            elif mood in ("sad", "tired"):
                lighting = "dusk"
            elif mood in ("triumphant", "happy"):
                lighting = "dawn"

            if tension >= 5:
                lighting = "shadow" if lighting == "day" else "dark"

            beat.lighting = lighting
        return beats

    # ── Transitions ──

    def _assign_transitions(self, beats: list[DirectorialBeat],
                            scene_idx: int, total_scenes: int) -> list[DirectorialBeat]:
        """Assign transitions between beats and scenes."""
        for i, beat in enumerate(beats):
            if beat.transition != "dissolve":
                continue
            if i == 0 and scene_idx == 0:
                beat.transition = "fade_in"
            elif i == len(beats) - 1 and scene_idx == total_scenes - 1:
                beat.transition = "fade_out"
            elif beat.shake > 0:
                beat.transition = "cut"
            else:
                # Vary transitions
                opts = ["cut", "dissolve", "slide_left", "wipe_right"]
                beat.transition = opts[i % len(opts)]
        return beats

    # ── Detail filler ──

    def _fill_details(self, beats: list[DirectorialBeat],
                      concepts: dict) -> list[DirectorialBeat]:
        """Fill in remaining beat fields from concepts."""
        char_types = {"cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
                      "monkey", "horse", "elephant", "mouse", "rat", "lion", "tiger",
                      "bird", "deer", "cow", "dinosaur", "dragon"}
        chars = [c for c in concepts if c in char_types]
        props = [c for c in concepts if c not in char_types and c != "none"]

        for beat in beats:
            if not beat.characters and chars:
                beat.characters = chars[:1]
            if not beat.props and props:
                beat.props = props[:2]

            # Derive mood from beat context if not set
            if not beat.mood or beat.mood == "neutral":
                beat.mood = "neutral"

            # Camera details
            shot = SHOT_DEFS.get(beat.camera, SHOT_DEFS["medium"])
            beat.duration = max(0.8, beat.duration)

            # Shake effects
            if beat.shake > 0:
                pass

        return beats

    # ── Motif-based overrides ──

    def _apply_motif_overrides(self, beats: list[DirectorialBeat],
                                characters: list[str]) -> list[DirectorialBeat]:
        """Apply character-typed visual motif overrides to beats.

        When a character has a strong visual motif (wolf->moonlight,
        human->firelight, etc.), that motif overrides the generic
        lighting/mood/animation choices.
        """
        if not characters:
            return beats

        try:
            from src.story_intelligence import VISUAL_MOTIFS
        except ImportError:
            return beats

        # Find first character with a matching motif
        motif = None
        for ch in characters:
            if ch in VISUAL_MOTIFS:
                motif = VISUAL_MOTIFS[ch]
                break
            # Fuzzy match
            for motif_key in VISUAL_MOTIFS:
                if motif_key in ch or ch in motif_key:
                    motif = VISUAL_MOTIFS[motif_key]
                    break
            if motif:
                break

        if not motif:
            return beats

        motif_lighting = motif.get("lighting", "")
        motif_mood = motif.get("mood", "")
        motif_camera = motif.get("camera", "")
        motif_animation = motif.get("animation", "")

        if not motif_lighting and not motif_mood and not motif_animation:
            return beats

        for beat in beats:
            # Apply motif lighting — overrides generic lighting
            if motif_lighting and beat.lighting != motif_lighting:
                # Only override if beat lighting is generic (not archetype-critical)
                # Keep archetype lighting when tension is high (it's intentional)
                if beat.tension_level < 7:
                    beat.lighting = motif_lighting
            # Apply motif mood if beat has neutral or no mood
            if motif_mood and beat.mood in ("neutral", ""):
                beat.mood = motif_mood
            # Apply motif camera suggestion if beat is generic medium
            if motif_camera and beat.camera == "medium" and beat.tension_level < 5:
                beat.camera = motif_camera
            # Apply motif animation if beat has no specific animation
            if motif_animation and beat.animation in ("idle", "freeze", ""):
                beat.animation = motif_animation

        return beats

    # ── Beat → Scene conversion ──

    def beat_to_scene(self, beat: DirectorialBeat, rng: random.Random = None) -> dict:
        """Convert a DirectorialBeat into a renderable scene dict.

        The output is compatible with SketchGenerator.render_scene().
        Visual directives from the concept translator influence positioning,
        lighting, and composition.
        """
        if rng is None:
            rng = random.Random()

        directives = beat.visual_directives or {}

        shot = SHOT_DEFS.get(beat.camera, SHOT_DEFS["medium"])
        lighting = LIGHTING_DEFS.get(beat.lighting, LIGHTING_DEFS["day"])

        # ── Apply concept visual directives ──
        # Warmth: shift color grade
        warmth = directives.get("warmth", 0.5)
        brightness = directives.get("brightness", 0.5)

        # Build bg config (base from archetype lighting)
        base_colors = [list(lighting["colors"][0]), list(lighting["colors"][1])]
        ground_color = list(lighting["ground_color"])

        # Warmth adjustment: lerp colors toward warm or cool
        if warmth < 0.3:
            # Cool tint
            bg_config = {
                "type": "gradient",
                "colors": [
                    [int(c * 0.6 + 60 * 0.4) for c in base_colors[0]],
                    [int(c * 0.6 + 40 * 0.4) for c in base_colors[1]],
                ],
                "horizon": 0.5,
                "ground_color": [int(c * 0.7) for c in ground_color],
            }
        elif warmth > 0.7:
            # Warm tint
            bg_config = {
                "type": "gradient",
                "colors": [
                    [min(255, int(base_colors[0][0] + 40)), min(255, int(base_colors[0][1] * 0.9)), min(255, int(base_colors[0][2] * 0.8))],
                    [min(255, int(base_colors[1][0] + 30)), min(255, int(base_colors[1][1] * 0.9)), min(255, int(base_colors[1][2] * 0.8))],
                ],
                "horizon": 0.5,
                "ground_color": [min(255, int(ground_color[0] + 20)), int(ground_color[1] * 0.9), int(ground_color[2] * 0.8)],
            }
        else:
            bg_config = {
                "type": "gradient",
                "colors": [list(base_colors[0]), list(base_colors[1])],
                "horizon": 0.5,
                "ground_color": list(ground_color),
            }

        # Brightness adjustment
        if brightness < 0.3:
            darken = 0.5
            bg_config["colors"] = [
                [int(c * darken) for c in bg_config["colors"][0]],
                [int(c * darken) for c in bg_config["colors"][1]],
            ]
            bg_config["ground_color"] = [int(c * darken) for c in bg_config["ground_color"]]
        elif brightness > 0.7:
            lighten = 1.3
            bg_config["colors"] = [
                [min(255, int(c * lighten)) for c in bg_config["colors"][0]],
                [min(255, int(c * lighten)) for c in bg_config["colors"][1]],
            ]
            bg_config["ground_color"] = [min(255, int(c * lighten)) for c in bg_config["ground_color"]]

        # Contrast / asymmetry via camera shake
        contrast = directives.get("contrast", 0.5)
        if contrast > 0.7:
            beat.shake = max(beat.shake, 0.1)  # slight unease

        # Apply color grade from directives or beat
        cg = beat.color_grade
        if directives.get("posture") in ("slumped", "closed") and cg == "normal":
            cg = "desaturated"
        elif directives.get("warmth", 0.5) > 0.7 and cg == "normal":
            cg = "warm"

        if cg == "desaturated":
            bg_config["colors"] = [
                [int(c * 0.6 + 128 * 0.4) for c in bg_config["colors"][0]],
                [int(c * 0.6 + 128 * 0.4) for c in bg_config["colors"][1]],
            ]
        elif cg == "warm":
            bg_config["colors"][0][0] = min(255, bg_config["colors"][0][0] + 30)
            bg_config["colors"][1][0] = min(255, bg_config["colors"][1][0] + 20)
        elif cg == "cool":
            bg_config["colors"][0][2] = min(255, bg_config["colors"][0][2] + 30)
            bg_config["colors"][1][2] = min(255, bg_config["colors"][1][2] + 20)

        # ── Build elements with directive-aware placement ──
        elements = []
        subject_elevation = directives.get("subject_elevation", 0.5)
        subject_prominence = directives.get("subject_prominence", 0.5)
        horizontal_bias = directives.get("horizontal_bias", 0.5)

        for ch in beat.characters:
            elem_def = ELEMENT_DEFS.get(ch, {})
            elem = dict(elem_def)
            elem["x"] = round(horizontal_bias * 0.6 + 0.2, 3)  # 0.2-0.8 based on bias
            elem["y"] = round(subject_elevation * 0.35 + 0.25, 3)  # 0.25-0.6

            # Camera-based position adjustments
            cam = beat.camera
            if cam in ("closeup", "extreme_closeup"):
                elem["y"] = round(0.35 + (1.0 - subject_elevation) * 0.2, 3)
                elem["scale"] = elem.get("scale", 2.0) * (1.0 + subject_prominence * 0.5)
            elif cam == "wide":
                elem["scale"] = elem.get("scale", 2.0) * 0.6
                elem["y"] = round(0.3 + subject_elevation * 0.15, 3)
            elif cam == "extreme_wide":
                elem["scale"] = elem.get("scale", 2.0) * 0.3
                elem["y"] = round(0.25 + subject_elevation * 0.1, 3)
            elif cam in ("low_angle",):
                elem["y"] = round(0.5 + subject_elevation * 0.15, 3)
            elif cam in ("high_angle",):
                elem["y"] = round(0.2 + subject_elevation * 0.1, 3)
            elif cam in ("over_shoulder",):
                elem["x"] = round(0.2, 3)

            # Prominence affects scale
            if subject_prominence < 0.3:
                elem["scale"] = elem.get("scale", 1.0) * 0.5
            elif subject_prominence > 0.7:
                elem["scale"] = elem.get("scale", 1.0) * 1.5

            # Mood from directives or beat
            elem["mood"] = beat.mood

            # Animation hints
            elem["_animation"] = beat.animation

            # Posture hint for renderer (if renderer supports it)
            posture = directives.get("posture", "")
            if posture:
                elem["_posture_hint"] = posture

            elements.append(elem)

        for prop in beat.props:
            if prop in ELEMENT_DEFS:
                elem = dict(ELEMENT_DEFS[prop])
                if "x" not in elem:
                    elem["x"] = round(rng.uniform(0.1, 0.9), 3)
                    elem["y"] = round(rng.uniform(0.15, 0.7), 3)
                elements.append(elem)

        # Symbolic ground elements from concept translator
        symbolic_ground = directives.get("symbolic_ground", [])
        for se in symbolic_ground:
            # Convert relative (0-1) coords to element format
            elem = dict(se)
            elem.setdefault("z_index", 2)
            elements.append(elem)

        # Symbolic atmosphere overrides
        symbolic_atmos = directives.get("symbolic_atmosphere")
        atmos = {
            "particles": "none",
            "fog": False,
            "shake": beat.shake,
        }
        if symbolic_atmos:
            for k, v in symbolic_atmos.items():
                atmos[k] = v

        scene = {
            "bg": bg_config,
            "elements": elements,
            "atmosphere": atmos,
            "mood": beat.mood or "neutral",
            "narration": beat.narration_excerpt,
            "camera": {
                "shot": beat.camera,
                "zoom": shot["zoom"],
                "zoom_target": [0.5, 0.4],
                "movement": beat.camera_movement,
                "shake": beat.shake,
                "vignette": beat.vignette,
            },
            "director": {
                "beat": beat.narrative_beat,
                "goal": beat.visual_goal,
                "animation": beat.animation,
                "duration": beat.duration,
                "transition": beat.transition,
                "tension": beat.tension_level,
            },
        }
        return scene


# ── Convenience: full pipeline ──

def direct_narration_to_beats(narration_text: str, rng: random.Random = None) -> list[list[DirectorialBeat]]:
    """Full narrative → list of scene beat sequences (per-sentence Director)."""
    from src.narrative_to_scenes import narration_to_scenes
    if rng is None:
        rng = random.Random()

    raw = narration_to_scenes(narration_text)
    director = Director(rng)
    all_beat_sequences = []

    for i, scene_info in enumerate(raw):
        sentence = scene_info.get("narration", "")
        beats = director.direct(sentence, scene_idx=i, total_scenes=len(raw))
        all_beat_sequences.append(beats)

    return all_beat_sequences


def direct_narration_with_archetype(narration_text: str, rng: random.Random = None) -> dict:
    """Full narrative → archetype analysis + Director beat sequences.

    Returns dict with:
      - archetype: detected archetype name
      - archetype_label: human-readable name
      - phases: list of phase names
      - beat_sequences: list[list[DirectorialBeat]]
      - num_beats: total beat count
      - num_phases: number of narrative phases
    """
    if rng is None:
        rng = random.Random()
    from src.narrative_engines import NarrativeEngine, analyze_narrative

    # Get narrative analysis
    analysis = analyze_narrative(narration_text)

    # Direct with archetype awareness
    director = Director(rng, narrative_engine=NarrativeEngine(rng))
    beat_sequences = director.direct_from_narrative(narration_text)

    return {
        "archetype": analysis["archetype"],
        "archetype_label": analysis["archetype_label"],
        "description": analysis["description"],
        "phases": analysis["phases"],
        "tension_arc": analysis["tension_arc"],
        "lighting_arc": analysis["lighting_arc"],
        "num_sentences": analysis["num_sentences"],
        "num_phases": analysis["num_phases"],
        "num_beats": sum(len(seq) for seq in beat_sequences),
        "beat_sequences": beat_sequences,
        "reveal_strategy": analysis.get("reveal_strategy", {}),
    }


def beat_sequences_to_scenes(beat_sequences: list[list[DirectorialBeat]],
                              rng: random.Random = None) -> list[dict]:
    """Convert all beat sequences to flat list of renderable scenes."""
    if rng is None:
        rng = random.Random()
    director = Director(rng)
    scenes = []
    for seq in beat_sequences:
        for beat in seq:
            scene = director.beat_to_scene(beat, rng)
            scenes.append(scene)
    return scenes
