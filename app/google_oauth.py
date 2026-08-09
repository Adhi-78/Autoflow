"""
Handles the Google OAuth "web application" flow.

SETUP REQUIRED (see README for full steps):
1. Create a Google Cloud project, enable Gmail API + Sheets API
2. Create OAuth credentials of type "Web application"
3. Add this exact redirect URI in the Google Cloud Console:
     http://127.0.0.1:8000/google/callback   (local dev)
     https://your-app.onrender.com/google/callback   (deployed - see README section 10)
4. Download the credentials JSON and save it as `credentials.json`
   in your project root (same folder as requirements.txt)

Without that file, /google/connect will return a clear error telling you what's missing.
"""

import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def build_flow() -> Flow:
    return Flow.from_client_secrets_file(
        settings.GOOGLE_CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


def get_authorization_url(state: str) -> str:
    """Builds the Google consent screen URL the user gets redirected to."""
    flow = build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",       # needed to get a refresh_token
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code_for_credentials(code: str) -> Credentials:
    """After Google redirects back with a `code`, trades it for real credentials."""
    flow = build_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_to_json(creds: Credentials) -> str:
    return creds.to_json()


def credentials_from_json(creds_json: str) -> Credentials:
    """Rebuilds a Credentials object from what's stored in the database,
    refreshing the access token first if it has expired."""
    info = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds
