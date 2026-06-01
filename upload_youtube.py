"""Upload video to YouTube via API v3 + auto-playlist + viral SEO."""

import sys, os, json, pickle, random
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.viral_seo import generate_viral_title, generate_viral_description, generate_viral_tags, generate_viral_hashtags, CHANNEL_HANDLE
from src.viral_thumbnail import save_viral_thumbnail
from src.keywords import get_youtube_category

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.pickle"
PERF_FILE = Path(__file__).parent / "performance.json"

PLAYLISTS = {
    "story": {"name": "Glitchverse: Story", "desc": "AI-generated cinematic series with edge-of-seat storytelling."},
    "facts": {"name": "Mind-Blowing Facts", "desc": "Daily facts that will change how you see the world."},
    "what_if": {"name": "What If? Imagination", "desc": "Imaginative what if scenarios that spark curiosity."},
    "how_it_works": {"name": "How Things Actually Work", "desc": "Everyday objects explained in 30 seconds."},
    "riddles": {"name": "Riddles That Break Your Brain", "desc": "Riddles only 1% can solve. Are you that 1%?"},
    "would_you_rather": {"name": "Would You Rather?", "desc": "Impossible choices. Which side are you on?"},
    "history_minute": {"name": "History You Weren't Taught", "desc": "History facts they didn't put in textbooks."},
    "psychology": {"name": "Psychology Hacks", "desc": "Mind tricks your brain doesn't want you to know."},
    "life_hacks": {"name": "Life Hacks That Work", "desc": "Clever hacks that save time, money, and effort."},
    "urban_legends": {"name": "Urban Legends Debunked", "desc": "Spooky stories vs the real truth."},
    "coincidences": {"name": "Crazy Coincidences", "desc": "Real coincidences that sound fake but are 100% true."},
    "unsolved_mysteries": {"name": "Unsolved Mysteries", "desc": "Real cold cases that still baffle investigators."},
    "movie_trivia": {"name": "Movie Secrets Revealed", "desc": "Behind-the-scenes secrets Hollywood kept hidden."},
    "animal_kingdom": {"name": "Animal Kingdom Facts", "desc": "Incredible animal facts from around the world."},
    "space_wonders": {"name": "Space Wonders", "desc": "NASA-confirmed space facts that break your brain."},
    "box_office": {"name": "Box Office Records", "desc": "Movie earnings records that will shock you."},
    "things_they_dont_teach": {"name": "Hard Truths", "desc": "Hard truths about life, money, career, and relationships they don't teach you in school."},
    "challenges": {"name": "Challenges & Stunts", "desc": "Fast-paced challenges and stunts that test your skills. Can you do them all?"},
    "satisfying": {"name": "Oddly Satisfying & DIY", "desc": "Oddly satisfying visuals, satisfying restorations, cleaning transformations, and DIY projects."},
    "negative_hooks": {"name": "Dark Truths", "desc": "Dark, uncomfortable truths about life, society, and human nature. Reality check incoming."},
    "try_this": {"name": "Try This — Brain Hacks", "desc": "Interactive brain hacks and visual illusions. Try them yourself and feel your brain break."},
}


def get_service():
    creds = None
    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


def get_or_create_playlist(youtube, playlist_key: str = "story") -> str:
    info = PLAYLISTS.get(playlist_key, PLAYLISTS["story"])
    request = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
    response = request.execute()
    for item in response.get("items", []):
        if item["snippet"]["title"] == info["name"]:
            print(f"  Playlist found: {info['name']}")
            return item["id"]

    body = {
        "snippet": {
            "title": info["name"],
            "description": info["desc"],
        },
        "status": {"privacyStatus": "public"},
    }
    result = youtube.playlists().insert(part="snippet,status", body=body).execute()
    print(f"  Playlist created: {info['name']}")
    return result["id"]


def add_to_playlist(youtube, playlist_id: str, video_id: str, playlist_key: str = "story"):
    info = PLAYLISTS.get(playlist_key, PLAYLISTS["story"])
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    youtube.playlistItems().insert(part="snippet", body=body).execute()
    print(f"  Added to playlist: {info['name']}")


def log_performance(video_id: str, title: str, mode: str):
    """Log uploaded video for performance tracking."""
    from datetime import datetime
    perf = {"videos": []}
    if PERF_FILE.exists():
        perf = json.loads(PERF_FILE.read_text())
    perf["videos"].append({
        "video_id": video_id,
        "title": title,
        "mode": mode,
        "uploaded_at": datetime.now().isoformat(),
    })
    PERF_FILE.write_text(json.dumps(perf, indent=2))


def upload(video_path: str, title: str = "", description: str = "", tags: list[str] = None,
           privacy: str = "public", playlist_key: str = "story", made_for_kids: bool = False,
           mode: str = "facts", script_data: dict = None):
    """Upload with viral SEO optimization."""
    youtube = get_service()

    # Generate viral title, description, tags if not provided
    if script_data and not title:
        title = generate_viral_title(mode, script_data)
    if script_data and not description:
        description = generate_viral_description(mode, script_data)
        hashtags = generate_viral_hashtags(mode)
        description += f"\n\n{hashtags}"
    if script_data and not tags:
        tags = generate_viral_tags(mode, script_data)
    if not title:
        title = "Amazing #Shorts"
    if not description:
        description = f"Subscribe for more! {CHANNEL_HANDLE}\n#shorts"
    if not tags:
        tags = ["shorts", mode, "youtubeshorts"]

    cat_id = {"education": "27", "entertainment": "24", "howto": "26"}.get(get_youtube_category(mode), "22")
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": cat_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    print(f"\n📤 Uploading: {title[:60]}...")
    print(f"   Mode: {mode.upper()} | Tags: {len(tags)}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"✅ Uploaded! https://youtu.be/{video_id}")

    # Add to playlist
    try:
        playlist_id = get_or_create_playlist(youtube, playlist_key)
        add_to_playlist(youtube, playlist_id, video_id, playlist_key)
    except Exception as e:
        print(f"   Playlist skipped: {e}")

    # Log for performance tracking
    log_performance(video_id, title, mode)

    print(f"   Channel: https://youtube.com/{CHANNEL_HANDLE}")
    return video_id


if __name__ == "__main__":
    mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        print("No MP4 files in output/")
        exit(1)
    video = str(mp4s[0])
    upload(
        video_path=video,
        title="Cat Kidnapping & Bike Rescue Squad | Cinematic Short Film",
        description="Daily cinematic short film.\n#shorts #cinematic",
        tags=["cinematic", "shorts", "story"],
        privacy="public",
    )
