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

WORKFLOWS_CONFIG_PATH = Path("config/workflows.yml")


def _load_workflows() -> List[dict]:
    if not WORKFLOWS_CONFIG_PATH.exists():
        return []
    with WORKFLOWS_CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return [w for w in data if isinstance(w, dict) and w.get("id")]


def _save_workflows(items: List[dict]) -> None:
    with WORKFLOWS_CONFIG_PATH.open("w", encoding="utf-8") as f:
        if items:
            yaml.dump(items, f, allow_unicode=True, default_flow_style=False)
        else:
            f.write("")


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
    all_workflows = _load_workflows()

    # Split into unused (available to publish) and used (available as examples)
    unused = [w for w in all_workflows if w.get("id") not in recent_ids]
    used_examples = [w for w in all_workflows if w.get("id") in recent_ids]

    if unused:
        # Pass the author's rough draft to Claude to flesh out into the full format.
        # The entry can be as sparse as a title + a few notes — Claude does the rest.
        chosen = unused[0]
        wf_id = chosen.get("id", "workflow")
        print(f"[workflow] Polishing author draft: '{chosen.get('title', '')}'")

        signals = _fetch_workflow_signals(issue_date)
        generated = generate_workflow_from_web(
            signals=signals,
            draft=chosen,
            examples=used_examples if used_examples else None,
        )
        print(f"[workflow] LLM {'succeeded' if generated else 'returned None'}")

        if not generated:
            return None

        # Keep the original id so history tracking works
        generated["id"] = wf_id
        if wf_id in recent_ids:
            wf_id = f"{wf_id}-{issue_date.date().isoformat()}"
            generated["id"] = wf_id

        workflow = WorkflowOfWeek(
            id=wf_id,
            title=generated.get("title", chosen.get("title", "AI workflow of the week")),
            who_for=generated.get("who_for", chosen.get("who_for", "")),
            domain=generated.get("domain", chosen.get("domain", "work")),
            problem=generated.get("problem", chosen.get("problem", "")),
            tools=generated.get("tools", chosen.get("tools", "")),
            steps_codeblock=(generated.get("steps_codeblock") or "").strip(),
        )

        append_history("workflows", [wf_id], issue_date.date().isoformat())

        # Remove the used draft from the config file
        remaining = [w for w in all_workflows if w.get("id") != chosen.get("id")]
        _save_workflows(remaining)
        print(f"[workflow] Removed '{chosen.get('id')}' from workflows config")

        return workflow

    # No drafts in the config — generate one from scratch with Claude.
    # Pass any previously published workflows as style/quality references.
    print(f"[workflow] No author drafts — generating from scratch with Claude")
    if used_examples:
        print(f"[workflow] Passing {len(used_examples)} past workflow(s) as style examples")

    signals = _fetch_workflow_signals(issue_date)
    print(f"[workflow] {len(signals)} signals fetched from feeds")

    generated = generate_workflow_from_web(
        signals=signals,
        examples=used_examples if used_examples else None,
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
