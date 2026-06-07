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
    "mammal":        {"type":"animal","tags":["mammal","deer","wolf","fox","bear","rabbit","squirrel","horse","cattle","cow","bull","calf","ox","sheep","lamb","goat","pig","hog","boar","bison","moose","elk","donkey","mule","llama","alpaca","camel","zebra","giraffe","rhino","rhinoceros","hippo","hippopotamus","elephant","lion","tiger","leopard","panther","jaguar","cheetah","hyena","dog","kitten","puppy","mouse","mice","rat","beaver","otter","hedgehog","bat","kangaroo","koala","sloth","raccoon","skunk","weasel","badger","mole","vole","shrew","opossum","porcupine","armadillo","anteater","monkey","ape","gorilla","chimpanzee","orangutan","gibbon","baboon","mandrill","lemur","panda","bamboo"],"y":"ground"},
    "cat":           {"type":"cat","tags":["cat","kitten","feline","meow","purr","whisker"],"y":"ground"},
    "mouse":         {"type":"mouse","tags":["mouse","mice","rodent","pest","vermin","squeak"],"y":"ground"},
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
    "sun":           {"type":"sun","tags":["sun","sunlight","sunshine","sunrise","sunset","dawn","dusk","morning","daylight","solstice"],"y":"sky"},
    "moon":          {"type":"moon","tags":["moon","crescent","lunar","full moon","half moon","night"],"y":"sky"},
    "star":          {"type":"star","tags":["star","stars","night sky","constellation","galaxy","universe","celestial","astronomy"],"y":"sky","count":8,"small":1},
    "cloud":         {"type":"cloud","tags":["cloud","clouds","sky","atmosphere","weather","overcast","fog","mist","haze","smoke"],"y":"sky"},
    "comet":         {"type":"comet","tags":["comet","meteor","shooting star","asteroid","tail","streak","fiery","glowing"],"y":"sky","special":1},
    "lightning":     {"type":"lightning","tags":["lightning","thunder","storm","bolt","electrical"],"y":"sky"},
    "rainbow":       {"type":"rainbow","tags":["rainbow","arc","prism"],"y":"sky"},
    # Structures
    "building":      {"type":"building","tags":["house","home","hut","cabin","building","structure","temple","pyramid","monument","palace","castle","fort","wall","city","village","town","settlement","civilization"],"y":"ground"},
    "tent":          {"type":"tent","tags":["tent","camp","campsite","shelter","teepee","nomad"],"y":"ground"},
    "bridge":        {"type":"bridge","tags":["bridge","crossing","causeway","overpass"],"y":"ground"},
    "path":          {"type":"path","tags":["path","trail","road","walkway","walk","walking","street"],"y":"ground"},
    # Objects
    "boat":          {"type":"ship","tags":["boat","ship","sail","vessel","canoe","raft","ark","voyage","explore","navigation"],"y":"water"},
    "book":          {"type":"book","tags":["book","scroll","manuscript","document","papyrus","knowledge","story","tale","record"],"y":"ground"},
    "compass":       {"type":"compass","tags":["compass","astrolabe","sextant","navigation","direction"],"y":"ground"},
    "globe":         {"type":"globe","tags":["globe","earth","planet","sphere","orb"],"y":"ground"},
    "crystal":       {"type":"crystal","tags":["crystal","gem","jewel","diamond","ruby","emerald","mineral"],"y":"ground"},
    "tool":          {"type":"tool","tags":["tool","axe","hammer","spear","knife","sword","bow","arrow","weapon","instrument","artifact"],"y":"ground"},
    "pottery":       {"type":"pottery","tags":["pot","pottery","vase","jar","bowl","urn","amphora","container"],"y":"ground"},
    "throne":        {"type":"throne","tags":["throne","seat","chair","bench","stool"],"y":"ground"},
    "altar":         {"type":"altar","tags":["altar","shrine","sacrifice","offering","ritual"],"y":"ground"},
    "torch":         {"type":"torch","tags":["torch","lantern","lamp","candle","light","illuminate","glow"],"y":"ground"},
    # Abstract - silence, shadow, sound, time
    "shadow":        {"type":"shadow","tags":["shadow","darkness","shade","gloom","eclipse","dark","darken"],"y":"sky","special":1},
    "sound":         {"type":"sound_wave","tags":["sound","hear","buzzing","noise","roar","cry","whisper","echo","quiet","loud"],"y":"air","special":1},
    "wind":          {"type":"wind","tags":["wind","breeze","gust","atmosphere","breathe","breath","warm","heavy","humid"],"y":"air"},
    # Emotional / narrative scene types
    "warning":       {"type":"warning","tags":["warning","omen","bad omen","portend","danger","threat"],"y":"sky","special":1},
    "question":      {"type":"question","tags":["nobody knows","no one knows","don't know","unknown","mystery","mysterious","wonder","curious","puzzl","confus"],"y":"air","special":1},
    "predictable":   {"type":"predictable","tags":["predictable","familiar","exactly where","yesterday","same","always","routine","ordinary","normal","expected"],"y":"sky","special":1},
    "alien":         {"type":"alien","tags":["feels alien","unfamiliar","foreign","otherworldly","surreal"],"y":"ground","special":1},
    "silence":       {"type":"silence","tags":["silence","silent","no birds","no mammals","no humans","no dinosaur","no sound"],"y":"ground","special":1},
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
    "mask":         {"type":"mask","tags":["mask","disguise","costume","veil","theater"],"y":"ground"},
    # Military
    "tank":         {"type":"tank","tags":["tank","armored","armored vehicle","military vehicle","war machine","battalion"],"y":"ground"},
    "explosion":    {"type":"explosion","tags":["explosion","explode","blast","boom","detonate","burst","bomb","missile","grenade","shell"],"y":"air","special":1},
    # Sci-fi
    "ufo":          {"type":"ufo","tags":["ufo","unidentified","flying saucer","spaceship","extraterrestrial","alien ship","craft"],"y":"sky","special":1},
    "alien_creature":{"type":"alien_creature","tags":["alien being","extraterrestrial","little green","grey alien","space alien","martian","venusian","alien craft"],"y":"ground","special":1},
    # Abstract concepts
    "atom":          {"type":"atom","tags":["atom","molecule","nucleus","electron","proton","neutron","particle","microscopic","atomic"],"y":"air"},
    "dna":           {"type":"dna","tags":["dna","gene","genetic","chromosome","helix","heredity","double helix"],"y":"air"},
    "heart":         {"type":"heart","tags":["heart","cardiac","blood","valentine","love","passion"],"y":"ground"},
    "infinity":      {"type":"infinity","tags":["infinity","infinite","boundless","limitless"],"y":"air"},
    "target":        {"type":"target","tags":["target","aim","goal","bullseye","focus","concentrate"],"y":"ground"},
    "puzzle":        {"type":"puzzle","tags":["puzzle","mystery","enigma","problem","challenge","riddle","conundrum"],"y":"ground"},
    "scales":        {"type":"scales","tags":["scales","balance","justice","weigh","measure","equal","fair","equality"],"y":"ground"},
    # Sci-fi
    "astronaut":     {"type":"astronaut","tags":["astronaut","spaceman","cosmonaut","space traveler","space suit"],"y":"ground"},
    "spaceship":     {"type":"spaceship","tags":["spaceship","starship","spacecraft","rocket","ship","space travel"],"y":"sky"},
    # Objects
    "hourglass":     {"type":"hourglass","tags":["hourglass","sand","timer","countdown"],"y":"ground"},
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
    # Sports & recreation
    "ball":          {"type":"ball","tags":["ball","football","soccer","basketball","volleyball","baseball","tennis","cricket","sports","game","playground","play","playing"],"y":"ground"},
    # Devices
    "telescope":     {"type":"telescope","tags":["telescope","binocular","binoculars","spyglass","magnify","stargaze","lookout"],"y":"ground"},
    "window":        {"type":"window","tags":["window","pane","glass","view","porthole"],"y":"ground"},
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
    "play":   {"tags":["play","playing","kick","throw","catch","hit","chase","sport","game","practice"],"effect":"run_pose"},
}

_POSITION_ZONES = {
    "sky":     {"y_range": (0.06, 0.30), "size": 0.7},
    "air":     {"y_range": (0.12, 0.40), "size": 0.8},
    "horizon": {"y_range": (0.50, 0.62), "size": 1.0},
    "ground":  {"y_range": (0.52, 0.75), "size": 1.0},
    "water":   {"y_range": (0.68, 0.82), "size": 0.9},
}

def _tag_match(tag, text):
    """Match tag with optional regular plural suffix (s, es)."""
    if tag.endswith('s') or tag.endswith('es'):
        return re.search(rf'\b{re.escape(tag)}\b', text)
    return re.search(rf'\b{re.escape(tag)}(?:s|es)?\b', text)


def _extract_entities(text):
    """Extract relevant entities from narration text, limited to top 5 by relevance."""
    t = text.lower()
    found = {}
    for key, info in _ENTITY_MAP.items():
        for tag in info["tags"]:
            if _tag_match(tag, t):
                # Skip if tag appears to be a proper name (preceded by title, with optional middle word)
                if re.search(
                    rf'\b(?:dr|mr|mrs|ms|prof|capt|sgt|sir|lady|lord|queen|king|prince|princess)\.?\s+(?:\w+\s+)?{re.escape(tag)}\b',
                    t,
                ):
                    continue
                count = info.get("count", 1)
                if any(re.search(rf'\b{w}\b', t) for w in ["all","many","every","dozen","hundred","thousand","million","billion","countless","numerous","several"]):
                    count = max(count, info.get("count", 1) * 2)
                if key in ("crowd","people","population","tribe","clan","family","civilization","culture","society","nation","public","group"):
                    count = max(count, 4)
                found[key] = {"info": info, "count": count}
                break

    # Score entities by relevance and keep top 5
    scored = []
    for key, data in found.items():
        info = data["info"]
        matching_tags = sum(1 for tag in info["tags"] if _tag_match(tag, t))
        total_tags = len(info["tags"])
        score = matching_tags / max(total_tags, 1)

        # Human entity: increase count for distinct role words
        if key == "human":
            role_words = ["man","woman","child","boy","girl","baby","elder","parent","mother","father","son","daughter","brother","sister","friend","enemy","stranger","teacher","student","doctor","nurse","soldier","king","queen","prince","princess","hero","villain","witness","explorer","pilgrim","merchant","artist","musician","poet","writer","scholar"]
            matching_roles = sum(1 for w in role_words if re.search(rf'\b{w}\b', t))
            if matching_roles > 1:
                data["count"] = max(data["count"], matching_roles)

        # Bonus if entity name or key appears literally in text
        if re.search(rf'\b{re.escape(key.replace("_", " "))}\b', t):
            score += 1.0
        # Penalize if matched only by a short generic tag (≤4 chars)
        short_tag_matches = sum(1 for tag in info["tags"] if len(tag) <= 4 and _tag_match(tag, t))
        if short_tag_matches > 0 and matching_tags == 1:
            score -= 0.5
        scored.append((key, data, score))

    scored.sort(key=lambda x: -x[2])
    return {key: data for key, data, score in scored[:5]}

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
        elif etype == "cat":
            sc2 = sc * 0.6
            elems.append({"type":"ellipse","x":x,"y":y-0.01,"width":int(20*sc2),"height":int(14*sc2),"fill":list(c)+[220],"stroke":[c[0]-20,c[1]-20,c[2]-20,180],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.015,"y":y-0.03,"radius":int(7*sc2),"fill":list(c)+[220]})
            elems.append({"type":"polygon","points":[[round(x+0.035,2),round(y-0.03,2)],[round(x+0.045,2),round(y-0.045,2)],[round(x+0.04,2),round(y-0.02,2)]],"fill":[c[0],c[1],c[2],200]})
            elems.append({"type":"polygon","points":[[round(x-0.005,2),round(y-0.03,2)],[round(x-0.015,2),round(y-0.045,2)],[round(x-0.01,2),round(y-0.02,2)]],"fill":[c[0],c[1],c[2],200]})
            elems.append({"type":"line","x":x+0.002,"y":y+0.025,"x2":x+0.04,"y2":y+0.015,"stroke":[c[0]-20,c[1]-20,c[2]-20,180],"stroke_width":1})
            elems.append({"type":"line","x":x+0.035,"y":y+0.025,"x2":x+0.04,"y2":y+0.015,"stroke":[c[0]-20,c[1]-20,c[2]-20,180],"stroke_width":1})
            elems.append({"type":"circle","x":x+0.018,"y":y-0.032,"radius":1,"fill":[40,180,40,200]})
            elems.append({"type":"circle","x":x+0.025,"y":y-0.032,"radius":1,"fill":[40,180,40,200]})
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
        elif etype == "ball":
            elems.append({"type":"circle","x":x,"y":y,"radius":int(14*sc),"fill":[c[0] or 220,c[1] or 180,c[2] or 60,220],"stroke":[80,60,40,180],"stroke_width":2})
        elif etype == "telescope":
            elems.append({"type":"telescope","x":x,"y":y,"scale":round(sc*0.9,1),"fill":[c[0] or 120,c[1] or 80,c[2] or 60]})
        elif etype == "window":
            elems.append({"type":"rect","x":x,"y":y,"width":int(22*sc),"height":int(28*sc),"fill":[200,220,255,180],"stroke":[100,120,140,200],"stroke_width":2,"rx":2})
            elems.append({"type":"line","x":x,"y":y-0.015,"x2":x,"y2":y+0.015,"stroke":[100,120,140,150],"stroke_width":1})
            elems.append({"type":"line","x":x-0.012,"y":y,"x2":x+0.012,"y2":y,"stroke":[100,120,140,150],"stroke_width":1})
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

    # 3. Apply scene layout adjustments based on action context
    _adjust_scene_layout(elements, actions, t, rng)

    # 4. Add ambient fill if scene feels bare
    _add_ambient_elements(elements, phase, rng)

    return elements


