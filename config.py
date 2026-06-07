import os, platform
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent
ASSETS_DIR = ROOT_DIR / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
FONTS_DIR = ASSETS_DIR / "fonts"
MUSIC_DIR = ASSETS_DIR / "music"
OUTPUT_DIR = ROOT_DIR / "output"
TEMP_DIR = ROOT_DIR / "temp"

for d in [ASSETS_DIR, BACKGROUNDS_DIR, FONTS_DIR, MUSIC_DIR, OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(exist_ok=True)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
HF_BASE = "https://api-inference.huggingface.co/v1/"
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
HF_API_KEY = os.getenv("HF_API_KEY", "")

TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")

VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", 720))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", 1280))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", 24))

SHORTS_SIZE = (VIDEO_WIDTH, VIDEO_HEIGHT)

BRAND_NAME = os.getenv("BRAND_NAME", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")


def get_font() -> str:
    """Find best available bold font across platforms."""
    font_dirs = []
    system = platform.system()
    if system == "Windows":
        font_dirs = [Path("C:/Windows/Fonts")]
    elif system == "Linux":
        font_dirs = [
            Path("/usr/share/fonts/truetype/dejavu"),
            Path("/usr/share/fonts/truetype/liberation"),
            Path("/usr/share/fonts/truetype/noto"),
        ]
    elif system == "Darwin":
        font_dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library/Fonts",
        ]

    names = [
        "impact.ttf", "arialbd.ttf", "arial.ttf",
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf", "LiberationSans.ttf",
        "NotoSans-Bold.ttf", "NotoSans.ttf",
        "Arial Bold.ttf", "Arial.ttf",
    ]

    for d in font_dirs:
        if d.exists():
            for name in names:
                candidates = list(d.rglob(name)) if d.is_dir() else []
                if candidates:
                    return str(candidates[0])

    return str(font_dirs[0] / names[3]) if font_dirs else names[3]
