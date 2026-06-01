"""Try This — interactive brain hacks, one quick illusion per short. Watch and experience."""

import random
import bank_manager
from src.high_retention import retention_tts

TRICKS = [
    {
        "hook": "Do not look away from the red dot in the center.",
        "setup": "Your brain is currently deleting the color green from your vision.",
        "action": "In three seconds, the image will change. You will see something that isn't actually there.",
        "reveal": "Look at the wall next to you. The afterimage is burned into your retina.",
        "explanation": "Your cones get fatigued. The brain projects the opposite color. You're seeing something that has zero physical existence.",
        "prompt": "That was your brain lying to you.",
        "image_style": "solid red dot in center, pure black background, high contrast, minimalist, 9:16",
    },
    {
        "hook": "Stare at the cross in the center. Do not move your eyes.",
        "setup": "In a moment, four dots will appear on the edges of your screen.",
        "action": "Without moving your eyes, count how many are red. Ready. Watch.",
        "reveal": "There were four dots. Three red, one blue. You missed the blue one.",
        "explanation": "Your peripheral vision is almost colorblind. Your brain assumed all four were red and you never questioned it.",
        "prompt": "You just experienced inattentional blindness.",
        "image_style": "white cross in center, four colored dots in corners, 3 red 1 blue, minimal design, 9:16",
    },
    {
        "hook": "Put your left hand on your forehead. Right hand on your stomach. Do it now.",
        "setup": "Hold for five seconds. Feel the temperature difference.",
        "action": "Now switch them. Left hand goes to stomach. Right hand goes to forehead.",
        "reveal": "Your left hand feels colder. But both hands are the same temperature.",
        "explanation": "Your brain compares sensations, it doesn't measure them. You just hacked your own nervous system.",
        "prompt": "That's your brain lying to you.",
        "image_style": "minimal illustration of two hands, clean white background, simple line art, 9:16",
    },
    {
        "hook": "Look at the center of the screen. Do not blink.",
        "setup": "I'm going to flash images at ten frames per second for ten seconds.",
        "action": "Starting now. Watch closely. ... Time's up. Now look at the wall next to you.",
        "reveal": "You see the afterimage. That image is not on the wall. It's in your brain.",
        "explanation": "Your eyes are cameras. Your brain is the projector. You're watching a movie that only exists inside your skull.",
        "prompt": "Your brain is the projector.",
        "image_style": "flashing abstract shapes, high contrast black and white, stroboscopic effect, 9:16",
    },
    {
        "hook": "Place your left hand palm up on the table. Stare at it.",
        "setup": "Take your right index finger and hover it one inch above your left palm. Do not touch.",
        "action": "Slowly move it in circles. Keep staring at your left palm.",
        "reveal": "You feel a tingling. A buzzing. Your brain created touch where there is none.",
        "explanation": "Your brain expected contact so strongly it generated the sensation. You just hallucinated touch. Nothing touched you.",
        "prompt": "You hallucinated touch.",
        "image_style": "close up of hand palm up, soft lighting, minimal background, 9:16, sense of anticipation",
    },
    {
        "hook": "I'm going to play a repeating sound. Listen carefully.",
        "setup": "The sound will stutter every second. You will hear every repetition.",
        "action": "Now I'm removing one repetition. Listen again.",
        "reveal": "You still heard it. The sound continued in your brain even after it stopped.",
        "explanation": "Your neural circuitry completes patterns automatically. Your brain prefers a predictable lie over an uncertain silence.",
        "prompt": "Your brain hears things that don't exist.",
        "image_style": "abstract sound waves, oscilloscope pattern, dark background with neon green lines, 9:16",
    },
    {
        "hook": "Look at your reflection on the black part of the screen.",
        "setup": "Look at your left eye. Now look at your right eye. Now back to left.",
        "action": "You cannot see your own eyes move. Did you notice?",
        "reveal": "Your brain edits out the motion between saccades. You have never actually seen your own eyes move.",
        "explanation": "The brain cuts out the blur during eye movement and splices together stable images. You're watching a movie with deleted frames.",
        "prompt": "You've never seen your own eyes move.",
        "image_style": "dark reflective surface, abstract eye reflection, minimal shadows, 9:16, cinematic noir",
    },
    {
        "hook": "I'm going to play a sentence backward. Listen.",
        "setup": "It will sound like gibberish. Just listen.",
        "action": "Now I'll play it forward. Now backward again.",
        "reveal": "You heard words that weren't there the first time. Once your brain knew the pattern, it imposed meaning on noise.",
        "explanation": "Your brain is a pattern-matching machine. It will find meaning in randomness if given a hint. You cannot turn this off.",
        "prompt": "Your brain finds meaning in noise.",
        "image_style": "abstract waveform visualization, glitch effect, dark background with neon blue, 9:16",
    },
    {
        "hook": "Pinch the skin between your thumb and index finger. Hard.",
        "setup": "Keep pinching. Feel the pain.",
        "action": "Now rub that spot vigorously with your other thumb while still pinching.",
        "reveal": "The pain dropped by half. Instantly.",
        "explanation": "Touch signals travel faster than pain signals. The faster signal literally closes the gate. You just hacked your spinal cord.",
        "prompt": "You hacked your own pain system.",
        "image_style": "minimal hand illustration, pressure point diagram, clean medical style, 9:16",
    },
    {
        "hook": "Read this sentence silently. Then close your eyes.",
        "setup": "Think about the smell of rain on hot concrete. Or the inside of an old book.",
        "action": "Close your eyes now. Wait three seconds.",
        "reveal": "You just smelled something that isn't there. Your brain created an odor with zero molecules in your nose.",
        "explanation": "Memory and smell are wired together. Your brain reconstructed a chemical experience from pure thought. You hallucinated a smell.",
        "prompt": "You hallucinated a smell.",
        "image_style": "abstract scent visualization, swirling lines, warm amber tones, 9:16, atmospheric",
    },
]


def generate_try_this_script() -> dict:
    entry = bank_manager.pick("try_this")
    if entry:
        print(f"  Using banked trick ({bank_manager.count('try_this')} left)")
        return entry

    print("  Bank empty, using fresh trick...")
    return _try_llm() or random.choice(TRICKS)


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Write ONE interactive brain hack or visual illusion for a short video. "
            "Format: a direct command ('Do not look away...'), a setup sentence, "
            "a countdown or action, a reveal, and a one-line explanation. "
            "The viewer must experience the effect in real time during the video. "
            "Format exactly:\n"
            "HOOK: [direct command, first 2 seconds]\n"
            "SETUP: [what the brain is doing, 3-5s]\n"
            "ACTION: [countdown or instruction]\n"
            "REVEAL: [what they just experienced]\n"
            "EXPLANATION: [one punchy line, 5-8s]\n"
            "PROMPT: [one line summary for the end]\n"
            "IMAGE: [short visual description for the image]\n\n"
            "Make it feel like a magic trick. The viewer must do something."
        )
        system = "You write interactive brain hacks and visual illusions. Short, punchy, experiential. They work in under 30 seconds."
        raw = _generate(prompt, temperature=0.9, max_tokens=500, system=system)
        if not raw:
            return None
        result = {}
        current = None
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("HOOK:"):
                current = "hook"
                result["hook"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("SETUP:"):
                current = "setup"
                result["setup"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("ACTION:"):
                current = "action"
                result["action"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("REVEAL:"):
                current = "reveal"
                result["reveal"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("EXPLANATION:"):
                current = "explanation"
                result["explanation"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("PROMPT:"):
                current = "prompt"
                result["prompt"] = line.split(":", 1)[-1].strip()
            elif line.upper().startswith("IMAGE:"):
                result["image_style"] = line.split(":", 1)[-1].strip() + ", 9:16"
        if result.get("hook") and result.get("reveal"):
            return result
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
