"""Auto-generate a full documentary script JSON for any topic.
Usage:
    python new_script.py "How Spiders Spin Webs"
    python new_script.py "Why the Titanic Sank" --niche history --scenes 8
"""

import sys, os, re, json, random
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

import config
from src.scene_composer import SceneComposer


# ═══════════════════════════════════════════════════════════════
#  LLM SCRIPT GENERATION
# ═══════════════════════════════════════════════════════════════

def _generate(prompt: str, temperature: float = 0.8, max_tokens: int = 6000,
              system: str = "") -> str:
    """Call configured LLM (Google / OpenAI / OpenRouter / HuggingFace)."""
    try:
        if config.LLM_PROVIDER == "google":
            return _generate_gemini(prompt, temperature, max_tokens, system)
        return _generate_openai(prompt, temperature, max_tokens, system)
    except Exception as e:
        err = str(e)[:200]
        code = getattr(e, 'status_code', getattr(e, 'code', ''))
        print(f"  LLM error ({config.LLM_PROVIDER}): [{code}] {err}")
        return ""


def _generate_gemini(prompt: str, temperature: float = 0.8,
                     max_tokens: int = 6000, system: str = "") -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=config.LLM_API_KEY)
    cfg = types.GenerateContentConfig(
        max_output_tokens=max_tokens, temperature=temperature,
        system_instruction=system,
    )
    response = client.models.generate_content(
        model=config.LLM_MODEL, contents=prompt, config=cfg,
    )
    if response.text:
        return response.text.strip()
    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text.strip()
    return ""


def _generate_openai(prompt: str, temperature: float = 0.8,
                     max_tokens: int = 6000, system: str = "") -> str:
    from openai import OpenAI
    if config.LLM_PROVIDER == "openrouter":
        base, key, model = config.OPENROUTER_BASE, config.LLM_API_KEY, config.LLM_MODEL
    elif config.LLM_PROVIDER == "huggingface":
        base, key, model = config.HF_BASE, config.HF_API_KEY, config.HF_MODEL
    else:
        base, key, model = None, config.LLM_API_KEY, config.LLM_MODEL
    client = OpenAI(api_key=key, base_url=base, timeout=60)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=model, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    text = response.choices[0].message.content
    return text.strip() if text else ""


# ═══════════════════════════════════════════════════════════════
#  FALLBACK — SceneComposer (no LLM needed)
# ═══════════════════════════════════════════════════════════════

def _fallback_script(topic: str, n_scenes: int = 8) -> dict:
    """Rule-based fallback — works for ANY topic, no API required."""
    composer = SceneComposer()
    script = composer.compose_script(topic, n_scenes=n_scenes)

    # Wrap scenes with visual key for documentary format
    for scene in script.get("scenes", []):
        visual = {
            "bg": scene.pop("bg", {"type": "solid", "color": [240, 240, 235]}),
            "elements": scene.pop("elements", []),
            "atmosphere": scene.pop("atmosphere", {"particles": "none", "fog": False}),
        }
        scene["visual"] = visual

    return script


# ═══════════════════════════════════════════════════════════════
#  LLM PROMPT
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a documentary filmmaker and visual artist. You create compelling visual stories.
You output ONLY valid JSON. You describe every visual detail precisely."""

USER_PROMPT_TEMPLATE = """Create a 60-90 second documentary about: {topic}

For each scene, you'll provide narration AND a full visual description that an illustration engine can render.

Output a JSON object with this structure:
{{
  "title": "documentary title",
  "scenes": [
    {{
      "scene_num": 1,
      "title": "scene title",
      "narration": "one compelling sentence, 8-15 words, spoken naturally",
      "mood": "peaceful|dramatic|hopeful|somber|epic|mysterious",
      "camera": null or "ken_burns_in|pan_right|pan_left|dolly_in",
      "visual": {{
        "bg": {{
          "type": "gradient|night|ocean|indoor|solid|sunset",
          "colors": [[R,G,B], [R,G,B], ...],
          "horizon": 0.55 or null,
          "ground_color": [R,G,B] or null
        }},
        "elements": [
          {{
            "type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|ship|building|text|label|arrow|x_mark|line|circle|rect|cannon|flag|polygon|book|scroll|compass|globe|quill|lightbulb|fire|clock|gear|crown|key|coin|skull|map|bird|fish|grass|path",
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
- {n_scenes} scenes flowing like a documentary narrative
- First scene: strong hook. Last scene: meaningful conclusion.
- Vary scenes: close-ups, wide shots, different perspectives
- Each scene's narration is 8-15 words, spoken naturally
- The "visual" describes what the audience SEES during this scene
- Choose background type and colors that match the mood and setting
- Place 3-8 elements per scene for a complete composition
- Use rich, harmonious colors (exact [R,G,B] values)
- Use "text" or "label" type for on-screen titles/labels
- Use "x_mark" for crossing out myths, "arrow" for pointing
- VARY scenes — don't repeat the same element types in every scene

Respond with ONLY the JSON object, no other text."""


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def generate_script_json(topic: str, n_scenes: int = 8) -> dict:
    """Generate a full documentary script JSON for any topic.
    Uses LLM if available, falls back to SceneComposer (no API)."""
    prompt = USER_PROMPT_TEMPLATE.format(topic=topic, n_scenes=n_scenes)
    fallback = _fallback_script(topic, n_scenes=n_scenes)

    if not config.LLM_API_KEY:
        print("  No LLM API key set, using rule-based fallback")
        return fallback

    try:
        raw = _generate(prompt, temperature=0.8, max_tokens=6000, system=SYSTEM_PROMPT)
        if not raw:
            print("  LLM returned empty (check API key, rate limits, or model access)")
            print("  Using rule-based fallback")
            return fallback

        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)

        if "scenes" in data and len(data["scenes"]) >= 4:
            print(f"  LLM OK: {data['title']} ({len(data['scenes'])} scenes)")
            return data

        print(f"  LLM returned invalid script ({len(data.get('scenes', []))} scenes), using fallback")
    except Exception as e:
        print(f"  LLM error: {e}, using fallback")

    return fallback


def save_script(data: dict, topic: str) -> Path:
    """Save script JSON to a clean filename derived from the topic."""
    name = re.sub(r'[^a-z0-9]+', '_', topic.lower()).strip('_')
    filename = ROOT_DIR / f"{name}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {filename}")
    return filename


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Auto-generate a full documentary script JSON for any topic.",
    )
    parser.add_argument("topic", help="The documentary topic (e.g. 'How Spiders Spin Webs')")
    parser.add_argument("--scenes", "-n", type=int, default=8,
                        help="Number of scenes (default: 8)")
    parser.add_argument("--niche", default="general knowledge",
                        help="Niche for context (default: general knowledge)")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM, use rule-based generation only")

    args = parser.parse_args()

    print(f"\nGenerating script for: {args.topic}")
    print(f"  Scenes: {args.scenes}")

    if args.no_llm:
        print("  LLM disabled, using rule-based SceneComposer")
        data = _fallback_script(args.topic, args.scenes)
    else:
        data = generate_script_json(args.topic, args.scenes)

    path = save_script(data, args.topic)
    print(f"\nDone! Run with: python auto_story.py --script {path.name}")
    print(f"Or via GitHub: use script_file: {path.name}")


if __name__ == "__main__":
    main()
