"""
News Digest action. Fetches headlines from RSS feeds and, if an OpenAI API
key is available, summarizes them into a short digest. Falls back to a plain
bullet list of headlines if no API key is configured, so this still works
even before you've set up OpenAI.
"""

import feedparser


def fetch_rss_headlines(feed_urls: list[str], max_per_feed: int = 5) -> list[dict]:
    items = []
    for url in feed_urls:
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:max_per_feed]:
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
            })
    return items


def summarize_with_openai(items: list[dict], api_key: str, max_bullets: int = 5) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    content = "\n\n".join(f"{item['title']}: {item['summary']}" for item in items)
    prompt = (
        f"Summarize the following news items into {max_bullets} short, punchy bullet points. "
        f"Just the bullets, no preamble:\n\n{content}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def summarize_important_only(items: list[dict], api_key: str) -> str:
    """Used for the 'ping me only if something big happens' workflow. Asks
    the model to filter out routine news and only report genuinely major
    or breaking items - replying with exactly 'NONE' if nothing qualifies,
    so the caller can skip sending a notification entirely."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    content = "\n\n".join(f"{item['title']}: {item['summary']}" for item in items)
    prompt = (
        "Look at the following news items. If there is genuinely major, breaking, "
        "or urgent news among them, reply with 2-4 short bullet points summarizing "
        "just that. If nothing here is significant breaking news, reply with exactly "
        f"the single word: NONE\n\n{content}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


def build_digest(feed_urls: list[str], openai_api_key: str | None = None, important_only: bool = False) -> str:
    """Main entry point used by action_runner.py."""
    items = fetch_rss_headlines(feed_urls)
    if not items:
        return "No new articles found in the configured feeds."

    if openai_api_key:
        try:
            if important_only:
                return summarize_important_only(items, openai_api_key)
            return summarize_with_openai(items, openai_api_key)
        except Exception as e:
            # Fall back to a plain headline list rather than failing the whole workflow
            # just because the summarization step had an issue.
            headlines = "\n".join(f"- {item['title']}" for item in items[:8])
            return f"(Summary unavailable: {e})\n\n{headlines}"

    # No OpenAI key - can't judge "importance" without AI, so just list headlines.
    # (The workflow's important_only filtering only takes effect once a key is added.)
    return "\n".join(f"- {item['title']}" for item in items[:8])