def _adjust_scene_layout(elements, actions, text, rng):
    """Reposition elements so the scene looks coherent for the action context.
    
    When action words suggest interaction between entities (e.g. playing, watching),
    adjust positions to create a meaningful composition instead of random scatter."""
    if not actions:
        return

    action_names = [a["name"] for a in actions]
    humans = [e for e in elements if e.get("type") == "human"]
    balls = [e for e in elements if e.get("type") == "circle" and 10 < e.get("radius", 0) < 20]
    buildings = [e for e in elements if e.get("type") == "building"]
    telescopes = [e for e in elements if e.get("type") == "telescope"]

    # Playing: group humans together, put ball among them
    if "playing" in text.split() or "football" in text.split() or any(a in ("play", "walk", "run", "gather") for a in action_names):
        if humans:
            group_x = 0.30
            for i, h in enumerate(humans):
                h["x"] = round(group_x + i * 0.15, 2)
                h["y"] = round(0.62 + rng.uniform(-0.04, 0.04), 2)
            if balls:
                mid = len(humans) // 2
                bx = humans[mid]["x"] if mid < len(humans) else 0.40
                by = 0.60
                balls[0]["x"] = round(bx + 0.05, 2)
                balls[0]["y"] = round(by, 2)

    # Watching: place watcher near building, orient toward action
    if any(a == "watch" for a in action_names):
        if humans and telescopes:
            watcher = humans[-1]
            watcher["x"] = 0.78
            watcher["y"] = 0.50
            telescopes[0]["x"] = 0.83
            telescopes[0]["y"] = 0.48
        if buildings:
            buildings[0]["x"] = 0.82
            buildings[0]["y"] = 0.52


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

    # Regex-based pattern detection for types not easily captured by keywords
    if re.search(r'\bnot\b\s+\w+\s+\w+\s+\w+\s+\bbut\b', t) or re.search(r'\binstead of\b', t) or re.search(r'\brather than\b', t):
        comp_score = kw_count(["not", "but", "instead", "rather", "unlike", "versus"], t)
        if comp_score > best_score:
            best_type, best_score = "comparison", comp_score

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


# ──────────────────────────────────────────────────────
# LOCAL SEMANTIC ENGINE — Pure Python, zero API calls
# Comprehensive entity map (300+), biome detection,
# narrative arc awareness, multi-word phrase matching.
# ──────────────────────────────────────────────────────

# Biome signatures: (keyword, biome_name, bg_type, base_colors, ground_color)
_BIOMES = [
    (["desert", "sand", "dune", "arid", "cactus", "scorpion", "lizard", "coyote", "vulture", "sun-baked", "cracked earth", "dry", "dust", "blazing", "sahara", "gobi", "mirage", "oasis", "nomad", "camel"], "desert", "sunset", [(220, 160, 80), (190, 120, 60), (160, 90, 40)], (140, 100, 50)),
    (["ocean", "oceans", "sea", "seas", "deep", "wave", "waves", "shore", "beach", "tide", "surf", "coast", "marine", "underwater", "coral", "reef", "dolphin", "whale", "jellyfish", "anemone", "gills", "fins", "aquatic", "submarine", "nautical", "sailor", "mariner", "lighthouse", "anchor", "sail"], "ocean", "ocean", [(40, 100, 200), (20, 60, 150)], None),
    (["night", "midnight", "moon", "star", "darkness", "shadow", "eclipse", "constellation", "aurora", "twilight"], "night", "night", [(5, 3, 25), (15, 10, 40), (30, 25, 60)], (10, 8, 25)),
    (["sunset", "dusk", "dawn", "sunrise", "golden", "evening", "twilight", "afterglow"], "sunset", "sunset", [(230, 120, 70), (200, 100, 90), (150, 70, 100), (80, 50, 80)], (50, 40, 30)),
    (["forest", "forests", "woods", "jungle", "rainforest", "tree", "canopy", "thicket", "grove", "bush", "shrub", "wilderness"], "forest", "forest", [(120, 160, 80), (60, 100, 50)], (40, 70, 30)),
    (["snow", "ice", "arctic", "antarctic", "tundra", "glacier", "frozen", "blizzard", "winter", "cold", "frost", "hail", "north"], "arctic", "gradient", [(200, 215, 230), (180, 195, 210), (160, 175, 190)], (200, 210, 220)),
    (["mountain", "peak", "summit", "cliff", "ridge", "valley", "canyon", "gorge", "rock", "boulder", "stone", "hill", "highland"], "mountain", "gradient", [(140, 160, 200), (110, 130, 170), (80, 100, 130)], (90, 80, 70)),
    (["cave", "cavern", "underground", "subterranean", "grotto", "tunnel", "mine", "dungeon"], "cave", "indoor", [(50, 40, 35), (30, 25, 20)], None),
    (["city", "town", "village", "urban", "street", "building", "skyscraper", "neon", "lantern", "market", "temple", "palace", "castle", "fortress"], "city", "gradient", [(180, 180, 190), (140, 140, 160), (100, 100, 120)], (60, 60, 70)),
    (["sky", "skies", "cloud", "clouds", "flight", "flights", "flying", "soar", "soaring", "aerial", "airborne", "glide", "gliding", "wing", "wings", "bird", "birds", "hawk", "eagle", "falcon", "swift", "swifts", "flock", "flocks", "migration", "migrations", "migrate", "migrates", "migrated", "migrating", "atmosphere", "altitude", "hover", "hovering", "air", "breeze", "wind", "winds", "updraft", "thermals", "soars", "glides", "glided", "soared"], "sky", "sky", [(160, 200, 240), (200, 220, 245), (230, 240, 250)], (120, 180, 210)),
    (["space", "cosmos", "galaxy", "nebula", "asteroid", "orbit", "satellite", "astronaut", "universe", "solar", "comet"], "space", "night", [(3, 1, 20), (8, 5, 40), (15, 10, 60)], (2, 1, 15)),
    (["farm", "field", "pasture", "meadow", "grassland", "prairie", "ranch", "barn", "crop", "grain", "wheat", "hay", "orchard", "garden"], "farm", "gradient", [(160, 200, 130), (120, 160, 90)], (80, 120, 50)),
    (["swamp", "marsh", "bog", "fen", "wetland", "bayou", "everglade", "mangrove"], "swamp", "forest", [(100, 140, 80), (60, 90, 50)], (50, 80, 40)),
    (["river", "lake", "pond", "stream", "creek", "brook", "waterfall", "cascade"], "river", "ocean", [(80, 160, 210), (40, 100, 180)], None),
]

def _detect_biome(text: str) -> dict:
    """Detect environmental setting from text with auto-plural/variant matching."""
    import re
    text_lower = text.lower()
    # Extract individual words for matching
    words = set(re.findall(r'\b[a-z]+\b', text_lower))
    best_score = 0
    best_biome = "gradient"
    best_bg = {"type": "gradient", "colors": [(140, 160, 200), (100, 120, 170)], "horizon": 0.55, "ground_color": (80, 100, 70)}
    for keywords, biome, bg_type, colors, ground in _BIOMES:
        score = 0
        for kw in keywords:
            if kw in words:
                score += 2
            else:
                # Auto-plural/variant: try common suffixes
                k = kw
                if not any(k.endswith(s) for s in ('s', 'es', 'ed', 'ing')):
                    if k + 's' in words or k + 'es' in words or k + 'ed' in words or k + 'ing' in words:
                        score += 2
                if k.endswith('s') and not k.endswith('ss') and k[:-1] in words:
                    score += 2
        if score > best_score:
            best_score = score
            best_biome = biome
            best_bg = {"type": bg_type, "colors": [list(c) for c in colors], "horizon": 0.6 if biome in ("desert", "farm", "arctic") else 0.55, "ground_color": list(ground) if ground else None}
    return best_bg

def _detect_mood(text: str) -> str:
    """Detect emotional tone from text using expanded word sets."""
    l = text.lower()
    w = set(l.split())

    # Strip punctuation from words for matching
    import string as _st
    w = set(word.strip(_st.punctuation) for word in w)

    fear     = {"fear","afraid","terrified","terrifying","dread","horror","panic","scream","terror","nightmare","paralyzed","flee","cower","tremble","shudder","helpless","vulnerable","exposed","trapped","threat","danger","deadly","fatal","ominous","menace","dreadful","dies","dying","deathly","mortal"}
    hope     = {"hope","brave","courage","dawn","survive","survival","discover","explore","journey","future","safe","safety","shelter","home","warm","together","family","guide","lead","peace","triumph","victory","hero","rescue","salvation","miracle","faith","dream","inspire","wonder"}
    mystery  = {"mystery","mysterious","unknown","strange","weird","beyond","distant","fog","mist","hidden","secret","ancient","forgotten","lost","deep","depths","enigma","puzzle","curious","bizarre","uncanny","supernatural","magical","mythical","legend","perception","perceive","perceived","aware","conscious","consciousness","filter","filters","signal","signals","edge","edges","illusion","unreal","translated","edited","reality","question","questioning","introspection","reflection","contemplate","philosophical","complicated","complex","paradox","contradiction"}
    peaceful = {"peaceful","calm","quiet","still","gentle","serene","tranquil","beautiful","awe","majestic","vast","endless","reflection","contemplate","gaze","sky","wind","breeze","soft","slow","lazy","stillness","harmony","balance","serenity","meditative"}
    danger   = {"danger","threat","attack","strike","blood","wound","war","battle","fight","enemy","weapon","spear","arrow","sword","kill","death","destroy","crush","savage","brutal","violent","aggressive","predator","hunt","prey","tooth","claw","fang","venom","poison","ambush","pounce","chase","break","breaks","breaking","shatter","shattered","crash","smash"}
    surprise = {"sudden","suddenly","unexpected","shock","stun","startle","blast","explode","burst","erupt","instant","immediately","abrupt","snap","crash","bang","pow","extraordinary","incredible","unbelievable","remarkable","strangest","weirdest","bizarre","freakish","fantastic"}
    sadness  = {"sad","lonely","alone","isolation","isolated","abandon","forlorn","desolate","despair","grief","sorrow","heavy","weary","tired","lost","empty","void","numb","tear","cry","sob","mourn","funeral","grave","tomb","succumb","succumbs","fading","fades","passing","discard","discarded","missing"}
    wonder   = {"wonder","amazing","astonish","astonishing","extraordinary","marvel","spectacle","magnificent","glorious","sublime","breathtaking","stunning","fascinating","captivating","enchant","thrilling","exquisite","miracle","magical","mythical","fabled","epic","legendary","transform","transformation","metamorphosis","evolution","evolve","evolving","compete","competing","adapt","remarkable","incredible","unbelievable","imagine","imagination","creative"}

    scores = [
        ("somber",     len(w & fear) * 1.5 + len(w & sadness) * 1.2),
        ("hopeful",    len(w & hope) * 1.5 + len(w & wonder) * 0.8),
        ("mysterious", len(w & mystery) * 1.3 + len(w & surprise) * 0.5),
        ("peaceful",   len(w & peaceful) * 1.5),
        ("dramatic",   len(w & danger) * 1.5 + len(w & fear) * 0.8),
        ("surprising", len(w & surprise) * 1.5),
        ("sad",        len(w & sadness) * 1.5),
        ("wonder",     len(w & wonder) * 1.5 + len(w & peaceful) * 0.5),
    ]
    best = max(scores, key=lambda x: x[1])
    return best[0] if best[1] > 0 else "mysterious"

