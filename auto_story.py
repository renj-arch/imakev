"""Auto story — LLM-powered documentary video generator.
Uses sketch_generator.py for clean, full-color illustrations of any topic.
Each scene builds up progressively (stroke-by-stroke reveal animation)."""

import sys, os, re, time, random, json, math
if sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip,
    CompositeVideoClip,
)
import config
from src.text_to_speech import generate_tts_with_timestamps
from src.engagement import subscribe_end_card
from src.sketch_generator import SketchGenerator

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
rng = random.Random()


def _font(size=36):
    try: return ImageFont.truetype(config.get_font(), size)
    except: return ImageFont.load_default()


# ═══════════════════════════════════════════════════════════════
#  LLM SCRIPT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_script(topic: str) -> dict:
    """LLM generates a full documentary script with visual scene descriptions."""
    from src.script_generator import _generate

    system = """You are a documentary filmmaker and visual artist. You create rich, atmospheric visual stories like David Attenborough or Carl Sagan.
You output ONLY valid JSON. You describe every visual detail precisely. Your narration is immersive storytelling — never Q&A, never textbook facts."""

    prompt = f"""Create a documentary about: {topic}

Style: Immersive storytelling like a nature documentary. Rich, descriptive narration. Paint a picture with words. Never use question-and-answer format. Never list facts. Tell a story.

NARRATION STYLE REFERENCE (this is how your narration should read):
"Imagine standing in the African savanna millions of years ago. The land stretches endlessly. Trees dot the horizon. Herds of ancient animals wander through tall grass, all competing for the same thing: food."
"But high above the struggle, untouched leaves sway in the branches. A green buffet hanging just out of reach."
"Generation after generation, the process repeats. Not because nature planned it. Not because animals decided they wanted longer necks. But because individuals with small advantages were often better at surviving."
"Over millions of years, those tiny differences accumulated. A centimeter became several. Several became dozens."

For each scene, provide narration AND a full visual description that an illustration engine can render.

Output a JSON object with this structure:
{{
  "title": "documentary title",
  "scenes": [
    {{
      "scene_num": 1,
      "title": "scene title (like 'The Beginning')",
      "narration": "one to three compelling sentences, storytelling style, no Q&A",
      "mood": "peaceful|dramatic|hopeful|somber|epic|mysterious",
      "camera": null or "ken_burns_in|pan_right|pan_left|dolly_in",
      "visual": {{
        "bg": {{
          "type": "gradient|night|ocean|indoor|solid|sunset|forest",
          "colors": [[R,G,B], [R,G,B], ...],
          "horizon": 0.55 or null,
          "ground_color": [R,G,B] or null
        }},
        "elements": [
          {{
            "type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|ship|building|text|label|arrow|x_mark|line|circle|rect|cannon|flag|polygon|animal|bird|grass|flower",
            "x": 0.0-1.0,
            "y": 0.0-1.0,
            "scale": 0.5-2.0 or null,
            "fill": [R,G,B] or null,
            "stroke": [R,G,B] or null,
            "text": "text content" or null,
            "font_size": 14-60 or null,
            "width": 0.0-1.0 or null,
            "height": 0.0-1.0 or null,
            "radius": 0.0-1.0 or null,
            "tree_style": "round|pine|palm" or null,
            "snow": true|false or null,
            "sail_color": [R,G,B] or null,
            "window_color": [R,G,B] or null
          }}
        ],
        "atmosphere": {{
          "particles": "stars|rain|snow|none",
          "fog": true|false,
          "star_count": 0-60
        }}
      }}
    }}
  ]
}}

CREATIVE RULES:
- 6-12 scenes flowing like a documentary narrative
- First scene: atmospheric setup. Last scene: powerful, reflective conclusion.
- NARRATION: storytelling style — descriptive, atmospheric, 1-3 sentences per scene. Never Q&A. Never textbook.
- The "visual" describes what the audience SEES during this scene
- Choose background type and colors that match the mood and setting
- Place 3-8 elements per scene for a complete composition
- Use rich, harmonious colors (exact [R,G,B] values)
- Use "text" or "label" type for on-screen titles/labels only when needed
- Use "x_mark" for crossing out myths, "arrow" for pointing
- VARY scenes — don't repeat the same element types in every scene

Respond with ONLY the JSON object, no other text."""

    fallback = _fallback_script(topic)

    try:
        raw = _generate(prompt, temperature=0.9, max_tokens=1600, system=system)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        if "scenes" in data and len(data["scenes"]) >= 4:
            print(f"  LLM OK: {data['title']} ({len(data['scenes'])} scenes)")
            return data
    except Exception as e:
        print(f"  LLM script error: {e}")

    print("  Using fallback script")
    return fallback


# ── Entity-driven story scene engine ──
# Extracts ALL entities from narration text and generates elements for each.
# No LLM — comprehensive keyword-to-visual mapping + action-aware effects.

