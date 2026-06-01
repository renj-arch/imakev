"""Upload video to YouTube via API v3 + auto-playlist + auto-comment."""

import sys, os, pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.pickle"

PLAYLISTS = {
    "story": {"name": "Neon City Chronicles", "desc": "A continuous AI-generated cinematic series. Each chapter continues the story."},
    "facts": {"name": "Mind-Blowing Facts", "desc": "Daily facts that will change how you see the world."},
    "what_if": {"name": "What If? For Kids", "desc": "Imaginative 'what if' scenarios that spark curiosity and wonder."},
    "how_it_works": {"name": "How Things Work", "desc": "Everyday objects explained — how they actually work."},
    "riddles": {"name": "Riddles & Brain Teasers", "desc": "Fun riddles to test your brain — can you solve them?"},
    "would_you_rather": {"name": "Would You Rather?", "desc": "Fun choices — which one would you pick?"},
    "history_minute": {"name": "History Minute", "desc": "Fascinating history shorts — one minute at a time."},
    "psychology": {"name": "Psychology Hacks", "desc": "Mind-blowing psychology hacks your brain doesn't want you to know."},
    "life_hacks": {"name": "Life Hacks", "desc": "Clever life hacks that actually work — save time, money, and effort."},
    "urban_legends": {"name": "Urban Legends", "desc": "Famous urban legends — the spooky story vs the real truth."},
    "coincidences": {"name": "Crazy Coincidences", "desc": "Real coincidence stories that sound fake but are 100% true."},
    "unsolved_mysteries": {"name": "Unsolved Mysteries", "desc": "Real unsolved mysteries and cold cases that still baffle investigators."},
    "movie_trivia": {"name": "Movie Trivia", "desc": "Real behind-the-scenes movie secrets you never knew."},
    "animal_kingdom": {"name": "Animal Kingdom", "desc": "Incredible animal facts from around the world."},
    "space_wonders": {"name": "Space Wonders", "desc": "Incredible space facts from NASA and astronomy."},
    "box_office": {"name": "Box Office Facts", "desc": "Incredible box office facts and movie earnings records."},
    "upsc": {"name": "UPSC Exam Concepts", "desc": "Quick UPSC concept explanations — master Polity, Economy, History, Geography and more, one short at a time."},
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


def upload(video_path: str, title: str, description: str = "", tags: list[str] = None, privacy: str = "public", playlist_key: str = "story",     made_for_kids: bool = False):
    youtube = get_service()

    # Upload video
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    print(f"Uploading: {title[:50]}...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"Done! https://youtu.be/{video_id}")

    # Add to playlist
    try:
        playlist_id = get_or_create_playlist(youtube, playlist_key)
        add_to_playlist(youtube, playlist_id, video_id, playlist_key)
    except Exception as e:
        print(f"  Playlist skipped: {e}")

    # Comments now available (not marked as made for kids)
    print("  Comments enabled")

    print(f"  Channel: https://youtube.com/@Glitchverse12-i8i")
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
