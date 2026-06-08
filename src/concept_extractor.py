"""Concept extractor — extracts visual concepts from any narration text.

Turns plain English into structured visual ideas without external NLP.
Uses bigram-aware keyword matching + concept scoring to understand
what a text is about and what visual elements it needs.
"""

import re
import math
from collections import Counter


# ── Comprehensive concept dictionary ──────────────────────────
# Each concept maps descriptive words/phrases to visual element types

CONCEPTS = {
    # Space / Celestial
    "star":       ["star", "stars", "stellar", "constellation", "celestial", "astral"],
    "sun":        ["sun", "sunlight", "sunny", "solar", "sunshine", "sunrise", "sunset glow"],
    "moon":       ["moon", "lunar", "moonlight", "crescent", "full moon", "half moon"],
    "planet":     ["planet", "planetary", "orbits", "saturn", "jupiter", "mars", "venus",
                    "mercury", "neptune", "uranus", "earth", "world", "globe"],
    "astronaut":  ["astronaut", "spaceman", "space walk", "space suit", "cosmonaut"],
    "spaceship":  ["spaceship", "spacecraft", "rocket", "shuttle", "spaceship", "launch"],
    "blackhole":  ["black hole", "singularity", "event horizon", "gravitational"],
    "galaxy":     ["galaxy", "galactic", "milky way", "nebula", "cosmic"],
    "asteroid":   ["asteroid", "meteor", "comet", "shooting star", "meteorite"],

    # Nature / Landscape
    "tree":       ["tree", "trees", "forest", "woodland", "oak", "pine", "maple",
                    "leaf", "leaves", "branch", "trunk", "bark", "canopy"],
    "mountain":   ["mountain", "mountains", "peak", "summit", "cliff", "ridge",
                    "alpine", "highland", "hill", "hills", "slope", "himalayas",
                    "himalaya", "everest", "k2", "annapurna"],
    "water":      ["water", "river", "lake", "stream", "pond", "waterfall",
                    "creek", "brook", "flowing water"],
    "ocean":      ["ocean", "oceans", "sea", "seas", "wave", "waves", "marine", "coastal", "shore",
                    "beach", "coast", "seaside", "saltwater", "coral", "reef", "reefs", "coral reef"],
    "glacier":    ["glacier", "ice", "iceberg", "frozen", "ice sheet", "ice cap",
                    "glacial", "ice age", "freeze", "freezing"],
    "snow":       ["snow", "snowy", "snowfall", "snowflake", "blizzard", "winter",
                    "frost", "icicle"],
    "rain":       ["rain", "rainy", "raining", "rainfall", "raindrop", "shower",
                    "drizzle", "downpour", "monsoon"],
    "cloud":      ["cloud", "clouds", "cloudy", "overcast", "cumulus", "cirrus",
                    "nimbus", "storm cloud"],
    "desert":     ["desert", "sandy", "arid", "dune", "sand dune", "cactus",
                    "sahara", "dry land"],
    "flower":     ["flower", "flowers", "bloom", "blossom", "petal", "garden",
                    "meadow", "wildflower", "rose", "tulip", "daisy"],
    "grass":      ["grass", "grassy", "field", "pasture", "meadow", "lawn",
                    "prairie", "savanna", "grassland"],
    "path":       ["path", "trail", "road", "track", "route", "pathway", "way", "street",
                    "lane", "avenue", "boulevard", "alley"],

    # Weather
    "lightning":  ["lightning", "thunder", "thunderstorm", "electrical", "strike"],
    "storm":      ["storm", "stormy", "tempest", "hurricane", "cyclone", "typhoon",
                    "tornado", "whirlwind"],
    "rainbow":    ["rainbow", "colorful sky", "prism", "spectrum"],
    "fog":        ["fog", "foggy", "mist", "misty", "haze", "hazy", "smog"],

    # Animals
    "bird":       ["bird", "birds", "eagle", "hawk", "sparrow", "robin",
                    "pigeon", "crow", "raven", "swan", "duck", "owl",
                    "flamingo", "parrot", "feather", "wing", "flight"],
    "fish":       ["fish", "fishes", "fishing", "aquatic", "fin", "scales",
                    "salmon", "tuna", "goldfish", "tropical fish"],
    "whale":      ["whale", "whales", "humpback", "orca", "blue whale",
                    "cetacean", "mammal ocean"],
    "dolphin":    ["dolphin", "dolphins", "porpoise"],
    "shark":      ["shark", "sharks", "great white", "hammerhead", "predator fish"],
    "dinosaur":   ["dinosaur", "dinosaurs", "t rex", "tyrannosaurus", "triceratops",
                    "stegosaurus", "brachiosaurus", "velociraptor", "pterodactyl",
                    "mesozoic", "jurassic", "cretaceous", "prehistoric"],
    "snake":      ["snake", "snakes", "serpent", "cobra", "python", "viper",
                    "reptile slither"],
    "butterfly":  ["butterfly", "butterflies", "moth", "caterpillar", "chrysalis"],
    "dog":        ["dog", "dogs", "puppy", "canine", "hound", "retriever", "shepherd"],
    "cat":        ["cat", "cats", "kitten", "feline", "lion", "tiger", "leopard",
                    "cheetah", "panther", "jaguar"],
    "horse":      ["horse", "horses", "pony", "stallion", "mare", "foal",
                    "equestrian", "gallop"],
    "elephant":   ["elephant", "elephants", "tusker", "pachyderm"],
    "bear":       ["bear", "bears", "grizzly", "polar bear", "brown bear",
                    "black bear", "koala", "panda"],
    "monkey":     ["monkey", "monkeys", "ape", "apes", "gorilla", "chimp", "chimpanzee",
                    "orangutan", "primate"],
    "deer":       ["deer", "deers", "doe", "stag", "buck", "fawn", "antelope",
                    "caribou", "moose", "elk"],
    "rabbit":     ["rabbit", "rabbits", "bunny", "hare", "cottontail"],
    "squirrel":   ["squirrel", "squirrels", "chipmunk", "beaver"],
    "fox":        ["fox", "foxes", "fennec", "vulpes"],
    "wolf":       ["wolf", "wolves", "dire wolf", "canis lupus"],
    "frog":       ["frog", "frogs", "toad", "amphibian", "tadpole"],
    "turtle":     ["turtle", "turtles", "tortoise", "sea turtle"],
    "crocodile":  ["crocodile", "crocodiles", "alligator", "gator", "caiman",
                    "reptile"],

    # Human / Character
    "human":      ["person", "people", "human", "man", "woman", "child",
                    "scientist", "explorer", "adventurer", "soldier",
                    "doctor", "teacher", "artist", "musician",
                    "king", "queen", "prince", "princess",
                    "warrior", "knight", "hero", "figure",
                    "crowd", "audience", "group"],
    "eye":        ["eye", "eyes", "eyeball", "vision", "sight", "gaze", "stare"],
    "hand":       ["hand", "hands", "finger", "fingers", "palm", "fist", "grip"],
    "heart":      ["heart", "cardiac", "pumping blood", "circulation",
                    "cardio", "aorta", "ventricle"],
    "brain":      ["brain", "cerebral", "neuron", "synapse", "nervous system",
                     "cortex", "cerebellum", "cognition", "memory", "memories"],

    # Technology
    "computer":   ["computer", "cpu", "processor", "computing", "digital",
                    "microchip", "transistor", "semiconductor", "chip"],
    "network":    ["network", "internet", "web", "online", "connected",
                    "link", "linkage", "wireless", "fiber optic"],
    "robot":      ["robot", "robotic", "automation", "android", "droid",
                    "humanoid", "mechanical", "machine"],
    "ai":         ["ai", "artificial intelligence", "machine learning",
                    "neural", "deep learning", "intelligent system"],
    "circuit":    ["circuit", "circuit board", "electronics", "electronic",
                    "board", "wiring", "solder"],
    "data":       ["data", "information", "database", "storage", "binary",
                    "code", "software", "algorithm", "programming"],

    # Science
    "dna":        ["dna", "genetic", "gene", "genome", "chromosome", "helix",
                    "nucleotide", "hereditary", "blueprint of life"],
    "atom":       ["atom", "atomic", "molecule", "molecular", "particle", "particles",
                    "nucleus", "electron", "proton", "neutron", "quantum"],
    "plant":      ["plant", "plants", "vegetation", "botanical", "flora",
                    "seedling", "sprout", "foliage", "photosynthesis"],
    "microscope": ["microscope", "magnify", "lens", "specimen", "slide",
                    "petri dish", "laboratory"],
    "telescope":  ["telescope", "observatory", "astronomy", "astronomer",
                    "lens", "refractor", "reflector"],
    "experiment": ["experiment", "chemical", "reaction", "beaker", "flask",
                    "test tube", "lab", "laboratory", "scientist"],

    # History / Civilization
    "building":   ["building", "buildings", "house", "home", "structure",
                    "skyscraper", "tower", "palace", "temple", "church",
                    "cathedral", "mosque", "monument", "castle",
                    "fortress", "pyramid", "colosseum"],
    "factory":    ["factory", "factories", "mill", "refinery", "warehouse",
                    "industrial", "manufacturing", "smokestacks", "steam engine",
                    "assembly line", "machine"],
    "shop":       ["shop", "store", "market", "bakery", "cafe",
                    "restaurant", "pharmacy", "bookshop", "boutique",
                    "retail", "storefront", "merchant"],
    "flag":       ["flag", "banner", "pennant", "standard", "ensign"],
    "cannon":     ["cannon", "cannons", "artillery", "canon", "canons", "bombard"],
    "wall":       ["wall", "walls", "rampart", "ramparts", "fortification", "barricade"],
    "tent":       ["tent", "tents", "camp", "campsite", "encampment"],
    "chain":      ["chain", "chains", "barrier chain"],
    "crown":      ["crown", "king", "queen", "royal", "throne", "monarch",
                    "kingdom", "empire", "emperor"],
    "book":       ["book", "books", "library", "reading", "literature",
                    "manuscript", "scroll", "text", "knowledge", "classroom",
                    "school", "lesson", "study", "learn", "learning",
                    "newspaper", "newspapers", "magazine", "journal", "article"],
    "coin":       ["coin", "money", "currency", "treasure", "gold", "silver",
                    "wealth", "fortune", "riches"],
    "map":        ["map", "maps", "chart", "cartography", "navigation",
                    "atlas", "globe", "compass", "tectonic", "landmass"],
    "world_map":  ["world map", "continent", "continents", "continental", "asia", "africa",
                    "europe", "north america", "south america", "america", "australia",
                    "subcontinent", "world", "earth"],
    "india_map":  ["india map", "india outline", "indian map", "map of india"],
    "ship":       ["ship", "boat", "vessel", "sail", "sailboat", "yacht"],
    "canoe":      ["canoe", "canoeing"],
    "kayak":      ["kayak", "kayaking"],
    "raft":       ["raft", "rafting"],
    "pirate_ship":["pirate ship", "pirate", "pirates", "pirate galleon"],
    "galleon":    ["galleon", "tall ship"],
    "alien":      ["alien", "extraterrestrial", "space creature", "ufo"],
    "artifact":   ["artifact", "relic", "ancient object", "crystal"],
    "train":      ["train", "railway", "locomotive", "railroad", "rail",
                    "subway", "metro", "tram"],
    "car":        ["car", "auto", "automobile", "vehicle", "truck", "bus",
                    "sedan", "coupe", "suv", "van", "jeep"],
    "bike":       ["bike", "bicycle", "cycle", "motorcycle", "scooter", "moped",
                    "cycling", "cyclist", "biker"],
    "drive":      ["drive", "driving", "driver", "riding", "rider", "ride"],

    # Abstract / Concepts
    "clock":      ["clock", "time", "hour", "minute", "watch", "timer",
                    "stopwatch", "sundial", "hourglass", "ticking"],
    "lightbulb":  ["lightbulb", "idea", "inspiration", "innovation",
                    "invention", "creativity", "genius", "bright idea", "energy",
                     "candle", "candles", "flame",
                     "thought", "imagination", "dream"],
    "fire":       ["fire", "flame", "flames", "burning", "blaze", "inferno",
                    "campfire", "bonfire", "wildfire", "combustion"],
    "key":        ["key", "keys", "unlock", "padlock", "lock", "combination"],
    "question":   ["question", "questions", "mystery", "unknown", "wonder",
                    "curious", "curiosity", "puzzle", "riddle"],
    "target":     ["target", "goal", "aim", "bullseye", "objective", "mission"],
    "infinity":   ["infinity", "endless", "eternal", "forever", "boundless",
                    "infinite", "unlimited", "timeless"],
    "puzzle":     ["puzzle", "challenge", "problem", "complex", "complicated",
                    "difficult", "solve", "solution"],
    "scales":     ["scales", "balance", "justice", "fairness", "equality",
                    "weight", "measure", "compare"],
    "gear":       ["gear", "cog", "machinery", "mechanical", "engine",
                    "mechanism", "machine part", "transmission"],
    "hourglass":  ["hourglass", "sand timer", "countdown", "passage of time"],

    # Household items
    "chair":      ["chair", "chairs", "seat", "stool", "bench"],
    "table":      ["table", "tables", "desk", "counter"],
    "sofa":       ["sofa", "couch", "settee", "loveseat"],
    "bed":        ["bed", "bunk", "cot", "bedding", "mattress"],
    "cupboard":   ["cupboard", "cabinet", "wardrobe", "closet"],
    "fridge":     ["fridge", "refrigerator", "freezer", "icebox"],
    "oven":       ["oven", "stove", "range", "cooker"],
    "sink":       ["sink", "basin", "washbasin"],
    "toilet":     ["toilet", "commode", "lavatory", "bathroom"],
    "bathtub":    ["bathtub", "tub", "bath", "bath tub"],
    "mirror":     ["mirror", "looking glass", "reflection"],
    "curtain":    ["curtain", "drape", "drapes", "curtains"],
    "pillow":     ["pillow", "cushion", "pillowcase"],
    "door":       ["door", "doorway", "gate"],
    "window":     ["window", "windows", "casement"],

    # Pose concepts (modify human elements)
    "sitting":    ["sitting", "sits", "seated", "sat"],
    "lying":      ["lying", "laying", "reclining", "prone", "sleeping", "asleep", "nap", "napping", "dozing"],
    "kneeling":   ["kneeling", "kneels", "kneeled", "on knees"],
    "jogging":    ["jogging", "jogs", "jogged"],
    "running":    ["running", "runs", "ran", "sprinting"],
}


