"""Semantic scene knowledge base — TF-IDF powered scene matching.

Replaces brittle substring keyword matching with semantic similarity.
The engine learns relationships between words through TF-IDF vector space:
a query about "collapsing star" can match a template about "black hole"
because they share related vocabulary.

Usage:
    from src.scene_knowledge import semantic_scene, build_knowledge
    scene = semantic_scene("A black hole forms when a massive star collapses")
    # Returns matched scene dict with bg, elements, atmosphere, mood
"""

import math
import re
from collections import Counter


# ── TF-IDF Semantic Matcher ──────────────────────────────────────

class SemanticMatcher:
    """Matches narration against scene templates using TF-IDF + cosine similarity.
    
    Learns term importance across the template corpus. Words that appear
    in few templates (like "dinosaur" or "blackhole") get higher weight
    than common words (like "world" or "time").
    """

    def __init__(self):
        self.templates = []
        self._built = False

    def add(self, template: dict):
        self.templates.append(template)
        self._built = False

    def build(self):
        self.tokenized_docs = []
        self.vocab = set()
        for t in self.templates:
            tokens = self._tokenize(" ".join(t["keywords"]))
            self.tokenized_docs.append(tokens)
            self.vocab.update(tokens)

        N = len(self.templates)
        self.idf = {}
        for word in self.vocab:
            df = sum(1 for doc in self.tokenized_docs if word in doc)
            self.idf[word] = math.log((N + 1) / (df + 1)) + 1

        self.tfidf_vectors = []
        for doc in self.tokenized_docs:
            tf = Counter(doc)
            max_tf = max(tf.values()) if tf else 1
            vec = {}
            for word, count in tf.items():
                if word in self.idf:
                    vec[word] = (count / max_tf) * self.idf[word]
            self.tfidf_vectors.append(vec)

        self._built = True

    def _tokenize(self, text: str) -> list:
        return re.findall(r'\b[a-z]{2,}\b', text.lower())

    def _cosine_similarity(self, vec1: dict, vec2: dict) -> float:
        all_words = set(vec1) | set(vec2)
        dot = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)
        n1 = math.sqrt(sum(v * v for v in vec1.values()))
        n2 = math.sqrt(sum(v * v for v in vec2.values()))
        return dot / (n1 * n2) if n1 and n2 else 0.0

    def match(self, text: str, threshold: float = 0.2) -> tuple:
        if not self._built:
            self.build()
        words = self._tokenize(text)
        if not words:
            return None, 0.0
        tf = Counter(words)
        max_tf = max(tf.values())
        query_vec = {}
        for word, count in tf.items():
            if word in self.idf:
                query_vec[word] = (count / max_tf) * self.idf[word]
        
        # Bigram context check: detect false positives from idiomatic phrases
        tl = text.lower()
        false_positive_ids = set()
        from src.concept_extractor import PHRASE_FALSE_POSITIVES
        for concept, phrases in PHRASE_FALSE_POSITIVES.items():
            if any(p in tl for p in phrases):
                # Find templates whose strong keywords include this concept
                for i, tmpl in enumerate(self.templates):
                    kw_joined = " ".join(tmpl["keywords"])
                    if concept in kw_joined or concept + "s" in kw_joined:
                        # Only penalize if the template relies heavily on this word
                        unique_words = set(self._tokenize(kw_joined))
                        if concept in unique_words or concept + "s" in unique_words:
                            false_positive_ids.add(i)
        
        best_score = 0
        best = None
        for i, tmpl in enumerate(self.templates):
            score = self._cosine_similarity(query_vec, self.tfidf_vectors[i])
            # Apply penalty for false positive templates
            if i in false_positive_ids:
                score *= 0.3  # 70% penalty for idiomatically-used keywords
            if score > best_score:
                best_score = score
                best = tmpl
        if best and best_score >= threshold:
            return best, best_score
        return None, best_score


# ── Knowledge Base ─────────────────────────────────────────────

def _d(s):
    """Make a deep copy of a scene dict to avoid mutation."""
    import copy
    return copy.deepcopy(s)


