"""
Gmail API - Complete Authorization
Paste the redirect URL to complete OAuth flow.
"""

import os
import pickle
import sys
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.pickle')
REDIRECT_URI = 'http://localhost:8888/'

def complete_auth(redirect_url):
    """Complete OAuth using the redirect URL."""

    # Parse the code from the URL
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)

    if 'code' not in params:
        print("ERROR: No 'code' parameter found in the URL")
        print("Make sure you copied the full URL from the address bar")
        return False

    code = params['code'][0]
    print(f"Authorization code received: {code[:20]}...")

    # Create flow and exchange code for token
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(code=code)
    creds = flow.credentials

    # Save token
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)
    print(f"Token saved to {TOKEN_FILE}")

    # Test connection
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()

    print(f"\n✓ Authorization successful!")
    print(f"✓ Connected as: {profile['emailAddress']}")
    print(f"✓ You can now send emails using send_email.py")

    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python complete_auth.py <redirect_url>")
        print("\nPaste the full URL from your browser address bar after authorizing.")
        print("Example: python complete_auth.py 'http://localhost:8888/?code=4/0...'")
        sys.exit(1)

    complete_auth(sys.argv[1])