# ── Background type detection ─────────────────────────────────

def detect_bg_type(concepts: dict) -> str:
    """Pick the best background type from extracted concepts."""
    cosmic = sum(concepts.get(c, 0) for c in ["star", "sun", "moon", "planet",
                                               "astronaut", "spaceship", "blackhole",
                                               "galaxy", "asteroid"])
    aquatic = sum(concepts.get(c, 0) for c in ["ocean", "water", "whale", "dolphin",
                                               "shark", "fish", "ship"])
    forest = sum(concepts.get(c, 0) for c in ["tree", "mountain", "flower", "grass",
                                              "desert", "snow", "glacier", "path"])
    tech = sum(concepts.get(c, 0) for c in ["computer", "network", "robot", "ai",
                                            "circuit", "data"])
    city = sum(concepts.get(c, 0) for c in ["building", "flag", "crown", "book",
                                            "coin", "map", "train"])
    abstract = sum(concepts.get(c, 0) for c in ["clock", "lightbulb", "infinity",
                                                "puzzle", "gear", "target"])

    best = max([("gradient", 0), ("space", cosmic), ("ocean", aquatic),
                ("forest", forest), ("desert", forest), ("mountain", forest),
                ("industrial", tech), ("city", city), ("indoor", abstract)],
               key=lambda x: x[1])

    if best[1] >= 2:
        return best[0]
    return "gradient"


