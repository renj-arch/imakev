"""Render one frame per scene from the Maya cinematic storyboard."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
import textwrap

W, H = 1280, 720

def E(typ, x=0.5, y=0.5, scale=1.0, **kw):
    d = {"type": typ, "x": x, "y": y, "scale": scale}; d.update(kw); return d

def render(elements, seed=42, ground=(60,130,60), sky_top=(140,180,220), sky_bot=(100,160,200), horizon=0.55, night=False):
    scene = {
        "bg": {"type": "gradient", "colors": [list(sky_top), list(sky_bot)], "horizon": horizon, "ground_color": list(ground)},
        "elements": elements,
        "atmosphere": {"particles": "stars" if night else "none", "star_count": 60 if night else 0, "fog": False},
        "mood": "peaceful",
        "style": {"vignette": 0.1},
    }
    gen = SketchGenerator(W, H, seed=seed)
    return gen.render_scene(scene)

def add_text(img, text):
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except: font = ImageFont.load_default()
    for i, ln in enumerate(textwrap.wrap(text, 65)):
        b = draw.textbbox((0,0), ln, font=font)
        draw.text(((W-b[2])//2, H-55+i*26), ln, fill=(60,55,50), font=font)
    return img

OUT = "scene_samples"
os.makedirs(OUT, exist_ok=True)

scenes = [
    (0, "Wide establishing - pyramid, mountain, sun, trees", [
        E("pyramid",0.7,0.72,5.0,steps=5), E("mountain",0.2,0.65,3.0),
        E("sun",0.88,0.12,3.0), E("tree",0.15,0.78,3.5),
        E("tree",0.85,0.8,2.5), E("cloud",0.3,0.2,3.0), E("cloud",0.7,0.25,2.5),
    ], {}),
    (1, "Pyramid rising above jungle", [
        E("pyramid",0.5,0.72,6.0,steps=5), E("tree",0.1,0.78,3.5), E("tree",0.9,0.78,3.0),
    ], {}),
    (2, "Astronomer tracking stars - night sky", [
        E("moon",0.85,0.12,3.0), E("star",0.2,0.1,2.0), E("star",0.4,0.08,1.5),
        E("star",0.6,0.12,1.8), E("star",0.9,0.25,1.5),
        E("human",0.5,0.7,3.5,pose="standing",gender="man",mood="peaceful"),
    ], {"sky_top":(20,20,50),"sky_bot":(40,40,70),"horizon":0.5,"ground":(30,50,30),"night":True}),
    (3, "What happened - city with question mark", [
        E("pyramid",0.35,0.75,4.0,steps=4), E("pyramid",0.65,0.78,3.0,steps=4),
        E("sun",0.88,0.12,3.0), E("house",0.2,0.78,2.0), E("house",0.8,0.8,1.5),
        E("question_mark",0.5,0.2,10),
    ], {}),
    (4, "Timeline - buildings begin fading", [
        E("building",0.3,0.72,2.5), E("building",0.5,0.68,3.0), E("building",0.7,0.72,2.5),
    ], {"sky_top":(160,180,200),"sky_bot":(180,200,220),"ground":(100,120,90)}),
    (5, "Workers stop building monuments", [
        E("human",0.35,0.72,2.5,pose="standing",gender="man"),
        E("human",0.5,0.7,2.5,pose="standing",gender="man"),
        E("pyramid",0.7,0.78,3.0,steps=3),
    ], {"sky_top":(150,170,190),"sky_bot":(170,190,210),"ground":(90,110,80)}),
    (6, "Abandoned throne with leaves", [
        E("throne",0.5,0.72,3.5), E("leaf",0.2,0.35,1.5), E("leaf",0.8,0.25,1.0),
    ], {"sky_top":(130,140,150),"sky_bot":(160,170,180),"ground":(80,80,70)}),
    (7, "War - two cities, warriors, fire", [
        E("pyramid",0.2,0.75,3.5,steps=4), E("pyramid",0.8,0.75,3.5,steps=4),
        E("human",0.35,0.72,2.5,pose="fighting_stance",gender="man",mood="angry"),
        E("human",0.65,0.72,2.5,pose="fighting_stance",gender="man",mood="angry"),
        E("fire",0.45,0.55,1.5),
    ], {"sky_top":(100,90,80),"sky_bot":(140,120,100),"ground":(100,70,50)}),
    (8, "Drought - enlarged sun, cracked earth", [
        E("sun",0.5,0.1,5.0), E("cracked_ground",0.5,0.75,3.0,width=8,height=3),
    ], {"sky_top":(220,180,140),"sky_bot":(255,220,180),"ground":(180,150,100),"horizon":0.45}),
    (9, "Failed crops - wilting plants, harsh sun", [
        E("tree",0.3,0.75,3.0), E("tree",0.5,0.72,3.5), E("tree",0.7,0.75,3.0),
        E("sun",0.88,0.1,4.0),
    ], {"sky_top":(180,200,180),"sky_bot":(200,220,200),"ground":(160,200,140)}),
    (10, "Food scarce - empty baskets, worried family", [
        E("basket",0.35,0.72,3.0), E("basket",0.65,0.72,3.0),
        E("human",0.4,0.68,3.0,pose="standing",gender="man",mood="sad"),
        E("human",0.6,0.7,2.5,pose="standing",gender="woman",mood="sad"),
    ], {"sky_top":(160,170,180),"sky_bot":(190,200,210),"ground":(100,100,80)}),
    (11, "City-states fight - buildings on fire", [
        E("building",0.3,0.5,2.0), E("building",0.7,0.5,2.0),
        E("fire",0.3,0.4,4.0), E("fire",0.7,0.38,4.0),
    ], {"sky_top":(100,90,80),"sky_bot":(140,120,100),"ground":(100,70,50),"horizon":0.3}),
    (12, "Forests cleared - trees remain", [
        E("tree",0.2,0.75,3.0), E("tree",0.4,0.72,3.5),
        E("tree",0.6,0.75,3.0), E("tree",0.8,0.78,2.5),
    ], {"sky_top":(140,180,200),"sky_bot":(170,200,220),"ground":(60,120,50)}),
    (13, "People leaving - walking away, footprints", [
        E("pyramid",0.78,0.68,4.5,steps=4),
        E("human",0.2,0.68,3.0,pose="walking",gender="man"),
        E("human",0.3,0.72,2.5,pose="walking",gender="woman"),
        E("human",0.38,0.76,2.0,pose="walking",gender="child"),
        E("footprint",0.05,0.8,2.5), E("footprint",0.12,0.84,2.0), E("footprint",0.18,0.88,1.8),
        E("sun",0.88,0.2,2.5),
    ], {"sky_top":(150,170,190),"sky_bot":(180,200,220),"ground":(80,130,70)}),
    (14, "Jungle reclaims - vines, trees over pyramid", [
        E("pyramid",0.5,0.72,4.0,steps=4), E("tree",0.2,0.75,3.5),
        E("tree",0.8,0.78,3.0), E("grass",0.3,0.85,1.0),
    ], {"sky_top":(60,130,100),"sky_bot":(100,180,140),"ground":(40,100,40)}),
    (15, "Maya did not vanish - past connects to present", [
        E("human",0.35,0.72,3.0,pose="standing",gender="man",mood="hopeful"),
        E("human",0.65,0.72,3.0,pose="standing",gender="man",mood="hopeful"),
        E("human",0.7,0.76,2.0,pose="standing",gender="child",mood="hopeful"),
        E("sun",0.88,0.12,3.0),
    ], {"sky_top":(180,200,220),"sky_bot":(200,220,240),"ground":(60,140,60)}),
    (16, "Cities fell, people remained - sunset", [
        E("pyramid",0.25,0.78,2.5,steps=3),
        E("human",0.75,0.72,3.0,pose="standing",gender="man",mood="hopeful"),
        E("human",0.8,0.75,2.0,pose="standing",gender="woman",mood="hopeful"),
        E("human",0.85,0.78,1.5,pose="standing",gender="child",mood="hopeful"),
        E("sun",0.5,0.55,4.0),
    ], {"sky_top":(255,180,100),"sky_bot":(200,120,80),"ground":(100,80,60),"horizon":0.5}),
]

for sid, label, elems, bg_kw in scenes:
    frame = render(elems, seed=100+sid, **bg_kw)
    add_text(frame, f"Scene {sid}: {label}")
    path = os.path.join(OUT, f"scene_{sid:02d}.png")
    frame.save(path)
    sz = os.path.getsize(path) // 1024
    print(f"Scene {sid:02d} — {sz} KB — {label}")

print(f"\nAll saved to {OUT}/")
