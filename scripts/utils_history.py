from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set


HISTORY_DIR = Path("data/history")


def _load_history(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        return {}
    return {}


def _save_history(path: Path, data: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_recent_ids(kind: str, max_age_items: int = 12) -> Set[str]:
    """
    Return a set of recent ids for a given history kind.
    We store a mapping id -> ISO date string and keep only the last `max_age_items` entries.
    """
    path = HISTORY_DIR / f"{kind}_used.json"
    data = _load_history(path)
    # sort by date string descending and keep last max_age_items ids
    items = sorted(data.items(), key=lambda kv: kv[1], reverse=True)[:max_age_items]
    return {k for k, _ in items}


def append_history(kind: str, ids: List[str], iso_date: str) -> None:
    path = HISTORY_DIR / f"{kind}_used.json"
    data = _load_history(path)
    for _id in ids:
        data[_id] = iso_date
    _save_history(path, data)

