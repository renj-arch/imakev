"""Story State Engine — canonical world model for the narrative pipeline.

Single source of truth. All downstream layers read from here; only
StoryState methods mutate state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Individual state records ──

GLOBAL_EMOTION_DIMS = ["fear", "trust", "curiosity", "hope", "despair", "anger", "awe", "satisfaction", "confidence"]


@dataclass
class EmotionState:
    """Float intensities for standard emotion dimensions."""
    fear: float = 0.0
    trust: float = 0.0
    curiosity: float = 0.0
    hope: float = 0.0
    despair: float = 0.0
    anger: float = 0.0
    awe: float = 0.0
    satisfaction: float = 0.0
    confidence: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if v != 0.0}

    def dominant(self) -> Optional[str]:
        """Return the emotion dimension with the highest value, or None."""
        best = max((v, k) for k, v in self.__dict__.items() if v > 0)
        return best[1] if best[0] > 0 else None


@dataclass
class CharacterState:
    """What the engine knows about a single character at a point in time."""
    type: str = "wolf"                     # wolf, human, cat, etc.
    name: str = ""
    emotions: EmotionState = field(default_factory=EmotionState)
    visual_state: dict = field(default_factory=lambda: {
        "posture": "neutral",
        "prominence": 0.5,
        "elevation": 0.5,
    })
    goals: list[str] = field(default_factory=list)
    importance: float = 0.5                # 0-1 narrative weight
    first_seen: int = 0                    # beat index
    last_seen: int = 0
    is_alive: bool = True


@dataclass
class ObjectState:
    """A persistent object in the story world."""
    type: str = ""
    importance: float = 0.5
    owner: Optional[str] = None            # character key
    first_seen: int = 0
    last_seen: int = 0
    symbolic_meaning: list[str] = field(default_factory=list)
    state: str = "present"                 # present, used, consumed, destroyed, hidden


@dataclass
class RelationshipState:
    """Bidirectional dyadic relationship between two characters."""
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0


@dataclass
class NarrativeState:
    """Current narrative context from archetype engine."""
    archetype: str = "transformation"
    current_phase: str = "old_state"
    tension: float = 5.0
    reveal_stage: str = "none"             # none, hint, partial, full
    total_beats: int = 0
    current_beat: int = 0


@dataclass
class WorldState:
    """Environmental conditions."""
    time_of_day: str = "day"               # dawn, day, dusk, night, midnight
    safety: float = 0.5                    # 0 = dangerous, 1 = completely safe
    scarcity: float = 0.5                  # 0 = abundant, 1 = desperate
    weather: str = "clear"                 # clear, rain, snow, storm, ash


@dataclass
class HistoryEvent:
    """A single recorded event in the story timeline."""
    beat: int = 0
    event_type: str = ""
    detail: str = ""
    entities: list[str] = field(default_factory=list)


# ── Top-level Story State ──

@dataclass
class StoryState:
    """Canonical world model. Single source of truth for the entire pipeline."""

    characters: dict[str, CharacterState] = field(default_factory=dict)
    objects: dict[str, ObjectState] = field(default_factory=dict)
    relationships: dict[tuple[str, str], RelationshipState] = field(default_factory=dict)
    narrative: NarrativeState = field(default_factory=NarrativeState)
    world: WorldState = field(default_factory=WorldState)
    history: list[HistoryEvent] = field(default_factory=list)

    # ── Character methods ──

    def ensure_character(self, key: str, **overrides) -> CharacterState:
        """Get existing character or create with defaults + overrides."""
        if key not in self.characters:
            self.characters[key] = CharacterState(**overrides)
        return self.characters[key]

    def update_emotion(self, character_key: str, dim: str, value: float) -> None:
        """Set an emotion dimension, clamped 0-1."""
        ch = self.characters.get(character_key)
        if ch is None:
            return
        if hasattr(ch.emotions, dim):
            setattr(ch.emotions, dim, max(0.0, min(1.0, value)))

    def blend_emotion(self, character_key: str, dim: str, delta: float) -> None:
        """Add a delta to an emotion dimension, clamped 0-1."""
        ch = self.characters.get(character_key)
        if ch is None:
            return
        if hasattr(ch.emotions, dim):
            current = getattr(ch.emotions, dim)
            setattr(ch.emotions, dim, max(0.0, min(1.0, current + delta)))

    # ── Relationship methods ──

    def ensure_relationship(self, a: str, b: str) -> RelationshipState:
        """Get or create a bidirectional relationship."""
        key = self._rel_key(a, b)
        if key not in self.relationships:
            self.relationships[key] = RelationshipState()
        return self.relationships[key]

    def blend_relationship(self, a: str, b: str, dim: str, delta: float) -> None:
        """Adjust a relationship dimension."""
        rel = self.ensure_relationship(a, b)
        if hasattr(rel, dim):
            current = getattr(rel, dim)
            setattr(rel, dim, max(0.0, min(1.0, current + delta)))

    # ── Object methods ──

    def ensure_object(self, key: str, **overrides) -> ObjectState:
        if key not in self.objects:
            self.objects[key] = ObjectState(**overrides)
        return self.objects[key]

    # ── Narrative methods ──

    def advance_beat(self) -> None:
        self.narrative.current_beat += 1

    # ── History methods ──

    def record_event(self, event_type: str, detail: str = "", entities: list[str] | None = None) -> None:
        self.history.append(HistoryEvent(
            beat=self.narrative.current_beat,
            event_type=event_type,
            detail=detail,
            entities=entities or [],
        ))

    # ── Snapshot / export ──

    def snapshot(self) -> dict:
        """Serializable snapshot for downstream layers."""
        return {
            "characters": {
                k: {
                    "type": v.type,
                    "name": v.name,
                    "emotions": v.emotions.as_dict(),
                    "visual_state": dict(v.visual_state),
                    "goals": list(v.goals),
                    "importance": v.importance,
                    "first_seen": v.first_seen,
                    "last_seen": v.last_seen,
                    "is_alive": v.is_alive,
                }
                for k, v in self.characters.items()
            },
            "objects": {
                k: {
                    "type": v.type,
                    "importance": v.importance,
                    "owner": v.owner,
                    "first_seen": v.first_seen,
                    "last_seen": v.last_seen,
                    "symbolic_meaning": list(v.symbolic_meaning),
                    "state": v.state,
                }
                for k, v in self.objects.items()
            },
            "relationships": {
                f"{a}↔{b}": {"trust": r.trust, "fear": r.fear, "familiarity": r.familiarity}
                for (a, b), r in self.relationships.items()
            },
            "narrative": {
                "archetype": self.narrative.archetype,
                "current_phase": self.narrative.current_phase,
                "tension": self.narrative.tension,
                "reveal_stage": self.narrative.reveal_stage,
                "current_beat": self.narrative.current_beat,
                "total_beats": self.narrative.total_beats,
            },
            "world": {
                "time_of_day": self.world.time_of_day,
                "safety": self.world.safety,
                "scarcity": self.world.scarcity,
                "weather": self.world.weather,
            },
            "history": [
                {"beat": h.beat, "event_type": h.event_type, "detail": h.detail, "entities": h.entities}
                for h in self.history
            ],
        }

    # ── Internal helpers ──

    @staticmethod
    def _rel_key(a: str, b: str) -> tuple[str, str]:
        return tuple(sorted((a, b)))