KNOWLEDGE_TEMPLATES = [
    # ═══════════════════════════════════════════════════════════════
    #  COSMOS & SPACE
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "black_hole",
        "keywords": [
            "black hole", "singularity", "event horizon", "gravitational collapse",
            "gravitational pull", "spaghettification", "supermassive", "accretion disk",
            "star collapses", "space time", "wormhole", "schwarzschild",
            "gravity well", "cosmic vacuum", "dark star", "gravitational wave",
            "collapsing star", "dense core", "infinite density", "singularity"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[2, 2, 15], [8, 3, 25]], "horizon": 0.0},
            "elements": [
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 50, "fill": [0, 0, 0]},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 70, "fill": [60, 20, 60, 35],
                 "stroke": [200, 80, 180], "stroke_width": 3},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 90, "fill": [30, 8, 40, 15],
                 "stroke": [120, 60, 160], "stroke_width": 1},
                {"type": "star", "x": 0.15, "y": 0.12, "radius": 2, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.78, "y": 0.08, "radius": 1.5, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.82, "y": 0.35, "radius": 1.8, "fill": [255, 200, 200]},
                {"type": "star", "x": 0.12, "y": 0.55, "radius": 1.2, "fill": [200, 255, 200]},
                {"type": "star", "x": 0.88, "y": 0.65, "radius": 1.5, "fill": [255, 255, 255]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 40, "fog": False},
            "mood": "mysterious"
        }
    },

    {
        "id": "solar_system",
        "keywords": [
            "solar system", "planet orbit", "eight planets", "orbiting the sun",
            "jupiter", "saturn", "mars", "venus", "mercury", "uranus", "neptune",
            "inner planets", "outer planets", "planetary", "asteroid belt",
            "dwarf planet", "pluto", "gas giant", "rocky planet", "rings of saturn"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[2, 2, 18], [8, 4, 28]], "horizon": 0.0},
            "elements": [
                {"type": "sun", "x": 0.5, "y": 0.06, "radius": 16, "fill": [255, 230, 80]},
                {"type": "circle", "x": 0.5, "y": 0.3, "radius": 40, "fill": None,
                 "stroke": [100, 100, 150, 35], "stroke_width": 1},
                {"type": "circle", "x": 0.5, "y": 0.3, "radius": 60, "fill": None,
                 "stroke": [100, 100, 150, 25], "stroke_width": 1},
                {"type": "circle", "x": 0.5, "y": 0.3, "radius": 80, "fill": None,
                 "stroke": [100, 100, 150, 20], "stroke_width": 1},
                {"type": "circle", "x": 0.5, "y": 0.3, "radius": 100, "fill": None,
                 "stroke": [100, 100, 150, 15], "stroke_width": 1},
                {"type": "star", "x": 0.48, "y": 0.27, "radius": 3, "fill": [180, 100, 50]},
                {"type": "star", "x": 0.55, "y": 0.24, "radius": 3.5, "fill": [200, 160, 80]},
                {"type": "star", "x": 0.45, "y": 0.22, "radius": 2.5, "fill": [80, 120, 200]},
                {"type": "star", "x": 0.6, "y": 0.33, "radius": 2, "fill": [200, 180, 100]},
                {"type": "star", "x": 0.52, "y": 0.38, "radius": 2.8, "fill": [100, 180, 200]},
                {"type": "star", "x": 0.42, "y": 0.35, "radius": 2, "fill": [200, 100, 100]},
                {"type": "star", "x": 0.58, "y": 0.18, "radius": 1.8, "fill": [150, 150, 200]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 30, "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "galaxy_nebula",
        "keywords": [
            "galaxy", "nebula", "milky way", "andromeda", "spiral galaxy",
            "star cluster", "cosmic dust", "stellar nursery", "deep space",
            "interstellar", "cosmos", "universe", "cosmic", "celestial",
            "constellation", "star system", "astronomical", "outer space"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[3, 2, 18], [12, 6, 30]], "horizon": 0.0},
            "elements": [
                {"type": "ellipse", "x": 0.5, "y": 0.45, "width": 300, "height": 120,
                 "fill": [60, 20, 80, 25], "stroke": [100, 40, 140, 15], "stroke_width": 1},
                {"type": "ellipse", "x": 0.5, "y": 0.45, "width": 200, "height": 60,
                 "fill": [40, 10, 60, 35]},
                {"type": "ellipse", "x": 0.5, "y": 0.45, "width": 80, "height": 25,
                 "fill": [200, 180, 220, 40]},
                {"type": "star", "x": 0.2, "y": 0.15, "radius": 2.5, "fill": [255, 240, 200]},
                {"type": "star", "x": 0.7, "y": 0.1, "radius": 1.5, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.8, "y": 0.3, "radius": 3, "fill": [255, 200, 180]},
                {"type": "star", "x": 0.15, "y": 0.5, "radius": 1.8, "fill": [180, 255, 200]},
                {"type": "star", "x": 0.9, "y": 0.6, "radius": 2, "fill": [255, 220, 255]},
                {"type": "star", "x": 0.4, "y": 0.75, "radius": 1.5, "fill": [200, 255, 255]},
                {"type": "star", "x": 0.65, "y": 0.7, "radius": 2.2, "fill": [255, 200, 200]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 50, "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "big_bang",
        "keywords": [
            "big bang", "beginning of universe", "cosmic inflation",
            "primordial", "initial singularity", "universe began",
            "first moments", "cosmic expansion", "early universe",
            "birth of cosmos", "origin of everything", "fundamental forces"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[0, 0, 0], [20, 5, 40]], "horizon": 0.0},
            "elements": [
                {"type": "circle", "x": 0.5, "y": 0.45, "radius": 10, "fill": [255, 250, 220]},
                {"type": "circle", "x": 0.5, "y": 0.45, "radius": 25, "fill": [255, 200, 100, 60]},
                {"type": "circle", "x": 0.5, "y": 0.45, "radius": 50, "fill": [200, 100, 60, 30]},
                {"type": "circle", "x": 0.5, "y": 0.45, "radius": 80, "fill": [100, 50, 80, 15]},
                {"type": "circle", "x": 0.5, "y": 0.45, "radius": 120, "fill": [60, 20, 60, 8]},
                {"type": "star", "x": 0.1, "y": 0.1, "radius": 1, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.9, "y": 0.1, "radius": 1, "fill": [255, 200, 200]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    {
        "id": "astronaut_space",
        "keywords": [
            "astronaut", "space travel", "space station", "spacecraft",
            "rocket launch", "space mission", "moon landing", "space walk",
            "zero gravity", "space suit", "international space station",
            "space exploration", "nasa", "spacex", "orbit earth",
            "launch pad", "space flight", "cosmonaut", "shuttle"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[2, 2, 20], [8, 4, 35]], "horizon": 0.0},
            "elements": [
                {"type": "astronaut", "x": 0.5, "y": 0.4, "scale": 5.0, "fill": [220, 220, 240]},
                {"type": "star", "x": 0.15, "y": 0.12, "radius": 2, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.8, "y": 0.08, "radius": 1.5, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.85, "y": 0.3, "radius": 1.8, "fill": [255, 200, 200]},
                {"type": "star", "x": 0.1, "y": 0.5, "radius": 1.2, "fill": [200, 255, 200]},
                {"type": "star", "x": 0.9, "y": 0.6, "radius": 1.5, "fill": [255, 255, 255]},
                {"type": "circle", "x": 0.5, "y": 0.82, "radius": 80, "fill": [20, 60, 120, 40]},
                {"type": "circle", "x": 0.5, "y": 0.82, "radius": 60, "fill": [30, 80, 160, 30]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 35, "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "supernova",
        "keywords": [
            "supernova", "star explodes", "stellar explosion", "exploding star",
            "nova", "neutron star", "pulsar", "gamma ray burst",
            "star death", "bright explosion", "stellar remnant",
            "white dwarf", "type ia", "core collapse"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[2, 2, 15], [15, 5, 30]], "horizon": 0.0},
            "elements": [
                {"type": "star", "x": 0.5, "y": 0.4, "radius": 15, "fill": [255, 240, 200]},
                {"type": "star", "x": 0.5, "y": 0.4, "radius": 30, "fill": [255, 200, 100, 40]},
                {"type": "star", "x": 0.5, "y": 0.4, "radius": 50, "fill": [200, 100, 60, 20]},
                {"type": "star", "x": 0.5, "y": 0.4, "radius": 80, "fill": [100, 50, 80, 10]},
                {"type": "line", "x1": 0.3, "y1": 0.25, "x2": 0.4, "y2": 0.35, "fill": [255, 200, 50], "stroke_width": 2},
                {"type": "line", "x1": 0.6, "y1": 0.3, "x2": 0.7, "y2": 0.2, "fill": [255, 180, 60], "stroke_width": 2},
                {"type": "line", "x1": 0.35, "y1": 0.55, "x2": 0.25, "y2": 0.6, "fill": [255, 150, 50], "stroke_width": 1.5},
                {"type": "line", "x1": 0.65, "y1": 0.5, "x2": 0.75, "y2": 0.55, "fill": [255, 160, 60], "stroke_width": 1.5},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  TECHNOLOGY & COMPUTING
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "computer_chip",
        "keywords": [
            "computer chip", "microchip", "semiconductor", "transistor",
            "integrated circuit", "processor", "cpu", "silicon wafer",
            "circuit board", "motherboard", "nanometer", "computing power",
            "microprocessor", "logic gate", "electronic component"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[12, 18, 35], [25, 30, 55]], "horizon": 0.5, "ground_color": [15, 20, 40]},
            "elements": [
                {"type": "rect", "x": 0.2, "y": 0.3, "width": 0.28, "height": 0.35, "fill": [30, 45, 80, 180], "stroke": [80, 160, 220], "stroke_width": 2},
                {"type": "rect", "x": 0.52, "y": 0.35, "width": 0.28, "height": 0.25, "fill": [30, 45, 80, 180], "stroke": [80, 160, 220], "stroke_width": 2},
                {"type": "line", "x1": 0.48, "y1": 0.42, "x2": 0.52, "y2": 0.42, "fill": [80, 220, 140], "stroke_width": 2},
                {"type": "line", "x1": 0.48, "y1": 0.52, "x2": 0.52, "y2": 0.52, "fill": [80, 220, 140], "stroke_width": 2},
                {"type": "line", "x1": 0.2, "y1": 0.6, "x2": 0.48, "y2": 0.6, "fill": [80, 200, 220], "stroke_width": 2},
                {"type": "line", "x1": 0.52, "y1": 0.5, "x2": 0.8, "y2": 0.5, "fill": [80, 200, 220], "stroke_width": 2},
                {"type": "circle", "x": 0.48, "y": 0.42, "radius": 3, "fill": [120, 255, 180]},
                {"type": "circle", "x": 0.52, "y": 0.42, "radius": 3, "fill": [120, 255, 180]},
                {"type": "circle", "x": 0.48, "y": 0.52, "radius": 3, "fill": [120, 255, 180]},
                {"type": "circle", "x": 0.52, "y": 0.5, "radius": 3, "fill": [120, 220, 255]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "internet_network",
        "keywords": [
            "internet", "world wide web", "network", "online", "digital age",
            "fiber optic", "broadband", "connectivity", "data transfer",
            "cloud computing", "server", "web", "cyberspace", "global network",
            "information superhighway", "wifi", "wireless", "bandwidth"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[8, 12, 28], [18, 22, 45]], "horizon": 0.0},
            "elements": [
                {"type": "circle", "x": 0.15, "y": 0.25, "radius": 6, "fill": [60, 200, 120]},
                {"type": "circle", "x": 0.5, "y": 0.15, "radius": 8, "fill": [80, 180, 255]},
                {"type": "circle", "x": 0.85, "y": 0.3, "radius": 6, "fill": [60, 200, 120]},
                {"type": "circle", "x": 0.3, "y": 0.55, "radius": 5, "fill": [200, 180, 80]},
                {"type": "circle", "x": 0.7, "y": 0.5, "radius": 5, "fill": [200, 180, 80]},
                {"type": "circle", "x": 0.5, "y": 0.7, "radius": 7, "fill": [80, 180, 255]},
                {"type": "line", "x1": 0.15, "y1": 0.25, "x2": 0.5, "y2": 0.15, "fill": [60, 180, 200, 60], "stroke_width": 1},
                {"type": "line", "x1": 0.5, "y1": 0.15, "x2": 0.85, "y2": 0.3, "fill": [60, 180, 200, 60], "stroke_width": 1},
                {"type": "line", "x1": 0.15, "y1": 0.25, "x2": 0.3, "y2": 0.55, "fill": [60, 180, 200, 60], "stroke_width": 1},
                {"type": "line", "x1": 0.85, "y1": 0.3, "x2": 0.7, "y2": 0.5, "fill": [60, 180, 200, 60], "stroke_width": 1},
                {"type": "line", "x1": 0.3, "y1": 0.55, "x2": 0.5, "y2": 0.7, "fill": [60, 180, 200, 60], "stroke_width": 1},
                {"type": "line", "x1": 0.7, "y1": 0.5, "x2": 0.5, "y2": 0.7, "fill": [60, 180, 200, 60], "stroke_width": 1},
                {"type": "line", "x1": 0.5, "y1": 0.15, "x2": 0.5, "y2": 0.7, "fill": [60, 180, 200, 40], "stroke_width": 1},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "artificial_intelligence",
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "AI", "intelligent machine", "smart algorithm",
            "cognitive computing", "pattern recognition", "data science",
            "automated reasoning", "computer vision", "natural language",
            "intelligent system", "robot brain", "digital mind"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[10, 14, 30], [22, 26, 50]], "horizon": 0.0},
            "elements": [
                {"type": "human", "x": 0.3, "y": 0.45, "scale": 4.5, "fill": [140, 145, 155]},
                {"type": "gear", "x": 0.65, "y": 0.42, "scale": 5.0, "fill": [180, 185, 200]},
                {"type": "circle", "x": 0.3, "y": 0.3, "radius": 8, "fill": [100, 200, 255]},
                {"type": "circle", "x": 0.3, "y": 0.3, "radius": 4, "fill": [255, 255, 255]},
                {"type": "circle", "x": 0.65, "y": 0.3, "radius": 6, "fill": [100, 200, 255, 60]},
                {"type": "line", "x1": 0.35, "y1": 0.32, "x2": 0.6, "y2": 0.32, "fill": [100, 200, 255, 80], "stroke_width": 2},
                {"type": "line", "x1": 0.35, "y1": 0.37, "x2": 0.6, "y2": 0.37, "fill": [100, 200, 255, 60], "stroke_width": 1},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "robotics",
        "keywords": [
            "robot", "robotics", "automation", "autonomous", "android",
            "humanoid", "industrial robot", "robotic arm", "drone",
            "self driving", "autonomous vehicle", "cyborg", "bionic",
            "mechanical", "servo", "actuator", "automated factory"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[60, 65, 80], [80, 85, 100]], "horizon": 0.0},
            "elements": [
                {"type": "human", "x": 0.35, "y": 0.4, "scale": 5.0, "fill": [160, 165, 175]},
                {"type": "rect", "x": 0.25, "y": 0.3, "width": 0.2, "height": 0.05, "fill": [60, 60, 80], "stroke": [200, 200, 220], "stroke_width": 2},
                {"type": "rect", "x": 0.3, "y": 0.35, "width": 0.1, "height": 0.04, "fill": [60, 60, 80], "stroke": [200, 200, 220], "stroke_width": 1},
                {"type": "circle", "x": 0.35, "y": 0.3, "radius": 4, "fill": [100, 200, 255]},
                {"type": "circle", "x": 0.35, "y": 0.3, "radius": 2, "fill": [255, 255, 255]},
                {"type": "circle", "x": 0.65, "y": 0.7, "radius": 12, "fill": [100, 100, 120]},
                {"type": "circle", "x": 0.65, "y": 0.7, "radius": 8, "fill": [80, 80, 100]},
                {"type": "circle", "x": 0.65, "y": 0.7, "radius": 4, "fill": [60, 60, 80]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "programming_code",
        "keywords": [
            "programming", "coding", "software development", "computer program",
            "algorithm", "data structure", "source code", "debugging",
            "programmer", "developer", "software engineer", "app development",
            "python", "javascript", "web development", "open source",
            "version control", "api", "database", "full stack"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[12, 18, 28], [25, 30, 45]], "horizon": 0.0},
            "elements": [
                {"type": "rect", "x": 0.25, "y": 0.25, "width": 0.2, "height": 0.35, "fill": [20, 25, 40, 200], "stroke": [60, 180, 120], "stroke_width": 1},
                {"type": "rect", "x": 0.55, "y": 0.3, "width": 0.2, "height": 0.25, "fill": [20, 25, 40, 200], "stroke": [60, 180, 120], "stroke_width": 1},
                {"type": "line", "x1": 0.3, "y1": 0.3, "x2": 0.4, "y2": 0.3, "fill": [80, 220, 140], "stroke_width": 1},
                {"type": "line", "x1": 0.3, "y1": 0.35, "x2": 0.38, "y2": 0.35, "fill": [80, 220, 140], "stroke_width": 1},
                {"type": "line", "x1": 0.3, "y1": 0.4, "x2": 0.42, "y2": 0.4, "fill": [80, 220, 140], "stroke_width": 1},
                {"type": "line", "x1": 0.3, "y1": 0.45, "x2": 0.36, "y2": 0.45, "fill": [80, 220, 140], "stroke_width": 1},
                {"type": "line", "x1": 0.6, "y1": 0.35, "x2": 0.7, "y2": 0.35, "fill": [80, 220, 140], "stroke_width": 1},
                {"type": "line", "x1": 0.6, "y1": 0.4, "x2": 0.68, "y2": 0.4, "fill": [80, 220, 140], "stroke_width": 1},
                {"type": "line", "x1": 0.6, "y1": 0.45, "x2": 0.65, "y2": 0.45, "fill": [80, 220, 140], "stroke_width": 1},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  HUMAN BODY & MEDICINE
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "human_heart",
        "keywords": [
            "human heart", "heart beats", "pumping blood", "cardiovascular",
            "cardiac", "blood circulation", "heart pumps", "heart muscle",
            "aorta", "ventricle", "atrium", "heart rate", "blood flow",
            "circulatory system", "coronary", "heart disease", "heart attack"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[235, 228, 218], [218, 212, 202]], "horizon": 0.6, "ground_color": [200, 195, 185]},
            "elements": [
                {"type": "heart", "x": 0.5, "y": 0.4, "scale": 6.5, "fill": [220, 50, 50]},
                {"type": "line", "x1": 0.35, "y1": 0.45, "x2": 0.2, "y2": 0.58, "fill": [200, 50, 50], "stroke_width": 3},
                {"type": "line", "x1": 0.65, "y1": 0.45, "x2": 0.8, "y2": 0.58, "fill": [50, 100, 220], "stroke_width": 3},
                {"type": "circle", "x": 0.2, "y": 0.58, "radius": 3.5, "fill": [230, 60, 60]},
                {"type": "circle", "x": 0.8, "y": 0.58, "radius": 3.5, "fill": [60, 100, 230]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    {
        "id": "human_brain",
        "keywords": [
            "human brain", "cerebrum", "cerebellum", "neuron", "synapse",
            "cerebral cortex", "brain hemisphere", "neural network",
            "brain function", "nervous system", "brain stem",
            "grey matter", "white matter", "brain activity",
            "cognitive function", "memory", "thought process",
            "86 billion neurons", "brain wave", "neurotransmitter"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[238, 232, 222], [222, 216, 206]], "horizon": 0.6, "ground_color": [200, 195, 185]},
            "elements": [
                {"type": "ellipse", "x": 0.3, "y": 0.4, "width": 110, "height": 85, "fill": [200, 180, 200]},
                {"type": "ellipse", "x": 0.6, "y": 0.4, "width": 110, "height": 85, "fill": [190, 170, 195]},
                {"type": "line", "x1": 0.3, "y1": 0.4, "x2": 0.6, "y2": 0.4, "fill": [100, 100, 100], "stroke_width": 2},
                {"type": "line", "x1": 0.3, "y1": 0.4, "x2": 0.25, "y2": 0.65, "fill": [160, 140, 165], "stroke_width": 1},
                {"type": "line", "x1": 0.6, "y1": 0.4, "x2": 0.65, "y2": 0.65, "fill": [160, 140, 165], "stroke_width": 1},
                {"type": "circle", "x": 0.3, "y": 0.4, "radius": 2.5, "fill": [100, 100, 100]},
                {"type": "circle", "x": 0.6, "y": 0.4, "radius": 2.5, "fill": [100, 100, 100]},
                {"type": "circle", "x": 0.25, "y": 0.55, "radius": 1.5, "fill": [100, 100, 100]},
                {"type": "circle", "x": 0.65, "y": 0.55, "radius": 1.5, "fill": [100, 100, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    {
        "id": "dna_genetics",
        "keywords": [
            "dna", "gene", "genes", "genetic", "genetics", "genome",
            "chromosome", "chromosomes", "nucleotide",
            "double helix", "genetic code", "base pair",
            "adenine", "guanine", "cytosine", "thymine",
            "replication", "transcription", "translation",
            "blueprint of life", "genetic information", "heredity",
            "hereditary", "mutation", "mutations",
            "gene expression", "protein synthesis",
            "inherited trait", "inherit traits",
            "genetic material", "genetic instruction",
            "gene sequence", "human genome",
            "molecular biology", "nucleic acid",
            "deoxyribonucleic"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[232, 228, 225], [215, 210, 205]], "horizon": 0.6, "ground_color": [195, 190, 180]},
            "elements": [
                {"type": "dna", "x": 0.3, "y": 0.5, "width": 100, "height": 160, "fill": [60, 140, 230]},
                {"type": "dna", "x": 0.7, "y": 0.5, "width": 100, "height": 160, "fill": [60, 180, 120]},
                {"type": "circle", "x": 0.3, "y": 0.28, "radius": 6, "fill": [200, 200, 60]},
                {"type": "circle", "x": 0.7, "y": 0.28, "radius": 6, "fill": [60, 200, 200]},
                {"type": "circle", "x": 0.3, "y": 0.72, "radius": 5, "fill": [200, 100, 60]},
                {"type": "circle", "x": 0.7, "y": 0.72, "radius": 5, "fill": [100, 200, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    {
        "id": "human_anatomy",
        "keywords": [
            "human body", "human anatomy", "skeleton", "muscle", "organ",
            "respiratory system", "digestive system", "skeletal system",
            "spinal cord", "rib cage", "pelvis", "cranium", "femur",
            "ligament", "tendon", "joint", "cartilage", "vertebra"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[225, 220, 215], [210, 205, 200]], "horizon": 0.6, "ground_color": [190, 185, 175]},
            "elements": [
                {"type": "human", "x": 0.35, "y": 0.5, "scale": 5.0, "fill": [200, 180, 160]},
                {"type": "circle", "x": 0.35, "y": 0.25, "radius": 15, "fill": [210, 190, 170], "stroke": [160, 140, 120], "stroke_width": 2},
                {"type": "heart", "x": 0.65, "y": 0.35, "scale": 3.5, "fill": [210, 60, 60]},
                {"type": "circle", "x": 0.65, "y": 0.22, "radius": 8, "fill": [200, 180, 200]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  NATURE & WEATHER
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "volcano",
        "keywords": [
            "volcano", "volcanic", "eruption", "molten lava", "volcanic ash",
            "lava flows", "magma", "volcanic crater", "pyroclastic",
            "volcanic eruption", "active volcano", "volcanic cone",
            "lava tube", "volcanic rock", "igneous", "volcanic island",
            "ring of fire", "volcanic activity", "erupts with"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[90, 60, 40], [55, 35, 25]], "horizon": 0.55, "ground_color": [35, 22, 18]},
            "elements": [
                {"type": "mountain", "x": 0.5, "y": 0.55, "width": 0.55, "height": 0.38, "fill": [75, 45, 30]},
                {"type": "circle", "x": 0.5, "y": 0.23, "radius": 14, "fill": [255, 140, 20]},
                {"type": "circle", "x": 0.5, "y": 0.23, "radius": 9, "fill": [255, 190, 40]},
                {"type": "fire", "x": 0.5, "y": 0.55, "scale": 6.0, "fill": [255, 90, 15]},
                {"type": "line", "x1": 0.35, "y1": 0.28, "x2": 0.3, "y2": 0.08, "fill": [255, 120, 20], "stroke_width": 3},
                {"type": "line", "x1": 0.65, "y1": 0.28, "x2": 0.7, "y2": 0.1, "fill": [255, 120, 20], "stroke_width": 2},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "dramatic"
        }
    },

    {
        "id": "hurricane",
        "keywords": [
            "hurricane", "cyclone", "typhoon", "tropical storm", "eye of storm",
            "storm surge", "hurricane season", "category five",
            "tropical cyclone", "wind speed", "barometric pressure",
            "storm system", "severe weather", "coastal storm",
            "devastating winds", "destructive winds",
            "ocean storm", "storm forming", "storm forms",
            "strong winds", "powerful storm", "massive storm",
            "storm clouds", "wind damage", "flooding storm",
            "heavy rainfall", "extreme weather", "weather system",
            "tropical depression", "wind speed storm"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[90, 90, 110], [55, 55, 75]], "horizon": 0.0},
            "elements": [
                {"type": "ellipse", "x": 0.5, "y": 0.4, "width": 180, "height": 110, "fill": [70, 70, 90, 35], "stroke": [140, 140, 170], "stroke_width": 2},
                {"type": "ellipse", "x": 0.5, "y": 0.4, "width": 110, "height": 65, "fill": [55, 55, 75, 55], "stroke": [180, 180, 210], "stroke_width": 1},
                {"type": "ellipse", "x": 0.5, "y": 0.4, "width": 40, "height": 25, "fill": [190, 190, 210]},
                {"type": "cloud", "x": 0.25, "y": 0.12, "scale": 3.5, "fill": [45, 45, 65]},
                {"type": "cloud", "x": 0.75, "y": 0.15, "scale": 3.25, "fill": [45, 45, 65]},
                {"type": "cloud", "x": 0.15, "y": 0.55, "scale": 2.5, "fill": [50, 50, 70]},
                {"type": "cloud", "x": 0.85, "y": 0.5, "scale": 2.75, "fill": [50, 50, 70]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic"
        }
    },

    {
        "id": "thunderstorm",
        "keywords": [
            "thunderstorm", "lightning", "thunder", "electrical storm",
            "storm cloud", "cumulonimbus", "downpour", "heavy rain",
            "flash flood", "hailstorm", "severe thunderstorm",
            "supercell", "cloud to ground", "lightning strike"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[45, 45, 60], [25, 25, 40]], "horizon": 0.5, "ground_color": [20, 20, 30]},
            "elements": [
                {"type": "cloud", "x": 0.35, "y": 0.15, "scale": 5.0, "fill": [40, 40, 55]},
                {"type": "cloud", "x": 0.75, "y": 0.12, "scale": 4.25, "fill": [40, 40, 55]},
                {"type": "line", "x1": 0.4, "y1": 0.18, "x2": 0.35, "y2": 0.45, "fill": [255, 230, 50], "stroke_width": 4},
                {"type": "line", "x1": 0.35, "y1": 0.45, "x2": 0.3, "y2": 0.3, "fill": [255, 230, 50], "stroke_width": 3},
                {"type": "line", "x1": 0.38, "y1": 0.3, "x2": 0.45, "y2": 0.5, "fill": [255, 230, 50], "stroke_width": 2},
                {"type": "line", "x1": 0.7, "y1": 0.15, "x2": 0.75, "y2": 0.4, "fill": [255, 230, 50], "stroke_width": 3},
                {"type": "line", "x1": 0.75, "y1": 0.4, "x2": 0.72, "y2": 0.28, "fill": [255, 230, 50], "stroke_width": 2},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic"
        }
    },

    {
        "id": "earthquake",
        "keywords": [
            "earthquake", "seismic", "tremor", "tectonic shift",
            "seismic wave", "richter scale", "ground shaking",
            "fault line", "seismic activity", "aftershock",
            "epicenter", "plate movement", "earth's crust"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[150, 140, 120], [110, 100, 85]], "horizon": 0.5, "ground_color": [90, 80, 65]},
            "elements": [
                {"type": "building", "x": 0.35, "y": 0.5, "scale": 3.5, "fill": [130, 115, 95]},
                {"type": "building", "x": 0.65, "y": 0.53, "scale": 2.5, "fill": [120, 105, 85]},
                {"type": "line", "x1": 0, "y1": 0.6, "x2": 1, "y2": 0.65, "fill": [60, 50, 40], "stroke_width": 3},
                {"type": "line", "x1": 0, "y1": 0.62, "x2": 1, "y2": 0.67, "fill": [40, 35, 30], "stroke_width": 2},
                {"type": "polygon", "points": [0.0, 0.6, 0.3, 0.58, 0.5, 0.62, 0.7, 0.6, 1.0, 0.65],
                 "fill": [70, 60, 50]},
                {"type": "line", "x1": 0.35, "y1": 0.35, "x2": 0.38, "y2": 0.4, "fill": [100, 90, 75], "stroke_width": 1},
                {"type": "line", "x1": 0.65, "y1": 0.42, "x2": 0.62, "y2": 0.46, "fill": [100, 90, 75], "stroke_width": 1},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic"
        }
    },

    {
        "id": "desert",
        "keywords": [
            "desert", "sahara", "arid", "sand dune", "dry land",
            "scorching heat", "sandstorm", "oasis", "cactus",
            "barren landscape", "drought", "hot climate",
            "desertification", "dry climate", "camel"
        ],
        "scene": {
            "bg": {"type": "desert", "colors": [[225, 195, 140], [195, 165, 115]], "horizon": 0.5, "ground_color": [185, 155, 100]},
            "elements": [
                {"type": "hill", "x": 0.3, "y": 0.6, "width": 0.4, "height": 0.2, "fill": [200, 170, 120]},
                {"type": "hill", "x": 0.7, "y": 0.62, "width": 0.35, "height": 0.18, "fill": [190, 160, 110]},
                {"type": "sun", "x": 0.8, "y": 0.1, "radius": 22, "fill": [255, 210, 60]},
                {"type": "sun", "x": 0.8, "y": 0.1, "radius": 28, "fill": [255, 220, 80, 30]},
                {"type": "plant", "x": 0.2, "y": 0.65, "scale": 2.5, "fill": [80, 140, 60]},
                {"type": "plant", "x": 0.8, "y": 0.68, "scale": 2.0, "fill": [70, 130, 55]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    {
        "id": "rainforest",
        "keywords": [
            "rainforest", "jungle", "tropical forest", "canopy", "biodiversity",
            "amazon", "dense forest", "wilderness", "exotic plants",
            "tropical", "humid", "monsoon forest", "forest floor",
            "understory", "emergent layer", "vine", "tropical tree"
        ],
        "scene": {
            "bg": {"type": "forest", "colors": [[100, 160, 100], [60, 120, 60]], "horizon": 0.55, "ground_color": [40, 80, 35]},
            "elements": [
                {"type": "tree", "x": 0.2, "y": 0.68, "scale": 4.0, "tree_style": "round", "fill": [45, 115, 45]},
                {"type": "tree", "x": 0.5, "y": 0.7, "scale": 5.0, "tree_style": "pine", "fill": [35, 95, 35]},
                {"type": "tree", "x": 0.8, "y": 0.69, "scale": 4.25, "tree_style": "round", "fill": [50, 120, 50]},
                {"type": "flower", "x": 0.35, "y": 0.78, "scale": 2.5, "fill": [230, 80, 130]},
                {"type": "flower", "x": 0.65, "y": 0.8, "scale": 2.0, "fill": [230, 200, 60]},
                {"type": "plant", "x": 0.1, "y": 0.75, "scale": 2.5, "fill": [60, 140, 60]},
                {"type": "plant", "x": 0.9, "y": 0.76, "scale": 2.0, "fill": [55, 130, 55]},
            ],
            "atmosphere": {"particles": "mist", "fog": True},
            "mood": "peaceful"
        }
    },

    {
        "id": "mountain",
        "keywords": [
            "mountain", "peak", "summit", "alpine", "mountain range",
            "high altitude", "snow capped", "cliff", "ridge",
            "valley", "foothill", "elevation", "topography",
            "himalayas", "andes", "rocky mountain", "alps"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[160, 190, 220], [120, 150, 190]], "horizon": 0.5, "ground_color": [80, 120, 80]},
            "elements": [
                {"type": "mountain", "x": 0.3, "y": 0.5, "width": 0.5, "height": 0.4, "fill": [100, 130, 160]},
                {"type": "mountain", "x": 0.7, "y": 0.55, "width": 0.35, "height": 0.3, "fill": [110, 140, 170]},
                {"type": "mountain", "x": 0.15, "y": 0.55, "width": 0.25, "height": 0.25, "fill": [120, 150, 180]},
                {"type": "snow", "x": 0.3, "y": 0.25, "width": 0.2, "height": 0.05, "fill": [230, 240, 250]},
                {"type": "snow", "x": 0.7, "y": 0.35, "width": 0.1, "height": 0.03, "fill": [230, 240, 250]},
                {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 2.5, "fill": [200, 210, 230]},
                {"type": "tree", "x": 0.2, "y": 0.72, "scale": 2.5, "tree_style": "pine", "fill": [40, 100, 40]},
                {"type": "tree", "x": 0.8, "y": 0.74, "scale": 2.0, "tree_style": "pine", "fill": [35, 90, 35]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  HISTORY & CIVILIZATION
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "ancient_egypt",
        "keywords": [
            "ancient egypt", "egyptian", "pharaoh", "pyramid", "sphinx",
            "nile river", "hieroglyph", "tomb", "mummy", "sarcophagus",
            "cleopatra", "tutankhamun", "valley of kings", "obelisk",
            "ankh", "eye of horus", "afterlife", "papyrus"
        ],
        "scene": {
            "bg": {"type": "desert", "colors": [[225, 195, 140], [195, 165, 110]], "horizon": 0.5, "ground_color": [180, 150, 95]},
            "elements": [
                {"type": "polygon", "points": [0.25, 0.55, 0.35, 0.18, 0.45, 0.55], "fill": [180, 140, 80]},
                {"type": "polygon", "points": [0.55, 0.58, 0.65, 0.22, 0.75, 0.58], "fill": [170, 130, 70]},
                {"type": "polygon", "points": [0.38, 0.57, 0.5, 0.3, 0.62, 0.57], "fill": [160, 120, 65]},
                {"type": "sun", "x": 0.8, "y": 0.1, "radius": 22, "fill": [255, 215, 70]},
                {"type": "line", "x1": 0, "y1": 0.58, "x2": 1, "y2": 0.58, "fill": [140, 115, 70], "stroke_width": 2},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    {
        "id": "roman_empire",
        "keywords": [
            "roman empire", "ancient rome", "roman", "caesar", "colosseum",
            "gladiator", "roman legion", "roman republic", "pax romana",
            "julius caesar", "augustus", "roman senate", "roman aqueduct",
            "roman road", "roman architecture", "roman forum",
            "byzantine", "roman emperor", "roman civilization",
            "roman empire stretched", "three continents roman",
            "rome civilization", "roman conquest", "roman province",
            "roman bath", "pompeii", "roman engineering",
            "roman history", "roman army", "roman soldier",
            "roman empire fell", "fall of rome", "western roman",
            "rome", "romans", "roman empire history",
            "gladiator battle", "public spectacle", "ancient arena",
            "roman amphitheater", "roman emperor rome",
            "roman empire large", "empire rome", "ancient roman",
            "rome city", "eternal city", "roman capital"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[215, 195, 165], [175, 155, 125]], "horizon": 0.5, "ground_color": [155, 135, 105]},
            "elements": [
                {"type": "building", "x": 0.25, "y": 0.5, "scale": 4.0, "fill": [195, 175, 145]},
                {"type": "building", "x": 0.55, "y": 0.52, "scale": 3.25, "fill": [185, 165, 135]},
                {"type": "building", "x": 0.78, "y": 0.55, "scale": 2.5, "fill": [175, 155, 125]},
                {"type": "flag", "x": 0.3, "y": 0.12, "scale": 3.0, "fill": [200, 50, 50]},
                {"type": "sun", "x": 0.12, "y": 0.08, "radius": 15, "fill": [255, 220, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },
    {
        "id": "ancient_greece",
        "keywords": [
            "ancient greece", "greek", "athens", "sparta", "philosophy",
            "democracy", "olympic", "parthenon", "greek mythology",
            "socrates", "plato", "aristotle", "greek temple",
            "greek god", "zeus", "athena", "greek column"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[200, 195, 180], [160, 155, 140]], "horizon": 0.5, "ground_color": [140, 135, 120]},
            "elements": [
                {"type": "building", "x": 0.3, "y": 0.5, "scale": 4.0, "fill": [195, 185, 165]},
                {"type": "building", "x": 0.65, "y": 0.53, "scale": 2.75, "fill": [185, 175, 155]},
                {"type": "sun", "x": 0.15, "y": 0.1, "radius": 16, "fill": [255, 225, 120]},
                {"type": "line", "x1": 0.25, "y1": 0.35, "x2": 0.25, "y2": 0.5, "fill": [180, 170, 150], "stroke_width": 4},
                {"type": "line", "x1": 0.35, "y1": 0.35, "x2": 0.35, "y2": 0.5, "fill": [180, 170, 150], "stroke_width": 4},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    {
        "id": "medieval_castle",
        "keywords": [
            "medieval", "castle", "knight", "kingdom", "middle ages",
            "fortress", "king", "queen", "throne", "manor",
            "feudal", "crusade", "cathedral", "gothic",
            "village", "peasant", "noble", "siege", "rampart",
            "stone walls", "towering battlements", "defended castle",
            "knight armor", "medieval times", "dark ages",
            "castle siege", "royal court", "medieval kingdom",
            "chivalry", "heraldry", "drawbridge", "moat castle",
            "castle tower", "keep fortress", "medieval Europe",
            "castle gate", "stone fortress", "castle walls",
            "arrow slit", "castle defense", "medieval history"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[160, 175, 190], [120, 140, 160]], "horizon": 0.5, "ground_color": [80, 110, 80]},
            "elements": [
                {"type": "building", "x": 0.3, "y": 0.5, "scale": 4.0, "fill": [130, 120, 110]},
                {"type": "building", "x": 0.65, "y": 0.53, "scale": 3.0, "fill": [120, 110, 100]},
                {"type": "flag", "x": 0.3, "y": 0.1, "scale": 2.5, "fill": [200, 50, 50]},
                {"type": "cloud", "x": 0.5, "y": 0.15, "scale": 3.0, "fill": [190, 200, 215]},
                {"type": "cloud", "x": 0.8, "y": 0.12, "scale": 2.5, "fill": [185, 195, 210]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },
    {
        "id": "industrial_revolution",
        "keywords": [
            "industrial revolution", "steam engine", "factory", "manufacturing",
            "industrial age", "mass production", "coal mine", "textile mill",
            "steam power", "iron bridge", "railroad", "locomotive",
            "industrialization", "urbanization", "machine age"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[140, 130, 120], [95, 85, 75]], "horizon": 0.5, "ground_color": [75, 65, 55]},
            "elements": [
                {"type": "building", "x": 0.25, "y": 0.5, "scale": 3.75, "fill": [115, 95, 75]},
                {"type": "building", "x": 0.6, "y": 0.52, "scale": 3.25, "fill": [105, 85, 65]},
                {"type": "fire", "x": 0.25, "y": 0.22, "scale": 4.0, "fill": [255, 140, 40]},
                {"type": "fire", "x": 0.6, "y": 0.25, "scale": 3.0, "fill": [255, 140, 40]},
                {"type": "circle", "x": 0.25, "y": 0.24, "radius": 3, "fill": [255, 200, 60]},
                {"type": "circle", "x": 0.6, "y": 0.27, "radius": 2, "fill": [255, 200, 60]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "dramatic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  OCEAN & SEA
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "deep_ocean",
        "keywords": [
            "deep ocean", "deep sea", "ocean floor", "abyssal plain",
            "mariana trench", "midnight zone", "hydrothermal vent",
            "bioluminescent", "deep sea creature", "ocean depth",
            "pressure", "underwater volcano", "deepest point",
            "sonar", "submersible", "alien ocean"
        ],
        "scene": {
            "bg": {"type": "ocean", "sky_color": [5, 10, 30], "horizon_color": [10, 18, 45],
                   "horizon": 0.1, "water_color": [3, 10, 40]},
            "elements": [
                {"type": "fish", "x": 0.2, "y": 0.35, "scale": 2.5, "fill": [60, 120, 180]},
                {"type": "fish", "x": 0.7, "y": 0.4, "scale": 2.0, "fill": [80, 100, 160]},
                {"type": "fish", "x": 0.45, "y": 0.55, "scale": 1.75, "fill": [120, 80, 180]},
                {"type": "flower", "x": 0.2, "y": 0.72, "scale": 2.5, "fill": [180, 80, 140]},
                {"type": "flower", "x": 0.8, "y": 0.7, "scale": 2.0, "fill": [140, 180, 80]},
                {"type": "circle", "x": 0.35, "y": 0.3, "radius": 2, "fill": [100, 200, 180]},
                {"type": "circle", "x": 0.6, "y": 0.35, "radius": 1.5, "fill": [100, 200, 180]},
                {"type": "circle", "x": 0.5, "y": 0.5, "radius": 2, "fill": [200, 180, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "mysterious"
        }
    },

    {
        "id": "pirate_ship",
        "keywords": [
            "pirate", "pirate ship", "buccaneer", "treasure map",
            "buried treasure", "skull and crossbones", "plunder",
            "jolly roger", "caribbean", "corsair", "sea rover",
            "treasure chest", "doubloon", "shipwreck", "sunken treasure"
        ],
        "scene": {
            "bg": {"type": "ocean", "sky_color": [180, 190, 200], "horizon_color": [120, 140, 160],
                   "horizon": 0.4, "water_color": [25, 55, 110]},
            "elements": [
                {"type": "ship", "x": 0.5, "y": 0.35, "scale": 2.75, "fill": [80, 50, 30]},
                {"type": "wave", "x": 0.25, "y": 0.4, "scale": 3.5, "fill": [30, 60, 120]},
                {"type": "wave", "x": 0.75, "y": 0.42, "scale": 3.0, "fill": [30, 60, 120]},
                {"type": "cloud", "x": 0.5, "y": 0.1, "scale": 3.5, "fill": [120, 130, 150]},
                {"type": "cloud", "x": 0.2, "y": 0.12, "scale": 2.5, "fill": [130, 140, 160]},
                {"type": "flag", "x": 0.5, "y": 0.25, "scale": 2.0, "fill": [20, 20, 20]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  ANIMALS & NATURE
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "dinosaur",
        "keywords": [
            "dinosaur", "dinosaurs", "dino", "tyrannosaurus", "triceratops",
            "velociraptor", "stegosaurus", "brachiosaurus", "pterodactyl",
            "mesozoic", "jurassic", "cretaceous", "triassic",
            "fossil reptile", "prehistoric animal", "ancient reptile",
            "giant reptile", "dinosaur age", "dinosaur era",
            "extinct animal", "fossilized bones", "prehistoric predator",
            "carnivorous dinosaur", "herbivore dinosaur",
            "tyrannosaurus rex", "t rex", "raptor", "saur",
            "dinosaur fossil", "prehistoric creature",
            "dinosaur extinction", "age of dinosaur",
            "giant lizard", "ancient monster",
            "walked the earth", "million years dinosaur"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[140, 200, 230], [100, 160, 200]], "horizon": 0.6, "ground_color": [50, 110, 50]},
            "elements": [
                {"type": "dinosaur", "x": 0.5, "y": 0.55, "scale": 3.5, "fill": [80, 110, 70]},
                {"type": "tree", "x": 0.2, "y": 0.7, "scale": 3.5, "tree_style": "round", "fill": [45, 120, 45]},
                {"type": "tree", "x": 0.8, "y": 0.72, "scale": 3.0, "tree_style": "pine", "fill": [40, 110, 40]},
                {"type": "water", "x": 0.0, "y": 0.75, "width": 0.4, "height": 0.08, "fill": [50, 130, 200]},
                {"type": "mountain", "x": 0.8, "y": 0.5, "width": 0.3, "height": 0.3, "fill": [100, 140, 170]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    {
        "id": "savanna",
        "keywords": [
            "savanna", "savannah", "african plains", "safari", "grassland",
            "wild animals", "grazing", "herbivore", "predator",
            "acacia tree", "serengeti", "lion", "zebra", "giraffe",
            "elephant", "wildebeest", "antelope", "cheetah"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[200, 180, 130], [160, 140, 100]], "horizon": 0.5, "ground_color": [140, 120, 85]},
            "elements": [
                {"type": "tree", "x": 0.3, "y": 0.65, "scale": 3.5, "tree_style": "round", "fill": [60, 130, 50]},
                {"type": "tree", "x": 0.75, "y": 0.63, "scale": 2.5, "tree_style": "round", "fill": [55, 120, 45]},
                {"type": "animal", "x": 0.4, "y": 0.68, "scale": 2.5, "fill": [160, 130, 80]},
                {"type": "animal", "x": 0.6, "y": 0.7, "scale": 2.25, "fill": [150, 120, 75]},
                {"type": "sun", "x": 0.8, "y": 0.1, "radius": 20, "fill": [255, 210, 60]},
                {"type": "hill", "x": 0.2, "y": 0.55, "width": 0.25, "height": 0.1, "fill": [170, 150, 105]},
                {"type": "hill", "x": 0.7, "y": 0.56, "width": 0.2, "height": 0.08, "fill": [165, 145, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    {
        "id": "forest_woods",
        "keywords": [
            "forest", "woods", "woodland", "grove", "wilderness",
            "dense trees", "deciduous", "conifer", "pine forest",
            "forest path", "woods trail", "forest clearing",
            "autumn forest", "green canopy", "shady grove"
        ],
        "scene": {
            "bg": {"type": "forest", "colors": [[90, 150, 90], [60, 120, 60]], "horizon": 0.6, "ground_color": [40, 90, 35]},
            "elements": [
                {"type": "tree", "x": 0.2, "y": 0.7, "scale": 4.0, "tree_style": "round", "fill": [45, 115, 45]},
                {"type": "tree", "x": 0.5, "y": 0.72, "scale": 5.0, "tree_style": "pine", "fill": [35, 95, 35]},
                {"type": "tree", "x": 0.8, "y": 0.71, "scale": 3.75, "tree_style": "round", "fill": [50, 120, 50]},
                {"type": "path", "x": 0.5, "y": 0.75, "width": 0.1, "height": 0.08, "fill": [120, 100, 70]},
                {"type": "flower", "x": 0.35, "y": 0.78, "scale": 2.0, "fill": [230, 100, 150]},
                {"type": "flower", "x": 0.65, "y": 0.79, "scale": 1.75, "fill": [200, 200, 80]},
            ],
            "atmosphere": {"particles": "mist", "fog": True},
            "mood": "peaceful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  SCIENCE & DISCOVERY
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "evolution",
        "keywords": [
            "evolution", "natural selection", "species evolve", "darwin",
            "survival of fittest", "adaptation", "mutation",
            "common ancestor", "evolutionary tree", "speciation",
            "genetic drift", "fossil record", "transitional form",
            "evolutionary history", "biological evolution"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[200, 220, 200], [140, 180, 150]], "horizon": 0.55, "ground_color": [100, 140, 100]},
            "elements": [
                {"type": "animal", "x": 0.15, "y": 0.55, "scale": 2.0, "fill": [130, 110, 85]},
                {"type": "animal", "x": 0.35, "y": 0.53, "scale": 2.75, "fill": [110, 90, 70]},
                {"type": "animal", "x": 0.55, "y": 0.5, "scale": 3.25, "fill": [90, 75, 55]},
                {"type": "human", "x": 0.78, "y": 0.48, "scale": 3.75, "fill": [180, 150, 130]},
                {"type": "arrow", "x": 0.2, "y": 0.5, "x2": 0.3, "y2": 0.5, "fill": [100, 100, 100]},
                {"type": "arrow", "x": 0.4, "y": 0.48, "x2": 0.5, "y2": 0.48, "fill": [100, 100, 100]},
                {"type": "arrow", "x": 0.6, "y": 0.45, "x2": 0.72, "y2": 0.45, "fill": [100, 100, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "microscope_science",
        "keywords": [
            "microscope", "cell", "bacteria", "microorganism", "microscopic",
            "laboratory", "scientist", "research lab", "petri dish",
            "slide sample", "specimen", "magnification", "lens",
            "observation", "biology lab", "experiment"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[230, 228, 222], [215, 212, 205]], "horizon": 0.6, "ground_color": [195, 192, 185]},
            "elements": [
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 40, "fill": [180, 200, 230, 40], "stroke": [80, 120, 180], "stroke_width": 2},
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 25, "fill": [160, 190, 220, 60]},
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 10, "fill": [80, 140, 200]},
                {"type": "circle", "x": 0.42, "y": 0.3, "radius": 4, "fill": [60, 180, 120]},
                {"type": "circle", "x": 0.58, "y": 0.38, "radius": 3, "fill": [60, 180, 120]},
                {"type": "circle", "x": 0.48, "y": 0.4, "radius": 2, "fill": [200, 100, 60]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    {
        "id": "chemistry_lab",
        "keywords": [
            "chemistry", "chemical", "molecule", "compound", "reaction",
            "periodic table", "element", "atom", "molecular structure",
            "chemical bond", "laboratory experiment", "test tube",
            "beaker", "flask", "solution", "catalyst", "reagent"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[232, 230, 225], [218, 215, 210]], "horizon": 0.6, "ground_color": [198, 195, 190]},
            "elements": [
                {"type": "atom", "x": 0.3, "y": 0.4, "radius": 35, "fill": [60, 140, 220]},
                {"type": "atom", "x": 0.7, "y": 0.45, "radius": 30, "fill": [220, 100, 60]},
                {"type": "circle", "x": 0.3, "y": 0.4, "radius": 5, "fill": [200, 200, 60]},
                {"type": "circle", "x": 0.7, "y": 0.45, "radius": 4, "fill": [60, 200, 200]},
                {"type": "circle", "x": 0.5, "y": 0.7, "radius": 15, "fill": [100, 180, 220, 50]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  ABSTRACT & PHILOSOPHY
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "time",
        "keywords": [
            "time", "temporal", "past present future", "time travel",
            "clock", "era", "epoch", "centuries", "millennia",
            "chronological", "timeline", "era", "age", "period",
            "ancient times", "modern era", "passage of time",
            "ticking clock", "hourglass"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[180, 180, 200], [120, 120, 160]], "horizon": 0.0},
            "elements": [
                {"type": "clock", "x": 0.5, "y": 0.35, "scale": 6.5, "fill": [200, 200, 220]},
                {"type": "hourglass", "x": 0.5, "y": 0.65, "scale": 5.0, "fill": [180, 180, 200]},
                {"type": "star", "x": 0.2, "y": 0.12, "radius": 1.5, "fill": [200, 200, 220]},
                {"type": "star", "x": 0.8, "y": 0.1, "radius": 1.5, "fill": [200, 200, 220]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "mysterious"
        }
    },

    {
        "id": "dreams",
        "keywords": [
            "dream", "imagination", "vision", "fantasy", "nightmare",
            "subconscious", "sleep", "daydream", "imagine",
            "surreal", "ethereal", "hallucination", "trance",
            "wishful thinking", "aspiration", "ambition"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[40, 30, 60], [60, 40, 80]], "horizon": 0.0},
            "elements": [
                {"type": "lightbulb", "x": 0.5, "y": 0.35, "scale": 6.0, "fill": [255, 240, 150]},
                {"type": "star", "x": 0.3, "y": 0.2, "radius": 3, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.7, "y": 0.18, "radius": 2.5, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.2, "y": 0.5, "radius": 2, "fill": [255, 200, 200]},
                {"type": "star", "x": 0.8, "y": 0.45, "radius": 2.5, "fill": [200, 255, 200]},
                {"type": "circle", "x": 0.5, "y": 0.6, "radius": 30, "fill": [100, 80, 140, 25]},
                {"type": "circle", "x": 0.5, "y": 0.6, "radius": 15, "fill": [140, 100, 180, 20]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 25, "fog": False},
            "mood": "mysterious"
        }
    },

    {
        "id": "knowledge_learning",
        "keywords": [
            "knowledge", "learning", "education", "wisdom", "study",
            "reading", "book", "library", "school", "university",
            "intellectual", "understanding", "curiosity",
            "discovery", "insight", "enlightenment", "teaching"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[215, 200, 180], [195, 180, 160]], "horizon": 0.6, "ground_color": [175, 160, 140]},
            "elements": [
                {"type": "book", "x": 0.3, "y": 0.4, "scale": 6.0, "fill": [180, 120, 80]},
                {"type": "book", "x": 0.55, "y": 0.42, "scale": 5.0, "fill": [100, 140, 180]},
                {"type": "lightbulb", "x": 0.8, "y": 0.2, "scale": 4.0, "fill": [255, 240, 150]},
                {"type": "shelf", "x": 0.5, "y": 0.18, "width": 0.6, "height": 0.04, "fill": [150, 120, 90]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  CITY & URBAN
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "city_skyline",
        "keywords": [
            "city", "urban", "skyline", "skyscraper", "cityscape",
            "metropolitan", "downtown", "city street", "high rise",
            "urban landscape", "city at night", "city lights",
            "megalopolis", "concrete jungle", "neon"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[60, 70, 100], [30, 40, 70]], "horizon": 0.5, "ground_color": [25, 30, 50]},
            "elements": [
                {"type": "building", "x": 0.15, "y": 0.5, "scale": 4.5, "fill": [50, 60, 90]},
                {"type": "building", "x": 0.4, "y": 0.48, "scale": 5.0, "fill": [55, 65, 95]},
                {"type": "building", "x": 0.65, "y": 0.52, "scale": 4.0, "fill": [45, 55, 85]},
                {"type": "building", "x": 0.82, "y": 0.55, "scale": 3.0, "fill": [50, 60, 90]},
                {"type": "star", "x": 0.3, "y": 0.1, "radius": 1.5, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.6, "y": 0.08, "radius": 1, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.8, "y": 0.12, "radius": 1.2, "fill": [255, 200, 200]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 15, "fog": False},
            "mood": "epic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  SPORTS & ACTIVITY
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "sports",
        "keywords": [
            "sport", "athlete", "competition", "game", "match",
            "stadium", "champion", "olympic", "tournament",
            "soccer", "football", "basketball", "baseball",
            "tennis", "swimming", "racing", "marathon"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[100, 180, 100], [60, 140, 60]], "horizon": 0.45, "ground_color": [40, 100, 40]},
            "elements": [
                {"type": "human", "x": 0.3, "y": 0.45, "scale": 4.0, "fill": [180, 140, 100]},
                {"type": "human", "x": 0.6, "y": 0.46, "scale": 3.5, "fill": [160, 120, 90]},
                {"type": "circle", "x": 0.45, "y": 0.42, "radius": 6, "fill": [255, 255, 255]},
                {"type": "sun", "x": 0.8, "y": 0.1, "radius": 18, "fill": [255, 230, 80]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  MUSIC & ART
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "music",
        "keywords": [
            "music", "melody", "rhythm", "instrument", "song",
            "composer", "orchestra", "symphony", "concert",
            "piano", "guitar", "violin", "drum", "musician",
            "classical music", "jazz", "rock music", "band"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[40, 30, 50], [25, 15, 35]], "horizon": 0.0},
            "elements": [
                {"type": "circle", "x": 0.5, "y": 0.5, "radius": 40, "fill": [60, 40, 80, 30], "stroke": [200, 180, 220], "stroke_width": 1},
                {"type": "circle", "x": 0.5, "y": 0.5, "radius": 25, "fill": [80, 50, 100, 40]},
                {"type": "circle", "x": 0.5, "y": 0.5, "radius": 10, "fill": [200, 180, 220]},
                {"type": "star", "x": 0.2, "y": 0.2, "radius": 2, "fill": [200, 180, 220]},
                {"type": "star", "x": 0.8, "y": 0.2, "radius": 2, "fill": [200, 180, 220]},
                {"type": "star", "x": 0.3, "y": 0.75, "radius": 1.5, "fill": [200, 180, 220]},
                {"type": "star", "x": 0.7, "y": 0.75, "radius": 1.5, "fill": [200, 180, 220]},
            ],
            "atmosphere": {"particles": "sparkles", "star_count": 20, "fog": False},
            "mood": "peaceful"
        }
    },

    {
        "id": "art_painting",
        "keywords": [
            "art", "painting", "artist", "canvas", "brush",
            "drawing", "sketch", "portrait", "landscape painting",
            "creative", "masterpiece", "gallery", "exhibition",
            "watercolor", "oil painting", "sculpture", "museum"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[225, 218, 205], [210, 203, 190]], "horizon": 0.6, "ground_color": [190, 183, 170]},
            "elements": [
                {"type": "rect", "x": 0.35, "y": 0.25, "width": 0.3, "height": 0.4, "fill": [240, 235, 225], "stroke": [120, 100, 80], "stroke_width": 3},
                {"type": "sun", "x": 0.45, "y": 0.33, "radius": 10, "fill": [255, 230, 80]},
                {"type": "mountain", "x": 0.5, "y": 0.45, "width": 0.2, "height": 0.15, "fill": [100, 140, 170]},
                {"type": "tree", "x": 0.5, "y": 0.58, "scale": 1.5, "tree_style": "round", "fill": [40, 100, 40]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  FOOD & COOKING
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "food_cooking",
        "keywords": [
            "food", "cooking", "recipe", "kitchen", "meal",
            "delicious", "cuisine", "chef", "baking", "grill",
            "vegetable", "fruit", "dinner", "breakfast",
            "restaurant", "gourmet", "fresh ingredients"
        ],
        "scene": {
            "bg": {"type": "indoor", "colors": [[220, 200, 170], [195, 175, 145]], "horizon": 0.6, "ground_color": [170, 150, 120]},
            "elements": [
                {"type": "circle", "x": 0.3, "y": 0.45, "radius": 20, "fill": [220, 180, 100]},
                {"type": "circle", "x": 0.3, "y": 0.45, "radius": 14, "fill": [200, 160, 80]},
                {"type": "circle", "x": 0.65, "y": 0.4, "radius": 15, "fill": [200, 100, 80]},
                {"type": "circle", "x": 0.65, "y": 0.4, "radius": 11, "fill": [180, 80, 60]},
                {"type": "fruit", "x": 0.2, "y": 0.65, "scale": 3.0, "fill": [230, 80, 80]},
                {"type": "fruit", "x": 0.8, "y": 0.65, "scale": 2.5, "fill": [80, 200, 80]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  FEAR & DANGER
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "fear_danger",
        "keywords": [
            "fear", "danger", "threat", "scary", "terrifying",
            "horror", "creepy", "ominous", "menacing", "sinister",
            "threatening", "peril", "risk", "hazard", "caution",
            "warning", "dread", "anxiety", "panic", "survival"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[25, 15, 20], [40, 20, 30]], "horizon": 0.5, "ground_color": [15, 10, 12]},
            "elements": [
                {"type": "eye", "x": 0.4, "y": 0.35, "scale": 6.0, "fill": [255, 200, 50]},
                {"type": "eye", "x": 0.6, "y": 0.35, "scale": 6.0, "fill": [255, 200, 50]},
                {"type": "circle", "x": 0.4, "y": 0.35, "radius": 4, "fill": [0, 0, 0]},
                {"type": "circle", "x": 0.6, "y": 0.35, "radius": 4, "fill": [0, 0, 0]},
                {"type": "moon", "x": 0.8, "y": 0.1, "radius": 8, "fill": [200, 200, 220]},
                {"type": "line", "x1": 0.35, "y1": 0.55, "x2": 0.65, "y2": 0.55, "fill": [100, 50, 60], "stroke_width": 2},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "dramatic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  GEOLOGY & TECTONICS
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "tectonic_collision",
        "keywords": [
            "india", "asia", "himalayas", "himalaya", "tectonic", "tectonic plate",
            "continent", "continental", "subcontinent", "landmass", "collision",
            "crash into", "moving across", "ocean journey", "million years",
            "earth history", "crust", "mountain building", "orogeny",
            "indian plate", "eurasian plate", "convergent boundary",
            "mountain range", "tallest mountain", "everest", "roof of the world"
        ],
        "scene": {
            "bg": {"type": "sunset", "colors": [[220, 140, 80], [180, 90, 100], [100, 60, 100], [60, 70, 50]], "horizon": 0.5, "ground_color": [50, 60, 35]},
            "elements": [
                {"type": "mountain", "x": 0.5, "y": 0.5, "width": 0.6, "height": 0.45, "fill": [130, 120, 140], "snow": True},
                {"type": "mountain", "x": 0.2, "y": 0.52, "width": 0.3, "height": 0.2, "fill": [100, 95, 110], "snow": True},
                {"type": "mountain", "x": 0.78, "y": 0.52, "width": 0.3, "height": 0.22, "fill": [110, 100, 120], "snow": True},
                {"type": "sun", "x": 0.5, "y": 0.12, "radius": 4, "fill": [255, 210, 80]},
                {"type": "cloud", "x": 0.25, "y": 0.22, "scale": 2.0, "fill": [220, 180, 160, 180]},
                {"type": "cloud", "x": 0.7, "y": 0.2, "scale": 1.75, "fill": [210, 170, 150, 150]},
                {"type": "text", "x": 0.5, "y": 0.06, "text": "THE HIMALAYAS", "font_size": 26, "fill": [240, 220, 160]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
    },

    # ═══════════════════════════════════════════════════════════════
    #  MEMORY & RECONSTRUCTION (11-line narrative templates)
    # ═══════════════════════════════════════════════════════════════

    # LINE 1: "Think of your earliest memory."
    # Dark empty screen → slow fade-in. Glowing human silhouette
    # (viewer POV inside head). Floating mist forming a "memory space".
    # One faint door opening labeled "past".
    {
            "id": "earliest_memory",
            "keywords": [
                "think of your earliest memory", "earliest memory", "viewer pov inside head",
                "memory space", "faint door opening", "glowing human silhouette",
                "dark empty screen fade in"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[2, 2, 10], [10, 8, 25]], "horizon": 0.0},
                "elements": [
                    {"type": "shadow_figure", "x": 0.5, "y": 0.48, "scale": 3.5, "fill": [25, 22, 35]},
                    {"type": "circle", "x": 0.5, "y": 0.48, "radius": 40, "fill": [180, 160, 220, 15], "stroke": [200, 180, 240, 25]},
                    {"type": "circle", "x": 0.5, "y": 0.48, "radius": 24, "fill": [200, 180, 240, 20]},
                    {"type": "circle", "x": 0.5, "y": 0.48, "radius": 10, "fill": [220, 200, 255, 30]},
                    {"type": "circle", "x": 0.3, "y": 0.2, "radius": 30, "fill": [200, 180, 240, 10], "stroke": [200, 180, 240, 15]},
                    {"type": "circle", "x": 0.7, "y": 0.3, "radius": 20, "fill": [200, 180, 240, 10]},
                    {"type": "circle", "x": 0.2, "y": 0.7, "radius": 25, "fill": [200, 180, 240, 8]},
                    {"type": "rect", "x": 0.85, "y": 0.5, "width": 55, "height": 90, "fill": [180, 170, 200, 30], "stroke": [200, 190, 220, 60], "stroke_width": 1, "rx": 3},
                    {"type": "text", "x": 0.85, "y": 0.55, "text": "PAST", "font_size": 12, "fill": [200, 190, 220, 80], "align": "center"},
                ],
                "atmosphere": {"particles": "mist", "fog": True},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 2: "A birthday candle."
        #  Small birthday cake on table, one candle flickering, child silhouette
        #  blurred, warm orange glow, unstable flame.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "birthday_candle",
            "keywords": [
                "a birthday candle", "birthday candle flickering", "birthday cake on wooden table",
                "warm orange glow dark room", "child silhouette blurred", "flame unstable might change",
                "memory already feels unstable"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[30, 18, 10], [55, 35, 15]], "horizon": 0.7, "ground_color": [35, 25, 15]},
                "elements": [
                    {"type": "rect", "x": 0.5, "y": 0.72, "width": 80, "height": 8, "fill": [80, 55, 30], "stroke": [60, 40, 20]},
                    {"type": "rect", "x": 0.5, "y": 0.62, "width": 30, "height": 20, "fill": [200, 180, 150], "stroke": [160, 140, 110]},
                    {"type": "candle", "x": 0.5, "y": 0.56, "scale": 3.0, "fill": [255, 220, 180]},
                    {"type": "fire", "x": 0.5, "y": 0.42, "scale": 2.5, "fill": [255, 180, 50]},
                    {"type": "circle", "x": 0.5, "y": 0.5, "radius": 45, "fill": [255, 180, 80, 12]},
                    {"type": "circle", "x": 0.5, "y": 0.5, "radius": 25, "fill": [255, 200, 100, 18]},
                    {"type": "child", "x": 0.2, "y": 0.6, "scale": 3.0, "fill": [60, 50, 70]},
                    {"type": "circle", "x": 0.5, "y": 0.42, "radius": 8, "fill": [255, 220, 100, 40]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "quiet"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 3: "A school classroom."
        #  Old classroom with sun rays through window, rows of desks,
        #  distorted geometry, chalkboard with unreadable writing,
        #  teacher blurred in background, dust particles, warping edges.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "school_classroom",
            "keywords": [
                "a school classroom", "old classroom with sun rays", "rows of desks",
                "chalkboard with unreadable writing", "teacher shape blurred background",
                "dust particles floating", "edges of room subtly warping"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[170, 160, 140], [210, 195, 170]], "horizon": 0.55, "ground_color": [140, 120, 100]},
                "elements": [
                    {"type": "rect", "x": 0.5, "y": 0.2, "width": 140, "height": 50, "fill": [50, 60, 40], "stroke": [40, 45, 35]},
                    {"type": "text", "x": 0.5, "y": 0.22, "text": "2 + 2 = ?", "font_size": 20, "fill": [200, 200, 180, 60]},
                    {"type": "rect", "x": 0.2, "y": 0.5, "width": 50, "height": 28, "fill": [110, 85, 60], "stroke": [80, 60, 40]},
                    {"type": "rect", "x": 0.45, "y": 0.5, "width": 50, "height": 28, "fill": [110, 85, 60], "stroke": [80, 60, 40]},
                    {"type": "rect", "x": 0.7, "y": 0.5, "width": 50, "height": 28, "fill": [110, 85, 60], "stroke": [80, 60, 40]},
                    {"type": "rect", "x": 0.2, "y": 0.65, "width": 50, "height": 28, "fill": [110, 85, 60], "stroke": [80, 60, 40]},
                    {"type": "rect", "x": 0.45, "y": 0.65, "width": 50, "height": 28, "fill": [110, 85, 60], "stroke": [80, 60, 40]},
                    {"type": "rect", "x": 0.7, "y": 0.65, "width": 50, "height": 28, "fill": [110, 85, 60], "stroke": [80, 60, 40]},
                    {"type": "human", "x": 0.88, "y": 0.38, "scale": 4.0, "fill": [80, 70, 90]},
                    {"type": "line", "x": 0.3, "y": 0.0, "x2": 0.6, "y2": 0.3, "stroke": [255, 240, 200, 30], "stroke_width": 15},
                    {"type": "line", "x": 0.7, "y": 0.0, "x2": 0.5, "y2": 0.3, "stroke": [255, 240, 200, 22], "stroke_width": 12},
                    {"type": "circle", "x": 0.4, "y": 0.3, "radius": 3, "fill": [200, 200, 200, 50]},
                    {"type": "circle", "x": 0.6, "y": 0.4, "radius": 2.5, "fill": [200, 200, 200, 40]},
                    {"type": "circle", "x": 0.35, "y": 0.55, "radius": 3, "fill": [200, 200, 200, 45]},
                    {"type": "circle", "x": 0.75, "y": 0.45, "radius": 2.5, "fill": [200, 200, 200, 35]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "quiet"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 4: "A street from childhood."
        #  Narrow street with houses too tall/small, bicycle silhouette,
        #  street lights glowing in daytime, background shifting like dream.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "childhood_street",
            "keywords": [
                "a street from childhood", "narrow street houses too tall",
                "childhood street familiar but wrong", "bicycle silhouette passing",
                "street lights glowing daytime", "background shifting like dream"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[150, 170, 190], [210, 195, 175]], "horizon": 0.5, "ground_color": [130, 120, 110]},
                "elements": [
                    {"type": "path", "x": 0.0, "y": 0.75, "x2": 1.0, "y2": 0.9, "fill": [150, 135, 115], "width": 20},
                    {"type": "shadow_figure", "x": 0.45, "y": 0.62, "scale": 3.0, "fill": [30, 25, 35]},
                    {"type": "lamp", "x": 0.35, "y": 0.5, "scale": 3.0, "fill": [180, 160, 120]},
                    {"type": "lightbulb", "x": 0.35, "y": 0.47, "scale": 2.0, "fill": [255, 255, 200, 80]},
                    {"type": "lamp", "x": 0.65, "y": 0.5, "scale": 3.0, "fill": [180, 160, 120]},
                    {"type": "lightbulb", "x": 0.65, "y": 0.47, "scale": 2.0, "fill": [255, 255, 200, 80]},
                    {"type": "circle", "x": 0.35, "y": 0.47, "radius": 20, "fill": [255, 255, 200, 8]},
                    {"type": "circle", "x": 0.65, "y": 0.47, "radius": 20, "fill": [255, 255, 200, 8]},
                    {"type": "building", "x": 0.12, "y": 0.5, "width": 0.06, "height": 0.18, "fill": [140, 110, 90]},
                    {"type": "building", "x": 0.25, "y": 0.5, "width": 0.07, "height": 0.22, "fill": [160, 130, 100]},
                    {"type": "building", "x": 0.75, "y": 0.52, "width": 0.06, "height": 0.2, "fill": [150, 120, 95]},
                    {"type": "building", "x": 0.88, "y": 0.55, "width": 0.06, "height": 0.16, "fill": [170, 140, 110]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 5: "Now here's the uncomfortable truth:"
        #  Sudden cut to black. Thin white crack across screen.
        #  Whisper-like visual distortion waves. Pause before realization.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "uncomfortable_truth",
            "keywords": [
                "now here is the uncomfortable truth", "uncomfortable truth",
                "cut to black", "thin white crack appears across screen",
                "whisper like visual distortion waves", "pause before realization",
                "transition moment"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[0, 0, 0], [1, 1, 1]], "horizon": 0.0},
                "elements": [
                    {"type": "line", "x": 0.5, "y": 0.0, "x2": 0.55, "y2": 0.5, "stroke": [200, 200, 210, 60], "stroke_width": 2},
                    {"type": "line", "x": 0.55, "y": 0.5, "x2": 0.48, "y2": 1.0, "stroke": [200, 200, 210, 50], "stroke_width": 1},
                    {"type": "line", "x": 0.5, "y": 0.0, "x2": 0.48, "y2": 1.0, "stroke": [200, 200, 210, 20], "stroke_width": 1},
                    {"type": "circle", "x": 0.5, "y": 0.5, "radius": 25, "fill": [200, 200, 210, 8], "stroke": [200, 200, 210, 15]},
                    {"type": "circle", "x": 0.5, "y": 0.5, "radius": 45, "fill": [200, 200, 210, 4], "stroke": [200, 200, 210, 8]},
                    {"type": "circle", "x": 0.4, "y": 0.3, "radius": 12, "fill": [200, 200, 210, 5]},
                    {"type": "circle", "x": 0.6, "y": 0.7, "radius": 10, "fill": [200, 200, 210, 5]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "dramatic"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 6: "It might not be real."
        #  Birthday scene, classroom, street ALL appear at once.
        #  Glitching like broken film. Parts missing. Faces dissolve.
        #  One by one they fade out.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "might_not_be_real",
            "keywords": [
                "it might not be real", "might not be real",
                "birthday scene classroom street all at once", "glitching like broken film",
                "parts of images missing", "faces dissolve into blur",
                "doubt injected"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[35, 30, 45], [55, 45, 65]], "horizon": 0.0},
                "elements": [
                    {"type": "rect", "x": 0.2, "y": 0.3, "width": 80, "height": 60, "fill": [100, 80, 60, 40], "stroke": [150, 140, 130, 30]},
                    {"type": "rect", "x": 0.5, "y": 0.35, "width": 70, "height": 50, "fill": [80, 100, 70, 40], "stroke": [140, 150, 130, 30]},
                    {"type": "rect", "x": 0.75, "y": 0.4, "width": 60, "height": 42, "fill": [110, 100, 80, 40], "stroke": [150, 140, 130, 30]},
                    {"type": "line", "x": 0.15, "y": 0.25, "x2": 0.85, "y2": 0.25, "stroke": [200, 80, 80, 40], "stroke_width": 2},
                    {"type": "line", "x": 0.1, "y": 0.6, "x2": 0.9, "y2": 0.6, "stroke": [80, 80, 200, 35], "stroke_width": 2},
                    {"type": "line", "x": 0.2, "y": 0.0, "x2": 0.3, "y2": 0.3, "stroke": [200, 200, 200, 25], "stroke_width": 1},
                    {"type": "circle", "x": 0.5, "y": 0.5, "radius": 60, "fill": [200, 180, 220, 10]},
                    {"type": "circle", "x": 0.3, "y": 0.3, "radius": 20, "fill": [255, 200, 200, 8]},
                    {"type": "circle", "x": 0.7, "y": 0.6, "radius": 25, "fill": [200, 200, 255, 8]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 7: "Not completely."
        #  Half-built memory scene. Left side detailed, right side missing.
        #  Floating fragments. Puzzle pieces hovering in air.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "not_completely",
            "keywords": [
                "not completely", "half built memory scene",
                "left side detailed right side missing", "unfinished sketch style",
                "floating fragments not attached", "puzzle pieces hovering in air",
                "partial truth"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[45, 40, 55], [75, 65, 85]], "horizon": 0.0},
                "elements": [
                    {"type": "rect", "x": 0.25, "y": 0.5, "width": 100, "height": 140, "fill": [60, 55, 70, 50], "stroke": [140, 130, 160, 60], "stroke_width": 2},
                    {"type": "rect", "x": 0.75, "y": 0.5, "width": 65, "height": 110, "fill": [60, 55, 70, 20], "stroke": [140, 130, 160, 20], "stroke_width": 1},
                    {"type": "puzzle", "x": 0.75, "y": 0.2, "scale": 3.0, "fill": [160, 140, 180, 60]},
                    {"type": "puzzle", "x": 0.82, "y": 0.48, "scale": 3.0, "fill": [180, 150, 200, 50]},
                    {"type": "puzzle", "x": 0.7, "y": 0.75, "scale": 3.0, "fill": [150, 160, 190, 45]},
                    {"type": "circle", "x": 0.85, "y": 0.3, "radius": 4, "fill": [200, 180, 220, 40]},
                    {"type": "circle", "x": 0.18, "y": 0.2, "radius": 3, "fill": [200, 180, 220, 30]},
                    {"type": "circle", "x": 0.82, "y": 0.85, "radius": 3, "fill": [200, 180, 220, 25]},
                    {"type": "circle", "x": 0.65, "y": 0.15, "radius": 2, "fill": [200, 180, 220, 35]},
                    {"type": "text", "x": 0.25, "y": 0.08, "text": "HALF BUILT", "font_size": 10, "fill": [180, 170, 200, 50]},
                    {"type": "text", "x": 0.75, "y": 0.08, "text": "?", "font_size": 24, "fill": [180, 170, 200, 35]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 8: "Your memory is not a recording."
        #  Old VHS tape labeled MEMORY. Tape melts into ink.
        #  Ink reshapes into different scenes. Film strip breaks
        #  into floating images.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "memory_not_recording",
            "keywords": [
                "your memory is not a recording", "memory is not a recording",
                "vhs tape labeled memory", "tape melts into ink",
                "ink reshapes itself into different scenes", "film strip breaks into floating images",
                "strong metaphor shift"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[12, 8, 18], [28, 18, 35]], "horizon": 0.0},
                "elements": [
                    {"type": "rect", "x": 0.5, "y": 0.2, "width": 100, "height": 50, "fill": [40, 35, 50], "stroke": [100, 90, 120, 50], "stroke_width": 1},
                    {"type": "rect", "x": 0.5, "y": 0.2, "width": 55, "height": 18, "fill": [60, 55, 70]},
                    {"type": "text", "x": 0.5, "y": 0.2, "text": "MEMORY", "font_size": 11, "fill": [200, 200, 220, 60], "align": "center"},
                    {"type": "circle", "x": 0.5, "y": 0.62, "radius": 25, "fill": [25, 20, 35, 80]},
                    {"type": "circle", "x": 0.4, "y": 0.7, "radius": 15, "fill": [30, 25, 40, 60]},
                    {"type": "circle", "x": 0.6, "y": 0.68, "radius": 14, "fill": [25, 20, 35, 50]},
                    {"type": "rect", "x": 0.18, "y": 0.48, "width": 22, "height": 28, "fill": [60, 50, 70, 40]},
                    {"type": "rect", "x": 0.34, "y": 0.46, "width": 22, "height": 28, "fill": [50, 60, 70, 35]},
                    {"type": "rect", "x": 0.66, "y": 0.44, "width": 22, "height": 28, "fill": [70, 50, 60, 30]},
                    {"type": "rect", "x": 0.82, "y": 0.48, "width": 22, "height": 28, "fill": [60, 50, 70, 25]},
                    {"type": "text", "x": 0.18, "y": 0.5, "text": "🌅", "font_size": 14, "fill": [200, 180, 160, 60]},
                    {"type": "text", "x": 0.34, "y": 0.48, "text": "🎂", "font_size": 14, "fill": [200, 180, 160, 55]},
                    {"type": "text", "x": 0.66, "y": 0.46, "text": "🏫", "font_size": 14, "fill": [200, 180, 160, 50]},
                    {"type": "text", "x": 0.82, "y": 0.5, "text": "🛣", "font_size": 14, "fill": [200, 180, 160, 45]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 9: "It is a reconstruction."
        #  Brain shown as architect studio. Tiny worker figures
        #  rebuilding scenes. Memory being assembled like set design.
        #  Blueprint of childhood scene being redrawn.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "memory_reconstruction_architect",
            "keywords": [
                "it is a reconstruction", "brain as architect studio",
                "tiny worker figures rebuilding scenes", "walls of memory being assembled",
                "blueprint of childhood scene", "memory construction site",
                "blueprint being redrawn"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[22, 28, 55], [42, 48, 75]], "horizon": 0.0},
                "elements": [
                    {"type": "ellipse", "x": 0.5, "y": 0.3, "width": 100, "height": 75, "fill": [60, 55, 80, 60], "stroke": [100, 95, 140, 80], "stroke_width": 2},
                    {"type": "human", "x": 0.35, "y": 0.4, "scale": 3.5, "fill": [70, 80, 120]},
                    {"type": "human", "x": 0.5, "y": 0.45, "scale": 3.5, "fill": [80, 70, 130]},
                    {"type": "human", "x": 0.65, "y": 0.38, "scale": 3.5, "fill": [70, 80, 120]},
                    {"type": "rect", "x": 0.5, "y": 0.7, "width": 180, "height": 70, "fill": [30, 40, 80, 50], "stroke": [80, 100, 160, 60], "stroke_width": 1},
                    {"type": "line", "x": 0.2, "y": 0.65, "x2": 0.8, "y2": 0.65, "stroke": [80, 100, 160, 40], "stroke_width": 1},
                    {"type": "line", "x": 0.2, "y": 0.75, "x2": 0.8, "y2": 0.75, "stroke": [80, 100, 160, 40], "stroke_width": 1},
                    {"type": "line", "x": 0.5, "y": 0.65, "x2": 0.5, "y2": 0.65, "stroke": [80, 100, 160, 40]},
                    {"type": "rect", "x": 0.35, "y": 0.66, "width": 20, "height": 15, "fill": [60, 80, 140, 30], "stroke": [80, 100, 160, 40]},
                    {"type": "rect", "x": 0.62, "y": 0.66, "width": 20, "height": 15, "fill": [60, 80, 140, 30], "stroke": [80, 100, 160, 40]},
                    {"type": "text", "x": 0.5, "y": 0.92, "text": "RECONSTRUCTION", "font_size": 16, "fill": [80, 100, 160, 60]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 10: "And every time you remember something"
        #  Same memory scene appears again but slightly different.
        #  Camera circles it like something unstable.
        #  Echo copies of the same scene overlap.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "every_time_remember",
            "keywords": [
                "and every time you remember something", "every time you remember",
                "memory scene appears again but different", "camera circles like something unstable",
                "echo copies of the same scene overlap", "repetition change begins"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[55, 45, 65], [90, 75, 100]], "horizon": 0.0},
                "elements": [
                    {"type": "candle", "x": 0.35, "y": 0.4, "scale": 3.0, "fill": [255, 220, 180, 60]},
                    {"type": "candle", "x": 0.5, "y": 0.42, "scale": 3.5, "fill": [255, 220, 180, 80]},
                    {"type": "candle", "x": 0.65, "y": 0.38, "scale": 3.0, "fill": [255, 220, 180, 50]},
                    {"type": "ellipse", "x": 0.35, "y": 0.4, "width": 38, "height": 25, "fill": [200, 180, 200, 20]},
                    {"type": "ellipse", "x": 0.5, "y": 0.42, "width": 50, "height": 34, "fill": [200, 180, 200, 30]},
                    {"type": "ellipse", "x": 0.65, "y": 0.38, "width": 38, "height": 25, "fill": [200, 180, 200, 20]},
                    {"type": "arc", "x": 0.5, "y": 0.4, "radius": 65, "start_angle": 0, "end_angle": 360, "stroke": [200, 180, 220, 50], "stroke_width": 2},
                    {"type": "arc", "x": 0.5, "y": 0.4, "radius": 85, "start_angle": 0, "end_angle": 360, "stroke": [200, 180, 220, 30], "stroke_width": 1},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
        # ═══════════════════════════════════════════════════════════════
        #  LINE 11: "your brain quietly edits it again."
        #  Brain shown like editing room. Hands erasing details.
        #  Pencil rewriting faces, objects, lighting.
        #  "SAVE" button pressed repeatedly.
        # ═══════════════════════════════════════════════════════════════
        {
            "id": "brain_edits_again",
            "keywords": [
                "your brain quietly edits it again", "brain quiet edits again",
                "brain like editing room", "erasing details on memory canvas",
                "pencil rewriting faces objects lighting", "save button pressed repeatedly",
                "memory being rewritten right now"
            ],
            "scene": {
                "bg": {"type": "gradient", "colors": [[35, 38, 48], [55, 58, 70]], "horizon": 0.0},
                "elements": [
                    {"type": "ellipse", "x": 0.5, "y": 0.35, "width": 100, "height": 80, "fill": [70, 65, 85, 60], "stroke": [140, 130, 160, 60], "stroke_width": 2},
                    {"type": "hand", "x": 0.3, "y": 0.4, "scale": 4.0, "fill": [220, 190, 170]},
                    {"type": "hand", "x": 0.7, "y": 0.35, "scale": 4.0, "fill": [220, 190, 170]},
                    {"type": "line", "x": 0.3, "y": 0.25, "x2": 0.6, "y2": 0.2, "stroke": [200, 200, 220, 60], "stroke_width": 2},
                    {"type": "line", "x": 0.4, "y": 0.5, "x2": 0.7, "y2": 0.55, "stroke": [200, 200, 220, 50], "stroke_width": 2},
                    {"type": "line", "x": 0.5, "y": 0.3, "x2": 0.8, "y2": 0.35, "stroke": [200, 200, 220, 40], "stroke_width": 1},
                    {"type": "circle", "x": 0.4, "y": 0.25, "radius": 5, "fill": [255, 200, 100, 60]},
                    {"type": "circle", "x": 0.6, "y": 0.5, "radius": 4, "fill": [255, 200, 100, 50]},
                    {"type": "rect", "x": 0.5, "y": 0.85, "width": 60, "height": 24, "fill": [50, 60, 50, 60], "stroke": [100, 140, 100, 70], "stroke_width": 2, "rx": 4},
                    {"type": "text", "x": 0.5, "y": 0.85, "text": "SAVE", "font_size": 12, "fill": [140, 200, 140, 80]},
                ],
                "atmosphere": {"particles": "none", "fog": False},
                "mood": "mysterious"
            }
        },
    # ═══════════════════════════════════════════════════════════════
    #  FACTORY / INDUSTRIAL
    #  Factory building with smokestacks, industrial yard
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "factory_scene",
        "keywords": [
            "factory with smokestacks", "industrial factory", "factory building",
            "smokestacks", "manufacturing plant", "warehouse district",
            "refinery", "industrial zone", "assembly line"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[140, 130, 120], [95, 85, 75]], "horizon": 0.5, "ground_color": [75, 65, 55]},
            "elements": [
                {"type": "factory", "x": 0.2, "y": 0.5, "width": 0.14, "height": 0.25, "fill": [130, 110, 90], "window_color": [200, 180, 100]},
                {"type": "factory", "x": 0.5, "y": 0.5, "width": 0.18, "height": 0.28, "fill": [120, 100, 80], "window_color": [190, 170, 90]},
                {"type": "factory", "x": 0.8, "y": 0.52, "width": 0.12, "height": 0.22, "fill": [140, 120, 100], "window_color": [200, 180, 100]},
                {"type": "path", "x": 0.0, "y": 0.75, "x2": 1.0, "y2": 0.85, "fill": [100, 90, 75], "width": 16},
                {"type": "circle", "x": 0.2, "y": 0.18, "radius": 6, "fill": [180, 180, 180, 50]},
                {"type": "circle", "x": 0.5, "y": 0.12, "radius": 8, "fill": [180, 180, 180, 40]},
                {"type": "circle", "x": 0.8, "y": 0.2, "radius": 5, "fill": [180, 180, 180, 50]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "industrial"
        }
    },
    # ═══════════════════════════════════════════════════════════════
    #  SHOP / STOREFRONT
    #  Street-level shop with awning, display window
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "shop_scene",
        "keywords": [
            "shop on a street", "storefront", "retail shop",
            "corner shop", "local store", "market street",
            "shopping district", "boutique", "bakery shop",
            "cafe on a street", "restaurant street",
            "cafe in the city", "coffee shop", "city cafe",
            "downtown cafe"
        ],
        "scene": {
            "bg": {"type": "gradient", "colors": [[190, 195, 200], [160, 165, 170]], "horizon": 0.5, "ground_color": [130, 125, 120]},
            "elements": [
                {"type": "shop", "x": 0.25, "y": 0.5, "width": 0.14, "height": 0.22, "fill": [180, 150, 120], "window_color": [255, 240, 200]},
                {"type": "shop", "x": 0.75, "y": 0.5, "width": 0.14, "height": 0.22, "fill": [170, 145, 115], "window_color": [255, 240, 200]},
                {"type": "building", "x": 0.5, "y": 0.5, "width": 0.08, "height": 0.28, "fill": [150, 130, 110], "window_color": [255, 220, 100]},
                {"type": "lamp", "x": 0.5, "y": 0.52, "scale": 2.5, "fill": [180, 160, 120]},
                {"type": "path", "x": 0.0, "y": 0.75, "x2": 1.0, "y2": 0.85, "fill": [140, 130, 115], "width": 18},
                {"type": "human", "x": 0.5, "y": 0.62, "scale": 2.5, "fill": [100, 80, 70]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
    },
]

# ── Singleton matcher ──────────────────────────────────────────

_matcher = None
_knowledge_version = 0


def get_matcher():
    global _matcher, _knowledge_version
    if _matcher is None:
        _matcher = SemanticMatcher()
        for tmpl in KNOWLEDGE_TEMPLATES:
            _matcher.add(tmpl)
        _matcher.build()
        _knowledge_version = id(KNOWLEDGE_TEMPLATES)
    return _matcher


def rebuild():
    global _matcher
    _matcher = None
    get_matcher()


def semantic_scene(text: str, threshold: float = 0.2) -> dict | None:
    """Find best matching scene for narration using semantic similarity.
    
    Uses TF-IDF vectorization and cosine similarity across 40+ scene templates.
    Returns None if no template meets the confidence threshold.
    """
    matcher = get_matcher()
    template, score = matcher.match(text, threshold)
    if template:
        return _d(template["scene"])
    return None
