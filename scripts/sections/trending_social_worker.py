from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import requests
import yaml

from scripts.models import SocialItem
from scripts.utils_history import append_history, get_recent_ids
from scripts.llm_client import comment_on_social


CONFIG_PATH = Path("config/social_links_pending.yml")


def _load_pending_links() -> List[dict]:
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return data


def _fetch_page_snippet(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=5)
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    text = resp.text
    # Crude trim; we just want some context for the model, not full HTML.
    return text[:4000]


def run(issue_date: datetime) -> List[SocialItem]:
    """
    Build up to 5 social items from the pending list, skipping those that
    have previously been used, and generate Brew & AI-style commentary with Claude.
    """
    recent_ids = get_recent_ids("social")
    raw_links = _load_pending_links()

    items: List[SocialItem] = []
    for entry in raw_links:
        url = (entry or {}).get("url") or ""
        if not url or url in recent_ids:
            continue

        platform = (entry or {}).get("platform") or "x"
        handle = (entry or {}).get("handle") or ""
        note = (entry or {}).get("note") or ""

        snippet = _fetch_page_snippet(url)
        commentary = comment_on_social(url=url, raw_text=snippet, note=note)

        items.append(
            SocialItem(
                platform=platform,
                handle=handle,
                post_url=url,
                commentary=commentary,
            )
        )

        if len(items) >= 5:
            break

    append_history("social", [i.post_url for i in items], issue_date.date().isoformat())
    return items