_ENTITY_MAP = {
    # People & figures
    "human":         {"type":"human","tags":["man","woman","child","person","people","figure","human","homosapien","hunter","gatherer","farmer","warrior","priest","king","queen","shaman","tribe","baby","infant","toddler","girl","boy","teen","teenager","adult","elder","elderly","couple","parent","mother","father","son","daughter","sibling","brother","sister","family","ancestor","descendant","generation","population","native","tribal","clan","leader","chief","ruler","emperor","pharaoh","president","soldier","guard","knight","peasant","noble","lord","lady","prince","princess","hero","villain","stranger","friend","enemy","ally","companion","follower","disciple","witness","observer","explorer","pioneer","settler","colonist","immigrant","refugee","nomad","traveler","wanderer","pilgrim","missionary","merchant","trader","craftsman","artist","musician","dancer","singer","poet","writer","scholar","teacher","student","scientist","doctor","nurse","patient","victim","survivor","captive","prisoner","slave","servant","master","apprentice","student","pupil"],"y":"ground","plural":"crowd"},
    "crowd":         {"type":"human","tags":["crowd","people","population","tribe","clan","family","civilization","culture","society","nation","public","group","gather"],"y":"ground","count":4},
    # Animals
    "bird":          {"type":"bird","tags":["bird","crow","raven","eagle","hawk","falcon","vulture","owl","sparrow","finch","pigeon","dove","swallow","swan","duck","goose","turkey","peacock","parrot","macaw","cockatoo","heron","crane","stork","flamingo","penguin","ostrich","robin","bluebird","cardinal","hummingbird","woodpecker","kingfisher","seagull","pelican","albatross","magpie","canary","chicken","hen","rooster","cock","chick","quail","pheasant","grouse","partridge","pigeon","dove","cuckoo","nightingale","lark","thrush","blackbird","starling","oriole","tanager","finch","sparrow","wren","tit","nuthatch","creeper","swift","martin","swallow","pipit","waxwing","shrike","vireo","warbler","bunting","grosbeak","towhee","junco","siskin","redpoll","crossbill","dickcissel","meadowlark","grackle","cowbird"],"y":"sky"},
    "dragonfly":     {"type":"dragonfly","tags":["dragonfly","damselfly"],"y":"sky","special":1},
    "butterfly":     {"type":"butterfly","tags":["butterfly","moth"],"y":"sky"},
    "mammal":        {"type":"animal","tags":["mammal","deer","wolf","fox","bear","rabbit","squirrel","horse","cattle","cow","bull","calf","ox","sheep","lamb","goat","pig","hog","boar","bison","moose","elk","donkey","mule","llama","alpaca","camel","zebra","giraffe","rhino","rhinoceros","hippo","hippopotamus","elephant","lion","tiger","leopard","panther","jaguar","cheetah","hyena","dog","cat","kitten","puppy","mouse","rat","beaver","otter","hedgehog","bat","kangaroo","koala","sloth","raccoon","skunk","weasel","badger","mole","vole","shrew","opossum","porcupine","armadillo","anteater","monkey","ape","gorilla","chimpanzee","orangutan","gibbon","baboon","mandrill","lemur","panda","bamboo"],"y":"ground"},
    "dinosaur":      {"type":"animal","tags":["dinosaur","t-rex","triceratops","velociraptor","stegosaurus","brontosaurus","pterosaur","plesiosaur","ichthyosaur","ankylosaurus","parasaurolophus","pachycephalosaurus","allosaurus","brachiosaurus","diplodocus","creature","beast","monster"],"y":"ground","scale":1.5},
    "fish":          {"type":"fish","tags":["fish","shark","whale","dolphin","orca","porpoise","seal","walrus","salmon","trout","tuna","bass","perch","carp","catfish","cod","herring","sardine","mackerel","anchovy","eel","ray","skate","flounder","halibut","swordfish","marlin","grouper","snapper","tilapia","aquatic","sea creature","marine"],"y":"water"},
    "reptile":       {"type":"animal","tags":["reptile","lizard","gecko","iguana","chameleon","monitor","komodo","turtle","tortoise","terrapin","crocodile","alligator","caiman","gavial"],"y":"ground"},
    "amphibian":     {"type":"animal","tags":["amphibian","frog","toad","salamander","newt","axolotl","caecilian"],"y":"ground"},
    "insect":        {"type":"animal","tags":["insect","bug","beetle","ant","bee","wasp","hornet","fly","mosquito","dragonfly","damselfly","butterfly","moth","caterpillar","larva","pupa","cocoon","grasshopper","cricket","locust","cicada","flea","louse","termite","cockroach","mantis","praying mantis","stick insect","leaf insect","aphid","scale insect","lacewing","stonefly","mayfly","caddisfly","silverfish","firefly","lightning bug","ladybug","ladybird","centipede","millipede"],"y":"ground"},
    "crustacean":    {"type":"animal","tags":["crustacean","crab","lobster","shrimp","prawn","crayfish","krill","barnacle","copepod","isopod","amphipod"],"y":"water"},
    "mollusk":       {"type":"animal","tags":["mollusk","snail","slug","clam","oyster","mussel","scallop","cuttlefish","squid","octopus","nautilus","conch","cowrie","abalone","limpet","chiton"],"y":"water"},
    "snake":         {"type":"line","tags":["snake","serpent","viper","python","cobra","boa","anaconda","rattlesnake","adder","mamba","taipan"],"y":"ground"},
    "spider":        {"type":"spider","tags":["spider","tarantula","scorpion","tick","mite"],"y":"ground"},
    # Nature - plants
    "tree":          {"type":"tree","tags":["tree","oak","pine","spruce","birch","willow","maple","sequoia","redwood","palm","forest","woods","jungle"],"y":"ground"},
    "fern":          {"type":"fern","tags":["fern","foliage","leave","leaf","bush","shrub","bramble","thicket","undergrowth","vegetation","plant","grow"],"y":"ground"},
    "flower":        {"type":"flower","tags":["flower","bloom","blossom","rose","daisy","tulip","lily","sunflower","lavender","meadow"],"y":"ground"},
    "mushroom":      {"type":"mushroom","tags":["mushroom","fungus","toadstool","mold","spore"],"y":"ground"},
    "grass":         {"type":"grass","tags":["grass","field","prairie","savanna","plain"],"y":"ground"},
    # Landscape
    "mountain":      {"type":"mountain","tags":["mountain","hill","peak","summit","cliff","ridge","slope","alpine","highland"],"y":"horizon"},
    "water":         {"type":"water","tags":["water","river","lake","ocean","sea","pond","stream","creek","waterfall","wave","marine","aquatic"],"y":"water"},
    "cave":          {"type":"cave","tags":["cave","cavern","grotto","underground","subterranean"],"y":"ground"},
    "ice":           {"type":"snow","tags":["ice","snow","glacier","frozen","frost","icicle","arctic","tundra"],"y":"ground","color":[200,220,240]},
    "fire":          {"type":"fire","tags":["fire","flame","blaze","campfire","bonfire","burn","burning","ember","spark","volcano","lava","eruption"],"y":"ground"},
    "rock":          {"type":"rock","tags":["rock","stone","boulder","pebble","gravel","canyon","desert","arid","sand","dune"],"y":"ground"},
    # Sky & celestial
    "sun":           {"type":"sun","tags":["sun","sunlight","sunshine","sunrise","sunset","dawn","dusk","morning","day","daylight","solstice"],"y":"sky"},
    "moon":          {"type":"moon","tags":["moon","crescent","lunar","full moon","half moon","night"],"y":"sky"},
    "star":          {"type":"star","tags":["star","stars","night sky","constellation","galaxy","universe","celestial","astronomy"],"y":"sky","count":8,"small":1},
    "cloud":         {"type":"cloud","tags":["cloud","clouds","sky","atmosphere","weather","overcast","fog","mist","haze","smoke"],"y":"sky"},
    "comet":         {"type":"comet","tags":["comet","meteor","shooting star","asteroid","tail","streak","fiery","glowing"],"y":"sky","special":1},
    "lightning":     {"type":"lightning","tags":["lightning","thunder","storm","bolt","electrical"],"y":"sky"},
    "rainbow":       {"type":"rainbow","tags":["rainbow","arc","prism"],"y":"sky"},
    # Structures
    "building":      {"type":"building","tags":["house","hut","cabin","building","structure","temple","pyramid","monument","palace","castle","fort","wall","city","village","town","settlement","civilization"],"y":"ground"},
    "tent":          {"type":"tent","tags":["tent","camp","campsite","shelter","teepee","nomad"],"y":"ground"},
    "bridge":        {"type":"bridge","tags":["bridge","crossing","causeway","overpass"],"y":"ground"},
    "path":          {"type":"path","tags":["path","trail","road","track","route","way","walkway","walk","walking","street"],"y":"ground"},
    # Objects
    "boat":          {"type":"ship","tags":["boat","ship","sail","vessel","canoe","raft","ark","voyage","explore","navigation"],"y":"water"},
    "book":          {"type":"book","tags":["book","scroll","manuscript","document","papyrus","knowledge","story","tale","record"],"y":"ground"},
    "compass":       {"type":"compass","tags":["compass","astrolabe","sextant","navigation","direction"],"y":"ground"},
    "globe":         {"type":"globe","tags":["globe","earth","world","planet","sphere","orb"],"y":"ground"},
    "crystal":       {"type":"crystal","tags":["crystal","gem","jewel","diamond","ruby","emerald","mineral"],"y":"ground"},
    "tool":          {"type":"tool","tags":["tool","axe","hammer","spear","knife","sword","bow","arrow","weapon","instrument","artifact"],"y":"ground"},
    "pottery":       {"type":"pottery","tags":["pot","pottery","vase","jar","bowl","urn","amphora","container"],"y":"ground"},
    "throne":        {"type":"throne","tags":["throne","seat","chair","bench","stool"],"y":"ground"},
    "altar":         {"type":"altar","tags":["altar","shrine","sacrifice","offering","ritual"],"y":"ground"},
    "torch":         {"type":"torch","tags":["torch","lantern","lamp","candle","light","illuminate","glow"],"y":"ground"},
    # Abstract - silence, shadow, sound, time
    "shadow":        {"type":"shadow","tags":["shadow","darkness","shade","gloom","eclipse","dark","darken"],"y":"sky","special":1},
    "sound":         {"type":"sound_wave","tags":["sound","hear","buzzing","noise","roar","cry","whisper","echo","silence","quiet","loud"],"y":"air","special":1},
    "wind":          {"type":"wind","tags":["wind","breeze","gust","air","atmosphere","breathe","breath","warm","heavy","humid"],"y":"air"},
    # Emotional / narrative scene types
    "warning":       {"type":"warning","tags":["warning","omen","bad omen","portend","fear","terrify","afraid","scared","feared","danger","threat"],"y":"sky","special":1},
    "question":      {"type":"question","tags":["nobody knows","no one knows","don't know","unknown","mystery","mysterious","strange","why","wonder","curious","puzzl","confus"],"y":"air","special":1},
    "predictable":   {"type":"predictable","tags":["predictable","familiar","exactly where","yesterday","same","always","routine","ordinary","normal","expected"],"y":"sky","special":1},
    "alien":         {"type":"alien","tags":["feels alien","strange","unfamiliar","foreign","otherworldly","different","bizarre","weird","surreal"],"y":"ground","special":1},
    "silence":       {"type":"silence","tags":["silence","silent","no birds","no mammals","no humans","no dinosaur","no sound","nothing","empty","alone","nobody","disappear","vanish"],"y":"ground","special":1},
    # Vehicles
    "motorcycle":   {"type":"motorcycle","tags":["motorcycle","motorbike","bike","harley","scooter","honda"],"y":"ground"},
    "car":          {"type":"car","tags":["car","automobile","vehicle","truck","lorry","van","jeep","sedan","wagon","bus","taxi"],"y":"ground"},
    "train":        {"type":"train","tags":["train","railway","locomotive","railroad","subway","metro","rail"],"y":"ground"},
    "plane":        {"type":"plane","tags":["plane","airplane","aircraft","jet","airliner","fighter","aviation","flight"],"y":"sky"},
    "bicycle":      {"type":"bicycle","tags":["bicycle","bike","cycle","cyclist","pedal","mountain bike"],"y":"ground"},
    "chariot":      {"type":"chariot","tags":["chariot","carriage","wagon","cart","stagecoach"],"y":"ground"},
    # Technology
    "robot":        {"type":"robot","tags":["robot","android","automaton","machine","mechanical","cyborg","droid","artificial"],"y":"ground","special":1},
    "computer":     {"type":"computer","tags":["computer","laptop","desktop","pc","mac","device","digital","electronic","screen","monitor","display","keyboard","tech"],"y":"ground"},
    "phone":        {"type":"phone","tags":["phone","cellphone","smartphone","iphone","telephone","mobile","call"],"y":"ground"},
    "satellite":    {"type":"satellite","tags":["satellite","spacecraft","orbiter","probe","space station","gps"],"y":"sky"},
    "camera":       {"type":"camera","tags":["camera","photograph","photography","photo","video","lens","filming","record"],"y":"ground"},
    "telescope":    {"type":"telescope","tags":["telescope","astronomy","stargaze","observatory","lens","magnify"],"y":"ground"},
    # More nature
    "volcano":      {"type":"volcano","tags":["volcano","lava","eruption","magma","volcanic","ash"],"y":"ground"},
    "tornado":      {"type":"tornado","tags":["tornado","cyclone","hurricane","typhoon","twister","whirlwind","storm"],"y":"air","special":1},
    "waterfall":    {"type":"waterfall","tags":["waterfall","cascade","falls","rapids"],"y":"ground"},
    "geyser":       {"type":"geyser","tags":["geyser","hot spring","thermal","steam","spout","erupt"],"y":"ground"},
    "aurora":       {"type":"aurora","tags":["aurora","northern lights","southern lights","polar","borealis"],"y":"sky","special":1},
    # Fantasy & mythical
    "dragon":       {"type":"dragon","tags":["dragon","wyvern","draconic","serpent","mythical","legendary","fire-breathing"],"y":"sky","special":1},
    "unicorn":      {"type":"unicorn","tags":["unicorn","mythical","magical","horse","white"],"y":"ground"},
    "ghost":        {"type":"ghost","tags":["ghost","spirit","phantom","specter","apparition","soul","poltergeist"],"y":"air","special":1},
    "angel":        {"type":"angel","tags":["angel","divine","heavenly","seraph","cherub","guardian","holy"],"y":"sky"},
    "demon":        {"type":"demon","tags":["demon","devil","satan","evil","fiend","hell","infernal"],"y":"ground","special":1},
    "wizard":       {"type":"wizard","tags":["wizard","witch","mage","sorcerer","magician","druid","warlock","enchanter","conjure"],"y":"ground","special":1},
    "fairy":        {"type":"fairy","tags":["fairy","faerie","sprite","pixie","nymph","fae","pixie"],"y":"sky"},
    "elf":          {"type":"elf","tags":["elf","elves","elven","pointed ear"],"y":"ground"},
    "dwarf":        {"type":"dwarf","tags":["dwarf","dwarven","dwarves","underground","forge"],"y":"ground"},
    "troll":        {"type":"troll","tags":["troll","ogre","giant","monster","brute"],"y":"ground"},
    "zombie":       {"type":"zombie","tags":["zombie","undead","walking dead","corpse","decay"],"y":"ground"},
    # Music & art
    "guitar":       {"type":"guitar","tags":["guitar","instrument","music","song","melody","tune","lute","harp","banjo","violin","string"],"y":"ground"},
    "microphone":   {"type":"microphone","tags":["microphone","mic","sing","speak","announce","broadcast","voice"],"y":"ground"},
    "drum":         {"type":"drum","tags":["drum","drumming","percussion","beat","rhythm","tambourine"],"y":"ground"},
    # Food & drink
    "fruit":        {"type":"fruit","tags":["fruit","apple","orange","berry","grape","banana","harvest","ripe"],"y":"ground"},
    "bread":        {"type":"bread","tags":["bread","loaf","bake","baked","meal","food","grain","wheat","flour"],"y":"ground"},
    "cup":          {"type":"cup","tags":["cup","goblet","chalice","mug","glass","drink","wine","ale","beer","bottle","flask"],"y":"ground"},
    # Objects
    "bell":         {"type":"bell","tags":["bell","chime","ring","toll","cathedral"],"y":"ground"},
    "mirror":       {"type":"mirror","tags":["mirror","reflection","reflect","glass","looking glass"],"y":"ground"},
    "mask":         {"type":"mask","tags":["mask","disguise","costume","veil","face","theater"],"y":"ground"},
    # Military
    "tank":         {"type":"tank","tags":["tank","armored","armored vehicle","military vehicle","war machine","battalion"],"y":"ground"},
    "explosion":    {"type":"explosion","tags":["explosion","explode","blast","boom","detonate","burst","bomb","missile","grenade","shell"],"y":"air","special":1},
    # Sci-fi
    "ufo":          {"type":"ufo","tags":["ufo","unidentified","flying saucer","spaceship","extraterrestrial","alien ship","craft"],"y":"sky","special":1},
    "alien_creature":{"type":"alien_creature","tags":["alien being","extraterrestrial","little green","grey alien","space alien","martian","venusian","alien craft"],"y":"ground","special":1},
    # Abstract concepts
    "atom":          {"type":"atom","tags":["atom","molecule","nucleus","electron","proton","neutron","particle","microscopic","atomic"],"y":"air"},
    "dna":           {"type":"dna","tags":["dna","gene","genetic","chromosome","helix","heredity","double helix"],"y":"air"},
    "heart":         {"type":"heart","tags":["heart","cardiac","blood","pump","valentine","love","passion"],"y":"ground"},
    "infinity":      {"type":"infinity","tags":["infinity","endless","forever","eternal","infinite","boundless","limitless"],"y":"air"},
    "target":        {"type":"target","tags":["target","aim","goal","bullseye","focus","concentrate"],"y":"ground"},
    "puzzle":        {"type":"puzzle","tags":["puzzle","mystery","enigma","problem","challenge","riddle","conundrum"],"y":"ground"},
    "scales":        {"type":"scales","tags":["scales","balance","justice","weigh","measure","equal","fair","equality"],"y":"ground"},
    # Sci-fi
    "astronaut":     {"type":"astronaut","tags":["astronaut","spaceman","cosmonaut","space traveler","space suit"],"y":"ground"},
    "spaceship":     {"type":"spaceship","tags":["spaceship","starship","spacecraft","rocket","ship","space travel"],"y":"sky"},
    # Objects
    "hourglass":     {"type":"hourglass","tags":["hourglass","sand","timer","time","countdown"],"y":"ground"},
    "treasure_chest":{"type":"treasure_chest","tags":["treasure chest","treasure","chest","gold","loot","booty","fortune","riches","wealth"],"y":"ground"},
    "gravestone":    {"type":"gravestone","tags":["grave","gravestone","tombstone","tomb","burial","cemetery","death","dead","mortality"],"y":"ground"},
    # Clothing
    "hat":           {"type":"hat","tags":["hat","cap","crown","helmet","headwear","bonnet","hood","beret","fedora","top hat","cowboy hat","sombrero","headband","visor"],"y":"ground"},
    "clothing":      {"type":"clothing","tags":["clothing","clothes","garment","apparel","attire","robe","cloak","cape","coat","jacket","vest","suit","dress","gown","shirt","pants","trousers","jeans","shorts","skirt","uniform","armor","chainmail","leather","fabric","textile","wool","silk","linen","cotton"],"y":"ground"},
    "shoe":          {"type":"shoe","tags":["shoe","shoes","boot","boots","sandal","slipper","sneaker","footwear","sole","leather"],"y":"ground"},
    "jewelry":       {"type":"jewelry","tags":["jewelry","necklace","bracelet","ring","earring","brooch","pendant","amulet","charm","gem","diamond","ruby","emerald","sapphire","pearl","gold","silver","ornament","adornment"],"y":"ground"},
    # Furniture
    "furniture":     {"type":"furniture","tags":["furniture","table","chair","desk","bench","stool","cabinet","chest","drawer","shelf","bed","couch","sofa","seat","throne","cradle","crib","hammock","wardrobe","dresser","nightstand","coffee table"],"y":"ground"},
    # Kitchen
    "kitchen":       {"type":"kitchen","tags":["kitchen","pot","pan","skillet","kettle","pitcher","jug","bottle","flask","bowl","plate","dish","cup","mug","glass","goblet","chalice","utensil","fork","spoon","knife","spatula","ladle","strainer","colander","grater","peeler","whisk","rolling pin","cutting board","knife","cleaver","cooking","baking","roast","stew","soup","stove","oven","fireplace","hearth"],"y":"ground"},
}

_ACTION_MAP = {
    "walk":   {"tags":["walk","walking","step","pace","stride","march","wandered","travel"],"effect":"walk_pose","camera":"track"},
    "run":    {"tags":["run","running","flee","chase","sprint","rush","dash"],"effect":"run_pose","camera":"pan_right"},
    "fly":    {"tags":["fly","flying","soar","glide","hover","flutters"],"effect":"in_air"},
    "rise":   {"tags":["rise","rises","rising","ascend","climb","grow","tower","towering"],"effect":"low_angle","camera":"dolly_in"},
    "fall":   {"tags":["fall","falling","descend","drop","collapse","crumble"],"effect":"fall_pose","camera":"dolly_out"},
    "gather":  {"tags":["gather","gathered","crowd","meet","assemble","collect","coming together"],"effect":"group"},
    "appear": {"tags":["appear","appears","appeared","appearing","emerge","arise","show","reveal","suddenly","appear"],"effect":"fade_in"},
    "disappear":{"tags":["disappear","vanish","fade","gone","hidden","hide","conceal","obscure"],"effect":"fade_out"},
    "watch":  {"tags":["watch","watching","look","looking","gaze","stare","observe","study","examine"],"effect":"watching_pose","camera":"ken_burns_in"},
    "point":  {"tags":["point","pointing","indicate","gesture","signal","show","direction","direct"],"effect":"pointing_pose"},
}

_POSITION_ZONES = {
    "sky":     {"y_range": (0.06, 0.30), "size": 0.7},
    "air":     {"y_range": (0.12, 0.40), "size": 0.8},
    "horizon": {"y_range": (0.50, 0.62), "size": 1.0},
    "ground":  {"y_range": (0.52, 0.75), "size": 1.0},
    "water":   {"y_range": (0.68, 0.82), "size": 0.9},
}

def _extract_entities(text):
    """Extract ALL known entities from narration text, with multiplicities."""
    t = text.lower()
    found = {}
    for key, info in _ENTITY_MAP.items():
        for tag in info["tags"]:
            if re.search(rf'\b{re.escape(tag)}\b', t):
                count = info.get("count", 1)
                if any(w in t for w in ["all","many","every","dozen","hundred","thousand","million","billion","countless","numerous","several"]):
                    count = max(count, info.get("count", 1) * 2)
                if key in ("crowd","people","population","tribe","clan","family","civilization","culture","society","nation","public","group"):
                    count = max(count, 4)
                found[key] = {"info": info, "count": count}
                break
    return found

def _detect_actions(text):
    """Detect actions from narration text."""
    t = text.lower()
    actions = []
    for key, info in _ACTION_MAP.items():
        for tag in info["tags"]:
            if tag in t:
                actions.append({**info, "name": key})
                break
    return actions

def _elem(entity_type, x, y, extra=None):
    """Create a base element dict."""
    e = {"type": entity_type, "x": x, "y": y}
    if extra:
        e.update(extra)
    return e

