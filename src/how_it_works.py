"""How Things Work — curated everyday explanations for general audience."""

import random

HOOKS = [
    "Ever wondered how this works?", "Here's how it actually works.",
    "You use it every day. But how does it work?", "Let me explain how this works.",
    "The simple science behind how this works.",
]

TOPICS = [
    ("a zipper", "A zipper works using interlocking teeth. Each tooth has a tiny hook on top and a hollow on the bottom. When you slide the zipper up, the slider forces the teeth together at a precise angle, locking hook into hollow. When you pull down, the slider splits them apart again. One of the most elegant simple machines ever invented."),
    ("a microwave", "A microwave uses something called a magnetron, which shoots electromagnetic waves at 2.4 gigahertz. These waves bounce around the metal box and excite water molecules in your food, making them vibrate 2.4 billion times per second. That vibration creates heat through friction, cooking your food from the inside out."),
    ("a lock and key", "Inside a pin tumbler lock, there are spring-loaded pins split into two parts. When no key is inserted, the pins block the cylinder from turning. When you insert the correct key, its ridges push each pin pair up to exactly the right height so the gap between the pins aligns with the cylinder edge. Only then can the cylinder rotate and unlock."),
    ("a pencil", "What we call pencil lead is actually graphite mixed with clay. When you write, tiny layers of graphite slide off onto the paper. The H and B ratings tell you the ratio — more clay makes harder lighter marks (H), more graphite makes softer darker marks (B). The eraser is rubber with a gritty additive called pumice that physically abrades graphite off the paper."),
    ("a camera", "A camera works just like your eye. Light enters through the lens, which bends the rays to focus them. The aperture works like your iris, opening wide in dim light and closing in bright light. The shutter is like your eyelid — it opens for a precise fraction of a second to let light hit the sensor, which converts photons into electrical signals to create a digital image."),
    ("a refrigerator", "A refrigerator doesn't add cold — it removes heat. Inside, a liquid refrigerant flows through pipes and evaporates into gas, which absorbs heat from the food compartment. A compressor then squeezes that gas back into liquid outside the fridge, releasing the heat into your kitchen. The cycle repeats constantly, making the inside colder and colder."),
    ("a battery", "A battery stores chemical energy and converts it to electricity. Inside are two different metals called electrodes, separated by a chemical paste called electrolyte. When you connect a circuit, a chemical reaction strips electrons from one metal and sends them to the other through the wire — that flow of electrons is electricity. When all the chemical reactions are used up, the battery dies."),
    ("a toilet", "When you flush, the handle lifts a chain that opens a flapper valve at the bottom of the tank. Water rushes from the tank into the bowl, creating a siphon effect. The siphon pulls everything out of the bowl and down the pipe. As the tank empties, the flapper closes and a fill valve refills the tank. The bowl refills from the tank too, creating a water seal that stops sewer gases from coming up."),
    ("a lightbulb", "An incandescent bulb sends electricity through a thin tungsten filament. The filament resists the flow of electricity, which heats it to over 2,000 degrees Celsius — hot enough to glow white hot. The glass bulb is filled with argon gas to prevent the filament from burning up in oxygen. LED bulbs work differently: electrons move through a semiconductor and release energy as light instead of heat."),
    ("a faucet", "Inside a faucet is a simple valve mechanism. When you turn the handle, a screw mechanism lifts or slides a rubber washer away from a hole called the valve seat. This opens a path for water to flow from the pipe through the spout. The aerator at the tip adds air to the stream, making it smoother and using less water while maintaining pressure."),
    ("an escalator", "An escalator is a moving staircase powered by a single electric motor. The motor turns a chain loop that pulls the steps in a continuous circle. Each step has wheels on two tracks — one track for the top of the step and one for the bottom. At the top and bottom, the tracks flatten out, causing the steps to fold into a flat platform so you can step on and off safely."),
    ("a piano", "When you press a piano key, a felt-covered hammer strikes a metal string tuned to a specific pitch. The hammer immediately falls back so the string can vibrate freely. A felt damper then stops the string from vibrating when you release the key. Each key connects to its own hammer and damper through a precise mechanism of levers and springs called the action."),
]

IMAGE_PROMPT_TEMPLATE = "cinematic close-up illustration: {topic}, detailed technical cross-section view, clean lighting, educational style, 9:16 vertical"


def generate_howitworks_script() -> dict:
    topics = random.sample(TOPICS, min(4, len(TOPICS)))
    hook = random.choice(HOOKS)

    title = f"{hook} {topics[0][0].capitalize()}"
    image_prompts = []
    tts_lines = []

    for topic, explanation in topics:
        image_prompts.append(IMAGE_PROMPT_TEMPLATE.format(topic=topic))
        tts_lines.append(f"{explanation}")

    return {
        "title": title[:70],
        "hook": hook,
        "topics": [t[0] for t in topics],
        "explanations": [t[1] for t in topics],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }
