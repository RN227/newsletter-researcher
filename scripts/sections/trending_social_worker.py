from __future__ import annotations

from datetime import datetime
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


def _save_pending_links(items: List[dict]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        if items:
            yaml.dump(items, f, allow_unicode=True, default_flow_style=False)
        else:
            f.write("")


def _fetch_page_snippet(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    return resp.text[:4000]


def run(issue_date: datetime) -> List[SocialItem]:
    """
    Build up to 4 social items from the pending list, skipping previously used URLs.
    Generates Brew & AI-style commentary (with emoji) via Claude.
    Used items are removed from the config YAML after processing.
    """
    recent_ids = get_recent_ids("social")
    raw_links = _load_pending_links()
    print(f"[social] Loaded {len(raw_links)} pending links")

    items: List[SocialItem] = []
    for entry in raw_links:
        url = (entry or {}).get("url") or ""
        if not url or url in recent_ids:
            continue

        platform = (entry or {}).get("platform") or "x"
        handle = (entry or {}).get("handle") or ""
        note = (entry or {}).get("note") or ""

        snippet = _fetch_page_snippet(url)
        print(f"[social] {url[:60]}... snippet={'yes' if snippet else 'no'}")

        commentary = comment_on_social(url=url, raw_text=snippet, note=note)

        items.append(
            SocialItem(
                platform=platform,
                handle=handle,
                post_url=url,
                commentary=commentary,
            )
        )

        if len(items) >= 4:
            break

    append_history("social", [i.post_url for i in items], issue_date.date().isoformat())

    # Remove used items from the config YAML (both this run and previously used)
    all_used = recent_ids | {i.post_url for i in items}
    remaining = [e for e in raw_links if (e or {}).get("url") not in all_used]
    if len(remaining) != len(raw_links):
        _save_pending_links(remaining)
        print(f"[social] Removed {len(raw_links) - len(remaining)} used items from config")

    print(f"[social] Final: {len(items)} social items")
    return items
