"""scripts/gmail_setup.py — One-time Gmail OAuth2 setup.

How to use:
1. Go to https://console.cloud.google.com
2. Create a project (or use existing)
3. Enable Gmail API: APIs & Services > Library > search "Gmail API" > Enable
4. Create OAuth2 credentials:
   - APIs & Services > Credentials > Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Download JSON, save as: credentials/gmail_credentials.json
5. Run this script: python scripts/gmail_setup.py
6. A browser window opens — sign in and grant permissions
7. Token saved to credentials/gmail_token.json (auto-refreshes)

After setup, the server can send and search emails without any browser interaction.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

CREDS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_FILE = CREDS_DIR / "gmail_credentials.json"
TOKEN_FILE = CREDS_DIR / "gmail_token.json"


def main():
    CREDS_DIR.mkdir(exist_ok=True)

    if not CREDENTIALS_FILE.exists():
        print(f"\nERROR: {CREDENTIALS_FILE} not found!")
        print()
        print("Steps to get it:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project (or select existing)")
        print("  3. Enable Gmail API:")
        print("     APIs & Services > Library > Gmail API > Enable")
        print("  4. Create OAuth2 credentials:")
        print("     APIs & Services > Credentials > Create Credentials > OAuth client ID")
        print("     Application type: Desktop app")
        print("  5. Download the JSON file")
        print(f"  6. Save it as: {CREDENTIALS_FILE}")
        print("  7. Run this script again")
        sys.exit(1)

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        print("Gmail is already authenticated! Token is valid.")
        print(f"Token file: {TOKEN_FILE}")
        return

    if creds and creds.expired and creds.refresh_token:
        print("Token expired, refreshing...")
        creds.refresh(Request())
    else:
        print("Starting OAuth2 flow — a browser window will open.")
        print("Sign in with the Google account you want to send emails from.")
        print()
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), SCOPES
        )
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\nDone! Token saved to: {TOKEN_FILE}")
    print("The server can now send and search emails via Gmail API.")


if __name__ == "__main__":
    main()
