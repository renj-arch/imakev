import config

SYSTEM_PROMPT = """You are a YouTube Shorts script writer. Write short, engaging scripts (25-45 seconds when spoken).

Rules:
- Hook in the first 3 seconds
- Fast-paced and conversational
- Easy to understand without visuals
- Single clear topic or tip
- 40-80 words max

Return ONLY the script text. No titles, no metadata."""


def _generate_gemini(prompt: str, temperature: float = 0.8, max_tokens: int = 300, system: str = "") -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=config.LLM_API_KEY)
    cfg = types.GenerateContentConfig(max_output_tokens=max_tokens, temperature=temperature)
    if system:
        cfg.system_instruction = system
    response = client.models.generate_content(model=config.LLM_MODEL, contents=prompt, config=cfg)
    if response.text:
        return response.text.strip()
    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text.strip()
    return ""


def _generate_openai(prompt: str, temperature: float = 0.8, max_tokens: int = 300, system: str = "") -> str:
    from openai import OpenAI
    base = config.OPENROUTER_BASE if config.LLM_PROVIDER == "openrouter" else None
    client = OpenAI(api_key=config.LLM_API_KEY, base_url=base, timeout=15)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=config.LLM_MODEL, messages=messages, max_tokens=max_tokens, temperature=temperature,
    )
    text = response.choices[0].message.content
    return text.strip() if text else ""


def _generate(prompt: str, temperature: float = 0.8, max_tokens: int = 300, system: str = SYSTEM_PROMPT) -> str:
    try:
        if config.LLM_PROVIDER == "google":
            return _generate_gemini(prompt, temperature, max_tokens, system)
        return _generate_openai(prompt, temperature, max_tokens, system)
    except Exception as e:
        if hasattr(e, 'status_code') and e.status_code in (429, 402):
            pass
        return ""


def generate_script(topic: str = "", niche: str = "general knowledge") -> str:
    prompt = (
        f"Niche: {niche}\nTopic: {topic}\n\nWrite a short engaging YouTube Shorts script:"
        if topic
        else f"Niche: {niche}\n\nWrite a short engaging YouTube Shorts script on a {niche} topic:"
    )
    return _generate(prompt)


def generate_batch_scripts(count: int = 5, niche: str = "general knowledge") -> list[str]:
    return [_generate(f"Niche: {niche}\nBatch #{i+1}\n\nWrite a short engaging YouTube Shorts script:", temperature=0.9) for i in range(count)]


def generate_title_from_script(script: str) -> str:
    prompt = "Generate a click-worthy YouTube Shorts title (max 60 chars) from this script. Return ONLY the title.\n\n" + script
    return _generate(prompt, temperature=0.7, max_tokens=60, system="")
