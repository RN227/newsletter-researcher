from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from scripts.models import IssueDraft
from scripts.sections.ai_in_news_worker import run as run_news
from scripts.sections.trending_social_worker import run as run_social
from scripts.sections.workflow_of_week_worker import run as run_workflow
from scripts.sections.try_this_prompt_worker import run as run_prompt
from scripts.sections.weekly_reads_worker import run as run_reads
from scripts.formatters.markdown_formatter import format_markdown
from scripts.formatters.csv_formatter import write_links_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Brew & AI newsletter draft.")
    parser.add_argument(
        "--issue-number",
        type=int,
        default=None,
        help="Issue number to use in the title.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Issue date in YYYY-MM-DD (defaults to today).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    issue_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date
        else date.today()
    )
    issue_dt = datetime.combine(issue_date, datetime.min.time())

    ai_news = run_news(issue_dt)
    social = run_social(issue_dt)
    workflow = run_workflow(issue_dt)
    prompt = run_prompt(issue_dt)
    reads = run_reads(issue_dt)

    draft = IssueDraft(
        issue_number=args.issue_number,
        issue_date=issue_date,
        subtitle="",
        ai_in_the_news=ai_news,
        trending_on_social=social,
        workflow_of_week=workflow,
        try_this_prompt=prompt,
        weekly_reads=reads,
    )

    markdown = format_markdown(draft)

    drafts_dir = Path("newsletters")
    drafts_dir.mkdir(parents=True, exist_ok=True)
    base_name = issue_date.isoformat()
    md_path = drafts_dir / f"{base_name}-freshly-brewed.md"
    csv_path = drafts_dir / f"{base_name}-links.csv"

    md_path.write_text(markdown, encoding="utf-8")
    write_links_csv(draft, csv_path)


if __name__ == "__main__":
    main()

