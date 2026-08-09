import json
from app.actions.telegram_action import send_telegram_message
from app.config import settings


def _safe_format(template: str, context: dict) -> str:
    """Fills in {placeholders} from context, ignoring any that aren't present
    instead of crashing, so a missing field doesn't break the whole run."""
    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    return template.format_map(_SafeDict(context))


def run_action(action_type: str, action_config: str, context: dict) -> tuple[str, str]:
    """
    Runs a single action in a workflow.

    Returns (log_message, chain_value):
      - log_message: short string shown in the execution log
      - chain_value: the actual content this action produced. The NEXT action
        in the same workflow can reference it via {last_action_result} in its
        own config text - this is what lets "News Digest" feed into "Telegram"
        as two separate, reusable actions instead of one combined one.
    """
    config = json.loads(action_config) if action_config else {}

    if action_type == "telegram":
        text = config.get("message", "Workflow triggered!")
        text = _safe_format(text, context)
        bot_token = config.get("bot_token") or context.get("telegram_bot_token") or settings.TELEGRAM_BOT_TOKEN
        chat_id = config.get("chat_id") or context.get("telegram_chat_id") or settings.TELEGRAM_CHAT_ID
        if not bot_token or not chat_id:
            raise ValueError("No Telegram bot token/chat ID configured. Add them in Settings first.")
        send_telegram_message(bot_token, chat_id, text)
        return f"Sent Telegram message: {text[:60]}", text

    if action_type == "sheets":
        from app.google_oauth import credentials_from_json
        from app.actions.gmail_sheets_action import append_row_to_sheet

        creds_json = context.get("google_credentials")
        if not creds_json:
            raise ValueError("Google account not connected. Connect it in Settings first.")

        spreadsheet_id = config.get("spreadsheet_id") or context.get("sheets_spreadsheet_id")
        if not spreadsheet_id:
            raise ValueError("No spreadsheet ID configured (set it on the action or in Settings).")

        sheet_range = config.get("range", "Sheet1!A1")
        columns = config.get("columns") or ["{subject}", "{sender}", "{snippet}"]
        row = [_safe_format(c, context) for c in columns]

        creds = credentials_from_json(creds_json)
        append_row_to_sheet(creds, spreadsheet_id, sheet_range, row)
        row_preview = ", ".join(row)
        return f"Row appended to Sheet: {row_preview}", row_preview

    if action_type == "news_digest":
        from app.actions.news_action import build_digest

        feed_urls = config.get("feed_urls", [])
        if not feed_urls:
            raise ValueError("No RSS feed URLs configured for this action.")

        openai_key = config.get("openai_api_key") or context.get("openai_api_key")
        important_only = bool(config.get("important_only", False))
        digest = build_digest(feed_urls, openai_key, important_only=important_only)

        if important_only and digest.strip().upper() == "NONE":
            return "Checked news - nothing important right now, notification skipped", "__SKIP__"

        return "News digest generated", digest

    raise ValueError(f"Unknown action_type: {action_type}")
