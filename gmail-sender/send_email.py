"""
Gmail API Email Sender
Sends emails via Gmail API using OAuth2 credentials.
"""

import os
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.pickle')


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)


def create_message(sender, to, subject, body_text, body_html=None):
    """Create an email message."""
    if body_html:
        message = MIMEMultipart('alternative')
        message.attach(MIMEText(body_text, 'plain'))
        message.attach(MIMEText(body_html, 'html'))
    else:
        message = MIMEText(body_text)

    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def send_email(to, subject, body_text, body_html=None, sender='me'):
    """
    Send an email via Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject
        body_text: Plain text body
        body_html: Optional HTML body
        sender: Sender (use 'me' for authenticated user)

    Returns:
        Sent message details
    """
    service = get_gmail_service()
    message = create_message(sender, to, subject, body_text, body_html)

    result = service.users().messages().send(userId='me', body=message).execute()
    print(f"Email sent! Message ID: {result['id']}")
    return result


def send_cold_email(to, recipient_name, company_name=None):
    """
    Send a cold outreach email for BIM Ops Studio.

    Args:
        to: Recipient email address
        recipient_name: Name of the recipient
        company_name: Optional company name for personalization
    """
    subject = f"Quick Question for {recipient_name}"

    body_text = f"""Hi {recipient_name},

I came across {"your work at " + company_name if company_name else "your profile"} and wanted to reach out.

At BIM Ops Studio, we help architecture and engineering firms automate their Revit workflows and reduce manual drafting time by 40-60%.

Would you be open to a quick 15-minute call to see if this could help your team?

Best regards,
Weber Gouin
BIM Ops Studio
"""

    body_html = f"""
<html>
<body>
<p>Hi {recipient_name},</p>

<p>I came across {"your work at " + company_name if company_name else "your profile"} and wanted to reach out.</p>

<p>At <strong>BIM Ops Studio</strong>, we help architecture and engineering firms automate their Revit workflows and reduce manual drafting time by 40-60%.</p>

<p>Would you be open to a quick 15-minute call to see if this could help your team?</p>

<p>Best regards,<br>
<strong>Weber Gouin</strong><br>
BIM Ops Studio</p>
</body>
</html>
"""

    return send_email(to, subject, body_text, body_html)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python send_email.py <to_email> <recipient_name> [company_name]")
        print("Example: python send_email.py john@example.com John 'Acme Corp'")
        sys.exit(1)

    to_email = sys.argv[1]
    name = sys.argv[2]
    company = sys.argv[3] if len(sys.argv) > 3 else None

    send_cold_email(to_email, name, company)
