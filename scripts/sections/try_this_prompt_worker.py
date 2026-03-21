from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import feedparser

from scripts.models import PromptOfWeek
from scripts.utils_history import append_history, get_recent_ids
from scripts.llm_client import generate_prompt_from_web


FEEDS = [
    "https://news.google.com/rss/search?q=chatgpt+prompt+ideas&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=AI+prompt+examples+productivity&hl=en-US&gl=US&ceid=US:en",
]


def _fetch_prompt_signals(issue_date: datetime) -> List[dict]:
    one_week_ago = issue_date - timedelta(days=10)
    signals: List[dict] = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in getattr(feed, "entries", []):
            link = getattr(entry, "link", "") or ""
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""
            if not link or not title:
                continue
            published_parsed = getattr(entry, "published_parsed", None)
            if published_parsed:
                published_dt = datetime(
                    published_parsed.tm_year,
                    published_parsed.tm_mon,
                    published_parsed.tm_mday,
                )
                if published_dt < one_week_ago:
                    continue
            signals.append({"title": title, "url": link, "description": summary})
    return signals


def run(issue_date: datetime) -> Optional[PromptOfWeek]:
    recent_ids = get_recent_ids("prompts")
    signals = _fetch_prompt_signals(issue_date)
    generated = generate_prompt_from_web(signals)
    if not generated:
        return None

    pid = generated.get("id", "prompt")
    if pid in recent_ids:
        pid = f"{pid}-{issue_date.date().isoformat()}"

    prompt = PromptOfWeek(
        id=pid,
        title=generated.get("title", "Try this prompt"),
        cadence=generated.get("cadence", "weekly"),
        description=generated.get("description", ""),
        prompt_text=(generated.get("prompt_text") or "").strip(),
    )

    append_history("prompts", [pid], issue_date.date().isoformat())
    return prompt

