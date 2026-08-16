# AutoFlow — Personal Automation Platform

A self-hosted, full-stack automation platform that watches for triggers (a new email, a schedule,
a specific time of day) and runs a chain of actions in response (send a Telegram message, log to
a Google Sheet, summarize news with AI).

---

## Problem Statement

Everyday tasks like checking for new college notices, tracking job application emails, or reading
the morning news all require manually opening an app and looking for something new. This wastes
attention and means important updates are only noticed whenever you happen to check — not when
they actually happen.

AutoFlow solves this by watching for real events (new emails) and real schedules (a specific time
of day) automatically, and pushing only the relevant information straight to Telegram — no manual
checking required.

---

## Features

- Event-based triggers — reacts to new Gmail messages matching a search query, not just a timer
- Time-based triggers — run on a fixed interval or at an exact clock time every day
- Chainable actions — output from one action (e.g. an AI-generated news summary) feeds directly
  into the next (e.g. a Telegram message), without hardcoding combinations
- Multi-account Google support — connect and simultaneously monitor multiple Gmail inboxes (e.g.
  college and personal) from a single account
- AI-powered filtering — News Digest workflows can use OpenAI to judge whether anything is
  genuinely significant, and silently skip the notification if not
- One-tap Telegram connect — no manual bot tokens or chat IDs; a shared-bot + one-time-code flow
  links a Telegram account in two taps
- Full execution history — every workflow run is logged with status, duration, and result
- Mobile-responsive web UI — usable from any device, not just the machine running the server

---

## Technologies Used

**Backend:** Python, FastAPI, SQLAlchemy, APScheduler, JWT (python-jose), bcrypt
**Database:** PostgreSQL (production), SQLite (local development)
**Integrations:** Google OAuth2 (Gmail API, Sheets API), Telegram Bot API, OpenAI API, RSS (feedparser)
**Frontend:** HTML, CSS, vanilla JavaScript
**Deployment:** Render (web service + managed PostgreSQL), GitHub-integrated CI deploys, UptimeRobot

---

## Installation

### Prerequisites
- Python 3.12+
- A Telegram account
- A Google account
- A free Google Cloud project

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/autoflow.git
cd autoflow
```

### 2. Set up a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Fill in `.env`:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `TELEGRAM_BOT_TOKEN` — create a bot via @BotFather on Telegram
- Google OAuth credentials — see `README_SETUP.md`

### 5. Run it
```bash
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000/app**

For the complete step-by-step walkthrough (Google OAuth setup, deployment, multi-account
configuration), see `README_SETUP.md`.

---

## Future Improvements

- Move background job execution to Celery + Redis for async task processing at scale
- Add an analytics dashboard for execution history (success rate, average duration, trends)
- Switch Gmail polling to push notifications (Google Pub/Sub) instead of interval polling
- Add automated test coverage
- Google app verification, to remove the "unverified app" consent screen