def _extract_entities(text: str) -> list:
    """Extract visual entities from text. Returns list of (type, color) tuples."""
    import string as _st
    l = text.lower()
    words = l.split()
    # Strip punctuation from words for matching
    words = [w.strip(_st.punctuation) for w in words if w.strip(_st.punctuation)]
    found = []
    seen_types = set()
    auto_count = 0
    MAX_AUTO = 2

    # Entity map sorted by specificity: (word/phrase, element_type, color, weight)
    ENTITIES = [
        # ── Desert & Arid ──
        ("lizard", "animal", (130, 160, 70), 3), ("horned lizard", "animal", (140, 170, 80), 5),
        ("chameleon", "animal", (100, 180, 80), 3), ("gecko", "animal", (150, 180, 70), 3),
        ("iguana", "animal", (120, 160, 90), 3), ("scorpion", "animal", (180, 120, 40), 4),
        ("camel", "animal", (160, 130, 90), 4), ("coyote", "animal", (160, 140, 100), 4),
        ("fox", "animal", (200, 120, 60), 4), ("vulture", "bird", (80, 60, 50), 4),
        ("hawk", "bird", (60, 50, 40), 3), ("eagle", "bird", (50, 45, 35), 3),
        ("rattlesnake", "animal", (160, 130, 70), 4), ("snake", "animal", (140, 160, 80), 3),
        ("tortoise", "animal", (120, 140, 70), 3), ("armadillo", "animal", (150, 130, 100), 3),
        ("cactus", "plant", (60, 140, 40), 4), ("agave", "plant", (80, 140, 60), 3),
        ("yucca", "plant", (90, 150, 70), 3), ("palm", "tree", (60, 120, 40), 3),
        ("dune", "hill", (200, 170, 120), 3), ("sand", "hill", (210, 190, 150), 2),
        ("rock", "rock", (160, 140, 120), 3), ("boulder", "rock", (140, 130, 110), 3),
        ("cracked", "path", (160, 140, 110), 2), ("dry", "path", (180, 160, 130), 1),

        # ── Ocean & Aquatic ──
        ("whale", "whale", (60, 70, 100), 4), ("orca", "whale", (40, 45, 60), 4),
        ("shark", "shark", (80, 85, 95), 4), ("dolphin", "fish", (100, 140, 180), 3),
        ("jellyfish", "fish", (200, 100, 200), 3), ("turtle", "animal", (80, 140, 60), 3),
        ("crab", "animal", (200, 120, 80), 3), ("lobster", "animal", (200, 80, 60), 3),
        ("starfish", "fish", (220, 150, 80), 3), ("coral", "fish", (200, 120, 160), 3),
        ("seaweed", "plant", (60, 140, 60), 2), ("kelp", "plant", (50, 130, 50), 2),
        ("wave", "wave", (40, 100, 200), 4), ("surf", "wave", (60, 120, 220), 3),
        ("ocean", "wave", (30, 80, 180), 3), ("sea", "wave", (40, 90, 190), 3),
        ("deep", "water", (20, 60, 140), 4), ("mysterious", "star", (180, 160, 220), 4),
        ("barely", "water", (140, 160, 200), 2), ("bottom", "water", (40, 60, 120), 3),
        ("river", "water", (50, 130, 200), 3),

        # ── Forest & Jungle ──
        ("deer", "animal", (160, 120, 80), 4), ("bear", "animal", (100, 70, 50), 4),
        ("wolf", "animal", (120, 110, 100), 4), ("moose", "animal", (130, 100, 70), 4),
        ("rabbit", "animal", (180, 160, 140), 3), ("squirrel", "animal", (160, 120, 80), 3),
        ("owl", "bird", (140, 120, 100), 4), ("woodpecker", "bird", (200, 60, 40), 3),
        ("butterfly", "flower", (255, 200, 100), 3), ("firefly", "star", (255, 240, 100), 3),
        ("mushroom", "flower", (220, 180, 160), 3), ("fern", "plant", (60, 150, 60), 3),
        ("moss", "plant", (80, 160, 60), 2), ("vine", "plant", (60, 140, 40), 2),
        ("log", "rock", (100, 70, 50), 2),

        # ── Mountain & Cliff ──
        ("cliff", "cliff", (100, 80, 60), 4), ("mountain", "mountain", (100, 90, 80), 4),
        ("peak", "mountain", (140, 130, 150), 3), ("valley", "hill", (120, 140, 90), 3),
        ("canyon", "cliff", (180, 130, 70), 4), ("rock", "rock", (160, 140, 120), 3),
        ("boulder", "rock", (140, 130, 110), 3), ("avalanche", "mountain", (200, 210, 230), 3),

        # ── Arctic & Snow ──
        ("polar bear", "animal", (230, 230, 220), 5), ("penguin", "animal", (40, 40, 50), 4),
        ("seal", "animal", (160, 150, 140), 3), ("walrus", "animal", (140, 120, 100), 3),
        ("arctic fox", "animal", (240, 240, 235), 4), ("snow", "cloud", (240, 245, 250), 3),
        ("ice", "water", (200, 220, 240), 3), ("glacier", "cliff", (180, 210, 230), 4),
        ("igloo", "house", (200, 210, 220), 3),

        # ── Farm & Meadow ──
        ("horse", "animal", (100, 80, 60), 4), ("cow", "animal", (200, 180, 160), 4),
        ("sheep", "animal", (220, 220, 210), 3), ("goat", "animal", (180, 160, 130), 3),
        ("pig", "animal", (230, 180, 170), 3), ("chicken", "bird", (220, 200, 180), 3),
        ("rooster", "bird", (200, 80, 50), 3), ("barn", "house", (160, 60, 40), 4),
        ("tractor", "compass", (200, 60, 40), 3), ("hay", "plant", (210, 190, 100), 2),
        ("fence", "fence", (120, 90, 60), 3), ("wheat", "grass", (210, 190, 80), 3),

        # ── City & Urban ──
        ("skyscraper", "building", (120, 130, 150), 4), ("tower", "building", (100, 110, 130), 3),
        ("bridge", "building", (100, 80, 60), 3), ("church", "building", (180, 160, 140), 3),
        ("castle", "building", (140, 120, 100), 4), ("temple", "building", (200, 180, 150), 4),
        ("lamp", "lamp", (255, 220, 100), 3), ("window", "house", (255, 230, 150), 2),
        ("door", "house", (100, 60, 40), 2), ("roof", "house", (140, 60, 40), 2),
        ("street", "path", (80, 80, 90), 2), ("market", "house", (200, 160, 120), 3),

        # ── Fantasy & Mythical ──
        ("dragon", "sea_serpent", (60, 40, 80), 5), ("serpent", "sea_serpent", (40, 100, 60), 4),
        ("monster", "sea_serpent", (50, 80, 60), 4), ("leviathan", "sea_serpent", (30, 60, 50), 5),
        ("sea serpent", "sea_serpent", (40, 100, 60), 5), ("kraken", "sea_serpent", (50, 60, 80), 5),
        ("unicorn", "animal", (255, 240, 250), 4), ("griffin", "animal", (200, 180, 100), 4),
        ("phoenix", "bird", (220, 80, 40), 5), ("giant", "human", (100, 120, 100), 4),
        ("witch", "human", (80, 60, 100), 3), ("wizard", "human", (60, 60, 120), 3),
        ("fairy", "flower", (220, 200, 255), 3), ("elf", "human", (180, 200, 160), 3),
        ("mermaid", "human", (180, 200, 220), 4), ("ghost", "cloud", (220, 220, 240), 3),
        ("vampire", "human", (200, 200, 210), 3), ("zombie", "human", (120, 140, 100), 3),
        ("skeleton", "human", (220, 210, 190), 3), ("demon", "animal", (80, 40, 40), 4),

        # ── Celestial & Weather ──
        ("sun", "sun", (255, 200, 80), 4), ("moon", "moon", (220, 220, 200), 4),
        ("star", "star", (255, 240, 200), 3), ("constellation", "star", (200, 210, 255), 3),
        ("comet", "star", (255, 220, 100), 3), ("planet", "globe", (100, 150, 200), 3),
        ("rainbow", "moon_path", (255, 200, 150), 3), ("rain", "water", (100, 150, 200), 2),
        ("storm", "wave", (30, 60, 120), 3), ("lightning", "fire", (255, 240, 200), 3),
        ("cloud", "cloud", (200, 200, 210), 3), ("fog", "cloud", (180, 190, 200), 2),
        ("mist", "cloud", (170, 185, 200), 2), ("hurricane", "wave", (40, 60, 100), 4),
        ("tornado", "wave", (60, 50, 40), 4), ("sandstorm", "wave", (200, 180, 120), 4),
        ("moonlight", "moon_path", (200, 210, 230), 3), ("sunset", "sun", (255, 180, 80), 3),
        ("dawn", "sun", (255, 200, 120), 3), ("shooting star", "star", (255, 255, 200), 4),
        ("migration", "arrow", (100, 180, 220), 4), ("migrations", "arrow", (100, 180, 220), 4),
        ("migrate", "arrow", (100, 180, 220), 4), ("migrates", "arrow", (100, 180, 220), 4),
        ("migrating", "arrow", (100, 180, 220), 4), ("migratory", "arrow", (100, 180, 220), 4),
        ("migrated", "arrow", (100, 180, 220), 4), ("migration route", "arrow", (80, 160, 200), 5),
        ("world", "globe", (80, 160, 200), 4), ("earth", "globe", (60, 140, 180), 4),

        # ── Body Parts ──
        ("eye", "eye", (255, 250, 240), 4), ("eyes", "eye", (255, 250, 240), 4),
        ("face", "eye", (235, 200, 175), 3), ("hand", "hand", (235, 200, 175), 3),
        ("wing", "bird", (200, 180, 160), 3), ("feather", "bird", (220, 210, 200), 2),
        ("claw", "hand", (180, 160, 130), 3), ("fang", "rock", (240, 240, 235), 3),
        ("blood", "fire", (180, 30, 20), 4), ("teeth", "rock", (240, 240, 230), 2),
        ("heart", "heart", (200, 50, 70), 4), ("brain", "star", (200, 180, 220), 4),
        ("bone", "rock", (240, 235, 225), 3), ("bones", "rock", (240, 235, 225), 3),
        ("muscle", "human", (160, 100, 80), 3), ("muscles", "human", (160, 100, 80), 3),
        ("lung", "cloud", (220, 200, 210), 3), ("lungs", "cloud", (220, 200, 210), 3),
        ("arm", "human", (80, 60, 100), 2), ("arms", "human", (80, 60, 100), 2),
        ("leg", "human", (80, 60, 100), 2), ("legs", "human", (80, 60, 100), 2),
        ("foot", "human", (80, 60, 100), 2), ("feet", "human", (80, 60, 100), 2),
        ("finger", "hand", (235, 200, 175), 2), ("fingers", "hand", (235, 200, 175), 2),
        ("hair", "hand", (100, 80, 60), 2), ("tongue", "hand", (220, 180, 160), 2),

        # ── Human & Social ──
        ("human", "human", (80, 60, 120), 3), ("person", "human", (80, 60, 120), 3),
        ("man", "man", (70, 50, 100), 3), ("woman", "woman", (100, 80, 130), 3),
        ("child", "child", (120, 110, 130), 3), ("children", "child", (120, 110, 130), 3),
        ("baby", "child", (200, 180, 190), 3), ("toddler", "child", (190, 180, 170), 3),
        ("teenager", "human", (100, 120, 140), 3), ("teen", "human", (100, 120, 140), 3),
        ("adult", "human", (120, 100, 80), 3), ("adults", "human", (120, 100, 80), 3),
        ("people", "human", (80, 60, 120), 3),
        ("humans", "human", (80, 60, 120), 3),
        ("scientist", "human", (100, 100, 130), 4), ("scientists", "human", (100, 100, 130), 4),
        ("individual", "human", (90, 80, 110), 3), ("individuals", "human", (90, 80, 110), 3),
        ("crowd", "human", (80, 70, 110), 3), ("hunter", "human", (60, 40, 80), 4),
        ("warrior", "human", (80, 50, 60), 3), ("king", "human", (120, 80, 60), 3),
        ("queen", "human", (140, 100, 120), 3), ("baby", "human", (200, 180, 190), 3),
        ("shadow", "shadow_figure", (20, 25, 30), 4), ("silhouette", "shadow_figure", (20, 25, 30), 4),
        ("figure", "shadow_figure", (30, 35, 40), 3),
        ("doctor", "human", (180, 200, 220), 4), ("teacher", "human", (180, 160, 120), 4),
        ("farmer", "human", (140, 120, 80), 4), ("soldier", "human", (80, 70, 60), 4),
        ("sailor", "human", (60, 80, 120), 4), ("artist", "human", (200, 160, 120), 4),
        ("writer", "human", (180, 180, 160), 4), ("builder", "human", (160, 120, 80), 4),
        ("driver", "human", (120, 130, 140), 3), ("pilot", "human", (60, 80, 140), 4),
        ("worker", "human", (140, 120, 100), 3), ("leader", "human", (120, 80, 60), 4),
        ("captain", "human", (60, 80, 140), 4), ("chief", "human", (120, 80, 60), 4),
        ("elder", "human", (100, 80, 60), 4), ("stranger", "human", (100, 80, 100), 3),
        ("guardian", "human", (80, 100, 120), 4), ("protector", "human", (80, 100, 120), 4),
        ("servant", "human", (100, 100, 80), 3), ("slave", "human", (80, 80, 100), 3),
        ("friend", "human", (120, 160, 120), 4), ("enemy", "human", (160, 60, 60), 4),
        ("ally", "human", (120, 160, 140), 3), ("follower", "human", (100, 100, 120), 3),

        # ── Structures & Objects ──
        ("house", "house", (180, 160, 140), 3), ("hut", "house", (160, 140, 100), 3),
        ("cabin", "house", (120, 80, 50), 3), ("tent", "house", (200, 180, 160), 3),
        ("ship", "ship", (80, 60, 40), 4), ("boat", "boat", (80, 55, 35), 4),
        ("canoe", "canoe", (80, 55, 35), 4), ("raft", "canoe", (70, 50, 40), 3),
        ("sail", "ship", (220, 210, 190), 3), ("anchor", "anchor", (80, 75, 70), 3),
        ("totem", "totem", (120, 105, 85), 4), ("monolith", "totem", (100, 90, 75), 4),
        ("pillar", "totem", (140, 130, 110), 3), ("stone", "rock", (160, 150, 130), 3),
        ("fire", "fire", (220, 120, 40), 4), ("campfire", "fire", (220, 140, 60), 4),
        ("flame", "fire", (240, 160, 40), 3), ("torch", "fire", (220, 160, 40), 3),
        ("compass", "compass", (180, 150, 80), 3), ("map", "compass", (220, 200, 160), 3),
        ("treasure", "star", (255, 220, 50), 3), ("crown", "crown", (220, 180, 50), 3),
        ("sword", "rock", (180, 180, 190), 3), ("shield", "circle", (140, 80, 60), 3),
        ("spear", "rock", (160, 140, 100), 3), ("arrow", "arrow", (160, 140, 100), 3),
        ("bow", "moon_path", (120, 80, 50), 3), ("drum", "circle", (180, 120, 80), 3),
        ("mask", "eye", (200, 180, 150), 3), ("scroll", "scroll", (220, 200, 170), 3),
        ("book", "book", (140, 100, 60), 3), ("skull", "skull", (220, 210, 190), 4),
        ("cross", "cross", (120, 80, 60), 3), ("bell", "circle", (200, 180, 100), 3),
        ("coin", "star", (220, 190, 60), 2), ("key", "key", (180, 160, 100), 3),
        ("lamp", "lamp", (255, 220, 100), 3), ("candle", "fire", (255, 200, 100), 3),
        ("throne", "house", (120, 80, 60), 3), ("altar", "rock", (100, 90, 80), 3),

        # ── Music & Sound ──
        ("music", "star", (200, 180, 220), 4), ("song", "star", (200, 220, 180), 4),
        ("melody", "moon_path", (200, 180, 220), 4), ("rhythm", "circle", (180, 160, 120), 3),
        ("instrument", "star", (180, 160, 140), 3), ("drum", "circle", (180, 120, 80), 3),
        ("flute", "rock", (180, 160, 140), 3), ("horn", "moon_path", (180, 160, 100), 3),
        ("bell", "circle", (200, 180, 100), 3), ("voice", "star", (200, 180, 200), 3),
        ("echo", "moon_path", (180, 200, 220), 3), ("sound", "moon_path", (200, 200, 220), 3),
        ("silent", "cloud", (200, 200, 210), 2), ("silence", "cloud", (200, 200, 210), 2),
        ("whisper", "cloud", (200, 200, 220), 3), ("whispers", "cloud", (200, 200, 220), 3),

        # ── Sports & Movement ──
        ("sport", "human", (120, 120, 100), 3), ("game", "circle", (180, 180, 160), 3),
        ("race", "arrow", (200, 80, 60), 4), ("run", "human", (80, 60, 80), 3),
        ("runner", "human", (80, 60, 80), 3), ("jump", "human", (100, 100, 120), 3),
        ("throw", "hand", (200, 180, 160), 3), ("catch", "hand", (200, 180, 160), 3),
        ("ball", "circle", (220, 180, 100), 3), ("goal", "star", (255, 220, 80), 4),
        ("victory", "star", (255, 220, 50), 5), ("defeat", "skull", (120, 100, 80), 4),
        ("win", "star", (255, 220, 50), 4), ("lose", "skull", (120, 100, 80), 3),
        ("fight", "human", (140, 60, 60), 4), ("battle", "human", (140, 60, 60), 4),
        ("match", "circle", (180, 180, 160), 3), ("champion", "crown", (255, 200, 50), 5),
        ("medal", "circle", (255, 200, 50), 4), ("trophy", "star", (255, 200, 60), 4),
        ("score", "star", (200, 200, 220), 3), ("speed", "arrow", (200, 80, 60), 4),
        ("strength", "human", (140, 100, 80), 4), ("power", "star", (255, 200, 80), 4),

        # ── Technology & Machines ──
        ("machine", "gear", (140, 140, 150), 4), ("engine", "gear", (120, 120, 140), 4),
        ("motor", "gear", (130, 130, 140), 3), ("wheel", "circle", (100, 100, 100), 3),
        ("gear", "gear", (160, 150, 140), 4), ("gears", "gear", (160, 150, 140), 4),
        ("robot", "human", (140, 140, 160), 4), ("computer", "book", (60, 80, 140), 4),
        ("screen", "book", (100, 140, 200), 3), ("circuit", "moon_path", (60, 140, 100), 3),
        ("wire", "water", (140, 120, 100), 2), ("battery", "rock", (180, 180, 60), 3),
        ("light", "star", (255, 240, 200), 3), ("lamp", "lamp", (255, 220, 100), 3),
        ("electric", "star", (255, 240, 100), 4), ("electricity", "star", (255, 240, 100), 4),
        ("iron", "rock", (120, 120, 130), 2), ("steel", "rock", (130, 130, 140), 2),
        ("metal", "rock", (140, 140, 150), 2), ("tool", "rock", (160, 140, 100), 3),
        ("weapon", "rock", (120, 100, 80), 3), ("factory", "building", (120, 120, 130), 4),

        # ── Emotions & Feelings ──
        ("love", "heart", (220, 50, 80), 5), ("hate", "fire", (180, 30, 20), 4),
        ("anger", "fire", (220, 60, 30), 4), ("angry", "fire", (220, 60, 30), 4),
        ("rage", "fire", (220, 40, 20), 5), ("fury", "fire", (220, 40, 20), 5),
        ("joy", "star", (255, 220, 80), 4), ("happy", "star", (255, 220, 80), 4),
        ("happiness", "star", (255, 220, 80), 4), ("glad", "star", (255, 220, 80), 3),
        ("sad", "water", (100, 150, 200), 3), ("sorrow", "water", (80, 120, 180), 4),
        ("grief", "water", (60, 100, 160), 4),
        ("fear", "shadow_figure", (30, 30, 40), 4), ("afraid", "shadow_figure", (30, 30, 40), 4),
        ("terror", "shadow_figure", (20, 20, 30), 5), ("horror", "shadow_figure", (20, 20, 30), 5),
        ("pride", "crown", (220, 180, 60), 4), ("shame", "eye", (180, 160, 160), 3),
        ("envy", "eye", (100, 180, 80), 3), ("jealous", "eye", (100, 180, 80), 3),
        ("greed", "star", (255, 200, 50), 3), ("desire", "star", (255, 200, 80), 4),
        ("passion", "fire", (220, 80, 60), 4), ("hope", "star", (255, 240, 180), 4),
        ("faith", "star", (255, 240, 220), 3), ("trust", "hand", (200, 180, 160), 3),
        ("peace", "cloud", (200, 220, 240), 4), ("calm", "cloud", (200, 220, 240), 3),
        ("brave", "human", (140, 100, 60), 4), ("courage", "human", (140, 100, 60), 4),

        # ── Perception & Reality ──
        ("camera", "camera", (80, 80, 80), 4), ("cameras", "camera", (80, 80, 80), 4),
        ("filter", "filter", (120, 160, 200), 4), ("filters", "filter", (120, 160, 200), 4),
        ("signal", "signal", (100, 200, 100), 4), ("signals", "signal", (100, 200, 100), 4),
        ("edge", "edge", (200, 180, 160), 3), ("edges", "edge", (200, 180, 160), 3),
        ("color", "color_swatch", (255, 200, 100), 3), ("colors", "color_swatch", (255, 200, 100), 3),
        ("movement", "movement", (180, 200, 100), 4),
        ("discard", "discard", (120, 80, 80), 4), ("discards", "discard", (120, 80, 80), 4),
        ("discarded", "discard", (120, 80, 80), 4), ("discarding", "discard", (120, 80, 80), 4),
        ("aware", "awareness", (200, 220, 255), 4), ("awareness", "awareness", (200, 220, 255), 4),
        ("unaware", "awareness", (120, 140, 180), 3),
        ("perception", "eye", (200, 200, 220), 5), ("perceive", "eye", (200, 200, 220), 4),
        ("perceived", "eye", (200, 200, 220), 4), ("perceiving", "eye", (200, 200, 220), 4),
        ("reality", "globe", (180, 180, 220), 5), ("real", "globe", (160, 160, 200), 3),
        ("truth", "star", (255, 240, 220), 5), ("true", "star", (255, 240, 200), 3),
        ("version", "scroll", (200, 200, 200), 4), ("versions", "scroll", (200, 200, 200), 4),
        ("translated", "scroll", (180, 200, 220), 4), ("translation", "scroll", (180, 200, 220), 4),
        ("edited", "book", (180, 180, 160), 4), ("editing", "book", (180, 180, 160), 4),
        ("brain", "brain", (200, 180, 200), 5), ("mind", "brain", (200, 180, 220), 4),
        ("conscious", "brain", (200, 200, 240), 5), ("consciousness", "brain", (200, 200, 240), 5),
        ("unconscious", "brain", (140, 140, 180), 4),
        ("sensory", "signal", (180, 180, 220), 4), ("sense", "eye", (200, 200, 200), 3),
        ("senses", "eye", (200, 200, 200), 3),

        # ── Nature Elements (generic) ──
        ("tree", "tree", (50, 120, 50), 3), ("flower", "flower", (255, 100, 150), 3),
        ("grass", "grass", (50, 100, 40), 2), ("plant", "plant", (50, 120, 50), 3),
        ("plants", "plant", (50, 120, 50), 3), ("water", "water", (40, 100, 180), 3),
        ("fire", "fire", (220, 120, 40), 3), ("earth", "hill", (120, 100, 60), 2),
        ("ground", "path", (140, 120, 80), 1), ("sky", "cloud", (180, 200, 220), 2),
        ("air", "cloud", (200, 210, 230), 1), ("wind", "arrow", (180, 200, 220), 2),
        ("bird", "bird", (60, 50, 40), 3), ("birds", "bird", (60, 50, 40), 3),
        ("swift", "bird", (50, 55, 60), 4), ("swifts", "bird", (50, 55, 60), 4),
        ("flock", "bird", (60, 55, 50), 4), ("pterosaur", "bird", (80, 60, 50), 5),
        ("flying reptile", "bird", (80, 60, 50), 5), ("flying reptiles", "bird", (80, 60, 50), 5), ("fish", "fish", (200, 180, 100), 3),
        ("animal", "animal", (100, 80, 60), 2), ("insect", "animal", (80, 120, 60), 2),
        ("food", "fruit", (220, 180, 80), 3), ("weather", "cloud", (180, 200, 220), 3),
        ("continents", "globe", (80, 160, 100), 4), ("continent", "globe", (80, 160, 100), 4),
        ("see", "eye", (200, 200, 220), 3), ("sees", "eye", (200, 200, 220), 3),
        ("saw", "eye", (200, 200, 220), 3), ("seeing", "eye", (200, 200, 220), 3),
        ("touch", "hand", (220, 200, 180), 3), ("touches", "hand", (220, 200, 180), 3),
        ("touching", "hand", (220, 200, 180), 3),
        ("month", "clock", (180, 180, 160), 3), ("months", "clock", (180, 180, 160), 3),
        ("opportunity", "star", (255, 220, 80), 4), ("opportunities", "star", (255, 220, 80), 4),
        ("small", "star", (200, 200, 180), 2), ("tiny", "star", (200, 200, 180), 2),
        ("huge", "mountain", (140, 120, 100), 3), ("large", "mountain", (140, 120, 100), 3),
        ("tall", "tree", (80, 140, 60), 3), ("wide", "water", (100, 160, 200), 2),
        ("narrow", "path", (140, 110, 80), 2), ("cold", "water", (160, 200, 230), 3),
        ("hot", "fire", (240, 160, 40), 3), ("warm", "sun", (255, 200, 100), 3),
        ("cool", "water", (140, 200, 220), 2), ("build", "hand", (180, 140, 100), 3),
        ("builds", "hand", (180, 140, 100), 3), ("building", "hand", (180, 140, 100), 3),
        ("gather", "hand", (180, 160, 120), 3), ("gathers", "hand", (180, 160, 120), 3),
        ("collected", "hand", (180, 160, 120), 3), ("collecting", "hand", (180, 160, 120), 3),
        ("nest", "circle", (160, 130, 80), 4), ("leaf", "plant", (80, 180, 60), 3),
        ("leaves", "plant", (80, 180, 60), 3), ("twig", "rock", (140, 110, 70), 3),
        ("twigs", "rock", (140, 110, 70), 3), ("branch", "tree", (100, 80, 50), 3),
        ("branches", "tree", (100, 80, 50), 3), ("root", "tree", (120, 80, 40), 2),
        ("roots", "tree", (120, 80, 40), 2), ("soil", "hill", (140, 120, 80), 2),
        ("mud", "hill", (120, 100, 60), 2), ("stone", "rock", (160, 150, 130), 3),
        ("passes", "clock", (180, 180, 160), 3), ("passing", "clock", (180, 180, 160), 3),
        ("photograph", "book", (200, 180, 150), 3), ("photographs", "book", (200, 180, 150), 3),
        ("fade", "cloud", (180, 180, 200), 3), ("fades", "cloud", (180, 180, 200), 3),
        ("faded", "cloud", (180, 180, 200), 3), ("clear", "sun", (240, 240, 220), 2),
        ("blurry", "cloud", (180, 180, 200), 3), ("blurred", "cloud", (180, 180, 200), 3),
        ("swim", "fish", (100, 160, 200), 3), ("swims", "fish", (100, 160, 200), 3),
        ("fly", "bird", (100, 140, 180), 3), ("flies", "bird", (100, 140, 180), 3),
        ("grown", "tree", (80, 140, 60), 2), ("grows", "tree", (80, 140, 60), 2),
        ("grow", "tree", (80, 140, 60), 2), ("grew", "tree", (80, 140, 60), 2),
        ("ancient", "mountain", (100, 80, 60), 3), ("old", "hourglass", (180, 160, 140), 3),
        ("life", "human", (80, 120, 100), 3), ("live", "human", (80, 120, 100), 2),
        ("lives", "human", (80, 120, 100), 2), ("nature", "tree", (60, 140, 60), 3),
        ("wild", "animal", (100, 80, 60), 3), ("wildlife", "animal", (100, 80, 60), 3),
        ("creature", "animal", (120, 140, 100), 4), ("creatures", "animal", (120, 140, 100), 4),
        ("reptile", "animal", (100, 120, 80), 3), ("reptiles", "animal", (100, 120, 80), 3),
        ("dinosaur", "animal", (80, 100, 60), 5),
        ("alive", "human", (80, 120, 100), 3),

        # ── Actions / Events ──
        ("spray", "water", (180, 200, 230), 3), ("sprays", "water", (180, 200, 230), 3),
        ("splash", "water", (180, 210, 240), 3), ("drip", "water", (100, 150, 200), 2),
        ("stream", "water", (40, 100, 200), 3), ("flow", "water", (60, 120, 200), 2),
        ("explosion", "fire", (255, 150, 50), 4), ("explode", "fire", (255, 120, 40), 4),
        ("erupt", "fire", (255, 100, 30), 4), ("eruption", "fire", (255, 80, 20), 4),
        ("tracking", "eye", (180, 200, 220), 4), ("track", "eye", (180, 200, 220), 3),
        ("tracks", "eye", (180, 200, 220), 3), ("tracked", "eye", (180, 200, 220), 3),
        ("uncovered", "star", (255, 220, 100), 4), ("discovered", "star", (255, 220, 100), 4),
        ("discovery", "star", (255, 220, 100), 4), ("discover", "star", (255, 220, 100), 3),
        ("revealed", "star", (255, 220, 100), 3), ("reveal", "star", (255, 220, 100), 3),
        ("expanding", "star", (255, 200, 80), 4), ("everywhere", "star", (255, 240, 200), 4),
        ("competing", "arrow", (200, 80, 60), 4), ("evolving", "star", (255, 220, 100), 4),
        ("unstoppable", "arrow", (200, 60, 40), 5), ("overflowing", "water", (100, 200, 255), 4),
        ("vitality", "star", (255, 240, 100), 4), ("warning", "eye", (200, 160, 80), 4),
        ("future", "star", (200, 220, 255), 4), ("memories", "star", (255, 240, 200), 4),
        ("memory", "star", (255, 240, 200), 4), ("today", "sun", (255, 220, 100), 3),
        ("somewhere", "globe", (160, 200, 240), 3), ("become", "star", (255, 220, 100), 3),
        ("becomes", "star", (255, 220, 100), 3), ("becoming", "star", (255, 220, 100), 3),
        ("surprising", "star", (255, 240, 200), 4), ("surprise", "star", (255, 240, 200), 3),
        ("ever", "circle", (200, 220, 255), 3), ("met", "human", (100, 80, 100), 3),
        ("name", "book", (180, 140, 100), 3), ("shares", "hand", (200, 180, 160), 3),
        ("stranger", "shadow_figure", (60, 50, 60), 3),
        ("unfamiliar", "eye", (200, 180, 200), 3), ("violent", "fire", (200, 50, 30), 4),
        ("violence", "fire", (200, 50, 30), 4), ("changes", "star", (255, 200, 80), 3),
        ("reshapes", "arrow", (200, 80, 40), 4), ("reshape", "arrow", (200, 80, 40), 4),
        ("slowly", "clock", (180, 180, 160), 2), ("gently", "cloud", (200, 220, 240), 2),
        ("travel", "arrow", (180, 160, 100), 4), ("travels", "arrow", (180, 160, 100), 4),
        ("traveled", "arrow", (180, 160, 100), 4), ("traveling", "arrow", (180, 160, 100), 4),
        ("travelled", "arrow", (180, 160, 100), 4), ("travelling", "arrow", (180, 160, 100), 4),
        ("journey", "arrow", (180, 160, 120), 4), ("journeys", "arrow", (180, 160, 120), 4),
        ("route", "arrow", (160, 140, 100), 3),

        # ── Colors / Descriptors that add visual meaning ──
        ("red", "fire", (220, 40, 40), 2), ("golden", "sun", (255, 200, 80), 2),
        ("silver", "moon", (200, 210, 220), 2), ("dark", "shadow_figure", (20, 25, 30), 1),
        ("bright", "sun", (255, 240, 200), 1),         ("pale", "moon", (230, 230, 220), 1),
        ("shadowy", "shadow_figure", (20, 25, 30), 2),

        # ── Emotional / State words that need visual representation ──
        ("confused", "eye", (200, 180, 160), 3), ("confusion", "eye", (200, 180, 160), 3),
        ("shocked", "eye", (240, 230, 220), 4), ("shock", "eye", (240, 230, 220), 3),
        ("frozen", "human", (60, 60, 80), 3), ("freezes", "human", (60, 60, 80), 3),
        ("freeze", "human", (60, 60, 80), 3), ("still", "human", (60, 60, 80), 2),
        ("stunned", "eye", (240, 230, 220), 3), ("surprise", "eye", (240, 230, 210), 3),
        ("backs", "arrow", (160, 140, 100), 2), ("backing", "arrow", (160, 140, 100), 2),
        ("retreat", "arrow", (160, 140, 100), 3), ("fleeing", "human", (80, 60, 80), 3),
        ("runs", "human", (80, 60, 80), 2), ("running", "human", (80, 60, 80), 2),
        ("waits", "human", (60, 60, 80), 2), ("waiting", "human", (60, 60, 80), 2),
        ("happens", "star", (255, 240, 200), 3), ("happened", "star", (255, 240, 200), 3),
        ("occurs", "star", (255, 240, 200), 2), ("occur", "star", (255, 240, 200), 2),
        ("unexpected", "eye", (240, 230, 220), 4), ("sudden", "star", (255, 240, 200), 3),
        ("suddenly", "star", (255, 240, 200), 3), ("blast", "fire", (255, 200, 60), 4),
        ("burst", "fire", (255, 200, 40), 4), ("explosion", "fire", (255, 150, 50), 4),
        ("erupts", "fire", (255, 100, 30), 4), ("erupted", "fire", (255, 100, 30), 4),
        ("strange", "eye", (200, 180, 200), 3), ("bizarre", "eye", (200, 180, 220), 4),
        ("weird", "eye", (180, 170, 200), 3), ("weirdest", "eye", (200, 180, 220), 4),
        ("crazy", "eye", (240, 200, 200), 3), ("incredible", "star", (255, 240, 200), 4),
        ("unbelievable", "star", (255, 240, 200), 4),         ("remarkable", "star", (255, 240, 200), 3),
        ("magical", "star", (255, 240, 220), 3), ("fantastic", "star", (255, 240, 200), 3),
        ("extraordinary", "sun", (255, 220, 100), 4),
        ("astonishing", "star", (255, 240, 200), 4), ("astonished", "eye", (240, 230, 220), 4),
        ("welcome", "human", (80, 60, 120), 2), ("introducing", "human", (80, 60, 120), 2),
        ("meet", "arrow", (160, 140, 200), 2), ("introduces", "human", (80, 60, 120), 2),
        ("hero", "human", (100, 80, 60), 4), ("survivor", "human", (120, 140, 100), 4),
        ("survivors", "human", (120, 140, 100), 4),

        # ── Biology & Life Cycle ──
        ("female", "woman", (140, 100, 120), 4), ("male", "man", (70, 50, 100), 4),
        ("dominant", "human", (120, 60, 40), 3), ("breed", "human", (100, 80, 60), 3),
        ("breeding", "human", (100, 80, 60), 3), ("reproduce", "human", (100, 80, 60), 3),
        ("reproduction", "human", (100, 80, 60), 3), ("mate", "human", (100, 80, 60), 3),
        ("mating", "human", (100, 80, 60), 3), ("spawn", "water", (180, 200, 220), 3),
        ("egg", "circle", (240, 220, 180), 3), ("eggs", "circle", (240, 220, 180), 3),
        ("larva", "animal", (180, 200, 180), 3), ("larvae", "animal", (180, 200, 180), 3),
        ("tadpole", "animal", (120, 140, 100), 3), ("cocoon", "circle", (160, 140, 100), 3),
        ("chrysalis", "circle", (140, 120, 80), 3), ("metamorphosis", "eye", (200, 180, 220), 5),
        ("transform", "star", (255, 240, 200), 4), ("transforms", "star", (255, 240, 200), 4),
        ("transformation", "star", (255, 240, 200), 4), ("change", "star", (255, 240, 200), 3),
        ("changes", "star", (255, 240, 200), 3), ("evolve", "star", (255, 240, 200), 4),
        ("evolution", "star", (255, 240, 200), 4), ("adapt", "star", (255, 240, 200), 3),
        ("adaptation", "star", (255, 240, 200), 3), ("biology", "eye", (200, 180, 200), 3),
        ("biological", "eye", (200, 180, 200), 3), ("biologically", "eye", (200, 180, 200), 3),
        ("hormone", "eye", (200, 100, 150), 4), ("hormones", "eye", (200, 100, 150), 4),
        ("chemical", "water", (100, 180, 200), 3), ("genetic", "star", (200, 180, 220), 3),
        ("gene", "star", (200, 180, 220), 3), ("genes", "star", (200, 180, 220), 3),
        ("dna", "moon_path", (100, 200, 180), 4), ("cell", "circle", (200, 180, 200), 3),
        ("cells", "circle", (200, 180, 200), 3), ("organ", "eye", (200, 140, 160), 3),
        ("organs", "eye", (200, 140, 160), 3), ("body", "human", (100, 80, 100), 3),
        ("skin", "rock", (200, 180, 160), 2),
        ("scales", "rock", (180, 180, 170), 2), ("fin", "fish", (180, 160, 140), 3),
        ("fins", "fish", (180, 160, 140), 3), ("tail", "fish", (160, 140, 120), 2),
        ("gills", "fish", (200, 160, 140), 3), ("anemone", "flower", (200, 100, 160), 4),
        ("coral", "fish", (200, 120, 160), 3), ("reef", "rock", (160, 180, 200), 4),

        # ── Social / Hierarchy ──
        ("group", "human", (100, 100, 120), 4), ("community", "human", (100, 100, 120), 4),
        ("colony", "human", (100, 100, 120), 4), ("tribe", "human", (100, 90, 80), 4),
        ("clan", "human", (100, 90, 80), 3), ("herd", "animal", (120, 120, 100), 3),
        ("pack", "animal", (120, 100, 80), 3), ("school", "fish", (140, 160, 180), 3),
        ("shoal", "fish", (140, 160, 180), 3), ("swarm", "animal", (120, 120, 100), 3),
        ("hierarchy", "mountain", (120, 100, 80), 5), ("rank", "mountain", (140, 120, 100), 4),
        ("ranks", "mountain", (140, 120, 100), 4), ("order", "mountain", (120, 110, 100), 3),
        ("leader", "human", (120, 80, 60), 4), ("leadership", "human", (120, 80, 60), 4),
        ("queen", "human", (140, 100, 120), 4), ("king", "human", (120, 80, 60), 4),
        ("alpha", "human", (120, 60, 40), 4), ("beta", "human", (80, 80, 100), 3),
        ("dominance", "human", (140, 60, 40), 4), ("subordinate", "human", (80, 80, 100), 3),
        ("territory", "path", (140, 120, 80), 3), ("territorial", "path", (140, 120, 80), 3),
        ("vacancy", "star", (255, 240, 200), 3), ("vacant", "star", (255, 240, 200), 3),
        ("position", "mountain", (120, 110, 100), 3), ("promotion", "mountain", (140, 120, 80), 3),
        ("reorganize", "star", (255, 220, 100), 4), ("reorganizes", "star", (255, 220, 100), 4),
        ("reorganization", "star", (255, 220, 100), 4), ("restructure", "building", (120, 130, 140), 3),

        # ── Cycle / Time ──
        ("cycle", "circle", (100, 150, 200), 4), ("cycles", "circle", (100, 150, 200), 4),
        ("circular", "circle", (100, 150, 200), 3), ("repeat", "circle", (100, 150, 200), 3),
        ("repeats", "circle", (100, 150, 200), 3), ("loop", "circle", (100, 150, 200), 3),
        ("continues", "arrow", (160, 140, 100), 2), ("continue", "arrow", (160, 140, 100), 2),
        ("endless", "circle", (100, 150, 200), 3), ("forever", "circle", (100, 150, 200), 3),
        ("age", "hourglass", (180, 160, 140), 3), ("aging", "hourglass", (180, 160, 140), 3),
        ("old", "hourglass", (180, 160, 140), 3), ("time", "clock", (200, 190, 170), 3),

        # ── Death / Mortality ──
        ("dies", "skull", (200, 190, 180), 4), ("died", "skull", (200, 190, 180), 4),
        ("death", "skull", (200, 190, 180), 4), ("dead", "skull", (200, 190, 180), 4),
        ("corpse", "rock", (140, 120, 100), 3), ("carcass", "rock", (140, 120, 100), 3),
        ("grave", "rock", (120, 100, 80), 3), ("tomb", "rock", (120, 100, 80), 3),
        ("succumb", "human", (80, 60, 80), 3), ("succumbs", "human", (80, 60, 80), 3),

        # ── Conflict / Competition ──
        ("rival", "human", (140, 60, 40), 3), ("rivals", "human", (140, 60, 40), 3),
        ("competition", "human", (140, 80, 40), 3), ("compete", "human", (140, 80, 40), 3),
        ("contest", "human", (140, 80, 40), 3), ("challenge", "human", (140, 80, 40), 3),
        ("challenger", "human", (140, 60, 40), 3), ("defend", "hand", (160, 100, 60), 3),
        ("defense", "hand", (160, 100, 60), 3), ("protect", "hand", (160, 120, 80), 3),

        # ── Abstract Concepts ──
        ("nature", "tree", (50, 140, 50), 4), ("natural", "tree", (50, 140, 50), 3),
        ("rule", "book", (180, 160, 140), 3), ("rules", "book", (180, 160, 140), 3),
        ("law", "book", (180, 160, 140), 3), ("laws", "book", (180, 160, 140), 3),
        ("order", "book", (180, 160, 140), 3), ("system", "book", (180, 160, 140), 3),
        ("metaphor", "eye", (200, 180, 200), 3), ("metaphorical", "eye", (200, 180, 200), 3),
        ("metaphorically", "eye", (200, 180, 200), 3), ("literal", "eye", (200, 200, 220), 3),
        ("literally", "eye", (200, 200, 220), 3), ("completely", "circle", (200, 200, 220), 2),
        ("total", "circle", (200, 200, 220), 2), ("fully", "circle", (200, 200, 220), 2),
        ("somehow", "star", (255, 240, 200), 2), ("cause", "star", (255, 240, 200), 2),
        ("reason", "star", (255, 240, 200), 2), ("purpose", "star", (255, 240, 200), 2),
        ("meeting", "human", (100, 100, 120), 3), ("meetings", "human", (100, 100, 120), 3),
        ("election", "human", (120, 80, 60), 4), ("elections", "human", (120, 80, 60), 4),
        ("vote", "human", (120, 80, 60), 3), ("voting", "human", (120, 80, 60), 3),
        ("argument", "human", (140, 60, 60), 3), ("arguments", "human", (140, 60, 60), 3),
        ("debate", "human", (140, 80, 60), 3), ("discuss", "human", (100, 80, 100), 3),
        ("discussion", "human", (100, 80, 100), 3),
        ("gate", "building", (160, 140, 100), 3),
        ("vault", "building", (140, 120, 100), 4),
        ("prison", "building", (120, 100, 80), 4),
        ("secret", "book", (160, 140, 100), 4),
        ("archive", "book", (180, 160, 130), 4),
        ("freedom", "bird", (200, 220, 240), 4),
        ("confinement", "building", (100, 80, 70), 4),
        ("difference", "arrow", (160, 140, 100), 3),
        ("sometimes", "clock", (180, 180, 160), 2),
        ("single", "star", (200, 200, 180), 2),
        ("centimeter", "key", (180, 160, 100), 2),
        ("centimeters", "key", (180, 160, 100), 2),

    ]

    words = l.split()
    i = 0
    while i < len(words):
        word = words[i].strip(".,!?;:'\"()[]{}")
        matched = False
        blocked_by_type = False  # Track if word matched an ENTITY but type was already used
        # Try bigrams first (longest match)
        if i < len(words) - 1:
            bigram = word + " " + words[i+1].strip(".,!?;:'\"()[]{}")
            for phrase, etype, color, weight in ENTITIES:
                if phrase == bigram:
                    if etype not in seen_types:
                        found.append((etype, color, weight))
                        seen_types.add(etype)
                        i += 2
                        matched = True
                        break
                    else:
                        blocked_by_type = True
        if not matched:
            for phrase, etype, color, weight in ENTITIES:
                if ' ' not in phrase:
                    # Check if this word matches the entity phrase
                    is_match = False
                    if phrase == word:
                        is_match = True
                    elif len(word) >= len(phrase) + 1:
                        for suf in ('ing', 'es', 'ed', 's'):
                            if phrase + suf == word:
                                is_match = True
                                break
                    if not is_match and word.endswith('s') and not word.endswith('ss') and phrase == word[:-1]:
                        is_match = True
                    if not is_match and word.endswith('ies') and phrase == word[:-3] + 'y':
                        is_match = True

                    if is_match:
                        if etype not in seen_types:
                            found.append((etype, color, weight))
                            seen_types.add(etype)
                            matched = True
                            break
                        else:
                            blocked_by_type = True
        # ── Skip auto-synthesis if word had an entity match but was blocked by seen_types
        if not matched and blocked_by_type:
            matched = True  # Prevents auto-synthesis of meaningless text labels
        # ── Auto-synthesis for truly unmatched content words ──
        if not matched:
            if auto_count >= MAX_AUTO:
                matched = True  # Prevent adding more auto-synthesized entities
            # Skip function words, short words, and common verbs
            stop_words = {'the','a','an','is','are','was','were','be','been','being',
                          'have','has','had','do','does','did','will','would','could',
                          'should','may','might','can','shall','its','it','this','that',
                          'these','those','i','you','he','she','we','they','me','him',
                          'her','us','them','my','your','his','its','our','their',
                          'in','on','at','to','for','of','with','by','from','into',
                          'not','no','nor','but','or','and','if','then','else','so',
                          'as','than','very','just','also','too','only','all','each',
                          'every','both','some','any','more','most','other','such',
                          'own','same','here','there','when','where','how','what',
                          'who','which','why','before','after','during','until',
                           'while','about','above','below','under','over','through','like',
                           'between','among','against','without','because','although',
                           'though','even','still','already','yet','once','up','down',
                          'out','off','away','back','again','well','now','then',
                          'here','there','not','get','got','go','went','gone','come',
                          'came','take','took','make','made','know','knew','think',
                          'thought','see','saw','seen','give','gave','given','find',
                          'found','tell','told','become','became','leave','left',
                            'feel',                           'felt','put','set','bring','brought','begin','began',
                           'youll','havent','dont','doesnt','didnt','cant','wont',
                           'wasnt','werent','isnt','arent','hasnt','hadnt',
                           'couldnt','wouldnt','shouldnt','mustnt',
                           'thats','whats','whos','theres','theyre','youre',
                          'keep','kept','hold','held','write','wrote','written',
                          'stand','stood','hear','heard','let','say','said','show',
                          'shown','showed','mean','meant','need','call','try'}
            if auto_count >= MAX_AUTO:
                matched = True  # Prevent adding more auto-synthesized entities
            w_clean = word.translate(str.maketrans('', '', ".,!?;:'\"()[]{}-_")).lower()
            if (w_clean and len(w_clean) >= 5 and w_clean not in stop_words
                and not w_clean.isdigit() and not w_clean.startswith('http')):
                weight = 2  # Auto-synthesized words get low weight
                # Generate a deterministic semantic color from the word
                h = hash(w_clean) & 0xFFFFFF
                r = 60 + ((h >> 16) & 0xFF) % 140
                g = 60 + ((h >> 8) & 0xFF) % 140
                b = 60 + (h & 0xFF) % 140
                color = (r, g, b)
                if w_clean not in seen_types:
                    found.append((w_clean, color, weight))
                    seen_types.add(w_clean)
                    auto_count += 1
                    matched = True
        i += 1

    found.sort(key=lambda x: -x[2])
    return found[:4]

