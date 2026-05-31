import os
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
LLM_MODEL = os.getenv("LLM_MODEL", "moonshotai/kimi-k2.6:free")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"

TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")

VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", 1080))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", 1920))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", 24))

SHORTS_SIZE = (VIDEO_WIDTH, VIDEO_HEIGHT)
