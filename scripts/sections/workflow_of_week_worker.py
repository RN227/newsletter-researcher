from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml

from scripts.models import WorkflowOfWeek
from scripts.utils_history import append_history, get_recent_ids


CONFIG_PATH = Path("config/workflows.yml")


def _load_workflows() -> List[dict]:
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return data


def run(issue_date: datetime) -> Optional[WorkflowOfWeek]:
    recent_ids = get_recent_ids("workflows")
    workflows = _load_workflows()

    chosen = None
    for wf in workflows:
        wf_id = (wf or {}).get("id")
        if not wf_id or wf_id in recent_ids:
            continue
        chosen = wf
        break

    if not chosen and workflows:
        chosen = workflows[0]

    if not chosen:
        return None

    wf_id = chosen.get("id", "workflow")

    steps = chosen.get("steps") or ""
    steps_codeblock = steps.strip()

    workflow = WorkflowOfWeek(
        id=wf_id,
        title=chosen.get("title", "AI workflow of the week"),
        who_for=chosen.get("who_for", ""),
        domain=chosen.get("domain", ""),
        problem=chosen.get("problem", ""),
        tools=chosen.get("tools", ""),
        steps_codeblock=steps_codeblock,
    )

    append_history("workflows", [wf_id], issue_date.date().isoformat())
    return workflow