def _compose_narrative_position(scene_num: int, total: int) -> str:
    """Determine narrative position: setup, build, tension, climax, resolution."""
    if total <= 1:
        return "neutral"
    rel = scene_num / total
    if rel <= 0.15:
        return "setup"
    elif rel <= 0.40:
        return "build"
    elif rel <= 0.60:
        return "tension"
    elif rel <= 0.80:
        return "climax"
    else:
        return "resolution"

def _detect_scene_type(text: str) -> str:
    """Classify narration into a visual scene type: story, flowchart, timeline,
    diagram, map, bar_chart, pie_chart, line_graph, cycle_diagram, venn_diagram,
    comparison, network_diagram, tree_diagram, histogram, scatter_plot."""
    t = text.lower()
    import re as _re

    def kw_count(keywords, text):
        return sum(1 for w in keywords if _re.search(r'\b' + _re.escape(w) + r'\b', text))

    type_scores = [
        ("diagram",     ["tilt", "degree", "axis", "orbit", "angle", "direct sunlight",
                         "how it works", "structure", "anatomy", "labeled"]),
        ("timeline",    ["timeline", "years ago", "centuries", "generation after generation",
                         "over thousands", "eventually", "over time", "history", "evolved",
                         "gradually", "era", "epoch", "age", "period", "ancient", "began"]),
        ("flowchart",   ["leads to", "results in", "because of this", "chain reaction",
                         "cycle repeats", "step", "stage", "phase", "process",
                         "sequence", "progression"]),
        ("map",         ["across the world", "different cultures", "far away", "region",
                         "around the globe", "continent", "country", "territory",
                         "journey", "travel", "migration", "spread"]),
        ("bar_chart",   ["percent", "percentage", "statistics", "proportion", "fraction",
                         "majority", "minority", "most of", "half of", "quarter",
                         "how many", "how much"]),
        ("pie_chart",   ["share of", "portion", "divide into", "segment", "slice",
                         "distribution", "breakdown"]),
        ("line_graph",  ["increase", "decrease", "rise", "fall", "grow", "decline",
                         "trend", "over time", "over the years", "temperature",
                         "population", "rate"]),
        ("cycle_diagram", ["cycle", "repeats", "circular", "loop", "recurring",
                          "comes back", "turns around", "goes around", "rotates"]),
        ("venn_diagram", ["both", "in common", "shared", "similarities", "differences",
                         "compare and contrast", "unlike", "on one hand", "on the other"]),
        ("comparison",  ["before and after", "compared to", "versus", "rather than",
                         "instead of", "on the left", "on the right", "between two",
                         "either way"]),
        ("network_diagram", ["connected", "linked", "network", "relation", "connection",
                            "interconnected", "web of", "links to", "nodes"]),
        ("tree_diagram",   ["classification", "category", "divided into", "branches",
                           "subgroup", "hierarchy", "descends from", "evolved from"]),
        ("histogram",   ["distribution", "bell curve", "normal distribution", "frequency",
                         "range of", "spread of", "concentration"]),
        ("scatter_plot", ["correlation", "related to", "corresponds with",
                          "relationship between", "associated with", "plotted"]),
    ]

    best_type, best_score = "story", 0
    for stype, kws in type_scores:
        score = kw_count(kws, t)
        if score > best_score:
            best_type, best_score = stype, score

    # Regex patterns for comparison
    if _re.search(r'\bnot\b\s+\w+\s+\w+\s+\w+\s+\bbut\b', t) or \
       _re.search(r'\binstead of\b', t) or _re.search(r'\brather than\b', t):
        comp_score = kw_count(["not", "but", "instead", "rather", "unlike", "versus"], t)
        if comp_score > best_score:
            best_type, best_score = "comparison", comp_score

    return best_type


