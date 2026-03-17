from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from scripts.models import PromptOfWeek
from scripts.utils_history import append_history, get_recent_ids


CONFIG_PATH = Path("config/prompts.yml")


def _load_prompts() -> List[dict]:
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return data


def run(issue_date: datetime) -> Optional[PromptOfWeek]:
    recent_ids = get_recent_ids("prompts")
    prompts = _load_prompts()

    chosen = None
    for p in prompts:
        pid = (p or {}).get("id")
        if not pid or pid in recent_ids:
            continue
        chosen = p
        break

    if not chosen and prompts:
        chosen = prompts[0]

    if not chosen:
        return None

    pid = chosen.get("id", "prompt")

    prompt = PromptOfWeek(
        id=pid,
        title=chosen.get("title", "Try this prompt"),
        cadence=chosen.get("cadence", "weekly"),
        description=chosen.get("description", ""),
        prompt_text=(chosen.get("prompt") or "").strip(),
    )

    append_history("prompts", [pid], issue_date.date().isoformat())
    return prompt

