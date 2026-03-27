from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import feedparser
import yaml

from scripts.models import WorkflowOfWeek
from scripts.utils_history import append_history, get_recent_ids
from scripts.llm_client import generate_workflow_from_web


FEEDS = [
    "https://news.google.com/rss/search?q=AI+workflow+productivity&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=AI+automation+use+cases&hl=en-US&gl=US&ceid=US:en",
]

THEME_CONFIG_PATH = Path("config/weekly_theme.yml")


def _load_workflow_topic() -> Optional[str]:
    if not THEME_CONFIG_PATH.exists():
        return None
    with THEME_CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    topic = (data.get("workflow_topic") or "").strip()
    return topic if topic else None


def _fetch_workflow_signals(issue_date: datetime) -> List[dict]:
    one_week_ago = issue_date - timedelta(days=7)
    signals: List[dict] = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        entries = getattr(feed, "entries", [])
        print(f"[workflow] Feed {url[:60]}...: {len(entries)} entries")
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


def run(issue_date: datetime) -> Optional[WorkflowOfWeek]:
    recent_ids = get_recent_ids("workflows")

    topic = _load_workflow_topic()
    if topic:
        print(f"[workflow] Using weekly theme: '{topic}'")
    else:
        signals = _fetch_workflow_signals(issue_date)
        print(f"[workflow] {len(signals)} signals fetched from feeds")

    generated = generate_workflow_from_web(
        signals=[] if topic else signals,
        topic=topic,
    )
    print(f"[workflow] LLM {'succeeded' if generated else 'returned None'}")

    if not generated:
        return None

    wf_id = generated.get("id", "workflow")
    if wf_id in recent_ids:
        wf_id = f"{wf_id}-{issue_date.date().isoformat()}"

    workflow = WorkflowOfWeek(
        id=wf_id,
        title=generated.get("title", "AI workflow of the week"),
        who_for=generated.get("who_for", ""),
        domain=generated.get("domain", "work"),
        problem=generated.get("problem", ""),
        tools=generated.get("tools", ""),
        steps_codeblock=(generated.get("steps_codeblock") or "").strip(),
    )

    append_history("workflows", [wf_id], issue_date.date().isoformat())
    return workflow