def _reposition_semantically(elements: list, text: str):
    """Reposition elements so related objects group together meaningfully.
    Detects patterns like 'key opens X', 'difference between A and B'."""
    t = text.lower()
    elem_types = [e["type"] for e in elements]
    placed = set()  # track indices already positioned by semantic rules

    # ── Detect central/theme object ──
    central_candidates = {
        "key": ["key", "lock", "unlock", "open", "close"],
        "book": ["book", "read", "archive", "knowledge", "secret"],
        "compass": ["compass", "direction", "navigate", "journey"],
        "heart": ["heart", "love", "passion", "feel"],
        "crown": ["crown", "king", "queen", "royal", "ruler"],
        "lamp": ["lamp", "light", "illuminate", "bright"],
        "clock": ["clock", "time", "hour", "minute", "second"],
    }

    central_type = None
    central_idx = None
    for ctype, keywords in central_candidates.items():
        if ctype in elem_types and any(kw in t for kw in keywords):
            central_type = ctype
            break

    if central_type:
        for i, e in enumerate(elements):
            if e["type"] == central_type:
                e["x"] = 0.5
                e["y"] = 0.38
                e["scale"] = e.get("scale", 1.0) * 1.6
                placed.add(i)
                central_idx = i
                break

    # ── "difference between A and B" → A left, B right, bridge center ──
    if re.search(r'\bdifference\s+between\b', t) or re.search(r'\bversus\b', t):
        contrast_pairs = [
            ("bird", "building"),
            ("sun", "moon"),
            ("fire", "water"),
            ("human", "shadow_figure"),
        ]
        left_type, right_type = None, None
        for a, b in contrast_pairs:
            if a in elem_types and b in elem_types:
                left_type, right_type = a, b
                break
        if left_type and right_type:
            bridge_idx = 0
            for i, e in enumerate(elements):
                if e["type"] == left_type:
                    e["x"] = 0.22; e["y"] = 0.42
                    e["scale"] = e.get("scale", 1.0) * 1.3
                    placed.add(i)
                elif e["type"] == right_type:
                    e["x"] = 0.78; e["y"] = 0.42
                    e["scale"] = e.get("scale", 1.0) * 1.3
                    placed.add(i)
                elif e["type"] in ("key", "arrow", "circle"):
                    bridge_y = 0.48 + bridge_idx * 0.08
                    e["x"] = 0.5
                    e["y"] = min(bridge_y, 0.72)
                    e["scale"] = e.get("scale", 1.0) * 1.15
                    placed.add(i)
                    bridge_idx += 1

    # ── "open" pattern: key opens X → position openables around key ──
    elif central_type == "key" and "open" in t:
        open_slot = 0
        for i, e in enumerate(elements):
            if e["type"] in ("building", "circle", "house") and e["type"] != central_type and i not in placed:
                if open_slot == 0:
                    e["x"] = 0.22; e["y"] = 0.55
                elif open_slot == 1:
                    e["x"] = 0.78; e["y"] = 0.55
                else:
                    e["x"] = 0.5; e["y"] = 0.68
                e["scale"] = e.get("scale", 1.0) * 0.9
                placed.add(i)
                open_slot += 1

    # ── Place remaining elements in a ring around the composition ──
    ring_positions = [(0.50, 0.10), (0.12, 0.28), (0.88, 0.28),
                      (0.12, 0.62), (0.88, 0.62), (0.50, 0.78),
                      (0.12, 0.10), (0.88, 0.10)]
    ri = 0
    for i, e in enumerate(elements):
        if i in placed:
            continue
        if ri < len(ring_positions):
            e["x"] = ring_positions[ri][0]
            e["y"] = ring_positions[ri][1]
            e["scale"] = e.get("scale", 1.0) * 0.75
            ri += 1


