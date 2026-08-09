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

## 3. Set up your Telegram bot (2 minutes)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow the prompts, name it whatever you like
3. BotFather gives you a token like `123456:ABC-DEF...` → put this in `.env` as `TELEGRAM_BOT_TOKEN`
4. Send your new bot any message (e.g. "hi") — this lets it know where to reply
5. Visit this URL in your browser (replace `<TOKEN>`):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
6. Find `"chat":{"id": 123456789, ...}` in the response → that number is your `TELEGRAM_CHAT_ID`

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
2. Open **http://127.0.0.1:8000/app**
3. Register/log in
4. Go to **Settings**:
   - **Telegram** — paste your bot token + chat ID
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

## 9. Next steps (in order)

1. **Set up Google OAuth** (section 7 above) and connect your account through Settings.
2. **Build your real workflows** — a College Notice Tracker (Gmail → Sheets → Telegram) and a
   Morning News Digest (Schedule → News Digest → Telegram) are good first ones to try.
3. **Only after those work and you have spare time:** swap SQLite → PostgreSQL, add Celery + Redis
   for background task queueing instead of running actions synchronously, containerize with Docker.
   This is optional infrastructure polish — skip it if you're short on time, since it doesn't add
   any new capability, just changes what's running underneath.
