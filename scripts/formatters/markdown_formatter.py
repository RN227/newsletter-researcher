from __future__ import annotations

from datetime import date

from scripts.models import IssueDraft


def _format_date(d: date) -> str:
    return d.strftime("%b %-d, %Y")


def build_subtitle(issue: IssueDraft) -> str:
    if issue.ai_in_the_news:
        titles = [n.title for n in issue.ai_in_the_news[:3]]
        return ", ".join(titles)
    return issue.subtitle


def format_markdown(issue: IssueDraft) -> str:
    subtitle = build_subtitle(issue)
    lines = []

    lines.append(f"☕ Freshly Brewed #{issue.issue_number or ''}".rstrip())
    lines.append(subtitle)
    lines.append("")
    lines.append(_format_date(issue.issue_date))
    lines.append("")

    lines.append("# ☕ AI in the news")
    lines.append("")
    for item in issue.ai_in_the_news:
        lines.append(f"#### {item.title}")
        lines.append("")
        for p in item.summary_paragraphs:
            lines.append(p)
            lines.append("")
        lines.append(f"[Read more]({item.source_url})")
        lines.append("")

    lines.append("# ☕ Trending on social")
    lines.append("")
    for item in issue.trending_on_social:
        lines.append(f"- {item.platform} / {item.handle} – [{item.post_url}]({item.post_url})")
        lines.append("")
        lines.append(item.commentary)
        lines.append("")

    lines.append("# ☕ AI workflow of the week")
    lines.append("")
    if issue.workflow_of_week:
        wf = issue.workflow_of_week
        lines.append(f"**{wf.title}**")
        lines.append("")
        if wf.who_for:
            lines.append(f"Who this is for: {wf.who_for}")
            lines.append("")
        if wf.problem:
            lines.append(f"Problem: {wf.problem}")
            lines.append("")
        if wf.tools:
            lines.append(f"Tools: {wf.tools}")
            lines.append("")
        if wf.steps_codeblock:
            lines.append("```")
            lines.append(wf.steps_codeblock)
            lines.append("```")
            lines.append("")

    lines.append("# ☕ Try this out - prompts")
    lines.append("")
    if issue.try_this_prompt:
        p = issue.try_this_prompt
        lines.append(f"**{p.title}**")
        lines.append("")
        if p.description:
            lines.append(p.description)
            lines.append("")
        lines.append("```")
        lines.append(p.prompt_text)
        lines.append("```")
        lines.append("")

    lines.append("# ☕ Weekly Reads")
    lines.append("")
    for r in issue.weekly_reads:
        lines.append(f"- [{r.title}]({r.url})")
    lines.append("")

    return "\n".join(lines)