def _infer_visuals_local(narration: str, scene_num: int, total: int) -> dict | None:
    """Pure local semantic engine — analyzes narration for mood, biomes, entities.
    Understands narrative arcs. No API calls. Returns visual scene dict."""
    text = narration

    # ── Detect scene type (story / flowchart / timeline / diagram / chart) ──
    scene_type = _detect_scene_type(text)

    # Non-story types (flowchart, timeline, diagram, map, charts, etc.)
    # use the specialized element generators in _infer_visuals.
    if scene_type != "story":
        return _infer_visuals(narration, scene_num, total)

    # ── Detect biome / setting ──
    bg = _detect_biome(text)
    biome_bg_type = bg["type"]

    # ── Detect mood ──
    mood = _detect_mood(text)

    # ── Narrative position ──
    narr_pos = _compose_narrative_position(scene_num, total)

    # ── Extract entities ──
    entities = _extract_entities(text)

    # ── Build title from top entities ──
    if entities:
        title_part = entities[0][0].replace("_", " ").title()
        title = title_part[:30]
    else:
        title = f"Scene {scene_num}"

    # ── Mood color shifts background ──
    colors = bg["colors"]
    if mood == "somber":
        colors = [[max(0, c[0]-40), max(0, c[1]-30), max(0, c[2]-20)] for c in colors]
    elif mood == "hopeful":
        colors = [[min(255, c[0]+30), min(255, c[1]+20), c[2]] for c in colors]
    elif mood == "dramatic":
        colors = [[min(255, c[0]+40), max(0, c[1]-20), max(0, c[2]-20)] for c in colors]
    elif mood == "surprising":
        colors = [[min(255, c[0]+50), c[1], c[2]] for c in colors]
    elif mood == "sad":
        colors = [[max(0, c[0]-20), max(0, c[1]-15), c[2]] for c in colors]

    # ── Compose elements from entities ──
    # Known entity types for scene-aware placement
    _KNOWN_TYPES = {"sun","moon","star","cloud","bird","water","wave","moon_path",
                    "mountain","cliff","hill","building","rock","totem","anchor",
                    "fire","campfire","lamp","animal","human","shadow_figure","eye",
                    "hand","face","path","fence","plant","flower","grass","tree",
                    "globe","whale","sea_serpent","ship","canoe","house","book",
                    "scroll","compass","crown","key","cross","coin","telescope",
                    "heart","gear","skull","clock","camera","filter","signal",
                    "movement","discard","awareness","edge","color_swatch","brain",
                    "man","woman","child","circle","arrow","fruit"}
    elements = []
    # Pass 1: position known scene entities
    known_entities = [(i, e) for i, e in enumerate(entities) if e[0] in _KNOWN_TYPES]
    synth_entities = [(i, e) for i, e in enumerate(entities) if e[0] not in _KNOWN_TYPES]
    for i, (etype, ecolor, _) in known_entities:
        n = len(known_entities)
        # Anti-overlap positioning: spread elements across frame
        # Top row: celestial/air elements (y=0.08-0.25)
        if etype in ("sun", "moon", "star", "cloud", "bird"):
            col = i % 4
            px = 0.1 + col * 0.25
            py = 0.08 + (i // 4) * 0.08
        # Water elements (fixed bottom position)
        elif etype in ("water", "wave", "moon_path"):
            px, py = 0.5, 0.65
        # Background landscape (mid-ground)
        elif etype in ("mountain", "cliff", "hill", "building"):
            col = i % 3
            px = 0.1 + col * 0.35
            py = 0.5
        # Ground-level objects
        elif etype in ("rock", "totem", "anchor", "fire", "campfire", "lamp"):
            col = i % 3
            px = 0.15 + col * 0.35
            py = 0.6
        # Characters/animals spread across ground
        elif etype in ("animal", "human", "shadow_figure"):
            step = 1.0 / max(n, 2)
            px = 0.1 + i * step * 0.7
            py = 0.55 + (i % 3) * 0.05
        # Face/body parts (centered)
        elif etype in ("eye", "hand", "face"):
            px, py = 0.5, 0.45
        elif etype in ("path", "fence"):
            px, py = 0.5, 0.55
        # Vegetation
        elif etype in ("plant", "flower", "grass", "tree"):
            col = i % 4
            px = 0.05 + col * 0.25
            py = 0.6 + (i // 4) * 0.06
        # New known types (camera, filter, etc.) — background layer
        else:
            col = i % 3
            px = 0.1 + col * 0.35
            py = 0.5 + (i // 3) * 0.08

        # Scale varies by type
        scale = 1.0
        if etype in ("mountain", "cliff", "whale", "sea_serpent", "wave", "globe"):
            scale = 1.3
        elif etype in ("star", "bird", "flower", "eye", "coin"):
            scale = 0.7
        elif etype in ("sun", "moon"):
            scale = 0.9
        elif etype in ("human", "shadow_figure", "animal"):
            scale = 0.8

        elements.append({
            "type": etype, "x": min(px, 0.85), "y": min(py, 0.85),
            "scale": scale, "fill": list(ecolor) if isinstance(ecolor, tuple) else ecolor
        })

    # Pass 2: position auto-synthesized concept words as floating cards
    for j, (orig_i, (etype, ecolor, _)) in enumerate(synth_entities):
        # Place in a ring around the frame edges
        total = len(synth_entities)
        angle = (j / max(total, 1)) * 6.283  # Full circle
        # Distribute around the frame edges, not center
        margin = 0.08
        if j % 4 == 0:  # Top edge
            px = margin + (j // 4 % 5) * 0.2
            py = margin
        elif j % 4 == 1:  # Right edge
            px = 0.88
            py = margin + (j // 4 % 6) * 0.13
        elif j % 4 == 2:  # Bottom edge
            px = margin + (j // 4 % 5) * 0.2
            py = 0.88
        else:  # Left edge
            px = margin
            py = margin + (j // 4 % 6) * 0.13
        elements.append({
            "type": etype, "x": min(px, 0.9), "y": min(py, 0.9),
            "scale": 0.7, "fill": list(ecolor) if isinstance(ecolor, tuple) else ecolor
        })

    # ── Semantic repositioning: arrange elements to tell a visual story ──
    _reposition_semantically(elements, text)

    # ── Narrative arc influences composition ──
    if narr_pos == "setup":
        # Wide establishing shots — fewer, smaller elements, more negative space
        for e in elements:
            e["scale"] = e.get("scale", 1.0) * 0.7
            e["y"] = min(e["y"] + 0.05, 0.85)
    elif narr_pos == "tension":
        # Tighter framing, more dramatic
        for e in elements:
            e["scale"] = e.get("scale", 1.0) * 1.2
        if mood in ("dramatic", "mysterious", "surprising"):
            colors = [[min(255, c[0]+20), max(0, c[1]-15), max(0, c[2]-10)] for c in colors]
    elif narr_pos == "climax":
        # Biggest, most dramatic
        for e in elements:
            e["scale"] = e.get("scale", 1.0) * 1.4
    elif narr_pos == "resolution":
        # Pull back, show the aftermath
        for e in elements:
            e["scale"] = e.get("scale", 1.0) * 0.85
            e["y"] = min(e["y"] + 0.03, 0.85)

    # ── Fallback if no entities found ──
    if not elements:
        if "desert" in text.lower() or "sand" in text.lower():
            elements = [
                {"type": "hill", "x": 0.5, "y": 0.65, "scale": 1.5, "fill": [200, 170, 120]},
                {"type": "sun", "x": 0.5, "y": 0.15, "scale": 1.0, "fill": [255, 200, 80]},
            ]
        elif "predator" in text.lower() or "hunt" in text.lower():
            elements = [{"type": "shadow_figure", "x": 0.5, "y": 0.6, "scale": 1.0, "fill": [20, 25, 30]}]
        elif "blood" in text.lower() or "attack" in text.lower():
            elements = [{"type": "fire", "x": 0.5, "y": 0.5, "scale": 0.8, "fill": [180, 30, 20]}]
        else:
            elements = [{"type": "cloud", "x": 0.5, "y": 0.3, "scale": 1.0, "fill": [200, 210, 220]}]

    # ── Atmosphere ──
    is_night = bg["type"] == "night"
    star_count = 30 if is_night else 0
    particles = "stars" if is_night else ("none")
    fog = mood in ("mysterious", "somber", "sad")

    # ── Camera ──
    camera_map = {"setup": None, "build": "ken_burns_in", "tension": "dolly_in",
                  "climax": "ken_burns_in", "resolution": "pan_left", "neutral": "ken_burns_in"}
    camera = camera_map.get(narr_pos, "ken_burns_in")

    return {
        "title": title,
        "mood": mood,
        "camera": camera,
        "visual": {
            "scene_type": "story",
            "bg": {"type": bg["type"], "colors": colors, "horizon": bg.get("horizon", 0.55),
                   "ground_color": bg.get("ground_color")},
            "elements": elements,
            "atmosphere": {"particles": particles, "fog": fog, "star_count": star_count},
        },
    }


def generate_script_from_narration(text: str) -> dict:
    """Split pre-written narration into scenes. Uses LLM for meaning-aware visuals
    when available, falls back to keyword-based _infer_visuals()."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    if len(paragraphs) < 4:
        sentences = [s.strip() for s in text.replace('?', '.').replace('!', '.').split('.') if s.strip()]
        sentences = [s + '.' for s in sentences if s]
        paragraphs = []
        chunk = []
        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 2:
                paragraphs.append(' '.join(chunk))
                chunk = []
        if chunk:
            paragraphs.append(' '.join(chunk))

    if len(paragraphs) < 2:
        paragraphs = [text]

    # Merge paragraphs into thematically coherent scenes
    merged = []
    buffer = []
    for p in paragraphs:
        buffer.append(p)
        word_count = sum(len(c.split()) for c in buffer)
        if word_count >= 15 or len(buffer) >= 2:
            merged.append(' '.join(buffer))
            buffer = []
    if buffer:
        tail = ' '.join(buffer)
        if len(tail.split()) >= 10:
            merged.append(tail)
        elif merged:
            merged[-1] = merged[-1] + ' ' + tail
        else:
            merged.append(tail)

    # Split merged scenes at contrast markers (but/however/yet at sentence boundaries)
    final_scenes = []
    for m in merged:
        parts = re.split(r'(?<=[.])\s+(?=(?:but|however|yet|instead|meanwhile|conversely|nevertheless|nonetheless|although|though|despite|unlike)\b)', m, flags=re.IGNORECASE)
        final_scenes.extend(p.strip() for p in parts if p.strip())

    title_words = final_scenes[0].split()[:6]
    title = " ".join(title_words).rstrip(".,!?")

    scenes = []
    # Track persistent story state across scenes for visual consistency
    story_state = {"bg": None, "recent_entities": [], "scene_num": 0}

    for i, para in enumerate(final_scenes):
        scene_num = i + 1
        raw_prompt = para.strip()
        if not raw_prompt:
            continue

        # Try LLM first for meaning-aware visuals
        llm_result = _infer_visuals_local(raw_prompt, scene_num, len(final_scenes))
        if llm_result:
            visuals = llm_result
            print(f"  Scene {scene_num}/{len(final_scenes)}: Local visual ✓")
        else:
            print(f"  Scene {scene_num}/{len(final_scenes)}: using keyword fallback")
            visuals = _infer_visuals(raw_prompt, scene_num, len(final_scenes))
        _enrich_story_context(visuals, raw_prompt, story_state, scene_num, len(final_scenes))

        scene = {
            "scene_num": scene_num,
            "title": visuals.get("title", " ".join(raw_prompt.split()[:4]).rstrip(".,!?")),
            "narration": raw_prompt,
            "mood": visuals.get("mood", "peaceful"),
            "camera": visuals.get("camera"),
            "visual_type": visuals.get("visual", {}).get("scene_type", "story"),
            "visual": visuals.get("visual", visuals),
        }
        scenes.append(scene)
        vt = scene["visual_type"]
        elems = len(scene["visual"]["elements"])
        print(f"           {vt:10s} {scene['mood']} ({elems} elems)")

    print(f"  Created {len(scenes)} scenes from narration")
    return {"title": title, "scenes": scenes}


def _enrich_story_context(visuals, text, state, scene_num, total):
    """Improve visual coherence by filtering elements and maintaining background consistency."""
    t = text.lower()
    vis = visuals.get("visual", {})
    elements = vis.get("elements", [])

    # Story scenes: keep only 3 most relevant elements for clean composition
    scene_type = vis.get("scene_type", "story")
    max_elems = 5 if scene_type != "story" else 3
    kept = []
    priority = []
    for i, elem in enumerate(elements):
        etype = elem.get("type", "")
        if scene_type != "story" and etype in ("text", "bar_chart", "pie_chart", "line_graph", "cycle_diagram", "venn_diagram", "comparison", "step_diagram", "network_diagram", "tree_diagram", "histogram", "scatter_plot"):
            kept.append(elem)
        elif etype in ("human", "animal"):
            priority.append((0, elem))
        elif elem.get("label", "") and len(elem["label"]) > 2:
            if elem["label"].lower() in t:
                priority.append((1, elem))
            else:
                priority.append((3, elem))
        else:
            priority.append((2, elem))

    priority.sort(key=lambda x: x[0])
    slot = max_elems - len(kept)
    kept.extend(e[1] for e in priority[:slot])
    vis["elements"] = kept[:max_elems]

    # Background consistency: carry same bg type forward unless text strongly suggests change
    if state["bg"] and scene_num > 1:
        bg = vis.get("bg", {})
        current_type = bg.get("type", "gradient") if isinstance(bg, dict) else "gradient"
        if current_type != state["bg"] and scene_num < total:
            if not re.search(r'\b(sunset|night|ocean|forest|indoor|desert|snow|fire|underwater|space)\b', t):
                if isinstance(bg, dict):
                    bg["type"] = state["bg"]
                    vis["bg"] = bg
    else:
        bg = vis.get("bg", {})
        if isinstance(bg, dict):
            state["bg"] = bg.get("type", "gradient")
    visuals["visual"] = vis



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
        scene_data.append({"frames": frames, "duration": sd, "timeline": tl, "narration": scene["narration"]})
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

        # ── Typewriter narration overlay (cinematic lower-third) ──
        narration_text = active.get("narration", "")
        if narration_text:
            seg_start = active["start"]
            seg_end = active["end"]
            seg_progress = (t - seg_start) / max(seg_end - seg_start, 0.01)
            char_count = int(len(narration_text) * max(0, seg_progress - 0.03) / 0.97)
            if char_count > 0 and char_count <= len(narration_text):
                typed = narration_text[:char_count]
                # Split into lines for wrapping
                ftw = _font(20)
                line_h = 30
                max_w = W - 120
                lines = []
                for word in typed.split():
                    if not lines:
                        lines.append(word)
                    else:
                        test = lines[-1] + " " + word
                        tw = cd.textbbox((0, 0), test, font=ftw)
                        if tw[2] - tw[0] > max_w:
                            lines.append(word)
                        else:
                            lines[-1] = test
                bar_h = len(lines) * line_h + 16
                bar_w = min(max(cd.textbbox((0, 0), l, font=ftw)[2] - cd.textbbox((0, 0), l, font=ftw)[0] for l in lines) + 40, W - 40)
                bx = (W - bar_w) // 2
                by = H - 230 - (len(lines) - 1) * 12
                cd.rounded_rectangle([bx, by, bx + bar_w, by + bar_h], radius=8, fill=(0, 0, 0, 160))
                for li, line in enumerate(lines):
                    lx = bx + 20
                    ly = by + 8 + li * line_h
                    cd.text((lx, ly), line, font=ftw, fill=(255, 255, 230))
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
    global FPS
    script = None
    custom_title = ""
    script_file = None

    # Parse flags
    args = sys.argv[1:]
    if "--title" in args:
        idx = args.index("--title")
        if idx + 1 < len(args):
            custom_title = args[idx + 1]
            args = args[:idx] + args[idx+2:]
    if "--fps" in args:
        idx = args.index("--fps")
        if idx + 1 < len(args):
            try:
                v = int(args[idx + 1])
                if v > 0:
                    config.VIDEO_FPS = v
                    FPS = v
                    print(f"  Using FPS={v}")
            except: pass
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
