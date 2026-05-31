"""Upload video to YouTube via API v3 + auto-playlist + auto-comment."""

import sys, os, pickle, time
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.pickle"
PLAYLIST_NAME = "Neon City Chronicles"
PLAYLIST_DESC = "A continuous AI-generated cinematic series. Each chapter continues the story."


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


def get_or_create_playlist(youtube) -> str:
    """Get existing playlist ID or create a new one."""
    request = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
    response = request.execute()
    for item in response.get("items", []):
        if item["snippet"]["title"] == PLAYLIST_NAME:
            print(f"  Playlist found: {PLAYLIST_NAME}")
            return item["id"]

    # Create new playlist
    body = {
        "snippet": {
            "title": PLAYLIST_NAME,
            "description": PLAYLIST_DESC,
        },
        "status": {"privacyStatus": "public"},
    }
    result = youtube.playlists().insert(part="snippet,status", body=body).execute()
    print(f"  Playlist created: {PLAYLIST_NAME}")
    return result["id"]


def add_to_playlist(youtube, playlist_id: str, video_id: str):
    """Add video to playlist."""
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    youtube.playlistItems().insert(part="snippet", body=body).execute()
    print(f"  Added to playlist: {PLAYLIST_NAME}")


def upload(video_path: str, title: str, description: str = "", tags: list[str] = None, privacy: str = "public"):
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
            "selfDeclaredMadeForKids": False,
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
        playlist_id = get_or_create_playlist(youtube)
        add_to_playlist(youtube, playlist_id, video_id)
    except Exception as e:
        print(f"  Playlist skipped: {e}")

    # Auto-comment
    time.sleep(2)
    try:
        comment = f"What should happen in Chapter X? 👇"
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment}},
                }
            },
        ).execute()
        print(f"  Auto-commented")
    except Exception as e:
        print(f"  Auto-comment skipped: {e}")

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
