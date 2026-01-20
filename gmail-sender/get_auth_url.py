"""
Gmail API - Get Authorization URL
Prints the auth URL so you can open it in any browser you want.
"""

import os
from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')

# Use localhost redirect
REDIRECT_URI = 'http://localhost:8888/'

flow = Flow.from_client_secrets_file(
    CREDENTIALS_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

auth_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true',
    prompt='consent'
)

print("\n" + "="*70)
print("COPY THIS URL AND OPEN IT IN THE BROWSER WITH weber@bimopsstudio.com")
print("="*70)
print()
print(auth_url)
print()
print("="*70)
print("After authorizing, you'll be redirected to localhost:8888")
print("Copy the FULL URL from the address bar (including the code parameter)")
print("and paste it when running: python complete_auth.py")
print("="*70)
