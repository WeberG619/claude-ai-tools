#!/usr/bin/env python3
"""
First-time YouTube OAuth authorization.
Opens browser for consent, saves token.json for future unattended use.
"""
import os
import sys
from pathlib import Path

# Add the script directory to find client_secret.json
SCRIPT_DIR = Path(__file__).parent
CLIENT_SECRET = SCRIPT_DIR / "client_secret.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

def authorize():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.exists():
        print(f"ERROR: {CLIENT_SECRET} not found!")
        sys.exit(1)

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid:
            print("Already authorized! Token is valid.")
            print(f"Token file: {TOKEN_FILE}")
            return
        elif creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            print("Token refreshed successfully!")
            return

    print("Starting OAuth authorization flow...")
    print("A browser window will open for you to sign in and authorize.")
    print(f"Sign in with: weber@bimopsstudio.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET), SCOPES)

    # Use port 8085 for the callback
    creds = flow.run_local_server(
        port=8085,
        prompt="consent",
        success_message="Authorization successful! You can close this tab."
    )

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"\nAuthorization complete!")
    print(f"Token saved to: {TOKEN_FILE}")
    print("You can now upload videos without re-authorizing.")

if __name__ == "__main__":
    authorize()