# ── Mood detection ────────────────────────────────────────────

MOOD_WORDS = {
    "peaceful":  ["peaceful", "calm", "gentle", "serene", "quiet", "tranquil",
                   "soft", "still", "silent", "harmony", "bliss", "content",
                   "thoughtful"],
    "dramatic":  ["dramatic", "intense", "violent", "furious", "explosive",
                   "massive", "epic", "chaos", "turmoil", "battle",
                   "collision", "collide", "crash", "smashed", "impact",
                   "powerful", "greatest", "titanic", "angry", "rage"],
    "mysterious": ["mysterious", "strange", "unknown", "secret", "hidden",
                    "dark", "shadow", "enigmatic", "eerie", "uncanny"],
    "hopeful":   ["hopeful", "bright", "future", "promise", "beautiful",
                   "wonderful", "amazing", "majestic", "inspiring",
                   "happy"],
    "somber":    ["somber", "sad", "melancholy", "mournful", "gloomy",
                   "bleak", "desolate", "lonely", "tragic", "angry"],
    "epic":      ["epic", "legendary", "monumental", "historic", "grand",
                   "majestic", "heroic", "colossal", "titanic",
                   "journey", "greatest", "collision", "collide",
                   "million years", "millions", "ancient"],
}


def detect_mood(text: str) -> str:
    tl = text.lower()
    scores = {}
    for mood, words in MOOD_WORDS.items():
        scores[mood] = sum(1 for w in words if re.search(r'\b' + re.escape(w) + r'\b', tl))
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "peaceful"


# ── Phrase-aware context guard ────────────────────────────────
# Prevents false positives like "heart of the matter" → heart element

PHRASE_FALSE_POSITIVES = {
    "heart": ["heart of", "at heart", "in heart", "heart and soul",
              "heavy heart", "heart of gold", "change of heart",
              "heart of the matter", "heart of darkness",
              "heart of the city", "heart of the forest",
              "sweetheart", "heartbroken", "heartwarming"],
    "star":  ["star of the show", "rock star", "movie star",
              "all star", "superstar", "pop star", "film star",
              "starring", "starred", "starry eyed"],
    "light": ["light of my life", "in light of", "shed light",
              "come to light", "bring to light", "light year",
              "light bulb", "lightning"],
    "brain": ["brain of the operation", "brain trust", "brain storm", "brainstorm"],
    "fire":  ["fire of passion", "on fire", "under fire",
              "fire away", "fire department", "fire up"],
    "key":   ["key to", "key point", "key factor", "key role",
              "key element", "key aspect", "key component"],
    "book":  ["by the book", "book of", "book club", "book store",
              "cookbook", "notebook", "bookkeeping"],
    "ship":  ["friendship", "relationship", "leadership",
              "championship", "membership", "ownership"],
    "clock": ["clock in", "clock out", "around the clock",
              "clockwork", "o'clock"],
}


