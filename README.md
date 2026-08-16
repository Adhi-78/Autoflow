# AutoFlow — Personal Automation Platform

A working "if this happens, do that" engine: schedule/webhook/Gmail triggers → Telegram/Sheets/email actions,
with logging built in. This is Phase 1, tested end-to-end and confirmed working.

## What's included right now (Phase 1 — tested & working)

- FastAPI backend with JWT auth (register/login)
- SQLite database (Users, Workflows, Actions, Executions)
- APScheduler running in the background, checking every 60 seconds for due workflows
- Telegram action (fully working)
- `/workflows/{id}/run-now` endpoint to test a workflow immediately, without waiting for its schedule
- Execution logging (status, message, duration) for every run

## What's stubbed for later (Phase 2/3 — code included, needs your own credentials)

- `app/actions/gmail_sheets_action.py` — Gmail read + Google Sheets append, fully written but requires
  your own Google Cloud OAuth credentials to run (instructions inside the file)
- News digest (RSS + OpenAI summary) — not yet written, see "Next steps" below

---

## 1. Apps/accounts you need

| What | Why | Cost |
|---|---|---|
| Python 3.10+ | Runs the backend | Free |
| A Telegram account | Get notified by your workflows | Free |
| A Google account | For Gmail + Sheets (Phase 2) | Free |
| Google Cloud Console project | To get Gmail/Sheets API access | Free |
| (Later) OpenAI API key | For news summarization | Free tier, then paid per use |

No credit card needed to get Phase 1 working.

---

## 2. Local setup

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the environment template and fill it in
cp .env.example .env
```

Open `.env` and set:
- `SECRET_KEY` — generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` — see step 3 below

### Known dependency gotcha (already fixed in requirements.txt)
Newer `bcrypt` (v5) breaks `passlib`'s backend detection and throws a
`password cannot be longer than 72 bytes` error on registration. This repo pins
`bcrypt==4.0.1` to avoid it — don't remove that pin.

---

## 3. Set up your shared Telegram bot (one-time, ~2 minutes)

As of this version, users don't create their own bot or paste a chat ID — they just click
"Connect Telegram" and tap a link. You (the app owner) still need ONE bot for everyone to connect to:

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow the prompts, name it whatever you like
3. BotFather gives you a token like `123456:ABC-DEF...` → put this in `.env` as `TELEGRAM_BOT_TOKEN`
4. That's it — no chat ID needed here. Each user gets their own chat ID automatically the moment
   they tap the connect link and message the bot.

**Why this works with one bot for everyone:** Telegram gives every person-to-bot conversation its
own unique chat ID, even though it's the same bot. This is how Zapier/IFTTT-style "Connect Telegram"
buttons work under the hood — you never create your own bot when connecting those services either.

---

## 4. Run it

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** — this gives you an interactive Swagger UI where you can test
every endpoint without writing any client code.

---

## 5. Try it end-to-end

**Register:**
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'
```

**Log in (get a token):**
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you@example.com&password=yourpassword"
```
Copy the `access_token` from the response.

**Create a workflow** (replace `<TOKEN>`):
```bash
curl -X POST http://127.0.0.1:8000/workflows/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Ping",
    "trigger_type": "schedule",
    "trigger_config": {"interval_minutes": 60},
    "actions": [
      {"action_type": "telegram", "action_config": {"message": "Workflow ran: {trigger_message}"}, "step_order": 1}
    ]
  }'
```
This copies `id` from the response as `<WORKFLOW_ID>`.

