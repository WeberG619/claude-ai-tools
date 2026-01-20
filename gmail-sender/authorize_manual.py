"""
Gmail API Manual Authorization Script
For use when browser can't open automatically (WSL).
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
    """Run OAuth flow with manual URL copy/paste."""
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

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )

            auth_url, _ = flow.authorization_url(prompt='consent')

            print("\n" + "="*60)
            print("AUTHORIZATION REQUIRED")
            print("="*60)
            print("\n1. Open this URL in your browser:\n")
            print(auth_url)
            print("\n2. Sign in and authorize the app")
            print("3. Copy the authorization code and paste it below\n")

            code = input("Enter the authorization code: ").strip()

            flow.fetch_token(code=code)
            creds = flow.credentials

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        print(f"\nToken saved to {TOKEN_FILE}")

    # Test the connection
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    print(f"\nAuthorization successful!")
    print(f"Connected as: {profile['emailAddress']}")
    print(f"Total messages: {profile.get('messagesTotal', 'N/A')}")

if __name__ == '__main__':
    authorize()
