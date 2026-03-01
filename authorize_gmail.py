"""
authorize_gmail.py — One-time Gmail OAuth 2.0 authorization script.

Run this ONCE locally to generate token.json.
The contents of token.json become the GMAIL_TOKEN GitHub Secret.

Usage:
  1. Make sure credentials.json is in this folder (downloaded from Google Cloud Console)
  2. Run: python3 authorize_gmail.py
  3. Sign in with matthieu.jammers@gmail.com when the browser opens
  4. Click Allow
  5. Copy the contents of the generated token.json file
  6. Paste it as the GMAIL_TOKEN secret in your GitHub repository
"""

import os
import json

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main():
    print("\nLinkedIn Automation — Gmail Authorization\n")
    print("=" * 50)

    # Check credentials.json exists
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\nERROR: {CREDENTIALS_FILE} not found in this folder.")
        print("\nTo fix this:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Sign in with matthieu.jammers@gmail.com")
        print("  3. Go to APIs & Services → Credentials")
        print("  4. Click your OAuth 2.0 Client ID")
        print("  5. Click 'Download JSON' and save as credentials.json in this folder")
        return

    creds = None

    # Check if token already exists (for refresh)
    if os.path.exists(TOKEN_FILE):
        print(f"Found existing {TOKEN_FILE} — checking if it needs refresh...")
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

        if creds.expired and creds.refresh_token:
            print("Token expired — refreshing automatically...")
            creds.refresh(Request())
            print("Token refreshed successfully.")
        elif creds.valid:
            print("Existing token is still valid — no action needed.")

    # If no valid credentials, run the full OAuth flow
    if not creds or not creds.valid:
        print("\nOpening browser for authorization...")
        print("Please sign in with: matthieu.jammers@gmail.com\n")

        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        print("\nAuthorization successful!")

    # Save the token
    token_data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        creds.scopes,
        "expiry":        creds.expiry.isoformat() if creds.expiry else None,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\nToken saved to {TOKEN_FILE}")
    print("\n" + "=" * 50)
    print("NEXT STEP:")
    print(f"  1. Open {TOKEN_FILE} with any text editor")
    print("  2. Copy the entire file contents (Cmd+A, Cmd+C on Mac)")
    print("  3. Go to: https://github.com/scalrize/linkedin-automation")
    print("  4. Click Settings → Secrets and variables → Actions")
    print("  5. Add a new secret named: GMAIL_TOKEN")
    print("  6. Paste the file contents as the value")
    print("  7. Click 'Add secret'")
    print("\nYou're done! The system will handle all future token refreshes automatically.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
