"""
Gmail + Google Sheets actions.

These take an already-authenticated `Credentials` object (built from a user's
stored OAuth tokens via app.google_oauth.credentials_from_json) rather than
handling OAuth themselves. See app/google_oauth.py and app/routers/google_router.py
for how a user connects their Google account through the web UI.
"""

from googleapiclient.discovery import build


def fetch_unread_emails(creds, query: str = "is:unread", max_results: int = 5) -> list[dict]:
    """Fetches subject/sender/snippet for emails matching a Gmail search query.
    Example queries: "is:unread", "from:results@college.edu", "subject:invoice" """
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata", metadataHeaders=["Subject", "From"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "sender": headers.get("From", "(unknown)"),
            "snippet": msg.get("snippet", ""),
        })
    return emails


def append_row_to_sheet(creds, spreadsheet_id: str, sheet_range: str, row_values: list) -> dict:
    """Appends one row to a Google Sheet.
    spreadsheet_id: the long ID in the sheet's URL between /d/ and /edit
    sheet_range: e.g. "Sheet1!A1" """
    service = build("sheets", "v4", credentials=creds)

    body = {"values": [row_values]}
    return service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
