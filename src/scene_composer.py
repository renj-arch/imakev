"""Massive Scene Composer — a rule-based 'LLM' that generates rich,
topic-appropriate visual scenes for ANY subject. 1000+ keywords,
30+ element types, mood-aware color palettes, dynamic composition.

No external API needed. Works offline for any topic."""

import random, math


class SceneComposer:
    """Compose a rich visual scene from any topic string."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    # ═══════════════════════════════════════════════════════════════
    #  MASSIVE KEYWORD → ELEMENT LIBRARY
    # ═══════════════════════════════════════════════════════════════

    PEOPLE = {
        "human": [
            # General
            "human", "person", "people", "man", "woman", "child", "baby", "adult", "teen",
            "boy", "girl", "elder", "old man", "old woman", "youth", "gentleman", "lady",
            "citizen", "civilian", "inhabitant", "native", "tribesman", "villager",
            "crowd", "mob", "group", "team", "crew", "gang",
            # Royalty
            "king", "queen", "prince", "princess", "emperor", "empress", "pharaoh",
            "sultan", "shah", "royal", "monarch", "ruler", "lord", "lady", "duke",
            "duchess", "count", "baron", "noble", "aristocrat", "crown",
            # Military
            "soldier", "warrior", "knight", "guard", "sentinel", "watchman",
            "captain", "general", "commander", "officer", "admiral", "colonel",
            "marine", "infantry", "cavalry", "archer", "spearman", "swordsman",
            "gladiator", "samurai", "viking", "spartan", "legionnaire", "mercenary",
            "army", "troop", "regiment", "battalion", "garrison", "patrol",
            # Maritime
            "sailor", "pirate", "buccaneer", "corsair", "privateer", "captain",
            "shipwright", "boatman", "fisherman", "whaler", "navigator",
            # Science & Learning
            "scientist", "doctor", "physician", "surgeon", "nurse", "researcher",
            "engineer", "inventor", "technician", "programmer", "mathematician",
            "physicist", "chemist", "biologist", "astronomer", "geologist",
            "teacher", "professor", "scholar", "student", "pupil", "graduate",
            "philosopher", "thinker", "intellectual", "sage", "genius",
            "gutenberg", "einstein", "newton", "darwin", "galileo", "copernicus",
            "kepler", "pythagoras", "archimedes", "plato", "aristotle", "socrates",
            "freud", "curie", "tesla", "edison", "bell", "wright", "franklin",
            # Arts & Culture
            "artist", "painter", "sculptor", "musician", "composer", "singer",
            "dancer", "actor", "poet", "writer", "author", "journalist",
            "photographer", "filmmaker", "director", "producer", "architect",
            "designer", "fashion", "craftsman", "artisan", "potter", "weaver",
            # Religion & Spirituality
            "monk", "nun", "priest", "pastor", "rabbi", "imam", "monk",
            "missionary", "prophet", "saint", "pilgrim", "hermit", "oracle",
            "shaman", "druid", "wizard", "mage", "sorcerer", "witch",
            # Exploration
            "explorer", "adventurer", "pioneer", "settler", "colonist",
            "traveler", "voyager", "nomad", "wanderer", "pilgrim", "hiker",
            "courier", "messenger", "scout", "guide", "pathfinder",
            "columbus", "magellan", "vasco", "marco polo", "lewis", "clark",
            # Workers
            "worker", "laborer", "farmer", "peasant", "serf", "slave",
            "blacksmith", "carpenter", "mason", "builder", "miner", "smith",
            "baker", "butcher", "merchant", "trader", "shopkeeper", "vendor",
            "hunter", "gatherer", "herder", "shepherd", "cowboy", "rancher",
            "fisher", "lumberjack", "woodcutter", "tailor", "cobbler",
            # Historical figures
            "caesar", "napoleon", "alexander", "cleopatra", "nefertiti",
            "lincoln", "washington", "churchill", "elizabeth", "victoria",
            "gandhi", "mandela", "martin luther king", "mother teresa",
            "genghis", "attila", "charlemagne", "saladin", "leonidas",
        ],
    }

    ANIMALS = {
        "animal": [
            # Mammals
            "dog", "cat", "horse", "cow", "bull", "ox", "sheep", "goat", "pig",
            "rabbit", "hare", "deer", "stag", "doe", "moose", "elk", "caribou",
            "fox", "wolf", "bear", "lion", "tiger", "leopard", "panther", "jaguar",
            "elephant", "rhino", "hippo", "giraffe", "zebra", "antelope", "gazelle",
            "monkey", "ape", "gorilla", "chimp", "orangutan", "lemur",
            "kangaroo", "koala", "panda", "sloth", "raccoon", "squirrel", "chipmunk",
            "beaver", "otter", "mole", "hedgehog", "porcupine", "skunk", "badger",
            "bat", "rat", "mouse", "hamster", "guinea pig", "vole",
            "buffalo", "bison", "yak", "camel", "llama", "alpaca", "donkey", "mule",
            "seal", "walrus", "dolphin", "whale", "orca", "manatee",
            # Mythical
            "dragon", "unicorn", "griffin", "phoenix", "pegasus", "centaur",
            "minotaur", "chimera", "hydra", "basilisk", "werewolf", "vampire",
        ],
        "bird": [
            "bird", "eagle", "hawk", "falcon", "vulture", "raven", "crow", "magpie",
            "owl", "parrot", "macaw", "cockatoo", "canary", "finch", "sparrow",
            "robin", "bluebird", "cardinal", "hummingbird", "woodpecker", "kingfisher",
            "swan", "duck", "goose", "heron", "crane", "stork", "flamingo",
            "peacock", "turkey", "pheasant", "quail", "pigeon", "dove",
            "penguin", "ostrich", "emu", "kiwi", "albatross", "seagull", "pelican",
        ],
        "fish": [
            "fish", "shark", "whale", "dolphin", "tuna", "salmon", "trout", "bass",
            "goldfish", "koi", "clownfish", "angelfish", "swordfish", "marlin",
            "ray", "eel", "octopus", "squid", "jellyfish", "crab", "lobster",
            "shrimp", "seahorse", "starfish", "coral", "anemone",
        ],
    }

    NATURE_ELEMENTS = {
        "mountain": [
            "mountain", "mountains", "mountainous", "peak", "summit", "cliff", "cliffs",
            "alps", "himalaya", "andes", "rockies", "everest", "kilimanjaro",
            "volcano", "volcanic", "crater", "ridge", "range", "highland",
            "canyon", "gorge", "ravine", "valley", "crag", "bluff", "escarpment",
            "rocky", "rock", "boulder", "stone", "granite", "limestone", "marble",
        ],
        "tree": [
            "tree", "trees", "forest", "forests", "forestry", "woodland", "woods",
            "jungle", "rainforest", "grove", "orchard", "plantation",
            "pine", "oak", "maple", "birch", "willow", "cedar", "redwood",
            "sequoia", "palm", "coconut", "bamboo", "teak", "mahogany", "ebony",
            "conifer", "evergreen", "deciduous", "leaf", "leaves", "foliage",
            "park", "garden", "arboretum", "timber", "lumber",
        ],
        "hill": [
            "hill", "hills", "hilly", "rolling hills", "meadow", "meadows",
            "field", "fields", "pasture", "grassland", "prairie", "savanna",
            "plain", "plains", "plateau", "tableland", "mesa", "butte",
            "farmland", "countryside", "rural", "agriculture", "farm",
            "green", "grass", "grassy", "open field",
        ],
        "water": [
            "water", "ocean", "sea", "seaside", "marine", "maritime",
            "river", "rivers", "riverbank", "stream", "creek", "brook",
            "lake", "lakes", "pond", "lagoon", "reservoir",
            "waterfall", "falls", "cascade", "rapids", "waterfall",
            "wave", "waves", "surf", "swell", "current", "tide",
            "beach", "shore", "shoreline", "coast", "coastal", "bay",
            "harbor", "port", "dock", "pier", "wharf", "marina",
            "coral", "reef", "atoll", "island", "isle", "peninsula",
            "riverbank", "estuary", "delta", "fjord", "sound", "strait",
        ],
        "cloud": [
            "cloud", "clouds", "cloudy", "overcast", "sky", "skies",
            "fog", "foggy", "mist", "misty", "haze", "hazy",
            "rain", "rainy", "rainbow", "raindrop",
            "storm", "stormy", "thunder", "lightning", "tempest",
            "hurricane", "tornado", "cyclone", "typhoon", "monsoon",
            "breeze", "wind", "windy", "gale", "gust",
        ],
        "sun": [
            "sun", "sunny", "sunlight", "sunshine", "sunrise", "sunset",
            "dawn", "dusk", "twilight", "daybreak", "morning", "noon",
            "afternoon", "daytime", "daylight", "bright", "shining",
        ],
        "moon": [
            "moon", "moonlight", "moonlit", "crescent", "full moon",
            "half moon", "new moon", "lunar", "eclipse",
            "night", "nighttime", "midnight", "evening", "dusk",
        ],
        "star": [
            "star", "stars", "starry", "starlight", "constellation",
            "galaxy", "galaxies", "nebula", "milky way",
            "comet", "asteroid", "meteor", "shooting star",
            "planet", "saturn", "jupiter", "mars", "venus", "mercury",
            "solar", "cosmos", "celestial", "astronomy", "astronaut",
        ],
        "desert": [
            "desert", "deserts", "deserted", "arid", "dry", "drought",
            "sand", "sandy", "dune", "dunes", "sahara", "gobi",
            "cactus", "cacti", "succulent", "agave", "yucca",
            "oasis", "mirage", "heat", "scorching",
        ],
        "snow": [
            "snow", "snowy", "snowfall", "snowflake", "snowman",
            "winter", "wintry", "ice", "icy", "icicle", "iceberg",
            "glacier", "frozen", "freeze", "frost", "frosty",
            "arctic", "antarctic", "polar", "north pole", "south pole",
            "tundra", "blizzard", "sleet", "hail", "chill",
            "ski", "snowboard", "snowball", "igloo",
        ],
    }

    # ── Environments ──
    ENVIRONMENTS = [
        ("indoor", [
            "indoor", "inside", "interior", "room", "house", "home", "building",
            "workshop", "studio", "laboratory", "lab", "library", "study",
            "church", "temple", "mosque", "shrine", "cathedral", "chapel",
            "castle", "palace", "fortress", "dungeon", "cell", "prison",
            "cave", "cavern", "underground", "basement", "attic",
            "office", "factory", "school", "classroom", "hospital",
            "kitchen", "bathroom", "bedroom", "living room", "dining",
            "hall", "corridor", "staircase", "gallery", "museum",
            "theater", "cinema", "auditorium", "arena", "colosseum",
            "restaurant", "cafe", "tavern", "inn", "bar", "pub",
            "store", "shop", "market", "bazaar", "warehouse",
            "garage", "shed", "barn", "stable", "greenhouse",
            "tent", "tepee", "yurt", "hut", "cabin", "cottage",
        ]),
        ("night", [
            "night", "nighttime", "midnight", "evening", "dusk", "twilight",
            "moon", "moonlight", "moonlit", "star", "starry", "starlight",
            "dark", "darkness", "shadow", "shadows", "black",
            "space", "outer space", "galaxy", "nebula", "cosmos",
            "astronaut", "rocket", "spaceship", "satellite", "telescope",
            "campfire", "bonfire", "torch", "candle", "lantern",
        ]),
        ("ocean", [
            "ocean", "sea", "seaside", "marine", "maritime", "nautical",
            "beach", "shore", "shoreline", "coast", "coastal", "bay",
            "harbor", "port", "pier", "dock", "wharf",
            "wave", "waves", "surf", "tide", "underwater",
            "pirate", "ship", "boat", "sail", "sailor", "fleet",
            "fish", "shark", "whale", "dolphin", "coral", "reef",
            "island", "isle", "peninsula", "lighthouse",
            "mermaid", "kraken", "sea monster",
        ]),
        ("sunset", [
            "sunset", "sunrise", "dawn", "dusk", "twilight",
            "evening", "golden hour", "horizon",
        ]),
        ("desert", [
            "desert", "arid", "sand", "dune", "cactus", "sahara",
            "oasis", "mirage", "scorching", "drought",
        ]),
        ("snow", [
            "snow", "winter", "ice", "glacier", "arctic", "frozen",
            "blizzard", "tundra", "polar", "iceberg", "snowy",
        ]),
        ("forest", [
            "forest", "woodland", "woods", "jungle", "rainforest",
            "grove", "thicket", "wilderness", "bush", "bamboo",
            "green", "foliage", "canopy", "undergrowth",
        ]),
        ("underwater", [
            "underwater", "submarine", "deep sea", "ocean floor",
            "coral reef", "coral", "kelp", "seaweed", "aquatic",
            "diving", "scuba", "submersible", "atlantis",
        ]),
        ("space", [
            "space", "outer space", "universe", "cosmos", "galaxy",
            "star", "planet", "satellite", "rocket", "spaceship",
            "astronaut", "telescope", "observatory", "nebula",
            "mars", "moon", "jupiter", "saturn", "solar system",
        ]),
        ("city", [
            "city", "cities", "urban", "downtown", "metropolis",
            "skyscraper", "tower", "street", "road", "avenue",
            "neighborhood", "district", "suburb", "town", "village",
            "busy", "traffic", "crowd", "market", "plaza", "square",
            "bridge", "highway", "railway", "station",
        ]),
        ("farm", [
            "farm", "farmland", "ranch", "pasture", "barn", "stable",
            "crop", "harvest", "field", "countryside", "rural",
            "tractor", "windmill", "silo", "hay", "fence",
            "cow", "horse", "sheep", "chicken", "pig", "goat",
        ]),
        ("industrial", [
            "factory", "industrial", "manufacturing", "plant",
            "warehouse", "mill", "foundry", "smoke", "chimney",
            "machine", "engine", "steam", "coal", "steel",
            "assembly line", "robot", "automation", "industry",
        ]),
    ]

    BUILDINGS = {
        "building": [
            "building", "buildings", "skyscraper", "tower", "towers",
            "castle", "fortress", "citadel", "stronghold", "bastion",
            "palace", "mansion", "villa", "estate", "manor",
            "temple", "church", "cathedral", "mosque", "shrine", "pagoda",
            "pyramid", "monument", "memorial", "statue", "obelisk",
            "ruins", "ruined", "abandoned", "ancient",
            "bridge", "aqueduct", "viaduct", "wall", "gate",
            "lighthouse", "windmill", "mill", "barn", "silo",
            "stadium", "arena", "colosseum", "amphitheater",
            "observatory", "planetarium", "museum", "gallery",
            "station", "terminal", "airport", "hangar",
            "fountain", "well", "monastery", "convent",
            "fort", "fortification", "bunker", "pillbox",
            "lighthouse", "beacon", "minaret", "spire", "dome",
            "city", "town", "village", "settlement", "outpost",
        ],
        "house": [
            "house", "houses", "home", "cottage", "cabin", "hut", "shack",
            "villa", "bungalow", "ranch", "farmhouse", "manor",
            "roof", "door", "window", "porch", "balcony", "terrace",
            "chimney", "fireplace", "hearth", "garden", "yard",
            "fence", "gate", "driveway", "garage", "shed",
            "neighbor", "neighborhood", "suburb", "residential",
        ],
    }

    OBJECTS = {
        "ship": [
            "ship", "ships", "boat", "boats", "vessel", "craft",
            "sail", "sailboat", "sailing", "yacht", "canoe", "kayak",
            "raft", "dinghy", "skiff", "rowboat", "gondola",
            "galleon", "frigate", "warship", "man-of-war",
            "submarine", "battleship", "carrier", "destroyer",
            "pirate ship", "merchant ship", "cargo ship", "tanker",
            "fleet", "navy", "flotilla", "armada",
        ],
        "vehicle": [
            "car", "cars", "automobile", "truck", "bus", "van",
            "taxi", "jeep", "suv", "sedan", "coupe", "convertible",
            "train", "locomotive", "railway", "railroad", "tram",
            "bicycle", "bike", "motorcycle", "scooter",
            "plane", "airplane", "aircraft", "jet", "helicopter",
            "rocket", "spaceship", "shuttle", "capsule",
            "wagon", "cart", "carriage", "chariot", "stagecoach",
            "tractor", "bulldozer", "crane", "forklift",
            "ambulance", "fire truck", "police car",
            "hot air balloon", "blimp", "dirigible", "airship",
        ],
        "cannon": [
            "cannon", "cannons", "artillery", "gun", "guns", "rifle",
            "pistol", "musket", "revolver", "shotgun",
            "bow", "crossbow", "arrow", "spear", "javelin",
            "sword", "blade", "saber", "cutlass", "dagger", "knife",
            "shield", "armor", "helmet", "weapon", "weapons",
            "missile", "rocket", "bomb", "grenade", "mine",
            "tank", "battle tank", "howitzer", "mortar",
        ],
        "flag": [
            "flag", "flags", "banner", "banners", "standard",
            "pennant", "ensign", "colors", "emblem",
            "coat of arms", "heraldry", "crest", "insignia",
        ],
        "path": [
            "path", "paths", "trail", "trails", "road", "roads",
            "street", "streets", "route", "lane", "alley",
            "highway", "motorway", "freeway", "expressway",
            "bridge", "walkway", "sidewalk", "pavement",
            "track", "rail", "railway", "railroad", "line",
            "journey", "travel", "route", "passage", "corridor",
        ],
        "throne": [
            "throne", "throne room", "seat", "chair", "bench",
            "sofa", "couch", "bed", "table", "desk", "stool",
        ],
        "chest": [
            "chest", "treasure chest", "box", "crate", "barrel",
            "basket", "bucket", "safe", "vault", "locker",
        ],
        "book": [
            "book", "books", "scroll", "scrolls", "manuscript",
            "document", "paper", "page", "letter", "map", "chart",
            "newspaper", "magazine", "journal", "diary", "notebook",
            "library", "shelf", "bookshelf", "reading",
        ],
        "lamp": [
            "lamp", "lamp", "lantern", "candle", "torch", "light",
            "chandelier", "bulb", "beacon", "fire", "flame",
            "campfire", "bonfire", "hearth", "furnace", "oven",
        ],
        "bell": [
            "bell", "bells", "gong", "chime", "clock", "hourglass",
            "sundial", "compass", "telescope", "microscope",
        ],
        "cross": [
            "cross", "crucifix", "star", "crescent", "symbol",
            "emblem", "totem", "idol", "statue", "figure",
        ],
        "furniture": [
            "table", "desk", "chair", "bench", "stool", "throne",
            "bed", "couch", "sofa", "cabinet", "chest", "drawer",
            "shelf", "bookshelf", "rack", "wardrobe", "dresser",
            "counter", "altar", "pedestal", "lectern", "podium",
        ],
        "food": [
            "food", "fruit", "bread", "meat", "cheese", "wine",
            "cup", "glass", "bottle", "plate", "bowl", "dish",
            "feast", "banquet", "meal", "dinner", "bread",
            "grapes", "apple", "corn", "wheat", "grain", "harvest",
        ],
        "tool": [
            "tool", "hammer", "saw", "axe", "hoe", "shovel",
            "pickaxe", "sickle", "plow", "anvil", "forge",
            "wheel", "pulley", "lever", "gear", "spring",
            "machine", "engine", "motor", "pump", "turbine",
            "clockwork", "mechanism", "robot", "automaton",
        ],
        "pottery": [
            "pot", "pottery", "vase", "urn", "jar", "amphora",
            "bowl", "plate", "cup", "goblet", "chalice",
        ],
    }

    ABSTRACT = {
        "text": [
            "story", "legend", "myth", "tale", "fable", "history",
            "knowledge", "wisdom", "truth", "secret", "message",
            "idea", "concept", "theory", "law", "rule", "principle",
            "word", "language", "writing", "literature", "poetry",
            "education", "learning", "science", "philosophy",
            "freedom", "justice", "peace", "love", "hope", "dream",
            "discovery", "invention", "innovation", "progress",
            "revolution", "change", "transformation", "evolution",
            "power", "strength", "courage", "bravery", "honor",
            "beauty", "wonder", "awe", "mystery", "magic",
            "time", "eternity", "infinity", "destiny", "fate",
            "life", "death", "birth", "rebirth", "immortality",
            "faith", "belief", "religion", "spirit", "soul",
            "war", "battle", "conflict", "struggle", "victory",
            "defeat", "surrender", "peace", "truce", "alliance",
            "kingdom", "empire", "nation", "republic", "democracy",
            "wealth", "treasure", "gold", "silver", "riches",
            "poverty", "hunger", "disease", "suffering", "pain",
        ],
        "label": [
            "name", "title", "sign", "symbol", "signature",
            "brand", "logo", "mark", "stamp", "seal",
            "label", "tag", "badge", "emblem", "insignia",
        ],
        "arrow": [
            "arrow", "arrows", "direction", "point", "pointing",
            "pointer", "guide", "compass", "navigate",
            "path", "journey", "progress", "forward", "future",
            "movement", "direction", "vector", "flow",
        ],
        "x_mark": [
            "no", "not", "never", "stop", "end", "death", "danger",
            "wrong", "false", "myth", "lie", "deception",
            "forbidden", "banned", "illegal", "cancel",
            "cross", "x mark", "dead end", "blocked",
        ],
    }

    # ── Marine mammals (whales, dolphins — separate from generic fish) ──
    MARINE_MAMMALS = {
        "whale": [
            "whale", "whales", "whale's", "blue whale", "humpback", "sperm whale",
            "orca", "killer whale", "minke", "right whale", "bowhead",
            "beluga", "narwhal", "pilot whale",
            "cetacean", "cetaceans",
        ],
        "dolphin": [
            "dolphin", "dolphins", "porpoise", "bottlenose",
        ],
        "walking_whale": [
            "ambulocetus", "pakicetus", "basilosaurus", "dorudon",
            "walking whale", "ancient whale", "early whale", "first whale",
            "whale ancestor", "proto-whale", "primitive whale",
            "rodhocetus", "maiacetus", "kutchicetus",
        ],
    }

    # ── Anatomy / body parts ──
    ANATOMY = {
        "skeleton": [
            "skeleton", "skeletal", "bone", "bones", "pelvic", "pelvis",
            "pelvic bone", "pelvic bones", "rib", "ribs", "ribcage",
            "skull", "vertebra", "vertebrae", "spine", "backbone",
            "fossil", "fossils", "fossilized", "fossil record",
            "remnant", "remnants", "hind leg", "hind legs",
            "hindlimb", "hind limbs", "vestigial",
        ],
        "flipper": [
            "flipper", "flippers", "fin", "fins", "paddle", "paddles",
            "forelimb", "forelimbs", "front leg", "front legs",
        ],
        "blowhole": [
            "blowhole", "blowholes", "nostril", "nostrils",
            "breathe air", "surface", "spout",
        ],
        "tail": [
            "tail", "tails", "tail fluke", "fluke", "flukes",
            "caudal", "tail fin",
        ],
        "mammal": [
            "mammal", "mammals", "mammalian", "milk", "nurse",
            "warm-blooded", "warm blooded", "fur", "hair",
            "breathe air", "lungs", "live birth", "offspring",
        ],
    }

    # ── Polar / Antarctica / Ice ──
    POLAR = {
        "glacier": [
            "glacier", "glaciers", "glacial", "ice sheet", "ice sheets", "ice shelf",
            "iceberg", "icebergs", "ice cap", "ice caps", "polar ice",
            "frozen continent", "endless ice", "world of ice", "continent of ice",
            "wilderness of ice", "frozen wilderness",
        ],
        "iceberg": [
            "iceberg", "icebergs", "ice floe", "ice flow", "pack ice",
            "floating ice", "frozen ocean", "ice chunks",
        ],
        "tundra": [
            "tundra", "barren", "frozen desert", "frozen wasteland",
            "permafrost", "cold desert", "frost", "frosty",
        ],
        "antarctica": [
            "antarctica", "antarctic", "south pole", "southernmost",
            "polar region", "south polar", "southern continent",
        ],
    }

    # ── Evolution / prehistory / time ──
    PREHISTORY = {
        "evolution": [
            "evolution", "evolve", "evolved", "evolving", "evolutionary",
            "natural selection", "adaptation", "adapt", "adapted",
            "mutation", "mutations", "genetic", "generation", "generations",
            "species", "speciation", "descendant", "descendants",
            "ancestor", "ancestors", "ancestral", "common ancestor",
            "transitional", "transition", "intermediate",
            "darwin", "origin of species",
        ],
        "prehistoric": [
            "prehistoric", "ancient", "million years", "million-year",
            "50 million", "fifty million", "era", "epoch",
            "eocene", "oligocene", "miocene", "pliocene", "pleistocene",
            "mesozoic", "cenozoic", "paleocene",
            "early mammal", "early mammals", "primitive mammal",
            "land mammal", "terrestrial",
        ],
        "timeline": [
            "timeline", "time", "years", "era", "age", "ages",
            "past", "history", "origin", "beginning",
            "long ago", "once upon a time",
        ],
    }

    # ── Mood detection ──
    MOOD_KEYWORDS = {
        "dramatic": [
            "dramatic", "ice takes control", "cooling accelerated",
            "ice advanced", "powerful current", "moat", "barrier",
            "war", "battle", "fight", "warrior", "attack", "explosion", "crash",
            "storm", "danger", "enemy", "invade", "destroy", "death", "kill",
            "blood", "fire", "burn", "explode", "battle", "conflict",
            "crisis", "emergency", "urgent", "intense", "fierce",
            "chase", "escape", "race", "speed", "rush",
            "clash", "collision", "impact", "strike", "blow",
            "rage", "fury", "anger", "wrath", "vengeance",
            "desperate", "last stand", "final", "showdown",
        ],
        "somber": [
            "death", "dead", "grave", "funeral", "mourn", "grief",
            "sad", "sorrow", "tragedy", "loss", "cry", "tears",
            "darkness", "shadow", "gloom", "despair", "hopeless",
            "misery", "suffer", "pain", "hunger", "famine",
            "disease", "plague", "illness", "wound", "injured",
            "poverty", "poor", "homeless", "lonely", "alone",
            "ruins", "destroyed", "abandoned", "desolate",
            "rain", "cold", "winter", "gray", "dreary",
            "slave", "chains", "prison", "captive", "captivity",
        ],
        "hopeful": [
            "hope", "hopeful", "future", "dream", "dreams",
            "discover", "discovery", "invention", "innovation",
            "freedom", "liberate", "free", "peace", "harmony",
            "brave", "bravery", "courage", "hero", "heroic",
            "success", "victory", "triumph", "achievement",
            "rise", "rise up", "born", "birth", "new life",
            "light", "sunrise", "dawn", "spring", "bloom",
            "miracle", "wonder", "amazing", "beautiful",
            "love", "kindness", "compassion", "mercy",
            "inspire", "inspiration", "aspire", "ambition",
            "progress", "advance", "forward", "better",
        ],
        "epic": [
            "epic", "legend", "legendary", "myth", "mythical",
            "hero", "heroic", "journey", "quest", "adventure",
            "empire", "kingdom", "dynasty", "civilization",
            "world", "universe", "cosmos", "galaxy", "infinite",
            "revolution", "transformation", "great", "grand",
            "mountain", "ocean", "desert", "temple", "pyramid",
            "ancient", "eternal", "timeless", "immortal",
            "glory", "majesty", "splendor", "magnificent",
            "colossal", "massive", "titanic", "enormous",
            "god", "goddess", "divine", "celestial", "mythology",
            "saga", "chronicle", "history", "age", "era",
            "evolution", "evolve", "evolved", "million years",
            "prehistoric", "ancestor", "ancestors", "origin",
            "largest", "biggest", "greatest", "ruling",
        ],
        "mysterious": [
            "mystery", "mysterious", "secret", "hidden", "unknown",
            "ancient", "forgotten", "lost", "discover",
            "myth", "legend", "folklore", "supernatural",
            "magic", "magical", "enchant", "spell", "curse",
            "ghost", "spirit", "phantom", "haunt", "haunted",
            "strange", "weird", "odd", "peculiar", "bizarre",
            "dark", "shadow", "fog", "mist", "gloom",
            "forbidden", "sacred", "occult", "arcane", "esoteric",
            "riddle", "puzzle", "enigma", "cryptic", "code",
            "oracle", "prophecy", "vision", "dream", "trance",
            "monster", "creature", "beast", "alien", "unknown",
            "secret hidden inside", "remnant", "remnants", "vestigial",
            "evidence", "clue", "clues", "trace", "traces",
            "whisper", "memory", "fossilized",
        ],
        "peaceful": [
            "peace", "peaceful", "calm", "quiet", "silent", "still",
            "gentle", "soft", "tender", "warm", "cozy",
            "beautiful", "lovely", "charming", "delightful",
            "love", "romance", "together", "family", "home",
            "garden", "flower", "meadow", "stream", "breeze",
            "village", "countryside", "rural", "pastoral",
            "happy", "joy", "smile", "laugh", "content",
            "rest", "sleep", "dream", "meditate", "relax",
            "sunset", "sunrise", "dawn", "golden", "serene",
            "harmony", "balance", "tranquil", "placid",
            "nest", "hearth", "fireplace", "warmth", "comfort",
        ],
    }

    # ── Color palettes ──
    PALETTES = {
        "gradient": [
            {"colors": [[200, 210, 230], [140, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]},
            {"colors": [[180, 200, 220], [100, 150, 200]], "horizon": 0.55, "ground_color": [50, 80, 40]},
            {"colors": [[230, 220, 200], [180, 170, 150]], "horizon": 0.6, "ground_color": [100, 90, 70]},
            {"colors": [[200, 220, 240], [160, 190, 220]], "horizon": 0.55, "ground_color": [70, 100, 60]},
            {"colors": [[220, 230, 210], [150, 180, 140]], "horizon": 0.6, "ground_color": [80, 110, 60]},
            {"colors": [[210, 200, 220], [150, 140, 180]], "horizon": 0.55, "ground_color": [70, 60, 90]},
            {"colors": [[240, 230, 210], [200, 180, 150]], "horizon": 0.6, "ground_color": [140, 120, 90]},
        ],
        "night": [
            {"colors": [[5, 3, 20], [15, 10, 40]], "horizon": 0.6, "ground_color": [15, 20, 30]},
            {"colors": [[8, 6, 25], [25, 18, 50]], "horizon": 0.55, "ground_color": [20, 25, 35]},
            {"colors": [[10, 8, 30], [30, 25, 60]], "horizon": 0.6, "ground_color": [20, 30, 20]},
        ],
        "ocean": [
            {"sky_color": [180, 210, 240], "horizon_color": [120, 170, 220], "horizon": 0.5, "water_color": [30, 70, 150]},
            {"sky_color": [160, 190, 230], "horizon_color": [100, 150, 200], "horizon": 0.48, "water_color": [25, 60, 130]},
            {"sky_color": [200, 220, 240], "horizon_color": [140, 180, 220], "horizon": 0.52, "water_color": [40, 90, 170]},
        ],
        "sunset": [
            {"colors": [[220, 100, 70], [200, 120, 90], [160, 80, 100], [80, 50, 80]], "horizon": 0.5, "ground_color": [40, 50, 30]},
            {"colors": [[230, 130, 90], [200, 100, 100], [140, 70, 100], [60, 40, 60]], "horizon": 0.5, "ground_color": [35, 45, 25]},
            {"colors": [[180, 90, 80], [200, 140, 100], [120, 80, 100], [50, 40, 50]], "horizon": 0.5, "ground_color": [45, 55, 35]},
        ],
        "desert": [
            {"colors": [[240, 220, 180], [200, 180, 140]], "horizon": 0.55, "ground_color": [180, 160, 100]},
            {"colors": [[250, 230, 190], [210, 190, 150]], "horizon": 0.5, "ground_color": [190, 170, 110]},
            {"colors": [[230, 210, 170], [190, 170, 130]], "horizon": 0.55, "ground_color": [170, 150, 90]},
        ],
        "snow": [
            {"colors": [[220, 230, 240], [180, 200, 220]], "horizon": 0.55, "ground_color": [200, 210, 220]},
            {"colors": [[200, 215, 235], [160, 185, 210]], "horizon": 0.5, "ground_color": [190, 200, 215]},
            {"colors": [[230, 240, 250], [190, 210, 235]], "horizon": 0.55, "ground_color": [210, 220, 230]},
        ],
        "forest": [
            {"colors": [[80, 140, 80], [30, 70, 30]], "horizon": 0.7, "ground_color": [25, 55, 25]},
            {"colors": [[100, 160, 100], [40, 80, 40]], "horizon": 0.65, "ground_color": [30, 60, 30]},
            {"colors": [[120, 170, 110], [50, 90, 50]], "horizon": 0.7, "ground_color": [35, 65, 35]},
        ],
        "underwater": [
            {"colors": [[10, 40, 80], [5, 20, 50]], "horizon": 0.0, "ground_color": [30, 60, 80]},
            {"colors": [[20, 60, 100], [10, 30, 60]], "horizon": 0.0, "ground_color": [40, 70, 90]},
            {"colors": [[30, 80, 120], [15, 40, 70]], "horizon": 0.0, "ground_color": [50, 80, 100]},
        ],
        "space": [
            {"colors": [[2, 2, 15], [5, 3, 25]], "horizon": 0.0},
            {"colors": [[3, 1, 18], [8, 5, 30]], "horizon": 0.0},
            {"colors": [[1, 2, 12], [4, 3, 22]], "horizon": 0.0},
        ],
        "city": [
            {"colors": [[180, 190, 210], [120, 140, 170]], "horizon": 0.5, "ground_color": [80, 80, 80]},
            {"colors": [[200, 200, 210], [150, 150, 170]], "horizon": 0.5, "ground_color": [90, 90, 90]},
            {"colors": [[100, 100, 120], [60, 60, 80]], "horizon": 0.5, "ground_color": [40, 40, 50]},
        ],
        "farm": [
            {"colors": [[200, 220, 190], [150, 180, 130]], "horizon": 0.6, "ground_color": [100, 130, 70]},
            {"colors": [[210, 225, 200], [160, 190, 140]], "horizon": 0.55, "ground_color": [110, 140, 80]},
            {"colors": [[190, 210, 180], [140, 170, 120]], "horizon": 0.6, "ground_color": [90, 120, 60]},
        ],
        "industrial": [
            {"colors": [[140, 140, 150], [90, 90, 100]], "horizon": 0.5, "ground_color": [60, 60, 65]},
            {"colors": [[160, 150, 140], [110, 100, 95]], "horizon": 0.5, "ground_color": [70, 65, 60]},
            {"colors": [[120, 130, 140], [80, 85, 95]], "horizon": 0.5, "ground_color": [50, 55, 60]},
        ],
        "indoor": [
            {"wall_color": [210, 200, 180], "floor_color": [160, 140, 120]},
            {"wall_color": [200, 190, 170], "floor_color": [140, 130, 110]},
            {"wall_color": [220, 210, 190], "floor_color": [170, 150, 130]},
            {"wall_color": [230, 215, 200], "floor_color": [150, 120, 100]},
            {"wall_color": [190, 200, 210], "floor_color": [140, 150, 160]},
            {"wall_color": [180, 170, 160], "floor_color": [130, 110, 100]},
            {"wall_color": [240, 235, 220], "floor_color": [180, 170, 150]},
        ],
    }

    # ═══════════════════════════════════════════════════════════════
    #  COMPOSITION
    # ═══════════════════════════════════════════════════════════════

    def compose_script(self, topic: str, n_scenes: int = 4) -> dict:
        """Generate a full multi-scene documentary script from a topic."""
        t = topic.lower()
        title = self._make_title(topic, t)
        env = self._detect_environment(t)

        scenes = []
        for i in range(n_scenes):
            scene_title = self._scene_title(t, i, n_scenes, env)
            narration = self._scene_narration(t, i, n_scenes, topic, env)
            scene = self.compose_scene(t + " " + scene_title.lower(), scene_title)
            # Wrap visual fields under "visual" key as expected by auto_story.py
            scene["visual"] = {
                "bg": scene.pop("bg", {}),
                "elements": scene.pop("elements", []),
                "atmosphere": scene.pop("atmosphere", {}),
            }
            scene["narration"] = narration
            scene["title"] = scene_title
            scene["scene_num"] = i + 1
            cams = [None, "ken_burns_in", "pan_right", "ken_burns_out",
                    "pan_left", "dolly_in", None, "dolly_out"]
            scene["camera"] = cams[i % len(cams)]
            scenes.append(scene)

        return {"title": title, "scenes": scenes}

    def _make_title(self, raw: str, lower: str) -> str:
        words = raw.split()
        if len(words) <= 4:
            return raw.title()
        return " ".join(w for w in words[:6]).title()

    def compose_scene(self, topic: str, scene_title: str = "") -> dict:
        """Compose a single scene from any topic string."""
        t = topic.lower()
        st = scene_title.lower()

        env = self._detect_environment(t, st)
        bg = self._make_background(env)
        mood = self._detect_mood(t, st)

        concepts = self._extract_concepts(t, st)
        elements = self._compose_elements(concepts, env, mood, st)

        if len(elements) < 3:
            elements += self._fill_elements(env, mood, len(elements))

        atmos = self._make_atmosphere(env, mood)

        return {
            "bg": bg,
            "elements": elements,
            "atmosphere": atmos,
            "mood": mood
        }

    # ── Environment detection ──
    def _detect_environment(self, topic: str, scene_title: str = "") -> str:
        combined = topic + " " + scene_title
        scored = []
        for env_name, keywords in self.ENVIRONMENTS:
            score = sum(1 for w in keywords if w in combined)
            if score > 0:
                scored.append((score, env_name))
        if scored:
            return max(scored, key=lambda x: x[0])[1]

        for kws in self.BUILDINGS.values():
            if any(w in combined for w in kws):
                return "indoor"
        for kws in self.NATURE_ELEMENTS.values():
            if any(w in combined for w in kws):
                return "gradient"
        return "indoor"

    # ── Mood detection ──
    def _detect_mood(self, topic: str, scene_title: str = "") -> str:
        combined = topic + " " + scene_title
        scores = {}
        for mood_name, keywords in self.MOOD_KEYWORDS.items():
            scores[mood_name] = sum(1 for w in keywords if w in combined)
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "peaceful"

    # ── Background ──
    def _make_background(self, env: str) -> dict:
        palettes = self.PALETTES.get(env, self.PALETTES["gradient"])
        bg = {"type": env}
        bg.update(self.rng.choice(palettes))
        return bg

    # ── Concept extraction ──
    def _extract_concepts(self, topic: str, scene_title: str = "") -> list:
        combined = topic + " " + scene_title
        found = []

        # Marine mammals (highest priority for whale topics)
        for etype, keywords in self.MARINE_MAMMALS.items():
            if any(w in combined for w in keywords):
                found.append((etype, 15))
                break

        # Anatomy / body parts
        for etype, keywords in self.ANATOMY.items():
            if any(w in combined for w in keywords):
                found.append((etype, 12))

        # Prehistory / evolution
        for etype, keywords in self.PREHISTORY.items():
            if any(w in combined for w in keywords):
                found.append((etype, 11))

        # Polar / Antarctica (high priority for icy texts)
        for etype, keywords in self.POLAR.items():
            if any(w in combined for w in keywords):
                found.append((etype, 14))
                break

        # People
        for etype, keywords in self.PEOPLE.items():
            if any(w in combined for w in keywords):
                found.append((etype, 10))
                break

        # Animals
        for etype, keywords in self.ANIMALS.items():
            if any(w in combined for w in keywords):
                found.append((etype, 8))
                break

        # Nature
        for etype, keywords in self.NATURE_ELEMENTS.items():
            weight = 9 if etype in ("mountain", "water") else 7
            if any(w in combined for w in keywords):
                found.append((etype, weight))

        # Buildings
        for etype, keywords in self.BUILDINGS.items():
            if any(w in combined for w in keywords):
                found.append((etype, 8))

        # Objects
        for etype, keywords in self.OBJECTS.items():
            if any(w in combined for w in keywords):
                found.append((etype, 6))

        # Abstract
        for etype, keywords in self.ABSTRACT.items():
            if any(w in combined for w in keywords):
                found.append((etype, 4))

        return found

    # ── Element composition ──
    def _compose_elements(self, concepts: list, env: str, mood: str, st: str = "") -> list:
        elements = []
        placed = set()
        has_water = False

        # Always add background landscape
        if env in ("gradient", "forest", "snow", "farm"):
            if self.rng.random() < 0.7 and "mountain" not in placed:
                elements.append(self._make_landscape("mountain", mood))
                placed.add("mountain")

        # Check for combined concepts unique to antarctica/fossils
        has_antarctica = any(c[0] == "antarctica" for c in concepts)
        has_fossil = any(c[0] == "skeleton" for c in concepts)
        has_tectonic = "tectonic" in st.lower() or any(w in st.lower() for w in ("tectonic", "continental drift", "plates drift"))

        for etype, weight in sorted(concepts, key=lambda x: -x[1]):
            if etype in placed:
                # Allow multiple trees, clouds, stars
                if etype not in ("tree", "cloud", "star", "building"):
                    continue

            if etype == "human":
                e = self._make_human(mood)
                if "human" not in placed:
                    elements.append(e); placed.add("human")
                    if self.rng.random() < 0.3 and env != "space":
                        e2 = self._make_human(mood)
                        e2["x"] = 0.65; elements.append(e2)
                else:
                    e["x"] = 0.65; elements.append(e)

            elif etype == "animal":
                e = self._make_animal(mood)
                elements.append(e); placed.add("animal")

            elif etype == "bird":
                e = self._make_bird(mood)
                elements.append(e); placed.add("bird")

            elif etype == "whale":
                if env in ("ocean", "underwater", "any"):
                    elements.append(self._make_whale(mood))
                    placed.add("whale")

            elif etype == "dolphin":
                if env in ("ocean", "underwater", "any"):
                    elements.append(self._make_fish())
                    placed.add("dolphin")

            elif etype == "walking_whale":
                elements.append({"type": "crocodile", "x": 0.5, "y": 0.65, "scale": 0.8,
                                  "fill": [80, 120, 70], "stroke": [50, 90, 40]})
                elements.append({"type": "water", "x": 0.05, "y": 0.7, "width": 0.9, "height": 0.15, "fill": [60, 120, 200]})
                placed.add("walking_whale"); placed.add("water")

            elif etype == "skeleton":
                elements.append(self._make_skeleton(mood))
                placed.add("skeleton")

            elif etype == "flipper":
                if env in ("ocean", "underwater", "any"):
                    elements.append(self._make_whale(mood))
                    placed.add("whale")

            elif etype in ("blowhole", "tail", "mammal"):
                if env in ("ocean", "underwater", "any"):
                    elements.append(self._make_whale(mood))
                    placed.add("whale")
                else:
                    elements.append({"type": "animal", "x": 0.5, "y": 0.62, "scale": 0.7, "fill": [80, 100, 120]})
                    placed.add("animal")

            elif etype == "evolution":
                elements.append({"type": "text", "x": 0.5, "y": 0.15, "text": "EVOLUTION",
                                  "font_size": 32, "fill": [200, 180, 60]})
                elements.append({"type": "arrow", "x": 0.3, "y": 0.5, "x2": 0.7, "y2": 0.5,
                                  "stroke": [200, 180, 60], "stroke_width": 3})
                placed.add("evolution"); placed.add("text")

            elif etype in ("prehistoric", "timeline"):
                elements.append({"type": "text", "x": 0.5, "y": 0.12, "text": etype.upper(),
                                  "font_size": 28, "fill": [160, 140, 100]})
                placed.add("text")

            elif etype == "fish":
                if env == "underwater" or env == "ocean":
                    elements.append(self._make_fish())
                    placed.add("fish")

            elif etype == "mountain":
                if env not in ("indoor", "underwater", "space"):
                    elements.append(self._make_landscape("mountain", mood))
                    placed.add("mountain")

            elif etype == "tree":
                e = self._make_tree(env)
                if "tree" not in placed:
                    elements.append(e); placed.add("tree")
                elif self.rng.random() < 0.5:
                    e["x"] = 0.85; e["y"] = 0.74; elements.append(e)

            elif etype == "hill":
                if env not in ("indoor", "underwater", "space", "ocean"):
                    elements.append(self._make_landscape("hill", mood))
                    placed.add("hill")

            elif etype == "water":
                if env not in ("space", "indoor"):
                    elements.append(self._make_water())
                    has_water = True
                    placed.add("water")

            elif etype == "cloud":
                if env not in ("indoor", "underwater", "space"):
                    elements.append(self._make_cloud())
                    placed.add("cloud")

            elif etype in ("sun", "moon", "star"):
                if env not in ("indoor", "underwater"):
                    elements.append(self._make_sky_object(etype, mood))
                    placed.add(etype)

            elif etype == "desert":
                if env == "desert":
                    elements.append({"type": "hill", "x": 0.3, "y": 0.7, "width": 0.4, "height": 0.08, "fill": [200, 180, 120]})
                    elements.append({"type": "hill", "x": 0.7, "y": 0.72, "width": 0.35, "height": 0.06, "fill": [190, 170, 110]})

            elif etype in ("building", "house"):
                e = self._make_building(etype, mood, env)
                elements.append(e); placed.add(etype)

            elif etype == "ship":
                if env in ("ocean", "any"):
                    elements.append(self._make_ship())
                    placed.add("ship")

            elif etype == "vehicle":
                e = self._make_vehicle(mood)
                elements.append(e); placed.add("vehicle")

            elif etype in ("cannon", "flag", "path", "throne", "chest", "book", "lamp",
                           "bell", "cross", "furniture", "food", "tool", "pottery"):
                e = self._make_object(etype, mood)
                if e:
                    elements.append(e)
                    placed.add(etype)

            elif etype == "glacier":
                if env in ("snow", "gradient", "ocean"):
                    elements.append({"type": "glacier", "x": 0.35, "y": 0.45, "scale": 0.6, "fill": [190, 210, 230]})
                    if self.rng.random() < 0.5:
                        elements.append({"type": "glacier", "x": 0.7, "y": 0.5, "scale": 0.5, "fill": [200, 215, 235]})
                    placed.add("glacier")

            elif etype == "iceberg":
                if env in ("snow", "ocean", "gradient"):
                    elements.append({"type": "iceberg", "x": 0.3, "y": 0.45, "scale": 0.5, "fill": [210, 225, 245]})
                    placed.add("iceberg")

            elif etype == "tundra":
                elements.append({"type": "hill", "x": 0.5, "y": 0.72, "width": 0.7, "height": 0.08, "fill": [160, 180, 190]})
                placed.add("tundra")

            elif etype == "antarctica":
                if has_fossil and "skeleton" not in placed:
                    elements.append({"type": "skeleton", "x": 0.5, "y": 0.72, "scale": 0.45, "fill": [200, 180, 150]})
                    placed.add("skeleton")
                if env == "snow" and "glacier" not in placed:
                    elements.append({"type": "glacier", "x": 0.5, "y": 0.45, "scale": 0.6, "fill": [190, 210, 230]})
                    placed.add("glacier")

        # Combined Antarctica-specific scenes
        if has_antarctica and env == "snow" and len(elements) < 3:
            if "glacier" not in placed and "mountain" in placed:
                elements.append({"type": "glacier", "x": 0.5, "y": 0.45, "scale": 0.6, "fill": [190, 210, 230]})
                placed.add("glacier")

        # Add text label
        if "text" in placed or any(c[0] in ("text", "label") for c in concepts):
            label_words = [c[0].upper() for c in concepts[:3]]
            if label_words:
                elements.append({
                    "type": "text", "x": 0.5, "y": 0.08,
                    "text": " ".join(label_words),
                    "font_size": 26, "fill": [255, 255, 240] if env == "night" else [60, 50, 40]
                })

        # x_mark for negative concepts
        if any(c[0] == "x_mark" for c in concepts):
            elements.append({"type": "x_mark", "x": 0.85, "y": 0.15, "scale": 0.7})

        return elements

    # ── Filler elements ──
    def _fill_elements(self, env: str, mood: str, count: int) -> list:
        fillers = []
        if env in ("gradient", "sunset", "farm"):
            fillers += [
                {"type": "tree", "x": 0.85, "y": 0.74, "scale": 0.6, "tree_style": "round", "fill": [50, 120, 50]},
                {"type": "hill", "x": 0.5, "y": 0.7, "width": 0.5, "height": 0.1, "fill": [60, 110, 50]},
                {"type": "cloud", "x": 0.3, "y": 0.18, "scale": 0.5},
            ]
        elif env in ("night", "space"):
            fillers += [
                {"type": "moon", "x": 0.7, "y": 0.2, "radius": 20},
                {"type": "star", "x": 0.2, "y": 0.15, "radius": 2, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.8, "y": 0.3, "radius": 1.5, "fill": [255, 255, 200]},
            ]
        elif env == "snow":
            fillers += [
                {"type": "glacier", "x": 0.3, "y": 0.45, "scale": 0.5, "fill": [200, 220, 240]},
                {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 0.6, "fill": [230, 235, 240]},
            ]

        elif env == "ocean":
            if self.rng.random() < 0.5:
                fillers += [
                    {"type": "whale", "x": self.rng.uniform(0.3, 0.6), "y": self.rng.uniform(0.45, 0.55),
                     "scale": self.rng.uniform(0.5, 0.8), "fill": [60, 70, 100]},
                ]
            else:
                fillers += [
                    {"type": "ship", "x": 0.5, "y": 0.55, "scale": 0.8, "fill": [80, 60, 40], "sail_color": [220, 210, 190]},
                ]
            fillers += [
                {"type": "cloud", "x": 0.3, "y": 0.15, "scale": 0.5},
            ]
        elif env == "forest":
            fillers += [
                {"type": "tree", "x": 0.3, "y": 0.7, "scale": 0.9, "tree_style": "pine", "fill": [30, 80, 30]},
                {"type": "tree", "x": 0.7, "y": 0.72, "scale": 0.8, "tree_style": "round", "fill": [40, 100, 40]},
            ]
        elif env == "indoor":
            fillers += [
                {"type": "human", "x": 0.5, "y": 0.55, "scale": 0.8, "fill": [80, 70, 60]},
                {"type": "rect", "x": 0.5, "y": 0.45, "width": 50, "height": 30, "fill": [160, 150, 130], "stroke": [100, 90, 80]},
            ]
        elif env == "city":
            fillers += [
                {"type": "building", "x": 0.5, "y": 0.6, "width": 0.1, "height": 0.3, "fill": [150, 140, 160], "window_color": [255, 220, 100]},
                {"type": "building", "x": 0.25, "y": 0.65, "width": 0.08, "height": 0.2, "fill": [140, 130, 150], "window_color": [255, 220, 100]},
            ]
        elif env == "desert":
            fillers += [
                {"type": "sun", "x": 0.5, "y": 0.25, "radius": 28, "fill": [255, 220, 80]},
                {"type": "hill", "x": 0.5, "y": 0.7, "width": 0.5, "height": 0.08, "fill": [200, 180, 120]},
            ]
        else:
            fillers += [
                {"type": "cloud", "x": 0.3, "y": 0.18, "scale": 0.5},
                {"type": "cloud", "x": 0.7, "y": 0.22, "scale": 0.4},
            ]

        while len(fillers) > 0 and count < 3:
            elements = fillers[:3 - count]
            count += len(elements)
            return elements
        return []

    # ═══════════════════════════════════════════════════════════════
    #  ELEMENT BUILDERS
    # ═══════════════════════════════════════════════════════════════

    def _make_human(self, mood: str) -> dict:
        colors = {
            "dramatic": [120, 50, 40], "somber": [60, 50, 50],
            "hopeful": [80, 120, 140], "epic": [140, 80, 60],
            "mysterious": [50, 40, 80], "peaceful": [80, 120, 90],
        }
        c = colors.get(mood, [80, 60, 120])
        x = self.rng.uniform(0.3, 0.5)
        return {"type": "human", "x": x, "y": 0.55, "scale": self.rng.uniform(0.7, 1.0), "fill": c}

    def _make_animal(self, mood: str) -> dict:
        x = self.rng.uniform(0.4, 0.7)
        colors = {"dramatic": [100, 60, 40], "somber": [60, 55, 50], "epic": [80, 60, 50],
                  "peaceful": [120, 100, 80], "hopeful": [90, 120, 100]}
        c = colors.get(mood, [100, 80, 60])
        return {"type": "animal", "x": x, "y": 0.62, "scale": self.rng.uniform(0.6, 0.9), "fill": c}

    def _make_bird(self, mood: str) -> dict:
        return {"type": "bird", "x": self.rng.uniform(0.3, 0.7), "y": self.rng.uniform(0.2, 0.35),
                "scale": self.rng.uniform(0.5, 0.8), "fill": [60, 50, 40]}

    def _make_whale(self, mood: str = "peaceful") -> dict:
        x = self.rng.uniform(0.3, 0.6)
        c = [60, 70, 100]
        if mood == "epic": c = [50, 60, 120]
        elif mood == "somber": c = [50, 55, 70]
        elif mood == "hopeful": c = [80, 110, 150]
        return {"type": "whale", "x": x, "y": self.rng.uniform(0.45, 0.55),
                "scale": self.rng.uniform(0.5, 0.9), "fill": c}

    def _make_skeleton(self, mood: str = "mysterious") -> dict:
        return {"type": "skeleton", "x": 0.5, "y": 0.55, "scale": 0.8,
                "fill": [220, 200, 180]}

    def _make_fish(self) -> dict:
        return {"type": "fish", "x": self.rng.uniform(0.3, 0.7), "y": self.rng.uniform(0.4, 0.6),
                "scale": self.rng.uniform(0.6, 1.0), "fill": [200, 180, 100]}

    def _make_landscape(self, etype: str, mood: str) -> dict:
        if etype == "mountain":
            snow = mood not in ("somber", "dramatic")
            return {"type": "mountain", "x": 0.5, "y": 0.65, "width": 0.5, "height": 0.3,
                    "fill": [100, 110, 140], "snow": snow}
        return {"type": "hill", "x": 0.3, "y": 0.7, "width": 0.4, "height": 0.12, "fill": [60, 120, 60]}

    def _make_tree(self, env: str) -> dict:
        style = "round"
        if env == "ocean": style = "palm"
        elif env in ("snow", "mountain"): style = "pine"
        elif env == "forest": style = self.rng.choice(["round", "pine"])
        return {"type": "tree", "x": 0.2, "y": 0.72, "scale": self.rng.uniform(0.6, 0.9),
                "tree_style": style, "fill": [40, 100, 40]}

    def _make_water(self) -> dict:
        return {"type": "water", "x": 0.05, "y": 0.6, "width": 0.9, "height": 0.15, "fill": [60, 120, 200]}

    def _make_cloud(self) -> dict:
        return {"type": "cloud", "x": self.rng.uniform(0.2, 0.8), "y": self.rng.uniform(0.12, 0.25),
                "scale": self.rng.uniform(0.4, 0.7)}

    def _make_sky_object(self, etype: str, mood: str) -> dict:
        if etype == "sun":
            c = [255, 220, 50] if mood != "somber" else [200, 180, 120]
            return {"type": "sun", "x": self.rng.uniform(0.4, 0.6), "y": self.rng.uniform(0.2, 0.35),
                    "radius": self.rng.randint(20, 30), "fill": c}
        elif etype == "moon":
            return {"type": "moon", "x": self.rng.uniform(0.6, 0.8), "y": self.rng.uniform(0.15, 0.25),
                    "radius": self.rng.randint(18, 24)}
        return {"type": "star", "x": self.rng.uniform(0.2, 0.8), "y": self.rng.uniform(0.1, 0.3),
                "radius": self.rng.uniform(1.5, 3), "fill": [255, 255, 200]}

    def _make_building(self, etype: str, mood: str, env: str) -> dict:
        if etype == "house":
            rx = self.rng.uniform(0.3, 0.6)
            return {"type": "house", "x": rx, "y": 0.7, "scale": self.rng.uniform(0.7, 1.0),
                    "fill": [180, 150, 120], "roof_color": [150, 50, 40]}
        elif env == "city":
            x = self.rng.uniform(0.25, 0.75)
            h = self.rng.uniform(0.15, 0.3)
            return {"type": "building", "x": x, "y": 0.65, "width": 0.1, "height": h,
                    "fill": [140, 130, 150], "window_color": [255, 220, 100]}
        elif env == "desert":
            return {"type": "building", "x": 0.5, "y": 0.6, "width": 0.12, "height": 0.3,
                    "fill": [200, 180, 140], "window_color": [255, 200, 100]}
        return {"type": "building", "x": 0.5, "y": 0.65, "width": 0.1, "height": 0.25,
                "fill": [120, 100, 80], "window_color": [255, 220, 100]}

    def _make_ship(self) -> dict:
        return {"type": "ship", "x": 0.5, "y": 0.55, "scale": self.rng.uniform(0.7, 1.0),
                "fill": [80, 60, 40], "sail_color": [220, 210, 190]}

    def _make_vehicle(self, mood: str) -> dict:
        return {"type": "rect", "x": 0.5, "y": 0.6, "width": 50, "height": 20,
                "fill": [100, 120, 140], "stroke": [60, 80, 100], "rx": 5}

    def _make_object(self, etype: str, mood: str) -> dict | None:
        mapping = {
            "cannon": {"type": "cannon", "x": 0.3, "y": 0.65, "scale": 0.8},
            "flag": {"type": "flag", "x": 0.7, "y": 0.5, "scale": 0.8, "fill": [200, 50, 50]},
            "path": {"type": "path", "x": 0.5, "y": 0.6, "x2": 0.5, "y2": 0.95, "width": 15},
            "throne": {"type": "rect", "x": 0.5, "y": 0.5, "width": 50, "height": 60,
                       "fill": [180, 150, 100], "stroke": [120, 100, 60], "rx": 3},
            "chest": {"type": "rect", "x": 0.5, "y": 0.55, "width": 40, "height": 30,
                      "fill": [120, 80, 40], "stroke": [80, 50, 30], "rx": 2},
            "book": {"type": "rect", "x": 0.5, "y": 0.5, "width": 30, "height": 40,
                     "fill": [200, 190, 170], "stroke": [100, 90, 80]},
            "lamp": {"type": "circle", "x": 0.5, "y": 0.4, "radius": 15,
                     "fill": [255, 200, 80], "stroke": [180, 130, 50]},
            "bell": {"type": "circle", "x": 0.5, "y": 0.4, "radius": 18,
                     "fill": [200, 180, 100], "stroke": [150, 130, 60]},
            "cross": {"type": "x_mark", "x": 0.5, "y": 0.5, "scale": 0.8},
            "furniture": {"type": "rect", "x": 0.5, "y": 0.55, "width": 50, "height": 25,
                          "fill": [160, 130, 100], "stroke": [100, 80, 60], "rx": 2},
            "food": {"type": "circle", "x": 0.5, "y": 0.5, "radius": 12,
                     "fill": [200, 150, 80], "stroke": [150, 100, 50]},
            "tool": {"type": "rect", "x": 0.5, "y": 0.5, "width": 30, "height": 10,
                     "fill": [120, 120, 120], "stroke": [80, 80, 80], "rx": 2},
            "pottery": {"type": "circle", "x": 0.5, "y": 0.5, "radius": 16,
                        "fill": [180, 140, 100], "stroke": [130, 90, 60]},
        }
        return mapping.get(etype)

    def _make_atmosphere(self, env: str, mood: str) -> dict:
        atmos = {"particles": "none", "fog": False}
        if env in ("night", "space"):
            atmos["particles"] = "stars"
            atmos["star_count"] = self.rng.randint(40, 80)
        if mood in ("mysterious", "somber"):
            atmos["fog"] = True
        return atmos

    # ── Scene titles ──
    def _scene_title(self, topic: str, idx: int, total: int, env: str) -> str:
        pools = {
            0: ["The Beginning", "Origins", "The Dawn", "First Light",
                "In the Beginning", "The Spark", "Before It All Began"],
            1: ["The Turning Point", "The Discovery", "The Breakthrough",
                "A New Era", "The Change", "Transformation", "The Shift"],
            2: ["The Impact", "How It Changed Us", "The Ripple Effect",
                "Consequences", "The Aftermath", "A New World"],
            3: ["The Legacy", "Today and Tomorrow", "The Final Chapter",
                "Remembering", "Ever After", "The Enduring Impact"],
        }
        pool = pools.get(min(idx, 3), pools[0])
        return self.rng.choice(pool)

    # ── Narration ──
    def _scene_narration(self, topic: str, idx: int, total: int, raw: str, env: str) -> str:
        pools = {
            0: [
                f"Long ago, the story of {raw} began.",
                f"Have you ever wondered about {raw}?",
                f"{raw.title()} — a story that shaped our world.",
                f"Before {raw} existed, the world was a very different place.",
                f"Imagine a world without {raw} — that was reality not long ago.",
                f"The story of {raw} is one of the most remarkable in history.",
            ],
            1: [
                f"Then everything changed with a single breakthrough.",
                f"The turning point came, and nothing was the same.",
                f"But how did this transformation happen?",
                f"Everything changed when a new discovery was made.",
                f"This was the moment that defined everything that followed.",
            ],
            2: [
                f"The impact was felt across the entire world.",
                f"This changed how people lived, worked, and thought.",
                f"From this moment forward, the world was different.",
                f"The consequences rippled through every aspect of society.",
                f"Nothing would ever be the same again.",
            ],
            3: [
                f"And that is the remarkable story of {raw}.",
                f"Today, we still feel the echoes of this story.",
                f"The legacy of {raw} lives on in ways we rarely notice.",
                f"So the next time you think of {raw}, remember this story.",
                f"And that is how {raw} changed the course of history.",
            ],
        }
        pool = pools.get(min(idx, 3), pools[0])
        return self.rng.choice(pool)
