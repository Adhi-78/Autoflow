# AutoFlow — Setup Guide

Full step-by-step setup, local development, and deployment instructions.

## What's included

- FastAPI backend with JWT auth (register/login)
- PostgreSQL (production) / SQLite (local dev) database
- APScheduler running in the background, checking every 60 seconds for due workflows
- Schedule triggers (interval-based or a fixed daily time) and Gmail triggers (new email matching a search query)
- Telegram action, with a shared-bot one-tap connect flow
- Google Sheets action
- News Digest action (RSS + optional OpenAI summarization, with an "only if significant" filter)
- Multi-account Google support — connect and independently monitor multiple Gmail inboxes
- Full execution logging (status, message, duration) for every run
- Mobile-responsive web UI

---

## 1. Apps/accounts you need

| What | Why | Cost |
|---|---|---|
| Python 3.12+ | Runs the backend | Free |
| A Telegram account | Get notified by your workflows | Free |
| A Google account | For Gmail + Sheets | Free |
| Google Cloud Console project | To get Gmail/Sheets API access | Free |
| OpenAI API key | For news summarization (optional) | Free tier, then paid per use |

---

## 2. Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
```

Open `.env` and set:
- `SECRET_KEY` — generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `TELEGRAM_BOT_TOKEN` — see section 3 below

### Known dependency gotcha (already fixed in requirements.txt)
Newer `bcrypt` (v5) breaks `passlib`'s backend detection and throws a
`password cannot be longer than 72 bytes` error on registration. This repo pins
`bcrypt==4.0.1` to avoid it — don't remove that pin.

---

## 3. Set up your shared Telegram bot (one-time, ~2 minutes)

Users don't create their own bot or paste a chat ID — they click "Connect Telegram" and tap a
link. You (the app owner) need ONE bot for everyone to connect to:

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow the prompts, name it whatever you like
3. BotFather gives you a token like `123456:ABC-DEF...` → put this in `.env` as `TELEGRAM_BOT_TOKEN`
4. That's it — no chat ID needed here. Each user gets their own chat ID automatically the moment
   they tap the connect link and message the bot.

Telegram gives every person-to-bot conversation its own unique chat ID, even though it's the same
bot, so one bot can message many different people individually.

---

## 4. Run it

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/app**

---

## 5. Project structure

```
autoflow/
├── requirements.txt
├── .env.example
├── README.md
├── README_SETUP.md
└── app/
    ├── main.py
    ├── config.py
    ├── database.py
    ├── models.py
    ├── schemas.py
    ├── auth.py
    ├── google_oauth.py
    ├── telegram_shared_bot.py
    ├── scheduler_engine.py
    ├── routers/
    │   ├── auth_router.py
    │   ├── workflow_router.py
    │   ├── settings_router.py
    │   ├── google_router.py
    │   └── google_accounts_router.py
    ├── actions/
    │   ├── telegram_action.py
    │   ├── action_runner.py
    │   ├── gmail_sheets_action.py
    │   └── news_action.py
    └── static/
        └── index.html
```

---

## 6. Google OAuth setup (needed for Gmail trigger + Sheets action)

1. Go to **https://console.cloud.google.com/** → create a new project
2. **APIs & Services → Library** → enable:
   - Gmail API
   - Google Sheets API
3. **OAuth consent screen**:
   - User type: External
   - Add your own Google account(s) as test users, or publish the app to allow any Google account
   - Scopes: add `gmail.readonly`, `spreadsheets`, and `userinfo.email`
4. **Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Web application**
   - Authorized redirect URI, exactly: `http://127.0.0.1:8000/google/callback`
5. Download the JSON file, rename it to `credentials.json`, place it in your project root
   (same folder as `requirements.txt` — not inside `app/`)
6. Restart the server if it's running

---

## 7. Using the web UI

1. Start the server: `uvicorn app.main:app --reload`
2. Open **http://127.0.0.1:8000/app**
3. Register/log in
4. Go to **Settings**:
   - **Telegram** — click "Connect Telegram", a Telegram chat opens automatically, tap **Start**,
     the page updates to "Connected" within a few seconds
   - **Google Accounts** — optionally name the account (e.g. "College"), click "+ Connect a Google
     account", approve access, it appears in the list with its name/email
   - **OpenAI** — optional, paste an API key if you want AI-summarized news digests
5. Go to **Workflows** → build one:
   - **Schedule trigger** — every N minutes, or once a day at a specific time
   - **Gmail trigger** — fires when new mail matches a search query, checked every few minutes
   - **Actions** (add as many as you want, they run in order):
     - **Telegram** — sends a message; use `{subject}`, `{sender}`, `{snippet}`, `{account_label}`,
       or `{last_action_result}` as placeholders
     - **Append to Sheet** — writes a row to a connected Google Sheet
     - **News Digest** — fetches RSS feeds, summarizes with OpenAI, with an option to only notify
       if something significant is found
6. Click **Run now** to test a workflow immediately, or **View logs** for its history

---

## 8. Connecting multiple Google accounts

Go to Settings → Google Accounts, optionally name the account (e.g. "College"), then click
"+ Connect a Google account". Repeat for additional accounts — each connect adds a new one, it
doesn't replace what's already connected.

When building a Gmail-trigger workflow, or adding an "Append to Sheet" action, a "Which Google
account?" dropdown lets you pick which connected account that workflow uses. This allows genuinely
independent, simultaneous monitoring of multiple inboxes, checked by the same background scheduler.

Use `{account_label}` in Telegram message text to show which account triggered a notification.

---

## 9. Viewing it on your phone (same WiFi, local dev only)

1. Find your laptop's local IP: run `ipconfig` (Windows), look for "IPv4 Address"
2. Start the server so it accepts connections from other devices:
   ```
   uvicorn app.main:app --host 0.0.0.0 --reload
   ```
3. On your phone (same WiFi), open `http://<your-laptop-ip>:8000/app`

This still requires your laptop to be on and running the server. For access from any device
without that dependency, deploy it (section 10).

---

## 10. Deploying it

Uses **Render** (free tier) and **GitHub**.

### Step 1 — Push your code to GitHub

Create a `.gitignore` in your project root:
```
.env
autoflow.db
venv/
__pycache__/
credentials.json
token.json
telegram_offset.json
```

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/autoflow.git
git push -u origin main
```

### Step 2 — Create a Render account and database

1. Go to render.com, sign up
2. **New → PostgreSQL** → free tier → Create
3. Copy the **Internal Database URL**

### Step 3 — Create the web service

1. **New → Web Service** → connect your GitHub repo
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment variables:
   - `SECRET_KEY`
   - `DATABASE_URL` — the Internal Database URL from Step 2
   - `TELEGRAM_BOT_TOKEN`
   - `PYTHON_VERSION` — `3.12.4`
   - `GOOGLE_REDIRECT_URI` — `https://<your-app-name>.onrender.com/google/callback`
5. **Create Web Service**

### Step 4 — Add Google credentials securely

1. Render → your service → **Environment → Secret Files**
2. Add a secret file named `credentials.json`, paste its contents
3. Set `GOOGLE_CREDENTIALS_FILE` to the mounted path Render shows (typically `/etc/secrets/credentials.json`)

### Step 5 — Update Google Cloud Console

Add the Render URL as an additional authorized redirect URI:
```
https://<your-app-name>.onrender.com/google/callback
```

### Step 6 — Keep it awake

Render's free tier sleeps after 15 minutes of no traffic. Use a free service like UptimeRobot to
ping your app's URL every 5 minutes, keeping the background scheduler running continuously.

### Step 7 — Test it

Open `https://<your-app-name>.onrender.com/app` from any device.
