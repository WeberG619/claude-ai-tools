"""
Gmail API Authorization Script
Run this first to authorize access to your Gmail account.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.pickle')

def authorize():
    """Run OAuth flow and save token."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
        print(f"Found existing token at {TOKEN_FILE}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print(f"Starting OAuth flow...")
            print(f"Using credentials from: {CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)  # Use any available port

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        print(f"Token saved to {TOKEN_FILE}")

    # Test the connection
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    print(f"\nAuthorization successful!")
    print(f"Connected as: {profile['emailAddress']}")
    print(f"Total messages: {profile.get('messagesTotal', 'N/A')}")

if __name__ == '__main__':
    authorize()
