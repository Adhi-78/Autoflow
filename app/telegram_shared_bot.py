"""
Shared-bot Telegram connect flow.

Telegram doesn't let bots be created through an API - creating one always
requires a human going through @BotFather. So instead of every user making
their own bot, everyone connects to ONE shared bot (the one whose token
lives in .env as TELEGRAM_BOT_TOKEN). Telegram gives each user-to-bot
conversation its own unique chat ID automatically, so one bot can still
message many different people individually - this is how Zapier, IFTTT,
etc. all do it under the hood.

How it works:
1. User clicks "Connect Telegram" -> we generate a random code, save it on
   their Settings row, and hand them a t.me/<bot_username>?start=<code> link.
2. They tap it in Telegram, which sends "/start <code>" to the shared bot.
3. A background poller (poll_telegram_updates, called every ~15s by the
   scheduler) checks for new messages, matches the code to a user, and
   saves that user's chat_id automatically - no manual copying needed.
"""

import json
import os
import secrets
import requests

from app.config import settings

OFFSET_FILE = "telegram_offset.json"


def _load_offset() -> int:
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE) as f:
                return json.load(f).get("offset", 0)
        except Exception:
            return 0
    return 0


def _save_offset(offset: int):
    with open(OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)


def generate_connect_code() -> str:
    return secrets.token_urlsafe(8)


def get_bot_username(bot_token: str):
    """Calls Telegram's getMe once to find the bot's @username, so the
    frontend doesn't need the user to type it in manually."""
    try:
        resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("username")
    except Exception:
        return None


def build_connect_link(bot_token: str, code: str):
    username = get_bot_username(bot_token)
    if not username:
        return None
    return f"https://t.me/{username}?start={code}"


def poll_telegram_updates(db):
    """Called periodically by the scheduler. Checks for new /start <code>
    messages sent to the shared bot and links them to whichever user
    generated that code."""
    from app import models

    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return  # Shared bot not configured yet - nothing to poll

    offset = _load_offset()
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={"offset": offset + 1, "timeout": 0},
            timeout=10,
        )
        resp.raise_for_status()
        updates = resp.json().get("result", [])
    except Exception:
        return  # Network hiccup - just try again next poll

    highest_id = offset
    for update in updates:
        highest_id = max(highest_id, update.get("update_id", 0))
        message = update.get("message", {})
        text = message.get("text", "") or ""
        chat_id = message.get("chat", {}).get("id")

        if text.startswith("/start ") and chat_id:
            code = text.replace("/start ", "").strip()
            settings_row = (
                db.query(models.Settings)
                .filter(models.Settings.telegram_connect_code == code)
                .first()
            )
            if settings_row:
                settings_row.telegram_chat_id = str(chat_id)
                settings_row.telegram_connect_code = None
                db.commit()
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "You're connected to AutoFlow! Your workflow notifications will arrive here.",
                        },
                        timeout=10,
                    )
                except Exception:
                    pass  # Connection still succeeded even if this confirmation ping fails

    if highest_id > offset:
        _save_offset(highest_id)
