"""How Things Work — curated explanations, tracker-driven, LLM fallback."""

import random
from src.tracker import pick

HOOKS = [
    "Ever wondered how this works?", "Here's how it actually works.",
    "You use it every day. But how does it work?", "Let me explain how this works.",
    "The simple science behind how this works.",
]

TOPICS = [
    ("a zipper", "A zipper works using interlocking teeth. Each tooth has a tiny hook on top and a hollow on the bottom. When you slide the zipper up, the slider forces the teeth together at a precise angle, locking hook into hollow. When you pull down, the slider splits them apart again."),
    ("a microwave", "A microwave uses a magnetron that shoots electromagnetic waves at 2.4 gigahertz. These waves bounce around the metal box and excite water molecules in your food, making them vibrate 2.4 billion times per second, creating friction heat that cooks from the inside out."),
    ("a lock and key", "Inside a pin tumbler lock, spring-loaded pins block the cylinder from turning. The correct key pushes each pin pair to exactly the right height so the gap aligns with the cylinder edge. Only then can the cylinder rotate and unlock."),
    ("a pencil", "Pencil lead is graphite mixed with clay. When you write, tiny graphite layers slide off onto paper. More clay means harder lighter marks (H), more graphite means softer darker marks (B). The eraser uses pumice to abrade graphite off the paper."),
    ("a camera", "A camera works like your eye. Light enters through the lens which bends rays to focus them. The aperture opens wide in dim light and closes in bright. The shutter opens for a fraction of a second to let light hit the sensor, converting photons into a digital image."),
    ("a refrigerator", "A fridge doesn't add cold — it removes heat. Liquid refrigerant evaporates into gas inside the fridge, absorbing heat. A compressor squeezes it back into liquid outside, releasing the heat into your kitchen. This cycle repeats constantly."),
    ("a battery", "A battery stores chemical energy. Inside are two different metals separated by an electrolyte. When connected, a chemical reaction sends electrons from one metal to the other through the wire. That flow of electrons is electricity."),
    ("a toilet", "When you flush, the handle opens a flapper valve. Water rushes from tank to bowl, creating a siphon that pulls everything out. The tank refills and a water seal prevents sewer gases from coming back up."),
    ("a lightbulb", "An incandescent bulb sends electricity through a thin tungsten filament. The resistance heats it to over 2,000 degrees Celsius, making it glow white hot. LED bulbs work differently: electrons move through a semiconductor and release energy directly as light."),
    ("a faucet", "Inside a faucet, turning the handle lifts a rubber washer away from a hole. This opens a path for water to flow from the pipe through the spout. The aerator at the tip adds air to the stream, using less water while maintaining pressure."),
    ("an escalator", "An escalator is a moving staircase powered by a single motor turning a chain loop that pulls steps in a continuous circle. Each step has wheels on two tracks — one for the top and one for the bottom, which flatten at the ends so you can step on and off safely."),
    ("a piano", "When you press a piano key, a felt-covered hammer strikes a metal string tuned to a specific pitch. The hammer immediately falls back so the string can vibrate. A felt damper stops vibration when you release the key."),
    ("a bicycle", "A bicycle converts your pedaling into forward motion through a chain and gears. Pedals turn the chainring, which drives the rear wheel through the chain. Gears change the ratio so you can go faster on flat ground or climb hills with less effort."),
    ("an umbrella", "An umbrella uses a sliding mechanism along a central pole. When pushed up, metal ribs connected to the slider expand outward, stretching the fabric into a dome shape. The curved shape deflects rain and wind away from you."),
    ("a vending machine", "When you insert money and press a button, the machine sends a signal to a motor that rotates a spiral coil holding your item. Each full rotation pushes one item off the shelf to drop into the collection tray below."),
    ("a smoke detector", "Inside a smoke detector, a tiny amount of radioactive material ionizes the air between two electrodes, creating a small electric current. Smoke particles disrupt this current, triggering the alarm. Some detectors use a light beam instead — smoke scatters the light onto a sensor."),
    ("a television remote", "Your remote uses infrared light to communicate. When you press a button, a microchip encodes the command and flashes an infrared LED in a specific pattern. The TV's sensor reads the flashing pattern and executes the command."),
    ("a keypad lock", "A keypad lock stores a PIN in memory. When you press numbers, the circuit compares your input to the stored PIN. If they match, it sends power to an electromagnet or motor that retracts the locking bolt."),
    ("a coffee maker", "A drip coffee maker heats water in a reservoir until it boils. The steam pushes water up a tube and over a showerhead that drips onto coffee grounds. Gravity pulls the brewed coffee through a filter and into the carafe below."),
    ("a vacuum cleaner", "A vacuum uses an electric motor to spin a fan that sucks air in. The rushing air creates low pressure inside, and outside air pushes in carrying dirt. Filters trap the particles while clean air is expelled back into the room."),
    ("a hand dryer", "A hand dryer uses a heating element to warm air while a fan blows it out at high speed. Some dryers have infrared sensors that detect your hands and automatically turn the fan on. Evaporation removes water from your skin faster."),
    ("a ceiling fan", "A ceiling fan motor spins blades at an angle, pushing air downward in summer. The moving air creates a wind chill effect that makes you feel cooler. Reversing the direction in winter circulates warm air trapped near the ceiling back down."),
    ("a stapler", "When you press down on a stapler, a spring-loaded mechanism drives a strip of metal staples forward. A metal anvil bends the staple legs inward as they pass through paper, clamping the pages together. The anvil can rotate to bend legs inward or outward."),
    ("a traffic light", "Traffic lights run on timers or sensors. A controller box at the intersection switches power between red, yellow, and green bulbs in a programmed sequence. Inductive loops in the road detect waiting cars and can extend green lights."),
    ("a speaker", "A speaker converts electrical signals into sound. An electromagnet inside moves a paper cone back and forth, pushing and pulling air to create sound waves. The strength and speed of the electrical signal determines volume and pitch."),
    ("a flushable toilet", "The flush mechanism uses gravity and siphoning. Lifting the flapper releases water from the tank into the bowl. The rush of water fills the siphon tube, creating suction that pulls waste from the bowl. When the tank empties, the siphon breaks and the flapper closes."),
    ("a combination lock", "Inside a combination lock, three or more rotating discs each have a notch. Aligning all notches with the locking bar requires turning the dial to the correct sequence. When all notches align, the bar falls into them and the lock opens."),
    ("a cork screw", "A corkscrew uses a spiral metal worm that twists into the cork. The sharp tip pierces the center, and the spiral's curves grip the cork material. When you pull the handle upward, the worm drags the cork out of the bottleneck."),
    ("a pressure cooker", "A pressure cooker traps steam inside a sealed pot, raising the internal pressure. Higher pressure raises water's boiling point above 100°C, cooking food faster at higher temperatures. A safety valve releases excess pressure to prevent explosions."),
    ("a digital thermometer", "A digital thermometer uses a thermistor — a resistor that changes resistance with temperature. A microchip measures the resistance, calculates the temperature, and displays it. Some use infrared to measure thermal radiation from the surface."),
    ("a can opener", "A can opener uses a sharp cutting wheel and a serrated drive wheel. Squeezing the handles clamps both wheels onto the can rim. Turning the knob rotates the drive wheel, which moves the can while the cutting wheel slices through the lid."),
    ("a door hinge", "A door hinge has two flat plates called leaves connected by a central pin. One leaf attaches to the door, the other to the frame. The pin acts as a pivot point, allowing the door to swing open and closed in an arc."),
    ("a paper clip", "A paper clip uses spring tension. The bent wire forms two loops that slightly separate. When you slide it over paper, the wire flexes open and its tension clamps the pages together. The loop shapes prevent the wire from tearing the paper."),
    ("a fire extinguisher", "A fire extinguisher contains compressed gas and a extinguishing agent. Pulling the pin and squeezing the handle releases the gas, which pushes the agent up a tube and out the nozzle. The agent smothers the fire by removing oxygen or cooling the fuel."),
    ("a magnifying glass", "A magnifying glass uses a convex lens — thicker in the middle than at the edges. The curved shape bends light rays inward, making them converge. When you look through it, the lens creates a larger virtual image of the object behind it."),
    ("a door lock chain", "A door chain lock has a sliding bracket mounted on the door and a slot on the frame. When engaged, the chain slides into the slot and stops the door from opening more than a few inches. The chain's strength holds the door against forced entry."),
    ("a percolator coffee pot", "A percolator works by boiling water at the bottom of the pot. Steam pressure forces the hot water up a tube and over the coffee grounds in a basket. The water drips back down through the grounds, getting stronger with each cycle."),
    ("a fluorescent light", "Fluorescent lights contain mercury vapor. Electricity excites the mercury atoms, which emit ultraviolet light. The UV light hits a phosphor coating on the inside of the tube, which glows visible white light. They use less energy than incandescent bulbs."),
    ("a transistor", "A transistor is a tiny semiconductor switch. A small voltage applied to the middle layer controls whether electricity can flow between the other two layers. This allows transistors to amplify signals or act as on-off switches in computers."),
    ("a compass", "A compass needle is a small magnet balanced on a pivot. The Earth's magnetic field pulls one end of the needle toward magnetic north. The red end usually points north, letting you orient yourself with the markings on the compass housing."),
]

IMAGE_PROMPT_TEMPLATE = "cinematic close-up illustration: {topic}, detailed technical cross-section view, clean lighting, educational style, 9:16 vertical"


def generate_howitworks_script() -> dict:
    topics = pick("how_it_works", TOPICS, 4)
    hook = random.choice(HOOKS)

    title = f"{hook} {topics[0][0].capitalize()}"
    image_prompts = []
    tts_lines = []

    for topic, explanation in topics:
        image_prompts.append(IMAGE_PROMPT_TEMPLATE.format(topic=topic))
        tts_lines.append(explanation)

    return {
        "title": title[:70],
        "hook": hook,
        "topics": [t[0] for t in topics],
        "explanations": [t[1] for t in topics],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }
