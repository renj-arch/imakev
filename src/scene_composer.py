"""Scene Composer — general-purpose topic → scene engine.
Parses any topic string and generates a structured scene description
with appropriate background, elements, mood, and composition.

No LLM required. Works for ANY topic."""

import random, math


class SceneComposer:
    """Compose a visual scene from any topic string."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    # ── Concept keywords → element mappings ─────────────────────

    PEOPLE = {
        "human": ["human", "person", "people", "man", "woman", "child", "baby", "adult", "crowd",
                   "king", "queen", "prince", "princess", "lord", "lady", "emperor", "pharaoh",
                   "soldier", "warrior", "knight", "guard", "army", "captain", "pirate", "sailor",
                   "scientist", "doctor", "engineer", "inventor", "teacher", "student", "monk",
                   "artist", "writer", "poet", "philosopher", "thinker", "leader", "hero",
                   "worker", "farmer", "hunter", "explorer", "traveler", "stranger", "friend",
                   "gutenberg", "einstein", "newton", "darwin", "galileo", "copernicus",
                   "caesar", "napoleon", "alexander", "cleopatra", "nefertiti"],
    }
    NATURE = {
        "mountain": ["mountain", "peak", "cliff", "summit", "volcano", "alps", "himalaya", "rocky"],
        "tree": ["tree", "forest", "woods", "jungle", "palm", "pine", "oak", "bamboo", "grove",
                 "woodland", "orchard", "garden", "park"],
        "hill": ["hill", "valley", "meadow", "field", "plain", "grassland", "prairie", "savanna"],
        "water": ["water", "ocean", "sea", "river", "lake", "stream", "pond", "wave", "beach",
                  "shore", "coast", "bay", "harbor", "port", "creek"],
        "cloud": ["cloud", "sky", "weather", "rain", "storm", "thunder", "fog", "mist", "haze"],
        "sun": ["sun", "sunrise", "sunset", "dawn", "dusk", "daylight", "morning", "noon"],
        "moon": ["moon", "night", "midnight", "evening", "lunar", "crescent", "full moon"],
        "star": ["star", "constellation", "galaxy", "nebula", "comet", "asteroid"],
        "desert": ["desert", "sand", "dune", "cactus", "oasis", "sahara", "arid"],
        "snow": ["snow", "winter", "ice", "glacier", "arctic", "frost", "cold", "frozen"],
    }
    BUILDINGS = {
        "building": ["building", "city", "town", "village", "urban", "skyscraper", "tower",
                      "castle", "fortress", "palace", "temple", "church", "cathedral", "mosque",
                      "pyramid", "monument", "statue", "ruins", "bridge", "wall"],
        "house": ["house", "home", "cottage", "cabin", "hut", "shelter", "roof", "door"],
    }
    OBJECTS = {
        "ship": ["ship", "boat", "sail", "vessel", "fleet", "navy", "canoe", "raft", "galleon"],
        "cannon": ["cannon", "gun", "weapon", "artillery", "bomb", "missile"],
        "flag": ["flag", "banner", "standard", "pennant", "colors", "emblem"],
        "path": ["path", "road", "trail", "street", "route", "way", "bridge", "rail", "track"],
        "rect": ["book", "table", "desk", "door", "window", "chest", "box", "crate",
                 "paper", "page", "document", "scroll", "map", "chart", "screen", "machine",
                 "press", "engine", "motor", "tool", "device", "apparatus", "instrument"],
        "circle": ["coin", "ring", "crown", "wheel", "plate", "shield", "clock", "globe"],
        "line": ["sword", "spear", "arrow", "stick", "rod", "pole", "staff", "cane",
                 "fence", "rail", "wire", "rope", "chain", "thread"],
    }
    ABSTRACT = {
        "text": ["story", "legend", "myth", "history", "knowledge", "idea", "concept",
                 "theory", "law", "rule", "truth", "secret", "message", "word"],
        "label": ["name", "title", "sign", "symbol", "emblem", "logo", "mark"],
        "arrow": ["point", "direction", "path", "journey", "progress", "movement"],
        "x_mark": ["no", "stop", "end", "death", "danger", "wrong", "false", "myth"],
    }

    # ── Environment detection ───────────────────────────────────

    ENVIRONMENTS = [
        ("indoor", ["indoor", "room", "house", "inside", "workshop", "lab", "library",
                    "church", "temple", "castle", "palace", "cave", "dungeon", "cell",
                    "office", "factory", "school", "studio", "kitchen", "hall"]),
        ("night", ["night", "moon", "star", "dark", "midnight", "evening", "space",
                   "galaxy", "constellation", "nebula", "astronaut", "rocket"]),
        ("ocean", ["ocean", "sea", "beach", "shore", "coast", "harbor", "port",
                   "pirate", "ship", "boat", "sail", "waves", "underwater"]),
        ("sunset", ["sunset", "dusk", "dawn", "evening", "twilight", "sunrise"]),
        ("desert", ["desert", "sand", "dune", "cactus", "sahara", "oasis", "arid"]),
        ("snow", ["snow", "winter", "ice", "glacier", "arctic", "frost", "frozen"]),
    ]

    # ── Mood detection ──────────────────────────────────────────

    MOOD_KEYWORDS = {
        "dramatic": ["war", "battle", "danger", "storm", "attack", "explosion", "crash",
                     "fight", "conflict", "death", "destroy", "enemy", "blood", "fire"],
        "somber": ["death", "sad", "tragedy", "loss", "grief", "sorrow", "grave", "darkness",
                   "misery", "suffer", "poor", "hunger", "disease", "pain", "cry"],
        "hopeful": ["hope", "future", "discovery", "invention", "dream", "freedom", "peace",
                    "brave", "courage", "success", "victory", "rise", "light", "born"],
        "epic": ["epic", "legend", "hero", "journey", "adventure", "quest", "empire",
                 "kingdom", "world", "universe", "revolution", "mountain", "ocean"],
        "mysterious": ["mystery", "secret", "unknown", "ancient", "myth", "legend", "magic",
                       "ghost", "spirit", "strange", "hidden", "forbidden", "dark"],
        "peaceful": ["peace", "calm", "quiet", "gentle", "beautiful", "love", "garden",
                     "village", "home", "family", "friend", "happy", "joy", "rest"],
    }

    def compose_script(self, topic: str, n_scenes: int = 4) -> dict:
        """Generate a full multi-scene script from a topic."""
        t = topic.lower()
        scenes = []
        for i in range(n_scenes):
            scene_title = self._scene_title(t, i, n_scenes)
            narration = self._scene_narration(t, i, n_scenes, topic)
            scene = self.compose_scene(t, scene_title)
            scene["narration"] = narration
            scene["title"] = scene_title
            scene["scene_num"] = i + 1
            scene["camera"] = [None, "ken_burns_in", "pan_right", "ken_burns_out"][i % 4]
            scenes.append(scene)

        title = topic[:60].title()
        return {"title": title, "scenes": scenes}

    def compose_scene(self, topic: str, scene_title: str = "") -> dict:
        """Compose a single scene from any topic string."""
        t = topic.lower()
        st = scene_title.lower()

        # Determine environment and background
        env = self._detect_environment(t, st)
        bg = self._make_background(env)

        # Determine mood
        mood = self._detect_mood(t, st)

        # Extract concepts from topic + scene title
        concepts = self._extract_concepts(t, st)

        # Compose elements from concepts
        elements = self._compose_elements(concepts, env, mood)

        # Ensure minimum elements
        if len(elements) < 3:
            elements += self._fill_elements(env, mood, len(elements))

        # Build atmosphere
        atmos = self._make_atmosphere(env, mood)

        return {
            "bg": bg,
            "elements": elements,
            "atmosphere": atmos,
            "mood": mood
        }

    def _detect_environment(self, topic: str, scene_title: str = "") -> str:
        """Detect the best environment/background type."""
        combined = topic + " " + scene_title
        for env_name, keywords in self.ENVIRONMENTS:
            if any(w in combined for w in keywords):
                return env_name

        # Check for building/house keywords → indoor
        for kws in self.BUILDINGS.values():
            if any(w in combined for w in kws):
                return "indoor"

        # Check for nature keywords → gradient
        for kws in self.NATURE.values():
            if any(w in combined for w in kws):
                return "gradient"

        # Default based on topic length/type
        if len(topic.split()) <= 3:
            return "gradient"
        return "indoor"

    def _detect_mood(self, topic: str, scene_title: str = "") -> str:
        """Detect the mood from keywords."""
        combined = topic + " " + scene_title
        scores = {}
        for mood_name, keywords in self.MOOD_KEYWORDS.items():
            scores[mood_name] = sum(1 for w in keywords if w in combined)

        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "peaceful"

    def _make_background(self, env: str) -> dict:
        """Generate background dict from environment type."""
        bg = {"type": env}

        if env == "gradient":
            palettes = [
                {"colors": [[200, 210, 230], [140, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]},
                {"colors": [[180, 200, 220], [100, 150, 200]], "horizon": 0.55, "ground_color": [50, 80, 40]},
                {"colors": [[230, 220, 200], [180, 170, 150]], "horizon": 0.6, "ground_color": [100, 90, 70]},
                {"colors": [[200, 220, 240], [160, 190, 220]], "horizon": 0.55, "ground_color": [70, 100, 60]},
            ]
            bg.update(self.rng.choice(palettes))
        elif env == "night":
            bg.update({"colors": [[5, 3, 20], [20, 15, 50]], "horizon": 0.6, "ground_color": [15, 20, 30]})
        elif env == "ocean":
            bg.update({"sky_color": [180, 210, 240], "horizon_color": [120, 170, 220],
                       "horizon": 0.5, "water_color": [30, 70, 150]})
        elif env == "sunset":
            bg.update({"colors": [[220, 100, 70], [200, 120, 90], [160, 80, 100], [80, 50, 80]],
                       "horizon": 0.5, "ground_color": [40, 50, 30]})
        elif env == "desert":
            bg.update({"colors": [[240, 220, 180], [200, 180, 140]], "horizon": 0.55, "ground_color": [180, 160, 100]})
        elif env == "snow":
            bg.update({"colors": [[220, 230, 240], [180, 200, 220]], "horizon": 0.55, "ground_color": [200, 210, 220]})
        elif env == "indoor":
            bg.update({"wall_color": [210, 200, 180], "floor_color": [160, 140, 120]})

        return bg

    def _extract_concepts(self, topic: str, scene_title: str = "") -> list:
        """Extract visual concepts from text.
        Returns list of (element_type, relevance_weight) tuples."""
        combined = topic + " " + scene_title
        concepts = []

        for etype, keywords in self.PEOPLE.items():
            if any(w in combined for w in keywords):
                concepts.append(("human", 10))
                break
        for etype, keywords in self.NATURE.items():
            weight = 8 if etype == "mountain" else 6
            if any(w in combined for w in keywords):
                concepts.append((etype, weight))
        for etype, keywords in self.BUILDINGS.items():
            if any(w in combined for w in keywords):
                concepts.append((etype, 7))
        for etype, keywords in self.OBJECTS.items():
            if any(w in combined for w in keywords):
                concepts.append((etype, 5))
        for etype, keywords in self.ABSTRACT.items():
            if any(w in combined for w in keywords):
                concepts.append((etype, 4))

        return concepts

    def _compose_elements(self, concepts: list, env: str, mood: str) -> list:
        """Build scene elements from extracted concepts."""
        elements = []
        placed = set()

        for etype, weight in sorted(concepts, key=lambda x: -x[1]):
            if etype == "human":
                elem = self._make_human(mood)
                if elem["type"] not in placed:
                    elements.append(elem)
                    placed.add(elem["type"])
            elif etype in ("mountain", "hill"):
                elem = self._make_landscape(etype, mood)
                elements.append(elem)
            elif etype == "tree":
                elem = self._make_tree(env)
                elements.append(elem)
            elif etype == "water":
                elem = self._make_water()
                elements.append(elem)
            elif etype == "cloud":
                elem = self._make_cloud()
                elements.append(elem)
            elif etype in ("sun", "moon", "star"):
                elem = self._make_sky_object(etype, mood)
                elements.append(elem)
            elif etype == "desert":
                elements.append({"type": "hill", "x": 0.3, "y": 0.7, "width": 0.4, "height": 0.08, "fill": [200, 180, 120]})
                elements.append({"type": "hill", "x": 0.7, "y": 0.72, "width": 0.35, "height": 0.06, "fill": [190, 170, 110]})
            elif etype == "snow":
                elements.append({"type": "mountain", "x": 0.5, "y": 0.65, "width": 0.5, "height": 0.3, "fill": [180, 190, 210], "snow": True})
            elif etype in ("building", "house"):
                elem = self._make_building(etype, mood)
                elements.append(elem)
            elif etype == "ship":
                elements.append(self._make_ship())
            elif etype == "cannon":
                elements.append({"type": "cannon", "x": 0.3, "y": 0.65, "scale": 0.8})
            elif etype == "flag":
                elements.append({"type": "flag", "x": 0.7, "y": 0.5, "scale": 0.8, "fill": [200, 50, 50]})
            elif etype == "path":
                elements.append({"type": "path", "x": 0.5, "y": 0.6, "x2": 0.5, "y2": 0.95, "width": 15})
            elif etype == "rect":
                elements.append({"type": "rect", "x": 0.5, "y": 0.5, "width": 50, "height": 60, "fill": [180, 170, 150], "stroke": [100, 90, 80]})
            elif etype == "circle":
                elements.append({"type": "circle", "x": 0.5, "y": 0.5, "radius": 20, "fill": [200, 180, 100], "stroke": [150, 130, 60]})
            elif etype == "line":
                elements.append({"type": "line", "x": 0.3, "y": 0.5, "x2": 0.7, "y2": 0.5, "stroke": [100, 90, 80], "stroke_width": 3})
            elif etype in ("text", "label"):
                # handled separately
                pass

        # Add text label from concepts if any abstract concept matched
        if any(c[0] in ("text", "label", "arrow", "x_mark") for c in concepts):
            elements.append({
                "type": "text", "x": 0.5, "y": 0.08,
                "text": " ".join(c[0] for c in concepts[:3]).upper(),
                "font_size": 26, "fill": [60, 50, 40]
            })
            # x_mark for negative concepts
            if any(w in str(concepts) for w in ["x_mark"]):
                elements.append({"type": "x_mark", "x": 0.85, "y": 0.15, "scale": 0.6})

        return elements

    def _fill_elements(self, env: str, mood: str, count: int) -> list:
        """Add filler elements when scene has too few."""
        fillers = []
        if env in ("gradient", "sunset"):
            fillers.append({"type": "tree", "x": 0.8, "y": 0.72, "scale": 0.6, "tree_style": "round", "fill": [50, 120, 50]})
            fillers.append({"type": "hill", "x": 0.5, "y": 0.7, "width": 0.5, "height": 0.1, "fill": [60, 110, 50]})
        elif env == "night":
            fillers.append({"type": "moon", "x": 0.7, "y": 0.2, "radius": 20})
            fillers.append({"type": "star", "x": 0.3, "y": 0.15, "radius": 2, "fill": [255, 255, 200]})
        elif env == "ocean":
            fillers.append({"type": "ship", "x": 0.5, "y": 0.55, "scale": 0.8, "fill": [80, 60, 40], "sail_color": [220, 210, 190]})
        elif env == "indoor":
            fillers.append({"type": "human", "x": 0.5, "y": 0.55, "scale": 0.8, "fill": [80, 70, 60]})
            fillers.append({"type": "rect", "x": 0.5, "y": 0.5, "width": 60, "height": 40, "fill": [160, 150, 130], "stroke": [100, 90, 80]})
        else:
            fillers.append({"type": "cloud", "x": 0.3, "y": 0.2, "scale": 0.6})
            fillers.append({"type": "cloud", "x": 0.7, "y": 0.25, "scale": 0.5})

        return fillers[:3 - count]

    def _make_human(self, mood: str) -> dict:
        """Create a human element appropriate to mood."""
        colors_by_mood = {
            "dramatic": [100, 60, 40], "somber": [60, 50, 50],
            "hopeful": [80, 100, 120], "epic": [120, 80, 60],
            "mysterious": [50, 40, 70], "peaceful": [80, 100, 80],
        }
        c = colors_by_mood.get(mood, [80, 60, 120])
        return {"type": "human", "x": 0.4, "y": 0.55, "scale": 0.9, "fill": c}

    def _make_landscape(self, etype: str, mood: str) -> dict:
        """Create mountain or hill element."""
        if etype == "mountain":
            return {"type": "mountain", "x": 0.5, "y": 0.65, "width": 0.5, "height": 0.3,
                    "fill": [100, 110, 140], "snow": True}
        return {"type": "hill", "x": 0.3, "y": 0.7, "width": 0.4, "height": 0.12, "fill": [60, 120, 60]}

    def _make_tree(self, env: str) -> dict:
        """Create a tree appropriate to environment."""
        style = "palm" if env == "ocean" else ("pine" if env == "snow" else self.rng.choice(["round", "pine"]))
        return {"type": "tree", "x": 0.2, "y": 0.72, "scale": 0.8, "tree_style": style, "fill": [40, 100, 40]}

    def _make_water(self) -> dict:
        return {"type": "water", "x": 0.1, "y": 0.6, "width": 0.8, "height": 0.15, "fill": [60, 120, 200]}

    def _make_cloud(self) -> dict:
        return {"type": "cloud", "x": 0.3 + self.rng.random() * 0.4, "y": 0.15 + self.rng.random() * 0.1, "scale": 0.6}

    def _make_sky_object(self, etype: str, mood: str) -> dict:
        if etype == "sun":
            return {"type": "sun", "x": 0.5, "y": 0.28, "radius": 25, "fill": [255, 220, 50]}
        elif etype == "moon":
            return {"type": "moon", "x": 0.7, "y": 0.2, "radius": 22}
        return {"type": "star", "x": 0.3, "y": 0.15, "radius": 2, "fill": [255, 255, 200]}

    def _make_building(self, etype: str, mood: str) -> dict:
        if etype == "house":
            return {"type": "house", "x": 0.5, "y": 0.7, "scale": 0.9, "fill": [180, 150, 120], "roof_color": [150, 50, 40]}
        return {"type": "building", "x": 0.5, "y": 0.65, "width": 0.12, "height": 0.25,
                "fill": [120, 100, 80], "window_color": [255, 220, 100]}

    def _make_ship(self) -> dict:
        return {"type": "ship", "x": 0.5, "y": 0.55, "scale": 0.9, "fill": [80, 60, 40], "sail_color": [220, 210, 190]}

    def _make_atmosphere(self, env: str, mood: str) -> dict:
        atmos = {"particles": "none", "fog": False}
        if env == "night":
            atmos["particles"] = "stars"
            atmos["star_count"] = 60
        if mood in ("mysterious", "somber"):
            atmos["fog"] = True
        return atmos

    def _scene_title(self, topic: str, idx: int, total: int) -> str:
        """Generate a scene title based on topic and scene index."""
        titles_pool = [
            ["Introduction", "The Beginning", "Origins", "Before It All Began"],
            ["The Turning Point", "The Discovery", "The Breakthrough", "A New Era"],
            ["How It Changed Us", "The Impact", "The Ripple Effect", "Transformation"],
            ["The Legacy", "Today and Tomorrow", "Remembering", "The Final Chapter"],
        ]
        pool = titles_pool[min(idx, len(titles_pool) - 1)]
        return self.rng.choice(pool)

    def _scene_narration(self, topic: str, idx: int, total: int, raw_topic: str) -> str:
        """Generate a narration sentence for a scene."""
        narrations = {
            0: [
                f"Long ago, the story of {raw_topic} began.",
                f"Have you ever wondered about {raw_topic}?",
                f"{raw_topic.title()} — a story that shaped our world.",
            ],
            1: [
                f"Then everything changed with a single breakthrough.",
                f"The turning point came, and nothing was the same.",
                f"But how did this transformation happen?",
            ],
            2: [
                f"The impact was felt across the entire world.",
                f"This changed how people lived, worked, and thought.",
                f"From this moment forward, the world was different.",
            ],
            3: [
                f"And that is the remarkable story of {raw_topic}.",
                f"Today, we still feel the echoes of this story.",
                f"The legacy of {raw_topic} lives on.",
            ],
        }
        pool = narrations.get(min(idx, 3), [f"The story of {raw_topic} continues."])
        return self.rng.choice(pool)
