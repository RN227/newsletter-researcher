from __future__ import annotations

import csv
from pathlib import Path

from scripts.models import IssueDraft


def write_links_csv(issue: IssueDraft, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "title", "url", "platform", "handle", "notes"])

        for n in issue.ai_in_the_news:
            writer.writerow(
                ["ai_in_the_news", n.title, n.source_url, "", "", ""]
            )
        for s in issue.trending_on_social:
            writer.writerow(
                [
                    "trending_on_social",
                    "",
                    s.post_url,
                    s.platform,
                    s.handle,
                    s.commentary,
                ]
            )
        for r in issue.weekly_reads:
            writer.writerow(["weekly_reads", r.title, r.url, "", "", ""])

