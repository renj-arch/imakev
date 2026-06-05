# imakev — AI Video Generator

**Completely free, unlimited, open-source AI video generation.**  
Generate YouTube Shorts, TikTok videos, and AI animations with zero paid APIs.

## Philosophy

- **No paid APIs** — All services used are 100% free forever
- **No API keys required** — Works out of the box with procedural content
- **Unlimited generation** — No rate limits, no daily caps, no credits
- **Open source** — MIT licensed, fork and modify freely

## How It Works

imakev has a layered fallback system that always produces output:

```
Script Generation (LLM or content bank)
  → Text-to-Speech (edge-tts, free & local)
  → Video Generation (multi-layered fallback):
      1. Procedural motion engine (no APIs, no GPU, always works)
      2. CogVideoX-2B (local, open-source, free — needs GPU)
      3. Coverr stock video (free stock footage)
      4. HF text-to-video (free inference API)
      5. AI image Ken Burns (Pollinations.ai, free)
      6. Stock photo Ken Burns (loremflickr, free)
      7. Pollinations.AI video (free API)
      8. HF Space T2V (Gradio Spaces, free tier)
      9. Storyboard animator (pure PIL, always works)
  → YouTube upload (optional, YouTube API)
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run animation mode (works immediately, no config needed)
python run_pipeline.py animation

# Run a specific mode (facts, riddles, etc.)
python run_pipeline.py facts

# Seed content banks (run once to populate 500+ entries per mode)
python seed_banks.py
```

## Modes

| Mode | Description |
|------|-------------|
| `animation` | AI animation from text prompt |
| `facts` | Surprising facts short |
| `what_if` | "What if?" scenarios |
| `how_it_works` | How things work |
| `riddles` | Riddles with answers |
| `would_you_rather` | "Would you rather?" |
| `history_minute` | History facts |
| `psychology` | Psychology hacks |
| `life_hacks` | Life hacks |
| `urban_legends` | Urban legend debunks |
| `coincidences` | Bizarre coincidences |
| `unsolved_mysteries` | Unsolved mysteries |
| `movie_trivia` | Movie trivia |
| `animal_kingdom` | Animal facts |
| `space_wonders` | Space facts |
| `box_office` | Box office facts |
| `challenges` | Try this challenge |
| `satisfying` | Satisfying content |
| `negative_hooks` | Dark hooks |
| `try_this` | Brain hacks |
| `loop` | Run all modes in sequence |

## Configuration

All settings are in `.env` (copy from `.env.example`). **Everything is optional:**

```
# LLM — free options: OpenRouter (free models), Google Gemini (free tier)
LLM_PROVIDER=openrouter
LLM_MODEL=moonshotai/kimi-k2.6:free
LLM_API_KEY=

# TTS — edge is free & local
TTS_PROVIDER=edge

# Video resolution & FPS
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
VIDEO_FPS=12

# Free AI video API (optional)
POLLINATIONS_KEY=

# HuggingFace token (optional, for HF Spaces)
HF_TOKEN=
```

Without any API keys, the system uses:
- Pre-seeded content banks (500+ entries per mode)
- Procedural motion video (no GPU, no API)
- Free stock photos and footage

## YouTube Automation

Enable automatic uploads by:
1. Creating a Google Cloud project + YouTube API v3 credentials
2. Saving `client_secret.json` in the project root
3. Run `upload_youtube.py` to authenticate (generates `token.pickle`)

## GitHub Actions

The included workflow (`.github/workflows/automation.yml`) runs on free GitHub Action minutes:
- Manual trigger with mode selection
- Auto mode cycles through all 20 modes
- Commits bank updates automatically

## Project Structure

```
imakev/
├── run_pipeline.py          # Main orchestrator
├── run_automatic.py         # Auto-run wrapper
├── bank_manager.py          # Content bank system
├── seed_banks.py            # Seed banks with fallback content
├── upload_youtube.py        # YouTube upload
├── config.py                # Configuration
├── animation_video.py       # Animation video generator
├── fact_video.py            # Mode-specific video generators (21 modes)
├── src/
│   ├── script_generator.py  # LLM client
│   ├── image_gen.py         # Image generation
│   ├── motion_video.py      # Procedural motion engine
│   ├── photo_video.py       # Photo/video sources
│   ├── engagement.py        # Visual hooks & branding
│   ├── storyboard_anim.py   # Storyboard animator
│   └── *.py                 # Script generators per mode
├── bank/                    # Pre-seeded content banks
├── assets/                  # Fonts, music, backgrounds
└── output/                  # Generated videos
```

## License

MIT — free to use, modify, and distribute.
