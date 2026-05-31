"""Upload video to YouTube via API v3 + auto-comment for engagement."""

import sys, os, pickle, time
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.pickle"


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


def upload(video_path: str, title: str, description: str = "", tags: list[str] = None, privacy: str = "public"):
    youtube = get_service()

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

    # Auto-comment for early engagement (algorithm boost)
    time.sleep(3)
    try:
        comment = f"Chapter X coming next. What should happen? 👇"
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment}},
                }
            },
        ).execute()
        print(f"  Auto-commented: '{comment}'")
    except Exception as e:
        print(f"  Auto-comment skipped: {e}")

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
