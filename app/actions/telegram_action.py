import requests


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> dict:
    """
    Sends a text message to a Telegram chat using a bot.

    Setup (takes ~2 minutes):
    1. Open Telegram, message @BotFather
    2. Send /newbot, follow prompts -> you get a bot token
    3. Message your new bot anything (so it can see your chat)
    4. Visit https://api.telegram.org/bot<TOKEN>/getUpdates
       -> find "chat":{"id": ...} -> that's your chat_id
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    response.raise_for_status()
    return response.json()