def has_false_positive(concept: str, text: str) -> bool:
    """Check if a concept match is actually a false positive (idiomatic usage)."""
    tl = text.lower()
    for phrase in PHRASE_FALSE_POSITIVES.get(concept, []):
        if " " in phrase:
            if phrase in tl:
                return True
        else:
            if re.search(r'\b' + re.escape(phrase) + r'\b', tl):
                return True
    return False


# ── Main extraction ───────────────────────────────────────────

def extract_concepts(text: str) -> dict:
    """Extract visual concepts from narration text.
    
    Returns dict of {concept_name: count} for all matched concepts.
    Filters false positives (idiomatic phrases).
    """
    tl = text.lower()
    result = {}

    for concept, keywords in CONCEPTS.items():
        count = 0
        for kw in keywords:
            if " " in kw:
                if kw in tl:
                    count += 1
            else:
                if re.search(r'\b' + re.escape(kw) + r'\b', tl):
                    count += 1
        if count > 0 and not has_false_positive(concept, text):
            result[concept] = count

    return result


# ── Scene type inference from concepts ────────────────────────

SCENE_TYPE_MAP = {
    "space":        ["star", "sun", "moon", "planet", "astronaut", "spaceship",
                     "blackhole", "galaxy", "asteroid", "telescope"],
    "weather":      ["lightning", "storm", "rainbow", "fog", "rain", "cloud"],
    "ocean":        ["ocean", "water", "whale", "dolphin", "shark", "fish", "ship"],
    "nature":       ["tree", "mountain", "flower", "grass", "desert", "snow",
                     "glacier", "path", "crocodile", "butterfly", "frog", "turtle"],
    "animals":      ["bird", "dog", "cat", "horse", "elephant", "bear", "monkey",
                     "deer", "rabbit", "squirrel", "fox", "wolf", "snake",
                     "dinosaur"],
    "human":        ["human", "eye", "hand", "heart", "brain"],
    "technology":   ["computer", "network", "robot", "ai", "circuit", "data"],
    "science":      ["dna", "atom", "microscope", "experiment"],
    "history":      ["building", "flag", "crown", "book", "coin", "map", "train"],
    "abstract":     ["clock", "lightbulb", "key", "question", "target",
                     "infinity", "puzzle", "scales", "gear", "hourglass"],
}


def infer_scene_type(concepts: dict) -> str:
    """Determine the overall scene type from extracted concepts."""
    scores = {}
    for stype, cnames in SCENE_TYPE_MAP.items():
        scores[stype] = sum(concepts.get(c, 0) for c in cnames)
    if max(scores.values()) >= 2:
        return max(scores, key=scores.get)
    return "general"
