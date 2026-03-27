from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import feedparser
import yaml

from scripts.models import PromptOfWeek
from scripts.utils_history import append_history, get_recent_ids
from scripts.llm_client import generate_prompt_from_web


FEEDS = [
    "https://news.google.com/rss/search?q=chatgpt+prompt+ideas&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=AI+prompt+examples+productivity&hl=en-US&gl=US&ceid=US:en",
]

THEME_CONFIG_PATH = Path("config/weekly_theme.yml")


def _load_prompt_topic() -> Optional[str]:
    if not THEME_CONFIG_PATH.exists():
        return None
    with THEME_CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    topic = (data.get("prompt_topic") or "").strip()
    return topic if topic else None


def _fetch_prompt_signals(issue_date: datetime) -> List[dict]:
    one_week_ago = issue_date - timedelta(days=10)
    signals: List[dict] = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        entries = getattr(feed, "entries", [])
        print(f"[prompt] Feed {url[:60]}...: {len(entries)} entries")
        for entry in entries:
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

    topic = _load_prompt_topic()
    if topic:
        print(f"[prompt] Using weekly theme: '{topic}'")
        signals: List[dict] = []
    else:
        signals = _fetch_prompt_signals(issue_date)
        print(f"[prompt] {len(signals)} signals fetched from feeds")

    generated = generate_prompt_from_web(signals=signals, topic=topic)
    print(f"[prompt] LLM {'succeeded' if generated else 'returned None'}")

    if not generated:
        return None

    pid = generated.get("id", "prompt")
    if pid in recent_ids:
        pid = f"{pid}-{issue_date.date().isoformat()}"

    prompt = PromptOfWeek(
        id=pid,
        title=generated.get("title", "Try this prompt"),
        cadence=generated.get("cadence", "weekly"),
        intro=generated.get("intro", ""),
        description=generated.get("description", ""),
        prompt_text=(generated.get("prompt_text") or "").strip(),
    )

    append_history("prompts", [pid], issue_date.date().isoformat())
    return prompt
