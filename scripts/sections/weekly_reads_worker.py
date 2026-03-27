from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
import yaml

from scripts.models import WeeklyRead
from scripts.utils_history import append_history, get_recent_ids
from scripts.llm_client import summarize_reads_items


CONFIG_PATH = Path("config/weekly_reads_pending.yml")


def _load_reads() -> List[dict]:
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return data


def _save_reads(items: List[dict]) -> None:
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


def run(issue_date: datetime) -> List[WeeklyRead]:
    """
    Build up to 3 weekly reads from the pending list. Fetches snippets where
    possible and uses Claude to generate source domain + 1-2 sentence descriptions.
    Used items are removed from the config YAML after processing.
    """
    recent_ids = get_recent_ids("reads")
    raw = _load_reads()
    print(f"[reads] Loaded {len(raw)} pending reads")

    # Filter to new items only and cap at 3
    candidates = []
    for entry in raw:
        url = (entry or {}).get("url") or ""
        if not url or url in recent_ids:
            continue
        candidates.append(entry)
        if len(candidates) >= 3:
            break

    print(f"[reads] {len(candidates)} new candidates after dedup")

    if not candidates:
        return []

    # Fetch page snippets for each candidate
    raw_for_llm = []
    for entry in candidates:
        url = entry.get("url") or ""
        snippet = _fetch_page_snippet(url)
        print(f"[reads] {url[:60]}... snippet={'yes' if snippet else 'no'}")
        raw_for_llm.append({
            "title": entry.get("title") or "",
            "url": url,
            "snippet": snippet or "",
        })

    # LLM generates source_domain + description for each
    enriched = summarize_reads_items(raw_for_llm)
    print(f"[reads] LLM enriched {len(enriched)} reads")

    items: List[WeeklyRead] = []
    urls_used: List[str] = []
    for entry in enriched:
        url = entry.get("url") or ""
        if not url:
            continue
        items.append(WeeklyRead(
            title=entry.get("title") or "Interesting read",
            url=url,
            source_domain=entry.get("source_domain") or None,
            description=entry.get("description") or None,
        ))
        urls_used.append(url)

    if urls_used:
        append_history("reads", urls_used, issue_date.date().isoformat())

    # Remove used items from config YAML (both this run and previously used)
    all_used = recent_ids | set(urls_used)
    remaining = [e for e in raw if (e or {}).get("url") not in all_used]
    if len(remaining) != len(raw):
        _save_reads(remaining)
        print(f"[reads] Removed {len(raw) - len(remaining)} used items from config")

    print(f"[reads] Final: {len(items)} reads")
    return items
