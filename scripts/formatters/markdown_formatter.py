from __future__ import annotations

from datetime import date

from scripts.models import IssueDraft

DEFAULT_SUBTITLE = "Your weekly AI digest"


def _format_date(d: date) -> str:
    # Cross-platform: use d.day to avoid Linux-only %-d modifier
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def build_subtitle(issue: IssueDraft) -> str:
    if issue.ai_in_the_news:
        titles = [n.title for n in issue.ai_in_the_news[:3]]
        return ", ".join(titles)
    return issue.subtitle or DEFAULT_SUBTITLE


def format_markdown(issue: IssueDraft) -> str:
    subtitle = build_subtitle(issue)
    lines = []

    lines.append(f"☕ Freshly Brewed #{issue.issue_number or ''}".rstrip())
    lines.append(subtitle)
    lines.append("")
    lines.append(_format_date(issue.issue_date))
    lines.append("")

    # ── AI in the News ──────────────────────────────────────────────────────────
    lines.append("# ☕ AI in the news")
    lines.append("")
    for item in issue.ai_in_the_news:
        lines.append(f"**{item.title}**")
        lines.append("")
        for p in item.summary_paragraphs:
            lines.append(p)
            lines.append("")
        if item.signal:
            lines.append(f"*{item.signal}*")
            lines.append("")
        lines.append(f"[Read more]({item.source_url})")
        lines.append("")

    # ── Trending on Social ──────────────────────────────────────────────────────
    lines.append("# ☕ Trending on social")
    lines.append("")
    for item in issue.trending_on_social:
        lines.append(item.commentary)
        lines.append("")
        lines.append(f"[View post]({item.post_url}) — @{item.handle} on {item.platform}")
        lines.append("")

    # ── AI Workflow of the Week ─────────────────────────────────────────────────
    lines.append("# ☕ AI workflow of the week")
    lines.append("")
    if issue.workflow_of_week:
        wf = issue.workflow_of_week
        lines.append(f"**{wf.title}**")
        lines.append("")
        if wf.who_for:
            lines.append(f"**Who this is for:** {wf.who_for}")
            lines.append("")
        if wf.problem:
            lines.append(f"**Problem:** {wf.problem}")
            lines.append("")
        if wf.tools:
            lines.append(f"**Tools:** {wf.tools}")
            lines.append("")
        if wf.steps_codeblock:
            lines.append("**How to run it (30–45 minutes)**")
            lines.append("")
            lines.append("```")
            lines.append(wf.steps_codeblock)
            lines.append("```")
            lines.append("")

    # ── Try This Out — Prompts ──────────────────────────────────────────────────
    lines.append("# ☕ Try this out — prompts")
    lines.append("")
    if issue.try_this_prompt:
        p = issue.try_this_prompt
        if p.title:
            lines.append(f"**{p.title}**")
            lines.append("")
        if p.intro:
            lines.append(p.intro)
            lines.append("")
        if p.description:
            lines.append(p.description)
            lines.append("")
        if p.prompt_text:
            lines.append("```")
            lines.append(p.prompt_text)
            lines.append("```")
            lines.append("")

    # ── Weekly Reads ────────────────────────────────────────────────────────────
    lines.append("# ☕ Weekly reads")
    lines.append("")
    for r in issue.weekly_reads:
        lines.append(f"**[{r.title}]({r.url})**")
        if r.source_domain:
            lines.append(r.source_domain)
        if r.description:
            lines.append("")
            lines.append(r.description)
        lines.append("")

    # ── LinkedIn Post ────────────────────────────────────────────────────────────
    if issue.linkedin_post:
        lines.append("---")
        lines.append("")
        lines.append("## LinkedIn post")
        lines.append("")
        lines.append(issue.linkedin_post)
        lines.append("")

    return "\n".join(lines)
