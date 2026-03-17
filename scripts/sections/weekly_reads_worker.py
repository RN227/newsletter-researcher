from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

import yaml

from scripts.models import WeeklyRead
from scripts.utils_history import append_history, get_recent_ids


CONFIG_PATH = Path("config/weekly_reads_pending.yml")


def _load_reads() -> List[dict]:
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return data


def run(issue_date: datetime) -> List[WeeklyRead]:
    recent_ids = get_recent_ids("reads")
    raw = _load_reads()

    items: List[WeeklyRead] = []
    urls_used: List[str] = []

    for entry in raw:
        url = (entry or {}).get("url") or ""
        if not url or url in recent_ids:
            continue

        title = (entry or {}).get("title") or "Interesting read"
        source = (entry or {}).get("source")

        items.append(WeeklyRead(title=title, url=url, source=source))
        urls_used.append(url)

        if len(items) >= 5:
            break

    if urls_used:
        append_history("reads", urls_used, issue_date.date().isoformat())

    return items