def _gen_entity_elements(key, info, count, rng, text):
    """Generate element(s) for one entity."""
    etype = info["type"]
    col = info.get("color")
    special = info.get("special", 0)
    elems = []
    y_range = _POSITION_ZONES.get(info.get("y","ground"), _POSITION_ZONES["ground"])["y_range"]
    sz = _POSITION_ZONES.get(info.get("y","ground"), _POSITION_ZONES["ground"])["size"]

    if special == 1:
        return None

    sc = sz
    if any(w in text for w in ["giant","huge","massive","enormous","gigantic","towering","immense","colossal"]):
        sc *= 1.8
    elif any(w in text for w in ["tiny","small","little","miniature","distant"]):
        sc *= 0.5

    for i in range(count):
        if count > 1:
            x = round(rng.uniform(0.08 + i*0.12, 0.15 + i*0.2), 2)
        else:
            x = round(rng.uniform(0.25, 0.75), 2)
        y = round(rng.uniform(y_range[0], y_range[1]), 2)
        c = col or [rng.randint(80,230) for _ in range(3)]

        if etype == "human":
            skin = [220+rng.randint(-20,20), 185+rng.randint(-15,15), 155+rng.randint(-15,15)]
            elems.append({"type":"human","x":x,"y":y,"scale":round(sc*(0.6+rng.random()*0.2),1),
                         "fill":[120+rng.randint(-20,40),90+rng.randint(-20,30),70+rng.randint(-20,20)],
                         "skin_color":skin})
        elif etype == "bird":
            elems.append({"type":"bird","x":x,"y":y-0.05,"scale":round(sc*0.6,1),"fill":c})
        elif etype == "tree":
            side = 0.12 if i < count//2 else 0.85
            elems.append({"type":"tree","x":side if count > 1 else x,"y":y,"scale":round(sc*(0.8+rng.random()*0.4),1),"fill":[40+rng.randint(0,60),110+rng.randint(0,40),40+rng.randint(0,30)]})
        elif etype == "mountain":
            elems.append({"type":"mountain","x":x,"y":0.68,"scale":round(0.8+sc*0.3,1),"fill":c})
        elif etype == "water":
            elems.append({"type":"water","x":0.5,"y":0.75,"scale":1.2,"fill":c})
        elif etype == "sun":
            elems.append({"type":"sun","x":x,"y":0.18,"scale":1.0,"fill":[255,220,50]})
        elif etype == "moon":
            elems.append({"type":"moon","x":x+0.12,"y":y,"scale":0.9})
        elif etype == "star":
            elems.append({"type":"star","x":x,"y":y,"radius":rng.randint(1,2),"fill":[255,255,210,200+rng.randint(0,55)]})
        elif etype == "cloud":
            elems.append({"type":"cloud","x":x,"y":round(rng.uniform(0.08,0.18),2),"scale":round(sc*(0.7+rng.random()*0.4),1),"fill":[200+rng.randint(0,30),210+rng.randint(0,20),220+rng.randint(0,15)]})
        elif etype == "fire":
            elems.append({"type":"fire","x":x,"y":0.62,"scale":round(sc*0.8,1),"fill":[255,150+rng.randint(0,60),30+rng.randint(0,30)]})
        elif etype == "building":
            elems.append({"type":"building","x":x,"y":round(rng.uniform(0.50,0.58),2),"scale":round(sc*0.8,1),"fill":[150+rng.randint(0,40),130+rng.randint(0,30),90+rng.randint(0,30)]})
        elif etype == "ship":
            elems.append({"type":"ship","x":x,"y":0.55,"scale":round(sc*0.8,1),"fill":[110,75,45]})
        elif etype == "animal":
            elems.append({"type":"animal","x":x,"y":y,"scale":round(sc*0.8,1),"fill":c})
        elif etype == "flower":
            elems.append({"type":"flower","x":x,"y":round(rng.uniform(0.60,0.75),2),"scale":round(sc*0.5,1),"fill":[200+rng.randint(0,55),60+rng.randint(0,60),140+rng.randint(0,60)]})
        elif etype == "cave":
            elems.append({"type":"cave","x":0.5,"y":0.5,"scale":1.1,"fill":[75,55,45]})
        elif etype == "book":
            elems.append({"type":"book","x":x,"y":0.58,"scale":0.7,"fill":[170,130,75]})
        elif etype == "compass":
            elems.append({"type":"compass","x":x,"y":y,"scale":0.7,"fill":[170,130,75]})
        elif etype == "globe":
            elems.append({"type":"globe","x":x,"y":y,"scale":0.8,"fill":[50+rng.randint(0,30),110+rng.randint(0,30),170+rng.randint(0,30)]})
        elif etype in ("fern","grass"):
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(40*sc),"height":int(15*sc),"fill":c,"opacity":160})
        elif etype == "ice":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(80*sc),"height":int(20*sc),"fill":[200,220,240,150]})
        elif etype == "rock":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(50*sc),"height":int(25*sc),"fill":[140,130,120,180]})
        elif etype == "crystal":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(20*sc),"height":int(30*sc),"fill":[180,200,230,180],"stroke":[150,170,210],"stroke_width":1})
        elif etype == "mushroom":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(20*sc),"height":int(12*sc),"fill":[200,180,160,200],"stroke":[180,160,140],"stroke_width":1})
            elems.append({"type":"rect","x":x,"y":y+0.015,"width":4,"height":int(12*sc),"fill":[180,160,140,180]})
        elif etype == "tool":
            elems.append({"type":"line","x":x-0.03,"y":y+0.02,"x2":x+0.03,"y2":y-0.02,"stroke":[140,120,100,200],"stroke_width":3})
            elems.append({"type":"ellipse","x":x+0.03,"y":y-0.025,"width":8,"height":6,"fill":[160,140,120,200]})
        elif etype == "tent":
            hh = int(40*sc)
            ww = int(30*sc)
            elems.append({"type":"polygon","points":[[x-ww/200,y+hh/100],[x,y-hh/100],[x+ww/200,y+hh/100]],"fill":[180+rng.randint(0,30),160+rng.randint(0,20),130+rng.randint(0,20),200]})
        elif etype == "torch":
            elems.append({"type":"line","x":x,"y":y+0.03,"x2":x,"y2":y,"stroke":[120,80,40,200],"stroke_width":3})
            elems.append({"type":"ellipse","x":x,"y":y-0.02,"width":6,"height":8,"fill":[255,200,50,200]})
        elif etype == "pottery":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(25*sc),"height":int(20*sc),"fill":[180+rng.randint(0,20),150+rng.randint(0,20),110+rng.randint(0,20),200]})
        elif etype == "bridge":
            elems.append({"type":"arc","x":x,"y":y,"radius":int(30*sc),"start_angle":0,"end_angle":180,"stroke":[120,100,80,200],"stroke_width":4})
        elif etype == "path":
            elems.append({"type":"line","x":x-0.08,"y":1.0,"x2":x-0.02,"y2":0.58,"stroke":[110,95,75,50],"stroke_width":4})
            elems.append({"type":"line","x":x+0.08,"y":1.0,"x2":x+0.02,"y2":0.58,"stroke":[110,95,75,50],"stroke_width":4})
        elif etype == "motorcycle":
            elems.append({"type":"circle","x":x-0.04,"y":y+0.03,"radius":int(10*sc),"fill":[40,40,45],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.04,"y":y+0.03,"radius":int(10*sc),"fill":[40,40,45],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"rect","x":x,"y":y-0.02,"width":int(40*sc),"height":int(12*sc),"fill":[180,50,50,200],"rx":2})
            elems.append({"type":"rect","x":x-0.02,"y":y-0.04,"width":int(15*sc),"height":int(8*sc),"fill":[60,60,65,200],"rx":1})
            elems.append({"type":"line","x":x-0.04,"y":y-0.04,"x2":x-0.04,"y2":y-0.08,"stroke":[60,60,65,200],"stroke_width":2})
            elems.append({"type":"line","x":x,"y":y-0.04,"x2":x+0.01,"y2":y-0.09,"stroke":[60,60,65,200],"stroke_width":2})
            elems.append({"type":"circle","x":x+0.01,"y":y-0.09,"radius":3,"fill":[200,200,190,220]})
        elif etype == "car":
            elems.append({"type":"circle","x":x-0.06,"y":y+0.03,"radius":int(10*sc),"fill":[30,30,35],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.06,"y":y+0.03,"radius":int(10*sc),"fill":[30,30,35],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"rect","x":x,"y":y-0.02,"width":int(55*sc),"height":int(18*sc),"fill":c,"rx":3})
            elems.append({"type":"rect","x":x+0.01,"y":y-0.035,"width":int(25*sc),"height":int(10*sc),"fill":[180,210,240,200],"rx":2})
            elems.append({"type":"rect","x":x-0.04,"y":y-0.035,"width":int(12*sc),"height":int(10*sc),"fill":[180,210,240,200],"rx":2})
        elif etype == "train":
            elems.append({"type":"rect","x":x,"y":y-0.02,"width":int(60*sc),"height":int(20*sc),"fill":c,"rx":2})
            elems.append({"type":"rect","x":x+0.02,"y":y-0.04,"width":int(8*sc),"height":int(14*sc),"fill":[200,210,230,220],"rx":1})
            elems.append({"type":"rect","x":x+0.01,"y":y-0.04,"width":int(8*sc),"height":int(14*sc),"fill":[200,210,230,220],"rx":1})
            for wx in [-0.05,-0.03,-0.01,0.01,0.03]:
                elems.append({"type":"rect","x":x+wx,"y":y-0.04,"width":int(6*sc),"height":int(14*sc),"fill":[240,240,230,200],"rx":1})
            for i in range(3):
                elems.append({"type":"circle","x":x-0.04+i*0.04,"y":y+0.03,"radius":int(6*sc),"fill":[40,40,45],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"rect","x":x+0.035,"y":y-0.02,"width":int(6*sc),"height":int(8*sc),"fill":[255,220,80,200],"rx":1})
        elif etype == "plane":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(70*sc),"height":int(16*sc),"fill":[200,210,230,220],"stroke":[140,160,190,180],"stroke_width":1})
            elems.append({"type":"polygon","points":[[x-0.02,y-0.08],[x-0.02,y+0.08],[x+0.06,y+0.03],[x+0.06,y-0.03]],"fill":[180,190,210,200]})
            elems.append({"type":"polygon","points":[[x+0.04,y-0.02],[x+0.05,y-0.10],[x+0.08,y-0.02]],"fill":[180,190,210,200]})
            elems.append({"type":"polygon","points":[[x+0.04,y+0.02],[x+0.05,y+0.10],[x+0.08,y+0.02]],"fill":[180,190,210,200]})
            elems.append({"type":"polygon","points":[[x-0.055,y-0.015],[x-0.065,y-0.06],[x-0.04,y-0.01]],"fill":[180,190,210,200]})
            elems.append({"type":"polygon","points":[[x-0.055,y+0.015],[x-0.065,y+0.06],[x-0.04,y+0.01]],"fill":[180,190,210,200]})
        elif etype == "bicycle":
            elems.append({"type":"circle","x":x-0.04,"y":y+0.02,"radius":int(10*sc),"fill":"none","stroke":[60,60,65,200],"stroke_width":2})
            elems.append({"type":"circle","x":x+0.04,"y":y+0.02,"radius":int(10*sc),"fill":"none","stroke":[60,60,65,200],"stroke_width":2})
            elems.append({"type":"line","x":x-0.04,"y":y+0.02,"x2":x,"y2":y-0.05,"stroke":[60,60,65,180],"stroke_width":2})
            elems.append({"type":"line","x":x+0.04,"y":y+0.02,"x2":x,"y2":y-0.05,"stroke":[60,60,65,180],"stroke_width":2})
            elems.append({"type":"line","x":x-0.04,"y":y+0.02,"x2":x,"y2":y,"stroke":[60,60,65,180],"stroke_width":2})
            elems.append({"type":"line","x":x,"y":y,"x2":x+0.04,"y2":y+0.02,"stroke":[60,60,65,180],"stroke_width":2})
            elems.append({"type":"line","x":x,"y":y-0.05,"x2":x,"y2":y,"stroke":[60,60,65,180],"stroke_width":2})
            elems.append({"type":"line","x":x,"y":y-0.05,"x2":x+0.005,"y2":y-0.08,"stroke":[60,60,65,200],"stroke_width":2})
            elems.append({"type":"circle","x":x+0.005,"y":y-0.08,"radius":2,"fill":[200,200,190,220]})
        elif etype == "chariot":
            elems.append({"type":"circle","x":x-0.04,"y":y+0.02,"radius":int(8*sc),"fill":[40,40,45],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.04,"y":y+0.02,"radius":int(8*sc),"fill":[40,40,45],"stroke":[20,20,25],"stroke_width":1})
            elems.append({"type":"rect","x":x,"y":y-0.03,"width":int(20*sc),"height":int(15*sc),"fill":[160,140,100,200]})
            elems.append({"type":"line","x":x-0.01,"y":y,"x2":x-0.05,"y2":y-0.06,"stroke":[100,80,50,200],"stroke_width":2})
            elems.append({"type":"rect","x":x-0.05,"y":y-0.07,"width":int(8*sc),"height":int(12*sc),"fill":[120,90,60,200]})
        elif etype in ("computer","laptop"):
            elems.append({"type":"rect","x":x,"y":y,"width":int(35*sc),"height":int(25*sc),"fill":[50,55,65,220],"rx":2})
            elems.append({"type":"rect","x":x,"y":y-0.005,"width":int(28*sc),"height":int(18*sc),"fill":[100,140,200,200],"rx":1})
            elems.append({"type":"rect","x":x,"y":y+0.03,"width":int(20*sc),"height":int(4*sc),"fill":[60,65,75,200],"rx":1})
        elif etype == "phone":
            elems.append({"type":"rect","x":x,"y":y,"width":int(14*sc),"height":int(28*sc),"fill":[30,35,45,220],"rx":3})
            elems.append({"type":"rect","x":x,"y":y-0.005,"width":int(10*sc),"height":int(20*sc),"fill":[80,120,200,200],"rx":1})
            elems.append({"type":"circle","x":x,"y":y+0.025,"radius":2,"fill":[50,55,65,200]})
        elif etype == "satellite":
            elems.append({"type":"rect","x":x,"y":y,"width":int(12*sc),"height":int(14*sc),"fill":[180,190,200,220],"rx":1})
            elems.append({"type":"rect","x":x-0.03,"y":y-0.01,"width":int(20*sc),"height":int(5*sc),"fill":[100,140,200,180],"rx":0})
            elems.append({"type":"rect","x":x-0.03,"y":y+0.01,"width":int(20*sc),"height":int(5*sc),"fill":[100,140,200,180],"rx":0})
            elems.append({"type":"line","x":x-0.03,"y":y,"x2":x-0.07,"y2":y,"stroke":[150,160,170,200],"stroke_width":1})
            elems.append({"type":"line","x":x+0.03,"y":y,"x2":x+0.07,"y2":y,"stroke":[150,160,170,200],"stroke_width":1})
        elif etype == "camera":
            elems.append({"type":"rect","x":x,"y":y,"width":int(30*sc),"height":int(18*sc),"fill":[60,65,75,220],"rx":2})
            elems.append({"type":"rect","x":x+0.01,"y":y-0.015,"width":int(10*sc),"height":int(5*sc),"fill":[70,75,85,220],"rx":1})
            elems.append({"type":"circle","x":x+0.01,"y":y,"radius":int(6*sc),"fill":[40,45,55,220],"stroke":[80,85,95],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.01,"y":y,"radius":int(4*sc),"fill":[120,150,200,200]})
            elems.append({"type":"circle","x":x-0.025,"y":y-0.01,"radius":2,"fill":[200,50,50,200]})
        elif etype == "telescope":
            elems.append({"type":"telescope","x":x,"y":y,"scale":round(sc*0.7,1),"fill":[140,110,80]})
        elif etype in ("volcano","volcanic"):
            elems.append({"type":"volcano","x":x,"y":0.62,"scale":round(sc*0.9,1),"fill":[100,85,70]})
            elems.append({"type":"circle","x":x+round(rng.uniform(-0.02,0.03),2),"y":0.50,"radius":int(5*sc),"fill":[255,150,30,200]})
            elems.append({"type":"circle","x":x+round(rng.uniform(-0.01,0.04),2),"y":0.48,"radius":int(3*sc),"fill":[255,200,50,180]})
        elif etype == "waterfall":
            elems.append({"type":"waterfall","x":x,"y":0.55,"scale":round(sc*0.8,1),"fill":[150,200,255]})
        elif etype == "geyser":
            elems.append({"type":"ellipse","x":x,"y":y+0.02,"width":int(15*sc),"height":int(6*sc),"fill":[140,180,200,200]})
            elems.append({"type":"line","x":x,"y":y+0.02,"x2":x,"y2":y-0.06,"stroke":[180,210,240,150],"stroke_width":3})
            elems.append({"type":"circle","x":x,"y":y-0.07,"radius":int(4*sc),"fill":[200,230,255,100]})
        elif etype == "fruit":
            elems.append({"type":"fruit","x":x,"y":y,"scale":round(sc*0.6,1),"fill":[220+rng.randint(0,35),80+rng.randint(0,60),40+rng.randint(0,30)]})
        elif etype == "bread":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(30*sc),"height":int(16*sc),"fill":[180+rng.randint(0,30),150+rng.randint(0,20),90+rng.randint(0,20),220]})
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(20*sc),"height":int(8*sc),"fill":[160,130,70,100]})
        elif etype == "cup":
            elems.append({"type":"rect","x":x,"y":y-0.005,"width":int(20*sc),"height":int(18*sc),"fill":[180+rng.randint(0,20),170+rng.randint(0,20),150+rng.randint(0,20),220],"rx":1})
            elems.append({"type":"arc","x":x,"y":y-0.03,"radius":int(10*sc),"start_angle":0,"end_angle":180,"stroke":[160,150,130,200],"stroke_width":2})
            elems.append({"type":"arc","x":x,"y":y+0.02,"radius":int(10*sc),"start_angle":180,"end_angle":360,"stroke":[160,150,130,200],"stroke_width":2})
        elif etype == "bell":
            elems.append({"type":"arc","x":x,"y":y-0.01,"radius":int(14*sc),"start_angle":30,"end_angle":150,"stroke":[180+rng.randint(0,40),160+rng.randint(0,30),60+rng.randint(0,30),200],"stroke_width":3})
            elems.append({"type":"circle","x":x,"y":y-0.03,"radius":2,"fill":[200,180,80,220]})
            elems.append({"type":"line","x":x,"y":y-0.03,"x2":x,"y2":y-0.06,"stroke":[180,160,60,200],"stroke_width":2})
        elif etype == "mirror":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(24*sc),"height":int(30*sc),"fill":[180,190,210,200],"stroke":[160,170,190,200],"stroke_width":2})
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(18*sc),"height":int(24*sc),"fill":[200,210,230,150]})
            elems.append({"type":"line","x":x,"y":y+0.025,"x2":x,"y2":y+0.04,"stroke":[140,120,100,200],"stroke_width":3})
        elif etype == "mask":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(30*sc),"height":int(22*sc),"fill":[180+rng.randint(0,30),170+rng.randint(0,20),160+rng.randint(0,20),200]})
            elems.append({"type":"circle","x":x-0.015,"y":y-0.005,"radius":3,"fill":[40,35,30,200]})
            elems.append({"type":"circle","x":x+0.015,"y":y-0.005,"radius":3,"fill":[40,35,30,200]})
            elems.append({"type":"line","x":x-0.01,"y":y+0.01,"x2":x+0.01,"y2":y+0.01,"stroke":[40,35,30,200],"stroke_width":1})
        elif etype == "tank":
            elems.append({"type":"rect","x":x,"y":y-0.01,"width":int(50*sc),"height":int(16*sc),"fill":[60+rng.randint(0,20),65+rng.randint(0,20),55+rng.randint(0,20),220],"rx":2})
            elems.append({"type":"circle","x":x-0.02,"y":y+0.02,"radius":int(7*sc),"fill":[30,35,30,200],"stroke":[50,55,50],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.02,"y":y+0.02,"radius":int(7*sc),"fill":[30,35,30,200],"stroke":[50,55,50],"stroke_width":1})
            elems.append({"type":"rect","x":x+0.01,"y":y-0.03,"width":int(20*sc),"height":int(8*sc),"fill":[80,90,70,220],"rx":1})
            elems.append({"type":"line","x":x+0.025,"y":y-0.03,"x2":x+0.05,"y2":y-0.035,"stroke":[60,70,50,200],"stroke_width":3})
        elif etype in ("unicorn","horse"):
            elems.append({"type":"animal","x":x,"y":y,"scale":round(sc*0.8,1),"fill":[200+rng.randint(0,30),180+rng.randint(0,20),150+rng.randint(0,20)]})
            if etype == "unicorn":
                elems.append({"type":"line","x":x+0.02,"y":y-0.06,"x2":x+0.025,"y2":y-0.12,"stroke":[220,200,150,200],"stroke_width":2})
                elems.append({"type":"star","x":x+0.025,"y":y-0.12,"radius":1,"fill":[255,255,210,200]})
        elif etype in ("fairy","elf"):
            skin = [220+rng.randint(-15,15), 185+rng.randint(-10,10), 155+rng.randint(-10,10)]
            elems.append({"type":"human","x":x,"y":y,"scale":round(sc*0.4,1),"fill":[60+rng.randint(0,30),80+rng.randint(0,30),120+rng.randint(0,20)],"skin_color":skin})
            if etype == "fairy":
                elems.append({"type":"ellipse","x":x-0.015,"y":y-0.02,"width":int(20*sc),"height":int(8*sc),"fill":[180,220,255,120],"stroke":[150,200,240,80],"stroke_width":1})
                elems.append({"type":"ellipse","x":x+0.015,"y":y-0.02,"width":int(20*sc),"height":int(8*sc),"fill":[180,220,255,120],"stroke":[150,200,240,80],"stroke_width":1})
                elems.append({"type":"circle","x":x+0.01,"y":y-0.04,"radius":2,"fill":[255,255,200,200]})
        elif etype == "dwarf":
            elems.append({"type":"human","x":x,"y":y+0.02,"scale":round(sc*0.5,1),"fill":[100+rng.randint(0,30),80+rng.randint(0,20),60+rng.randint(0,20)],"skin_color":[200,170,140]})
            elems.append({"type":"ellipse","x":x,"y":y-0.04,"width":int(14*sc),"height":int(8*sc),"fill":[160,110,70,200],"rx":2})
        elif etype == "troll":
            elems.append({"type":"human","x":x,"y":y,"scale":round(sc*1.2,1),"fill":[80+rng.randint(0,30),90+rng.randint(0,20),60+rng.randint(0,20)],"skin_color":[160,140,110]})
        elif etype == "zombie":
            elems.append({"type":"human","x":x,"y":y,"scale":round(sc*0.8,1),"fill":[60+rng.randint(0,20),70+rng.randint(0,20),60+rng.randint(0,20)],"skin_color":[140,150,130]})
            elems.append({"type":"circle","x":x-0.01,"y":y-0.03,"radius":2,"fill":[200,50,50,150]})
        elif etype == "guitar":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(14*sc),"height":int(20*sc),"fill":[160+rng.randint(0,30),120+rng.randint(0,30),60+rng.randint(0,20),220],"stroke":[120,90,40],"stroke_width":1})
            elems.append({"type":"rect","x":x+0.02,"y":y-0.03,"width":int(3*sc),"height":int(30*sc),"fill":[80,60,40,220],"rx":1})
            elems.append({"type":"circle","x":x+0.02,"y":y-0.035,"radius":2,"fill":[200,190,180,220]})
            elems.append({"type":"line","x":x+0.02,"y":y-0.035,"x2":x+0.02,"y2":y-0.07,"stroke":[60,50,40,200],"stroke_width":1})
            for i in range(4):
                elems.append({"type":"line","x":x+0.015,"y":y-0.015+i*0.01,"x2":x+0.03,"y2":y-0.015+i*0.01,"stroke":[200,190,180,150],"stroke_width":1})
        elif etype == "microphone":
            elems.append({"type":"rect","x":x,"y":y,"width":int(4*sc),"height":int(16*sc),"fill":[140,140,150,220],"rx":1})
            elems.append({"type":"ellipse","x":x,"y":y-0.025,"width":int(10*sc),"height":int(12*sc),"fill":[160,160,170,220]})
            elems.append({"type":"ellipse","x":x,"y":y-0.025,"width":int(6*sc),"height":int(8*sc),"fill":[80,80,90,220]})
            elems.append({"type":"rect","x":x,"y":y+0.02,"width":int(10*sc),"height":int(3*sc),"fill":[60,60,70,200],"rx":1})
        elif etype == "drum":
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(26*sc),"height":int(8*sc),"fill":[180+rng.randint(0,30),170+rng.randint(0,20),160+rng.randint(0,20),220]})
            elems.append({"type":"rect","x":x,"y":y,"width":int(26*sc),"height":int(16*sc),"fill":[160+rng.randint(0,20),150+rng.randint(0,20),140+rng.randint(0,20),220],"rx":0})
            elems.append({"type":"ellipse","x":x,"y":y+0.03,"width":int(26*sc),"height":int(8*sc),"fill":[140,130,120,220]})
        elif etype == "angel":
            skin = [230+rng.randint(-15,15), 200+rng.randint(-10,10), 170+rng.randint(-10,10)]
            elems.append({"type":"human","x":x,"y":y,"scale":round(sc*0.7,1),"fill":[200+rng.randint(0,30),180+rng.randint(0,20),150+rng.randint(0,20)],"skin_color":skin})
            elems.append({"type":"ellipse","x":x-0.02,"y":y-0.03,"width":int(20*sc),"height":int(8*sc),"fill":[240,240,255,150],"stroke":[220,220,240,80],"stroke_width":1})
            elems.append({"type":"ellipse","x":x+0.02,"y":y-0.03,"width":int(20*sc),"height":int(8*sc),"fill":[240,240,255,150],"stroke":[220,220,240,80],"stroke_width":1})
            elems.append({"type":"circle","x":x,"y":y-0.045,"radius":3,"fill":[255,255,200,150]})
        elif etype == "atom":
            elems.append({"type":"atom","x":x,"y":y,"radius":35,"fill":[80,140,200]})
        elif etype == "dna":
            elems.append({"type":"dna","x":x,"y":y,"width":120,"height":140,"fill":[60,140,200]})
        elif etype == "heart":
            elems.append({"type":"heart","x":x,"y":y,"scale":35,"fill":[220,60,80]})
        elif etype == "infinity":
            elems.append({"type":"infinity","x":x,"y":y,"scale":40,"fill":[100,160,200]})
        elif etype == "target":
            elems.append({"type":"target","x":x,"y":y,"radius":35,"fill":[200,60,60]})
        elif etype == "puzzle":
            elems.append({"type":"puzzle","x":x,"y":y,"scale":30,"fill":[180,140,80]})
        elif etype == "scales":
            elems.append({"type":"scales","x":x,"y":y,"scale":30,"fill":[180,160,100]})
        elif etype == "astronaut":
            elems.append({"type":"astronaut","x":x,"y":y,"scale":25,"fill":[220,220,230]})
        elif etype == "spaceship":
            elems.append({"type":"spaceship","x":x,"y":y,"scale":28,"fill":[160,180,210]})
        elif etype == "hourglass":
            elems.append({"type":"hourglass","x":x,"y":y,"scale":28,"fill":[180,160,120]})
        elif etype == "treasure_chest":
            elems.append({"type":"treasure_chest","x":x,"y":y,"scale":28,"fill":[140,90,50]})
        elif etype == "gravestone":
            elems.append({"type":"gravestone","x":x,"y":y,"scale":25,"fill":[160,150,140]})
        elif etype == "hat":
            elems.append({"type":"hat","x":x,"y":y,"scale":28,"fill":[180+rng.randint(0,40),160+rng.randint(0,30),100+rng.randint(0,30)]})
        elif etype == "clothing":
            elems.append({"type":"rect","x":x,"y":y,"width":int(30*sc),"height":int(35*sc),"fill":list(c)+[200],"rx":3})
            elems.append({"type":"rect","x":x,"y":y-0.02,"width":int(14*sc),"height":int(10*sc),"fill":[c[0]+20,c[1]+20,c[2]+20,200],"rx":2})
        elif etype == "shoe":
            def _dark(c, amt=20): return tuple(max(0,v-amt) for v in c[:3])
            elems.append({"type":"ellipse","x":x+0.01,"y":y+0.01,"width":int(28*sc),"height":int(12*sc),"fill":list(c)+[200],"stroke":list(_dark(c,20))+[180]})
            elems.append({"type":"line","x":x-0.015,"y":y,"x2":x+0.015,"y2":y,"stroke":[60,55,50,100],"stroke_width":1})
        elif etype == "jewelry":
            elems.append({"type":"circle","x":x,"y":y,"radius":int(10*sc),"fill":[200,180,80,200],"stroke":[180,150,50,180],"stroke_width":2})
            elems.append({"type":"circle","x":x,"y":y,"radius":int(5*sc),"fill":[255,100,150,180]})
        elif etype == "furniture":
            def _dark(c, amt=30): return tuple(max(0,v-amt) for v in c[:3])
            elems.append({"type":"rect","x":x,"y":y,"width":int(35*sc),"height":int(28*sc),"fill":list(c)+[200],"rx":2})
            elems.append({"type":"rect","x":x-0.02,"y":y+0.025,"width":int(6*sc),"height":int(10*sc),"fill":list(_dark(c,30))+[180]})
            elems.append({"type":"rect","x":x+0.02,"y":y+0.025,"width":int(6*sc),"height":int(10*sc),"fill":list(_dark(c,30))+[180]})
        elif etype == "kitchen":
            elems.append({"type":"ellipse","x":x-0.015,"y":y,"width":int(14*sc),"height":int(12*sc),"fill":list(c)+[200]})
            elems.append({"type":"rect","x":x+0.01,"y":y-0.01,"width":int(18*sc),"height":int(22*sc),"fill":[c[0]+20,c[1]+20,c[2]+20,200],"rx":2})
        else:
            elems.append({"type":"ellipse","x":x,"y":y,"width":int(30*sc),"height":int(20*sc),"fill":list(c)+[180]})
    return elems

