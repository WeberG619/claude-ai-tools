#!/usr/bin/env python3
"""
YouTube Video Uploader for BIM Ops Studio
Uses YouTube Data API v3 with OAuth2 refresh tokens for unattended uploads.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube"]

SCRIPT_DIR = Path(__file__).parent
CLIENT_SECRET = SCRIPT_DIR / "client_secret.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"

DEFAULT_TAGS = [
    "Revit", "BIM", "Autodesk Revit", "AI automation", "BIM automation",
    "Revit API", "RevitMCPBridge", "Model Context Protocol", "Claude AI",
    "AI agent", "BIM Ops Studio", "Weber Gouin"
]

DEFAULT_DESCRIPTION_FOOTER = """
---
BIM Ops Studio | AI-Powered Revit Automation
Website: https://www.bimopsstudio.com
GitHub: https://github.com/bimopsstudio

#Revit #BIM #AI #Automation
"""


def get_authenticated_service():
    """Authenticate and return YouTube API service."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                print(f"ERROR: {CLIENT_SECRET} not found.")
                print("Set up OAuth2 credentials at https://console.cloud.google.com/")
                print("1. Create project > Enable YouTube Data API v3")
                print("2. Create OAuth 2.0 Client ID (Desktop app)")
                print(f"3. Download client_secret.json to {SCRIPT_DIR}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path, title, description="", tags=None,
                 category_id="28", privacy="private",
                 is_short=False, publish_at=None, thumbnail=None):
    """
    Upload a video to YouTube.

    Args:
        video_path: Path to video file
        title: Video title
        description: Video description (footer auto-appended)
        tags: List of tags (defaults merged with DEFAULT_TAGS)
        category_id: YouTube category (28 = Science & Technology)
        privacy: "public", "private", or "unlisted"
        is_short: If True, prepend #Shorts to title
        publish_at: ISO 8601 datetime for scheduled publish
        thumbnail: Path to custom thumbnail image
    """
    youtube = get_authenticated_service()

    all_tags = list(set((tags or []) + DEFAULT_TAGS))

    full_description = description + DEFAULT_DESCRIPTION_FOOTER
    if is_short:
        full_description = "#Shorts\n" + full_description
        if "#Shorts" not in title:
            title = title + " #Shorts"

    body = {
        "snippet": {
            "title": title,
            "description": full_description,
            "tags": all_tags,
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    if publish_at and privacy == "private":
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(video_path, mimetype="video/mp4",
                            resumable=True, chunksize=10 * 1024 * 1024)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print(f"Uploading: {video_path}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"
    print(f"Upload complete: {video_url}")

    # Set custom thumbnail if provided
    if thumbnail and os.path.exists(thumbnail):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail)
            ).execute()
            print(f"Thumbnail set: {thumbnail}")
        except Exception as e:
            print(f"Thumbnail upload failed (may need verification): {e}")

    return video_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload video to BIM Ops Studio YouTube")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--description", default="", help="Video description")
    parser.add_argument("--tags", nargs="+", default=[], help="Additional tags")
    parser.add_argument("--privacy", default="private",
                        choices=["public", "private", "unlisted"])
    parser.add_argument("--short", action="store_true", help="Mark as YouTube Short")
    parser.add_argument("--publish-at", default=None,
                        help="Schedule publish (ISO 8601, e.g. 2026-02-10T15:00:00Z)")
    parser.add_argument("--category", default="28", help="Category ID (28=Sci&Tech)")
    parser.add_argument("--thumbnail", default=None, help="Path to thumbnail image")
    args = parser.parse_args()

    upload_video(
        video_path=args.video,
        title=args.title,
        description=args.description,
        tags=args.tags,
        category_id=args.category,
        privacy=args.privacy,
        is_short=args.short,
        publish_at=args.publish_at,
        thumbnail=args.thumbnail,
    )