**Run it immediately** (don't wait for the schedule):
```bash
curl -X POST http://127.0.0.1:8000/workflows/<WORKFLOW_ID>/run-now \
  -H "Authorization: Bearer <TOKEN>"
```
Check your Telegram — you should get a message within seconds.

**Check the logs:**
```bash
curl http://127.0.0.1:8000/workflows/<WORKFLOW_ID>/logs \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 6. Project structure

```
autoflow/
├── requirements.txt
├── .env.example
├── README.md
└── app/
    ├── main.py                 # FastAPI app entrypoint, starts scheduler on boot
    ├── config.py                # Reads .env into a Settings object
    ├── database.py               # SQLAlchemy engine/session setup
    ├── models.py                  # User, Workflow, Action, Execution tables
    ├── schemas.py                  # Pydantic request/response models
    ├── auth.py                      # Password hashing, JWT creation/validation
    ├── scheduler_engine.py           # APScheduler: polls DB every 60s, runs due workflows
    ├── routers/
    │   ├── auth_router.py             # /auth/register, /auth/login
    │   └── workflow_router.py          # /workflows CRUD, /run-now, /logs
    └── actions/
        ├── telegram_action.py          # Working Telegram sender
        ├── action_runner.py             # Dispatches action_type -> the right function
        └── gmail_sheets_action.py        # Phase 2 stub — Gmail read + Sheets append
```

---

## 7. Google OAuth setup (needed for Gmail trigger + Sheets action)

1. Go to **https://console.cloud.google.com/** → create a new project
2. **APIs & Services → Library** → enable:
   - Gmail API
   - Google Sheets API
3. **APIs & Services → OAuth consent screen**:
   - User type: External
   - Add your own Google account as a test user
   - Scopes: add `gmail.readonly` and `spreadsheets`
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Web application** (not Desktop!)
   - Authorized redirect URI, exactly: `http://127.0.0.1:8000/google/callback`
5. Download the JSON file it gives you, rename it to `credentials.json`, and place it in your
   project root (same folder as `requirements.txt` — **not** inside `app/`)
6. Restart the server if it's running

That's it — no code changes needed. Once `credentials.json` exists, the "Connect Google Account"
button in Settings will work.

## 8. Using the web UI

1. Start the server: `uvicorn app.main:app --reload`
2. Open **http://127.0.0.1:8000/app**3. Register/log in
4. Go to **Settings**:
   - **Telegram** — click "Connect Telegram", a Telegram chat opens automatically, tap **Start**,
     and the page updates to "Connected" within a few seconds (no copying tokens/chat IDs)
   - **Google** — click "Connect Google Account" (needs `credentials.json` from step 7 above),
     approve access in the Google popup, you'll land back on Settings showing "Connected"
   - **OpenAI** — optional, paste an API key if you want AI-summarized news digests
5. Go to **Workflows** → build one:
   - **Schedule trigger**: runs every N minutes — good for News Digest, daily reminders, etc.
   - **Gmail trigger**: fires when new mail matches a search query (e.g. `is:unread from:college.edu`) —
     checked every few minutes by the background scheduler
   - **Actions** (add as many as you want, they run in order):
     - **Telegram** — sends a message; use `{subject}`, `{sender}`, `{snippet}` (from a Gmail
       trigger) or `{last_action_result}` (output of the previous action) as placeholders
     - **Append to Sheet** — writes a row to your connected Google Sheet
     - **News Digest** — fetches RSS feeds, summarizes with OpenAI (or lists headlines plainly
       if no OpenAI key is set)
6. Click **Run now** on any workflow to test it immediately, or **View logs** to see its history

**Example: chaining News Digest into Telegram** — add a News Digest action first, then a Telegram
action with the message set to `{last_action_result}`. The digest text automatically flows into
the Telegram message.

## 8b. Viewing it on your phone (same WiFi)

The page itself is now mobile-responsive, but it still only runs on your laptop — your phone just
needs to be told where to find it, on the same WiFi network:

1. Find your laptop's local IP:
   - Windows: run `ipconfig` in the terminal, look for "IPv4 Address" (e.g. `192.168.1.5`)
2. Start the server so it accepts connections from other devices, not just itself:
   ```
   uvicorn app.main:app --host 0.0.0.0 --reload
   ```
3. On your phone (same WiFi), open: `http://<your-laptop-ip>:8000/app` (e.g. `http://192.168.1.5:8000/app`)

**Important limitation:** this still requires your laptop to be on, awake, and running the server.
It is not the same as deploying the app to the internet — closing your laptop or losing WiFi breaks
phone access immediately. True "works from anywhere, laptop off" access requires actually deploying
to a cloud host (Render, Railway, etc.), which is a separate, larger step — not needed for local
development or demoing the project.

## 10. Deploying it (so it works from any device, laptop off)

This makes the app reachable from anywhere, not just your laptop on your WiFi. It's a bigger step
than anything above — budget a real chunk of time, not a quick toggle. Uses **Render** (free tier)
and **GitHub** (to hold your code, since Render deploys from a Git repo).

### Step 1 — Push your code to GitHub

1. Install Git if you don't have it: https://git-scm.com/downloads
2. Create a free GitHub account at https://github.com if you don't have one
3. Create a new repository on GitHub (empty, no README) — call it `autoflow`
4. In your project folder terminal:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/autoflow.git
   git push -u origin main
   ```

**Important — don't commit secrets.** Before step 4, create a `.gitignore` file in your project root
containing:
```
.env
autoflow.db
venv/
__pycache__/
credentials.json
token.json
telegram_offset.json
```
This keeps your secrets and local database out of the public repo.

### Step 2 — Create a Render account and database

1. Go to https://render.com, sign up (free, can use your GitHub account to sign in)
2. **New → PostgreSQL** → give it a name, free tier → Create
3. Once created, copy the **"Internal Database URL"** — you'll need it in Step 3

### Step 3 — Create the web service

1. **New → Web Service** → connect your GitHub repo
2. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Under **Environment**, add these variables:
   - `SECRET_KEY` — generate one locally with the same command from section 2
   - `DATABASE_URL` — paste the Internal Database URL from Step 2
   - `TELEGRAM_BOT_TOKEN` — your existing bot token
   - `GOOGLE_REDIRECT_URI` — `https://<your-render-app-name>.onrender.com/google/callback`
     (you'll know the exact URL once Render assigns it after first deploy)
4. Click **Create Web Service** — Render will build and deploy automatically

### Step 4 — Add your Google credentials securely

Don't commit `credentials.json` to GitHub. Instead:
1. In Render, go to your service → **Environment → Secret Files**
2. Add a secret file named `credentials.json`, paste its contents
3. Set the env var `GOOGLE_CREDENTIALS_FILE` to whatever path Render mounts it at (shown in the
   Secret Files section, typically `/etc/secrets/credentials.json`)

### Step 5 — Update Google Cloud Console

Go back to your OAuth client in Google Cloud Console and add your new Render URL as an authorized
redirect URI (in addition to, or instead of, the localhost one):
```
https://<your-render-app-name>.onrender.com/google/callback
```

### Step 6 — Test it

Open `https://<your-render-app-name>.onrender.com/app` from your phone, anywhere, laptop closed.
Register, connect Telegram/Google, create a workflow.

### Known limitation of the free tier

Render's free web services "sleep" after 15 minutes of no traffic, which pauses your background
scheduler along with everything else — so a scheduled workflow might not fire exactly on time if
nobody's visited the site recently. A free external ping service (like UptimeRobot, hitting your
`/` endpoint every 10 minutes) keeps it awake continuously. This is a well-known workaround, not
something unique to this project — the same limitation applies to any app on Render's free tier.

## 9. Next steps (in order)

1. **Set up Google OAuth** (section 7 above) and connect your account through Settings.
2. **Build your real workflows** — a College Notice Tracker (Gmail → Sheets → Telegram) and a
   Morning News Digest (Schedule → News Digest → Telegram) are good first ones to try.
3. **Deploy it** (section 10) once everything works locally and you actually want laptop-independent
   access — not required for demoing the project in an interview.