def _handle_special_entity(key, t, rng, density, phase):
    """Generate elements for special narrative entities that need custom visuals."""
    elems = []
    if key == "comet":
        for i in range(10):
            elems.append({"type":"star","x":round(rng.uniform(0.02,0.98),2),"y":round(rng.uniform(0.02,0.50),2),
                         "radius":rng.randint(1,2),"fill":[255,255,210,180+rng.randint(0,75)]})
        cx, cy = 0.72, 0.12
        for i in range(8):
            frac = i / 8
            elems.append({"type":"circle","x":round(cx - frac*0.35 + rng.uniform(-0.008,0.008),3),
                         "y":round(cy + frac*0.08 + rng.uniform(-0.005,0.005),3),
                         "radius":max(1,int(6*(1-frac*0.85))),
                         "fill":[255,200+int(i*5),50+int(i*10),200-int(i*20)]})
        elems.append({"type":"circle","x":cx,"y":cy,"radius":7,"fill":[255,240,180,250],"stroke":[255,220,80],"stroke_width":1})
        for i in range(3):
            elems.append({"type":"circle","x":cx,"y":cy,"radius":11+i*5,"fill":[255,230,120,30-i*8]})
    elif key == "dragonfly":
        s = 1.0
        bw, bh = int(60*s), int(12*s)
        elems.extend([
            {"type":"line","x":0.65-int(bw/200),"y":0.25,"x2":0.65+int(bw/200),"y2":0.25,"stroke":[40,70,50,200],"stroke_width":max(int(5*s),2)},
            {"type":"ellipse","x":0.65,"y":0.25-int(bh/100),"width":bw+10,"height":bh,"fill":[180,210,240,140],"stroke":[140,180,210,80],"stroke_width":1},
            {"type":"ellipse","x":0.65,"y":0.25+int(bh/100),"width":bw+10,"height":bh,"fill":[180,210,240,140],"stroke":[140,180,210,80],"stroke_width":1},
            {"type":"ellipse","x":0.65-int(5*s/100),"y":0.25-int(bh*1.8/100),"width":int(bw*0.5),"height":int(bh*0.6),"fill":[190,220,245,120]},
            {"type":"ellipse","x":0.65-int(5*s/100),"y":0.25+int(bh*1.8/100),"width":int(bw*0.5),"height":int(bh*0.6),"fill":[190,220,245,120]},
            {"type":"circle","x":0.65+int(bw*0.45/100),"y":0.25,"radius":int(6*s),"fill":[30,55,35,200]},
        ])
    elif key == "shadow":
        elems.extend([
            {"type":"polygon","points":[[-0.05,0.32],[0.25,0.18],[0.65,0.20],[1.05,0.38],[-0.05,0.38]],"fill":[15,10,10,150]},
            {"type":"polygon","points":[[-0.05,0.32],[0.25,0.18],[0.65,0.20],[1.05,0.38],[-0.05,0.38]],"fill":[25,20,20,70]},
        ])
    elif key == "sound" or any(k in t for k in ["buzzing","hear","louder","sound"]):
        intensity = 1.0
        if "grows louder" in t: intensity = 2.0
        if "and louder" in t: intensity = 3.0
        cx, cy = 0.55, 0.40
        for i in range(min(4, 1+int(intensity))):
            r = 20 + i*25*intensity
            elems.append({"type":"arc","x":cx,"y":cy,"radius":int(r),"start_angle":330-int(i*5),"end_angle":30+int(i*5),
                         "stroke":[200,180,150,200-i*30],"stroke_width":max(2,3-i//2)})
        if intensity >= 2:
            for i in range(2):
                elems.append({"type":"line","x":0.25,"y":0.12+0.15*i,"x2":0.85,"y2":0.12+0.15*i,"stroke":[180,170,160,30+20*i],"stroke_width":1})
    elif key == "warning":
        for i in range(15):
            elems.append({"type":"star","x":round(rng.uniform(0.02,0.98),2),"y":round(rng.uniform(0.02,0.50),2),
                         "radius":rng.randint(1,2),"fill":[255,255,210,180+rng.randint(0,75)]})
        for i in range(3):
            frac = i / 3
            x1, y1 = 0.85-frac*0.4, 0.12+frac*0.20
            x2, y2 = 0.50-frac*0.35, 0.35+frac*0.25
            elems.append({"type":"line","x":x1,"y":y1,"x2":x2,"y2":y2,"stroke":[255,200,80,120-i*30],"stroke_width":4+i})
        elems.append({"type":"circle","x":0.85,"y":0.12,"radius":6,"fill":[255,230,150,250]})
    elif key == "question" or any(k in t for k in ["nobody knows","no one knows","don't know","unknown","mystery"]):
        for i in range(2):
            skin = [225,195,170]
            elems.append({"type":"human","x":0.28+i*0.32,"y":0.72,"scale":0.55,"fill":[55,45,70],"skin_color":skin})
        elems.append({"type":"text","x":0.5,"y":0.12,"text":"?","font_size":50,"fill":[200,200,180,70]})
    elif key == "predictable":
        for i in range(5):
            elems.append({"type":"star","x":round(rng.uniform(0.15,0.85),2),"y":round(rng.uniform(0.08,0.30),2),
                         "radius":rng.randint(2,3),"fill":[255,255,210,220]})
        elems.append({"type":"moon","x":0.5,"y":0.18,"scale":0.85})
    elif key == "silence" or any(k in t for k in ["no birds","no mammals","no humans","no dinosaur"]):
        if any(w in t for w in ["bird","sing"]):
            elems.append({"type":"line","x":0.45,"y":0.38,"x2":0.55,"y2":0.38,"stroke":[120,110,100,40],"stroke_width":2})
        elems.append({"type":"text","x":0.5,"y":0.62,"text":"...","font_size":36,"fill":[130,150,130,70]})
    elif key == "alien":
        for i in range(4):
            x = 0.12 + i*0.24
            elems.append({"type":"ellipse","x":x,"y":0.35,"width":40,"height":80,"fill":[80+rng.randint(0,30),150+rng.randint(0,30),80,120]})
            elems.append({"type":"ellipse","x":x,"y":0.20,"width":60,"height":15,"fill":[100,200,150,40]})
    elif key == "dragon":
        for i in range(3):
            xd = 0.40+i*0.12
            elems.append({"type":"ellipse","x":xd,"y":0.38-i*0.03,"width":int(30-i*4),"height":int(16-i*2),"fill":[40+rng.randint(0,30),100+rng.randint(0,20),50+rng.randint(0,20),200]})
        elems.append({"type":"line","x":0.40,"y":0.35,"x2":0.30,"y2":0.30,"stroke":[50,120,60,200],"stroke_width":4})
        elems.append({"type":"line","x":0.40,"y":0.35,"x2":0.30,"y2":0.40,"stroke":[50,120,60,200],"stroke_width":4})
        elems.append({"type":"polygon","points":[[0.35,0.30],[0.25,0.18],[0.45,0.28]],"fill":[50,130,60,180]})
        elems.append({"type":"polygon","points":[[0.35,0.40],[0.25,0.52],[0.45,0.42]],"fill":[50,130,60,180]})
        elems.append({"type":"circle","x":0.65,"y":0.28,"radius":6,"fill":[40,100,50,200],"stroke":[30,80,40],"stroke_width":1})
        elems.append({"type":"circle","x":0.63,"y":0.27,"radius":2,"fill":[255,200,50,200]})
        elems.append({"type":"line","x":0.65,"y":0.28,"x2":0.75,"y2":0.20,"stroke":[60,140,70,200],"stroke_width":2})
        for i in range(3):
            elems.append({"type":"circle","x":0.72+i*0.03,"y":0.18-i*0.02,"radius":3-i,"fill":[255,180,50,150-i*30]})
    elif key == "robot":
        elems.append({"type":"rect","x":0.45,"y":0.45,"width":int(25*1.0),"height":int(30*1.0),"fill":[100+rng.randint(0,40),110+rng.randint(0,30),130+rng.randint(0,20),220],"rx":2})
        elems.append({"type":"circle","x":0.45,"y":0.38,"radius":8,"fill":[120+rng.randint(0,30),130+rng.randint(0,20),150+rng.randint(0,20),220],"stroke":[80,90,110],"stroke_width":1})
        elems.append({"type":"circle","x":0.43,"y":0.37,"radius":2,"fill":[200,230,255,250]})
        elems.append({"type":"circle","x":0.47,"y":0.37,"radius":2,"fill":[200,230,255,250]})
        elems.append({"type":"rect","x":0.40,"y":0.42,"width":4,"height":2,"fill":[50,60,80,200]})
        elems.append({"type":"line","x":0.45,"y":0.52,"x2":0.38,"y2":0.72,"stroke":[100,110,130,200],"stroke_width":3})
        elems.append({"type":"line","x":0.45,"y":0.52,"x2":0.52,"y2":0.72,"stroke":[100,110,130,200],"stroke_width":3})
        elems.append({"type":"line","x":0.45,"y":0.58,"x2":0.38,"y2":0.58,"stroke":[100,110,130,200],"stroke_width":3})
        elems.append({"type":"line","x":0.45,"y":0.58,"x2":0.52,"y2":0.58,"stroke":[100,110,130,200],"stroke_width":3})
        elems.append({"type":"circle","x":0.38,"y":0.72,"radius":3,"fill":[80,90,110,220]})
        elems.append({"type":"circle","x":0.52,"y":0.72,"radius":3,"fill":[80,90,110,220]})
    elif key == "ghost":
        elems.append({"type":"ellipse","x":0.45,"y":0.40,"width":int(30*1.2),"height":int(40*1.2),"fill":[210,220,230,150],"stroke":[190,200,210,100],"stroke_width":1})
        elems.append({"type":"ellipse","x":0.45,"y":0.38,"width":int(22*1.2),"height":int(30*1.2),"fill":[220,230,240,120]})
        elems.append({"type":"circle","x":0.43,"y":0.36,"radius":2,"fill":[40,50,60,200]})
        elems.append({"type":"circle","x":0.47,"y":0.36,"radius":2,"fill":[40,50,60,200]})
        elems.append({"type":"ellipse","x":0.45,"y":0.40,"width":6,"height":3,"fill":[40,50,60,200]})
        elems.append({"type":"polygon","points":[[0.38,0.48],[0.42,0.44],[0.45,0.48],[0.48,0.44],[0.52,0.48]],"fill":[210,220,230,100]})
        hover = [{"type":"ellipse","x":0.45,"y":0.55,"width":int(25*1.2),"height":int(6*1.0),"fill":[210,220,230,40]} for _ in range(2)]
        elems.extend(hover)
    elif key == "demon":
        elems.append({"type":"human","x":0.45,"y":0.50,"scale":0.9,"fill":[100+rng.randint(0,30),40+rng.randint(0,20),50+rng.randint(0,20)],"skin_color":[180,100,80]})
        elems.append({"type":"line","x":0.45,"y":0.42,"x2":0.38,"y2":0.48,"stroke":[100,40,50,200],"stroke_width":2})
        elems.append({"type":"line","x":0.45,"y":0.42,"x2":0.52,"y2":0.48,"stroke":[100,40,50,200],"stroke_width":2})
        elems.append({"type":"polygon","points":[[0.35,0.38],[0.28,0.25],[0.42,0.35]],"fill":[100,40,50,150]})
        elems.append({"type":"polygon","points":[[0.55,0.38],[0.62,0.25],[0.48,0.35]],"fill":[100,40,50,150]})
        elems.append({"type":"line","x":0.45,"y":0.52,"x2":0.38,"y2":0.65,"stroke":[100,40,50,200],"stroke_width":3})
        elems.append({"type":"polygon","points":[[0.36,0.60],[0.38,0.65],[0.32,0.65]],"fill":[100,40,50,200]})
        elems.append({"type":"circle","x":0.43,"y":0.38,"radius":2,"fill":[255,50,50,200]})
        elems.append({"type":"circle","x":0.47,"y":0.38,"radius":2,"fill":[255,50,50,200]})
    elif key == "wizard":
        skin = [220,185,155]
        elems.append({"type":"human","x":0.42,"y":0.55,"scale":0.7,"fill":[80+rng.randint(0,30),60+rng.randint(0,20),100+rng.randint(0,30)],"skin_color":skin})
        elems.append({"type":"polygon","points":[[0.38,0.38],[0.42,0.32],[0.46,0.38]],"fill":[80,60,100,220]})
        elems.append({"type":"star","x":0.42,"y":0.34,"radius":1,"fill":[255,255,200,200]})
        elems.append({"type":"line","x":0.45,"y":0.52,"x2":0.55,"y2":0.40,"stroke":[120,90,60,200],"stroke_width":2})
        elems.append({"type":"circle","x":0.56,"y":0.39,"radius":3,"fill":[200,230,255,200]})
        elems.append({"type":"circle","x":0.56,"y":0.39,"radius":5,"fill":[200,230,255,60]})
    elif key == "ufo":
        elems.append({"type":"ellipse","x":0.50,"y":0.20,"width":int(60*1.0),"height":int(14*1.0),"fill":[150+rng.randint(0,30),160+rng.randint(0,20),180+rng.randint(0,20),220],"stroke":[120,130,150],"stroke_width":1})
        elems.append({"type":"arc","x":0.50,"y":0.18,"radius":int(14*1.0),"start_angle":0,"end_angle":180,"stroke":[180,190,210,200],"stroke_width":2})
        elems.append({"type":"ellipse","x":0.50,"y":0.20,"width":int(16*1.0),"height":int(6*1.0),"fill":[100,200,255,150]})
        for i in range(3):
            elems.append({"type":"circle","x":0.40+i*0.10,"y":0.205,"radius":2,"fill":[200,255,200,200]})
        for i in range(2):
            elems.append({"type":"circle","x":0.42+i*0.16,"y":0.20,"radius":4,"fill":[150,200,255,40]})
        for i in range(5):
            elems.append({"type":"line","x":0.30+i*0.10,"y":0.19,"x2":0.28+i*0.12,"y2":0.24+i*0.02,"stroke":[100,200,255,30+i*10],"stroke_width":1})
    elif key == "explosion":
        cx, cy = 0.50, 0.35
        for i in range(8):
            r = 5 + i*6 + rng.randint(0,5)
            a = 255 - i*30
            elems.append({"type":"circle","x":cx+round(rng.uniform(-0.02,0.02),2),"y":cy+round(rng.uniform(-0.02,0.02),2),
                         "radius":r,"fill":[255,200-rng.randint(0,100),50-rng.randint(0,40),max(20,a)]})
        for i in range(12):
            angle = rng.uniform(0, 6.28)
            dist = rng.uniform(0.03, 0.12)
            elems.append({"type":"line","x":cx,"y":cy,"x2":round(cx+math.cos(angle)*dist,3),"y2":round(cy+math.sin(angle)*dist,3),
                         "stroke":[255,200-rng.randint(0,100),50,180-rng.randint(0,80)],"stroke_width":rng.randint(1,3)})
        for i in range(3):
            elems.append({"type":"circle","x":cx+round(rng.uniform(-0.04,0.04),2),"y":round(cy-0.04+rng.uniform(-0.02,0.02),2),
                         "radius":rng.randint(2,4),"fill":[255,255,200,200]})
        elems.append({"type":"circle","x":cx,"y":cy,"radius":4,"fill":[255,255,220,250]})
    elif key == "tornado":
        pts = []
        for i in range(10):
            frac = i / 9
            tw = 0.02 + frac*0.12
            tx = 0.50 + math.sin(frac*6.28*2)*0.03
            ty = 0.15 + frac*0.55
            pts.append([round(tx-tw,3), round(ty,3)])
        for i in range(9, -1, -1):
            frac = i / 9
            tw = 0.02 + frac*0.12
            tx = 0.50 + math.sin(frac*6.28*2)*0.03
            ty = 0.15 + frac*0.55
            pts.append([round(tx+tw,3), round(ty,3)])
        elems.append({"type":"polygon","points":pts,"fill":[100,110,120,80],"stroke":[120,130,140,60],"stroke_width":1})
        for i in range(3):
            elems.append({"type":"ellipse","x":0.50,"y":0.15+i*0.18,"width":int(20-i*4),"height":int(6-i),"fill":[150,160,170,30+20*i]})
    elif key == "aurora":
        for layer in range(3):
            pts = []
            off = 0.15 + layer*0.05
            for i in range(12):
                frac = i / 11
                px = 0.05 + frac*0.90
                py = 0.05 + math.sin(frac*6.28*1.5+layer)*0.08 + off
                pts.append([round(px,3), round(py,3)])
            for i in range(11, -1, -1):
                frac = i / 11
                px = 0.05 + frac*0.90
                py = 0.08 + math.sin(frac*6.28*1.5+layer+0.5)*0.06 + off
                pts.append([round(px,3), round(py,3)])
            colors = [[50,200,100,40],[100,200,200,30],[50,150,255,20]]
            elems.append({"type":"polygon","points":pts,"fill":colors[layer]})
        for i in range(15):
            elems.append({"type":"star","x":round(rng.uniform(0.02,0.98),2),"y":round(rng.uniform(0.02,0.15),2),
                         "radius":rng.randint(1,2),"fill":[255,255,210,180+rng.randint(0,75)]})
    elif key == "alien_creature":
        for i in range(2):
            xa = 0.30+i*0.30
            elems.append({"type":"ellipse","x":xa,"y":0.38,"width":int(18*1.0),"height":int(28*1.0),"fill":[80+rng.randint(0,40),150+rng.randint(0,30),80+rng.randint(0,20),220],"stroke":[60,120,60],"stroke_width":1})
            elems.append({"type":"ellipse","x":xa,"y":0.28,"width":int(20*1.0),"height":int(16*1.0),"fill":[100+rng.randint(0,20),180+rng.randint(0,20),100+rng.randint(0,10),200]})
            elems.append({"type":"circle","x":xa-0.02,"y":0.27,"radius":3,"fill":[200,230,255,250]})
            elems.append({"type":"circle","x":xa+0.02,"y":0.27,"radius":3,"fill":[200,230,255,250]})
            elems.append({"type":"circle","x":xa-0.02,"y":0.27,"radius":1,"fill":[30,40,50,250]})
            elems.append({"type":"circle","x":xa+0.02,"y":0.27,"radius":1,"fill":[30,40,50,250]})
            elems.append({"type":"line","x":xa,"y":0.34,"x2":xa,"y2":0.36,"stroke":[60,120,60,200],"stroke_width":1})
            elems.append({"type":"line","x":xa,"y":0.48,"x2":xa-0.02,"y2":0.58,"stroke":[80,150,80,200],"stroke_width":2})
            elems.append({"type":"line","x":xa,"y":0.48,"x2":xa+0.02,"y2":0.58,"stroke":[80,150,80,200],"stroke_width":2})
    return elems

def _apply_action_effects(actions, elements, rng):
    """Modify elements based on detected actions."""
    for action in actions:
        name = action["name"]
        if name == "walk":
            # Add a walking human if none exists or enhance existing
            has_human = any(e["type"] == "human" for e in elements)
            if not has_human:
                elements.append({"type":"human","x":0.5,"y":0.60,"scale":0.6,"fill":[140,110,90],"skin_color":[230,200,175]})
            # Add movement lines behind
            for i in range(2):
                elements.append({"type":"line","x":0.42+i*0.04,"y":0.65,"x2":0.42+i*0.04,"y2":0.70,"stroke":[130,120,110,30],"stroke_width":1})
        elif name == "watch":
            # Add a human looking up if none exists
            has_human = any(e["type"] == "human" for e in elements)
            if not has_human:
                elements.append({"type":"human","x":0.35,"y":0.72,"scale":0.55,"fill":[60,55,75],"skin_color":[230,200,175]})
    return elements

def _add_ambient_elements(elements, phase, rng):
    """Ensure every scene has enough elements to feel complete."""
    if len(elements) < 3:
        n = 3 - len(elements)
        for i in range(n):
            etype = rng.choice(["mountain","tree","star","cloud","fern"])
            y_info = _POSITION_ZONES.get(_ENTITY_MAP.get(etype,{}).get("y","ground"),{"y_range":(0.5,0.7)})
            y = round(rng.uniform(y_info["y_range"][0], y_info["y_range"][1]), 2)
            x = round(rng.uniform(0.15, 0.85), 2)
            if etype == "star":
                elements.append({"type":"star","x":x,"y":round(rng.uniform(0.05,0.30),2),"radius":rng.randint(1,2),"fill":[255,255,210,200]})
            elif etype == "mountain":
                elements.append({"type":"mountain","x":x,"y":0.68,"scale":0.8+rng.random()*0.3,"fill":[80+rng.randint(0,40),90+rng.randint(0,30),120+rng.randint(0,30)]})
            elif etype == "tree":
                elements.append({"type":"tree","x":x,"y":y,"scale":0.8+rng.random()*0.3,"fill":[50+rng.randint(0,40),120+rng.randint(0,30),50+rng.randint(0,20)]})
            elif etype == "cloud":
                elements.append({"type":"cloud","x":x,"y":round(rng.uniform(0.08,0.18),2),"scale":0.7+rng.random()*0.3,"fill":[210,215,225]})
            elif etype == "fern":
                elements.append({"type":"ellipse","x":x,"y":y,"width":int(30+rng.random()*20),"height":int(10+rng.random()*8),"fill":[50+rng.randint(0,40),120+rng.randint(0,30),50+rng.randint(0,20),160]})

def _compose_story_scene(t, phase, rng, density):
    """Entity-driven story scene composition. Extracts ALL entities from
    narration and generates meaningful elements for each, then applies
    action effects and adds ambient fill. Never produces empty scenes."""
    text_lower = t  # already lowercased by caller
    entities = _extract_entities(t)
    actions = _detect_actions(t)
    elements = []

    # 1. Generate elements for each entity
    for key, data in entities.items():
        info = data["info"]
        count = data["count"]
        if info.get("special") == 1:
            custom = _handle_special_entity(key, t, rng, density, phase)
            if custom:
                elements.extend(custom)
        else:
            gen = _gen_entity_elements(key, info, count, rng, t)
            if gen:
                elements.extend(gen)

    # 2. Apply action effects
    if actions:
        elements = _apply_action_effects(actions, elements, rng)

    # 3. Add ambient fill if scene feels bare
    _add_ambient_elements(elements, phase, rng)

    return elements


def _infer_visuals(text: str, scene_num: int, total: int) -> dict:
    """Infer scene visuals from narrative arc position + keywords.

    The story arc drives the emotional progression: opening (mystery/setup)
    → rising action → climax → falling action → resolution.
    This gives the video a cinematic feel — scenes flow naturally.
    """
    t = text.lower()
    progress = (scene_num - 1) / max(total - 1, 1)

    # ── Pick arc phase from position ──
    if progress < 0.10:
        phase = "opening"
    elif progress < 0.30:
        phase = "rising_early"
    elif progress < 0.55:
        phase = "rising_late"
    elif progress < 0.70:
        phase = "climax"
    elif progress < 0.88:
        phase = "falling"
    else:
        phase = "resolution"

    # ── Arc-driven mood base (overridden by keywords below) ──
    arc_moods = {
        "opening": "mysterious",
        "rising_early": "hopeful",
        "rising_late": "peaceful",
        "climax": "dramatic",
        "falling": "somber",
        "resolution": "hopeful",
    }

    # ── Arc-driven background palette ──
    arc_bgs = {
        "opening":      {"type": "gradient", "colors": [[25, 25, 55], [55, 45, 80]]},
        "rising_early": {"type": "gradient", "colors": [[60, 70, 110], [120, 100, 130]]},
        "rising_late":  {"type": "gradient", "colors": [[100, 130, 170], [180, 150, 130]]},
        "climax":       {"type": "sunset",   "colors": [[200, 90, 40], [140, 60, 80]]},
        "falling":      {"type": "gradient", "colors": [[120, 100, 130], [80, 70, 110]]},
        "resolution":   {"type": "sunset",   "colors": [[240, 190, 120], [200, 140, 100]]},
    }

    bg = dict(arc_bgs[phase])
    bg["horizon"] = 0.55

    # ── Arc-driven camera ──
    arc_cameras = {
        "opening": "ken_burns_in",
        "rising_early": None,
        "rising_late": "pan_right",
        "climax": "dolly_in",
        "falling": None,
        "resolution": "ken_burns_in",
    }

    # ── Arc-driven element density ──
    arc_density = {
        "opening": 0.4,
        "rising_early": 0.6,
        "rising_late": 0.8,
        "climax": 1.0,
        "falling": 0.6,
        "resolution": 0.5,
    }

    # ── Keyword overrides ──
    mood = arc_moods[phase]
    camera = arc_cameras[phase]

    # Mood override from keywords
    if any(w in t for w in ["terrify", "fear", "darken", "eclipse", "monster", "devour", "end of the world"]):
        mood = "somber"
    elif any(w in t for w in ["amazing", "extraordinary", "astonish", "revolutionary", "discover", "astonishing"]):
        mood = "epic"
    elif any(w in t for w in ["mystery", "mysterious", "unknown", "strange", "why"]):
        mood = "mysterious"
    elif any(w in t for w in ["hope", "relief", "return", "spared", "won"]):
        mood = "hopeful"
    elif any(w in t for w in ["battle", "fought", "powerful", "immense", "force", "terrifying"]):
        mood = "dramatic"

    # Background override from keywords
    if any(w in t for w in ["sunset", "dusk", "dawn", "morning", "sunrise"]) or \
       ("rise" in t and "horizon" in t):
        bg = {"type": "sunset", "colors": [[255, 190, 80], [210, 120, 60]], "horizon": 0.55}
    elif any(w in t for w in ["night", "dark", "darkness", "evening", "disappear", "fade"]):
        bg = {"type": "night", "colors": [[8, 8, 35], [28, 18, 55]], "horizon": 0.55}
    elif any(w in t for w in ["ocean", "sea", "sail", "boat", "ship"]):
        bg = {"type": "ocean", "colors": [[25, 105, 190], [190, 210, 230]], "horizon": 0.55}
    elif any(w in t for w in ["forest", "tree", "plant", "grow", "woods"]):
        bg = {"type": "forest", "colors": [[50, 110, 50], [90, 150, 70]], "horizon": 0.55}
    elif any(w in t for w in ["snow", "frozen", "ice", "cold", "winter"]):
        bg = {"type": "gradient", "colors": [[190, 215, 235], [140, 170, 200]], "horizon": 0.55}
    elif any(w in t for w in ["indoor", "temple", "cave", "inside"]):
        bg = {"type": "indoor", "colors": [[70, 55, 45], [130, 100, 80]], "horizon": 0.55}
    elif any(w in t for w in ["fire", "campfire", "flame", "burn"]):
        bg = {"type": "sunset", "colors": [[175, 70, 25], [75, 25, 10]], "horizon": 0.55}
    elif any(w in t for w in ["desert", "sand", "egypt"]):
        bg = {"type": "gradient", "colors": [[210, 180, 130], [175, 140, 95]], "horizon": 0.55}

    camera_override = None
    if any(w in t for w in ["journey", "across", "sail", "travel", "crossing"]):
        camera_override = "pan_right"
    elif any(w in t for w in ["rise", "rises", "ascend", "above"]):
        camera_override = "dolly_in"
    elif any(w in t for w in ["observe", "watch", "stare", "gaze", "look"]):
        camera_override = "ken_burns_in"
    if camera_override:
        camera = camera_override

    # ── Elements ──
    elements = []
    added_types = set()
    rng = random.Random(scene_num * 9973 + total * 7919)
    density = arc_density[phase]

    def add(etype, x=None, y=None, scale=None, fill=None):
        if etype in added_types and len([e for e in elements if e["type"] == etype]) >= 2:
            return
        added_types.add(etype)
        elements.append({
            "type": etype,
            "x": x if x is not None else round(rng.uniform(0.15, 0.85), 2),
            "y": y if y is not None else round(rng.uniform(0.25, 0.75), 2),
            "scale": scale if scale is not None else round(rng.uniform(0.6, 1.5), 1),
            "fill": fill if fill else [rng.randint(80, 255) for _ in range(3)],
        })

    # ── Detect scene type for element generation ──
    def kw_count(keywords, text):
        """Count how many distinct keywords appear as whole words in text."""
        import re as _re
        return sum(1 for w in keywords if _re.search(r'\b' + _re.escape(w) + r'\b', text))

    type_scores = [
        ("diagram",     ["tilt", "degree", "23.5", "axis", "orbit", "angle", "direct sunlight", "less direct", "how it works", "structure", "anatomy", "labeled"]),
        ("timeline",    ["timeline", "years ago", "centuries", "generation after generation", "over thousands", "eventually", "over time", "history", "evolved", "gradually", "era", "epoch", "age", "period", "ancient", "began"]),
        ("flowchart",   ["leads to", "results in", "because of this", "chain reaction", "cycle repeats", "step", "stage", "phase", "process", "sequence", "progression"]),
        ("map",         ["across the world", "different cultures", "far away", "region", "around the globe", "continent", "country", "territory", "journey", "travel", "migration", "spread"]),
        ("bar_chart",   ["percent", "percentage", "statistics", "proportion", "fraction", "majority", "minority", "most of", "half of", "quarter", "how many", "how much"]),
        ("pie_chart",   ["share of", "portion", "divide into", "segment", "slice", "distribution", "breakdown"]),
        ("line_graph",  ["increase", "decrease", "rise", "fall", "grow", "decline", "trend", "over time", "over the years", "temperature", "population", "rate"]),
        ("cycle_diagram", ["cycle", "repeats", "circular", "loop", "recurring", "comes back", "turns around", "goes around", "rotates"]),
        ("venn_diagram", ["both", "in common", "shared", "similarities", "differences", "compare and contrast", "unlike", "on one hand", "on the other"]),
        ("comparison",  ["before and after", "compared to", "versus", "rather than", "instead of", "on the left", "on the right", "between two", "either way"]),
        ("network_diagram", ["connected", "linked", "network", "relation", "connection", "interconnected", "web of", "links to", "nodes"]),
        ("tree_diagram",   ["classification", "category", "divided into", "branches", "subgroup", "hierarchy", "descends from", "evolved from"]),
        ("histogram",   ["distribution", "bell curve", "normal distribution", "frequency", "range of", "spread of", "concentration"]),
        ("scatter_plot", ["correlation", "related to", "corresponds with", "relationship between", "associated with", "plotted"]),
    ]
    best_type, best_score = "story", 0
    for stype, kws in type_scores:
        score = kw_count(kws, t)
        if score > best_score:
            best_type, best_score = stype, score
    scene_type = best_type

    # ── Generate elements appropriate to scene type ──
    words = [w for w in re.findall(r'\b\w+\b', t.lower()) if len(w) > 3]
    unique_words = list(dict.fromkeys(words))

    def pick(n, items):
        return items[:n] if len(items) >= n else items + (items * (n // len(items) + 1))[:n - len(items)]

    if scene_type == "diagram":
        top_words = pick(3, unique_words[:6])
        title = f"How {' & '.join(w.capitalize() for w in top_words[:2])} Work" if len(top_words) >= 2 else f"Anatomy of {top_words[0].capitalize()}"
        elements = [
            {"type": "text", "x": 0.5, "y": 0.045, "text": title, "font_size": 26, "fill": [40, 35, 30]},
        ]
        cx, cy = 0.5, 0.42
        elements.append({"type": "circle", "x": cx, "y": cy, "radius": 55, "fill": [220, 230, 240, 100], "stroke": [100, 120, 140, 180], "stroke_width": 2})
        for i, w in enumerate(top_words):
            angle = math.radians(i * 360 / max(len(top_words),1) - 90)
            lx = cx + math.cos(angle) * 0.14
            ly = cy + math.sin(angle) * 0.14
            elements.append({"type": "circle", "x": lx, "y": ly, "radius": 4, "fill": [180, 120, 60, 220]})
            elements.append({"type": "line", "x": cx + math.cos(angle)*0.06, "y": cy + math.sin(angle)*0.06, "x2": lx - math.cos(angle)*0.01, "y2": ly - math.sin(angle)*0.01, "stroke": [140, 130, 120, 150], "stroke_width": 1})
            elements.append({"type": "text", "x": lx + 0.03, "y": ly - 0.015, "text": w.capitalize(), "font_size": 15, "fill": [60, 55, 50], "align": "left"})
        elements.append({"type": "text", "x": 0.5, "y": 0.88, "text": f"Key: {' | '.join(w.capitalize() for w in top_words)}", "font_size": 13, "fill": [100, 95, 90]})

    elif scene_type == "timeline":
        el = [
            {"type": "text", "x": 0.5, "y": 0.04, "text": "Timeline of Events", "font_size": 24, "fill": [40, 35, 30]},
            {"type": "line", "x": 0.22, "y": 0.14, "x2": 0.22, "y2": 0.88, "stroke": [120, 110, 100, 180], "stroke_width": 3},
        ]
        timeline_entries = []
        numbers = re.findall(r'(\d[\d,]*)\s*(million|billion|thousand|hundred)?\s*(years?|centur|decade|era)', t.lower())
        for num, unit, kind in numbers[:5]:
            label = f"{num} {unit or ''} {kind}".strip()
            timeline_entries.append((label, f"Significant event", len(timeline_entries)))
        if not timeline_entries:
            phrases = ["Beginning", "Early Period", "Middle Period", "Later Period", "Present Day"]
            for i, p in enumerate(phrases[:5]):
                timeline_entries.append((f"Stage {i+1}", p, i))
        spacing = 0.70 / max(len(timeline_entries), 1)
        for i, (date, desc, _) in enumerate(timeline_entries):
            y = 0.16 + (i + 0.5) * spacing
            el.append({"type": "circle", "x": 0.22, "y": y, "radius": 5, "fill": [180, 120, 60, 200]})
            el.append({"type": "text", "x": 0.28, "y": y - 0.012, "text": date, "font_size": 16, "fill": [100, 80, 60], "align": "left"})
            el.append({"type": "text", "x": 0.28, "y": y + 0.020, "text": desc, "font_size": 13, "fill": [140, 130, 120], "align": "left"})
        elements = el

    elif scene_type == "flowchart":
        steps = pick(4, unique_words[:5])
        step_labels = [f"Step {i+1}:\n{s.capitalize()}" for i, s in enumerate(steps)]
        elements = [
            {"type": "text", "x": 0.5, "y": 0.03, "text": f"How {' & '.join(s.capitalize() for s in steps[:2])} Happens", "font_size": 22, "fill": [40, 35, 30]},
        ]
        box_w, box_h, gap = 0.26, 0.09, 0.12
        start_y = 0.16
        for i, step in enumerate(step_labels):
            by = start_y + i * (box_h + gap)
            elements.append({"type": "rect", "x": 0.5, "y": by + box_h / 2, "width": box_w * 1080, "height": box_h * 720, "rx": 8, "fill": [220 + (15 if i % 2 else 0), 235 + (10 if i % 2 else 0), 245 + (10 if i % 2 else 0)], "stroke": [100 + i * 20, 130 + i * 10, 160], "stroke_width": 2})
            elements.append({"type": "text", "x": 0.5, "y": by + box_h / 2, "text": step, "font_size": 15, "fill": [50, 50, 60]})
            if i < len(step_labels) - 1:
                next_y = by + box_h
                elements.append({"type": "arrow", "x": 0.5, "y": next_y, "x2": 0.5, "y2": next_y + gap - 0.01, "stroke": [100, 130, 160, 200], "stroke_width": 2})

    elif scene_type == "map":
        location_kws = [w for w in unique_words if w[0].isupper() or w in ("region","land","continent","country","world","globe","territory","province","island","desert","forest","mountain","valley","river","ocean","sea","city","town","village")]
        markers = location_kws[:4] if location_kws else ["Region A", "Region B", "Region C"]
        el = [
            {"type": "text", "x": 0.5, "y": 0.05, "text": f"Map: {markers[0].capitalize()}" if markers else "Map", "font_size": 24, "fill": [40, 35, 30]},
        ]
        continents = [(0.28, 0.46, 100, 80), (0.57, 0.40, 140, 70), (0.12, 0.50, 60, 50), (0.62, 0.60, 50, 40)]
        for cx, cy, cw, ch in continents:
            el.append({"type": "ellipse", "x": cx, "y": cy, "width": cw, "height": ch, "fill": [180, 200, 160, 200], "stroke": [140, 160, 120], "stroke_width": 2})
        marker_positions = [(0.30, 0.44), (0.40, 0.52), (0.25, 0.55), (0.55, 0.48)]
        for i, name in enumerate(markers):
            mx, my = marker_positions[min(i, len(marker_positions)-1)]
            el.append({"type": "circle", "x": mx, "y": my, "radius": 5, "fill": [220, 80, 60, 200]})
            el.append({"type": "text", "x": mx + 0.025, "y": my - 0.015, "text": name.capitalize(), "font_size": 14, "fill": [60, 55, 50], "align": "left"})
        el.append({"type": "text", "x": 0.5, "y": 0.90, "text": f"Key locations: {', '.join(m.capitalize() for m in markers)}", "font_size": 14, "fill": [80, 75, 70]})
        elements = el

    elif scene_type == "bar_chart":
        items = unique_words[:5]
        title = " vs ".join(w.capitalize() for w in items[:2]) if items else "Data"
        data = [(w.capitalize(), rng.uniform(0.15, 0.95)) for w in items]
        elements = [{"type": "bar_chart", "x": 0.5, "y": 0.48, "data": data, "chart_w": 500, "chart_h": 320, "fill": [70, 130, 180], "chart_title": title}]

    elif scene_type == "pie_chart":
        items = unique_words[:6]
        total = sum(range(len(items), 0, -1))
        if total == 0: total = 1
        data = [(w.capitalize(), (len(items) - i) / total) for i, w in enumerate(items)]
        elements = [{"type": "pie_chart", "x": 0.45, "y": 0.48, "data": data, "radius": 130}]

    elif scene_type == "line_graph":
        n_pts = min(6, max(3, len(unique_words)))
        data = [(f"T{i+1}", rng.uniform(0.1, 0.9)) for i in range(n_pts)]
        elements = [{"type": "line_graph", "x": 0.5, "y": 0.48, "data": data, "chart_w": 480, "chart_h": 300, "fill": [200, 80, 60]}]

    elif scene_type == "cycle_diagram":
        steps = pick(4, unique_words[:6])
        elements = [{"type": "cycle_diagram", "x": 0.5, "y": 0.5, "steps": steps, "radius": 130}]

    elif scene_type == "venn_diagram":
        all_items = unique_words[:6]
        mid = len(all_items) // 2
        left = all_items[:mid] if mid > 0 else ["A"]
        right = all_items[mid:] if len(all_items) > mid else ["B"]
        left_title = " ".join(left[:2]).capitalize() if left else "Group A"
        right_title = " ".join(right[:2]).capitalize() if right else "Group B"
        common = [w for w in left if w in right] or ["Shared"]
        elements = [{"type": "venn_diagram", "x": 0.5, "y": 0.5, "left_label": left_title, "right_label": right_title, "common_label": common[0].capitalize(), "radius": 100}]

    elif scene_type == "comparison":
        all_items = unique_words[:8]
        mid = len(all_items) // 2
        left = [w.capitalize() for w in all_items[:mid]]
        right = [w.capitalize() for w in all_items[mid:]]
        elements = [{"type": "comparison", "x": 0.5, "y": 0.48, "left_title": "Before", "right_title": "After", "left_items": left or ["One"], "right_items": right or ["Two"]}]

    elif scene_type == "network_diagram":
        items = unique_words[:8]
        n = len(items)
        edges = [(i, (i + 1) % n) for i in range(n)] + ([(0, n // 2)] if n > 2 else [])
        elements = [{"type": "network_diagram", "x": 0.5, "y": 0.48, "nodes": items, "edges": edges, "radius": 28}]

    elif scene_type == "tree_diagram":
        items = unique_words[:10]
        levels = [["Root"]] + [[w.capitalize()] for w in items[:2]] + [[w.capitalize() for w in items[2:5]]]
        elements = [{"type": "tree_diagram", "x": 0.5, "y": 0.48, "levels": levels}]

    elif scene_type == "histogram":
        items = unique_words[:8]
        data = [(w.capitalize()[:4], rng.uniform(0.1, 1.0)) for w in items]
        elements = [{"type": "histogram", "x": 0.5, "y": 0.48, "data": data, "chart_w": 480, "chart_h": 300, "fill": [70, 130, 180]}]

    elif scene_type == "scatter_plot":
        items = unique_words[:8]
        points = [(w.capitalize(), rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)) for w in items]
        elements = [{"type": "scatter_plot", "x": 0.5, "y": 0.48, "points": points, "chart_w": 480, "chart_h": 320, "fill": [70, 130, 180]}]

    else:
        # ── Story scene: subject-aware composition ──
        elements = _compose_story_scene(t, phase, rng, density)

    # ── Atmosphere ──
    particles = "none"
    star_count = 0
    fog = False

    if scene_type == "story":
        if bg["type"] == "night":
            star_count = rng.randint(15, 45)
            particles = "stars"
        if any(w in t for w in ["snow", "ice", "frozen", "winter"]):
            particles = "snow"
        if any(w in t for w in ["rain", "storm"]):
            particles = "rain"
        if any(w in t for w in ["fog", "mist", "shadow", "underworld"]):
            fog = True
        if phase == "climax" and particles == "none":
            particles = "stars" if bg["type"] == "night" else "rain"

    # ── Title ──
    words = text.split()
    title = " ".join(words[:5]).rstrip(".,!?") if len(words) > 3 else f"Scene {scene_num}"
    if len(title) > 40:
        title = title[:40]

    return {
        "title": title,
        "mood": mood,
        "camera": camera,
        "visual_type": scene_type,
        "visual": {
            "scene_type": scene_type,
            "bg": bg,
            "elements": elements,
            "atmosphere": {"particles": particles, "fog": fog, "star_count": star_count},
        },
    }


def generate_script_from_narration(text: str) -> dict:
    """Split pre-written narration into scenes. Keyword-based visuals — no LLM needed."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    if len(paragraphs) < 4:
        sentences = [s.strip() for s in text.replace('?', '.').replace('!', '.').split('.') if s.strip()]
        sentences = [s + '.' for s in sentences if s]
        paragraphs = []
        chunk = []
        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 3:
                paragraphs.append(' '.join(chunk))
                chunk = []
        if chunk:
            paragraphs.append(' '.join(chunk))

    if len(paragraphs) < 2:
        paragraphs = [text]

    title_words = paragraphs[0].split()[:6]
    title = " ".join(title_words).rstrip(".,!?")

    scenes = []
    for i, para in enumerate(paragraphs):
        scene_num = i + 1
        raw_prompt = para.strip()
        if not raw_prompt:
            continue

        visuals = _infer_visuals(raw_prompt, scene_num, len(paragraphs))

        scene = {
            "scene_num": scene_num,
            "title": visuals["title"],
            "narration": raw_prompt,
            "mood": visuals["mood"],
            "camera": visuals["camera"],
            "visual_type": visuals["visual_type"],
            "visual": visuals["visual"],
        }
        scenes.append(scene)
        vt = scene["visual_type"]
        elems = len(scene["visual"]["elements"])
        print(f"  Scene {scene_num}/{len(paragraphs)}: {vt:10s} {scene['mood']} ({elems} elems)")

    print(f"  Created {len(scenes)} scenes from narration")
    return {"title": title, "scenes": scenes}


def _fallback_script(topic: str) -> dict:
    """Fallback when LLM fails — uses SceneComposer for ANY topic."""
    from src.scene_composer import SceneComposer
    composer = SceneComposer()
    return composer.compose_script(topic, n_scenes=4)


# ═══════════════════════════════════════════════════════════════
#  SCENE RENDERER — stroke-by-stroke progressive reveal
# ═══════════════════════════════════════════════════════════════

def render_scene_frames(scene: dict, scene_duration: float, fps=FPS):
    """Render a scene as progressive frames, producing exactly
    int(scene_duration * fps) frames so video duration matches narration."""
    visual = scene.get("visual", {})
    camera = scene.get("camera", None)
    generator = SketchGenerator(W, H, seed=rng.randint(0, 99999))
    scene_type = visual.get("scene_type", "story")
    elements = visual.get("elements", [])

    target_frames = max(int(scene_duration * fps), 1)

    if not elements:
        img = generator.render_scene(visual)
        return [np.array(img)] * target_frames

    if scene_type != "story":
        # Informational: 3-step fade-in across target_frames
        all_frames = []
        img = generator.render_scene(visual)
        for step in range(3, 0, -1):
            partial = img.copy()
            if step < 3:
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, int(180 - step * 60)))
                partial = Image.alpha_composite(partial.convert("RGBA"), overlay)
            chunk = target_frames // 3 + (1 if step <= target_frames % 3 else 0)
            for _ in range(chunk):
                all_frames.append(np.array(partial.convert("RGB")))
        return all_frames

    # Story: progressive reveal — each step shows more elements
    n_steps = min(target_frames, len(elements))
    base = target_frames // n_steps
    extra = target_frames % n_steps

    all_frames = []
    for step in range(1, n_steps + 1):
        batch = elements[:int(len(elements) * step / n_steps)]
        partial_visual = dict(visual)
        partial_visual["elements"] = batch
        img = generator.render_scene(partial_visual)
        frame_arr = np.array(img)
        if camera:
            from src.cinematic import apply_camera_move
            progress = step / n_steps
            frame_arr = apply_camera_move(frame_arr, progress, camera, W, H)
        count = base + (1 if step <= extra else 0)
        for _ in range(count):
            all_frames.append(frame_arr.copy())
    return all_frames


# ═══════════════════════════════════════════════════════════════
#  VIDEO BUILDER
# ═══════════════════════════════════════════════════════════════

def build_video(script_data: dict, output_path: str):
    scenes = script_data["scenes"]
    title = script_data["title"]

    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"  {len(scenes)} scenes | stroke-by-stroke documentary")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "auto_story"
    temp_dir.mkdir(exist_ok=True)

    # ── 1. Generate narration ──
    print(f"\n[1/4] Generating narration...")
    full_script = " ".join(s["narration"] for s in scenes)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_script, tts_path)
    total_dur = words[-1]["end"] if words else 8.0
    print(f"  {total_dur:.1f}s | {len(words)} words")

    # ── 2. Build timeline ──
    print(f"\n[2/4] Building timeline...")
    timeline = []
    wi = 0
    for i, scene in enumerate(scenes):
        scene_lower = scene["narration"].lower()
        start_wi = wi
        # Match TTS tokens to this scene using word-boundary regex,
        # handling multi-word tokens (e.g. "300 million years") correctly.
        while wi < len(words):
            token_text = words[wi]["text"].lower().strip(".,!?;: ")
            if re.search(rf'\b{re.escape(token_text)}\b', scene_lower):
                wi += 1
            elif wi == start_wi:
                wi += 1  # skip leading silence/punctuation
            else:
                break  # end of this scene's word range
        ws = start_wi if start_wi < len(words) else 0
        we = wi - 1 if wi > start_wi else start_wi
        start_time = words[ws]["start"] if ws < len(words) else 0
        if i < len(scenes) - 1:
            end_time = words[wi]["start"] if wi < len(words) else total_dur
        else:
            end_time = total_dur
        duration = max(end_time - start_time, 0.5)
        timeline.append({
            "start": start_time,
            "end": end_time,
            "word_start": ws,
            "word_end": we,
            "duration": duration,
        })

    # ── 3. Render scenes ──
    print(f"\n[3/4] Rendering {len(scenes)} scenes...")
    TD, ED = 2.5, 2.0
    scene_data = []
    total_frames = 0
    for i, scene in enumerate(scenes):
        sd = timeline[i]["duration"]
        if sd < 0.5: sd = 1.0
        print(f"  Scene {i+1}: {scene.get('title','')[:30]} [{scene.get('mood','')}] ({sd:.1f}s)")
        frames = render_scene_frames(scene, sd)
        tl = timeline[i]
        scene_data.append({"frames": frames, "duration": sd, "timeline": tl})
        total_frames += len(frames)
        print(f"    -> {len(frames)} frames")

    # ── 4. Assemble ──
    print(f"\n[4/4] Assembling video ({total_frames} scene frames)...")

    # Title card
    ti = Image.new("RGB", (W, H), (252, 250, 245))
    td = ImageDraw.Draw(ti)
    ft = _font(42)
    tlines = []
    cur = ""
    for w in title.split():
        test = (cur + " " + w).strip()
        tb = td.textbbox((0, 0), test, font=ft)
        if tb[2] - tb[0] > W - 80:
            tlines.append(cur); cur = w
        else: cur = test
    tlines.append(cur)
    y = H // 2 - 70
    for line in tlines:
        tb = td.textbbox((0, 0), line, font=ft)
        td.text(((W - (tb[2] - tb[0])) // 2, y), line, font=ft, fill=(40, 35, 30))
        y += 70
    fsub = _font(20)
    sub = "AN ILLUSTRATED DOCUMENTARY"
    tb = td.textbbox((0, 0), sub, font=fsub)
    td.text(((W - (tb[2] - tb[0])) // 2, H - 160), sub, font=fsub, fill=(140, 130, 120))
    title_arr = np.array(ti)

    # Build frame map — extend last scene to cover full audio
    frame_map = []
    cursor = TD
    for sd in scene_data:
        sd["start"] = cursor
        sd["end"] = cursor + sd["duration"]
        sd["ft"] = sd["duration"] / max(len(sd["frames"]), 1)
        frame_map.append(sd)
        cursor += sd["duration"]
    # Stretch last scene's end to match total audio duration
    audio_end = TD + total_dur
    if frame_map and cursor < audio_end:
        frame_map[-1]["end"] = audio_end
        cursor = audio_end
    vdur = cursor + ED

    bg_arr = np.full((H, W, 3), 248, dtype=np.uint8)

    def make_frame(t):
        if t < TD:
            p = t / TD
            a = int(255 * p * p * (3 - 2 * p))
            if a < 255:
                return ((bg_arr.astype(np.float32) * (255 - a) + title_arr.astype(np.float32) * a) / 255).astype(np.uint8)
            return title_arr
        tr = t - TD
        active = None
        for sd in frame_map:
            if sd["start"] <= t < sd["end"]:
                active = sd; break
        if active is None:
            for sd in reversed(frame_map):
                if t >= sd["end"]:
                    active = sd; break
        if active is None:
            return bg_arr
        lt = t - active["start"]
        fi = min(int(lt / active["ft"]), len(active["frames"]) - 1)
        base = active["frames"][fi].copy()
        tl = active["timeline"]
        tr_abs = t - TD
        cap = Image.fromarray(base)
        cd = ImageDraw.Draw(cap)
        ov = Image.new("RGBA", (W, 90), (0, 0, 0, 180))
        cap.paste(ov, (0, H - 100), ov)
        fcap = _font(28)
        fhl = _font(32)
        widx = list(range(tl["word_start"], min(tl["word_end"] + 1, len(words))))
        cw = -1
        for wi in widx:
            if words[wi]["start"] <= tr_abs:
                cw = wi; break
        x, lh_base = 20, 40
        for wi in widx:
            wt = words[wi]["text"]
            f = fhl if wi == cw else fcap
            d = " " + wt + " "
            bb = cd.textbbox((0, 0), d, font=f)
            ww = bb[2] - bb[0]
            if x + ww > W - 20:
                x = 20; lh_base += 40
            if wi == cw:
                cd.rounded_rectangle([x - 4, lh_base - 2, x + ww + 4, lh_base + 38], radius=5, fill=(200, 80, 60, 200))
            cd.text((x, lh_base), d, font=f, fill=(255, 255, 255) if wi != cw else (255, 220, 80))
            x += ww
        return np.array(cap)

    clip = VideoClip(make_frame, duration=vdur)

    audio = AudioFileClip(str(tts_path)).with_start(TD)
    music = list(config.MUSIC_DIR.glob("*.mp3"))
    if music:
        try:
            m = AudioFileClip(str(random.choice(music))).with_duration(vdur).with_volume_scaled(0.04)
            audio = CompositeAudioClip([audio, m])
        except:
            pass

    try:
        ec = subscribe_end_card(np.full((H, W, 3), 240, dtype=np.uint8), ED)
        ec = ec.with_start(cursor)
        final = CompositeVideoClip([clip, ec], size=config.SHORTS_SIZE).with_audio(audio)
    except Exception as e:
        print(f"  End card error: {e}")
        final = clip.with_audio(audio)

    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="fast", ffmpeg_params=["-movflags", "+faststart", "-crf", "22"], logger=None)
    final.close()
    print(f"\n  Done in {time.time() - t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    script = None
    custom_title = ""
    script_file = None

    # Parse --title flag
    args = sys.argv[1:]
    if "--title" in args:
        idx = args.index("--title")
        if idx + 1 < len(args):
            custom_title = args[idx + 1]
            args = args[:idx] + args[idx+2:]

    if args:
        arg = args[0]
        # .json file → load pre-made script
        if arg.endswith(".json"):
            path = Path(arg)
            if path.exists():
                print(f"Loading script from: {path}")
                with open(path, encoding="utf-8") as f:
                    script = json.load(f)
                print(f"  Loaded: {script.get('title', 'untitled')} ({len(script.get('scenes', []))} scenes)")
        # .txt file → pre-written narration, auto-generate visuals
        elif arg.endswith(".txt"):
            script_file = arg
            path = Path(arg)
            if path.exists():
                text = path.read_text(encoding="utf-8")
                print(f"Loaded narration ({len(text)} chars from {path})")
                print("\n[1/4] Generating scenes from narration...")
                script = generate_script_from_narration(text)
        else:
            topic = " ".join(args)
            print(f"Topic: {topic}")
            print("\n[1/4] Generating LLM script...")
            script = generate_script(topic)
    else:
        topic = "how the printing press changed the world"
        print(f"Topic: {topic}")
        print("\n[1/4] Generating LLM script...")
        script = generate_script(topic)

    if script:
        if custom_title:
            script["title"] = custom_title
        for s in script.get("scenes", []):
            ne = len(s.get("visual", {}).get("elements", []))
            print(f"  {s.get('title','?')[:35]}: {s['narration'][:50]}... [{s.get('mood','')}] ({ne} elements)")
        safe = re.sub(r'[^\w]+', '_', script.get('title', 'untitled').lower())[:40]
        out = config.OUTPUT_DIR / f"auto_story_{safe}.mp4"
        build_video(script, out)


if __name__ == "__main__":
    main()
