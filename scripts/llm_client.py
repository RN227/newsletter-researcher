from __future__ import annotations

import os
from typing import List

from anthropic import Anthropic, APIStatusError


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


def summarize_news_items(raw_items: List[dict]) -> List[dict]:
    """
    Given a list of raw news items with keys:
      - title
      - url
      - description
    return a list of dicts with:
      - title
      - url
      - summary_paragraphs (list[str])

    This uses Claude to generate a broad, non-jargony title and 1–2 short paragraphs
    in the Brew & AI tone.
    """
    if not raw_items:
        return []

    prompt_parts = [
        "You are helping draft a friendly AI newsletter called Brew & AI.",
        "For each news item, write:",
        "1) A broad, accessible title (no jargon).",
        "2) A 1–2 paragraph summary in simple language, in a conversational but clear tone.",
        "",
        "Return JSON only with this shape:",
        '[{"index": 0, "title": "...", "summary_paragraphs": ["...", "..."]}, ...]',
        "",
        "News items:",
    ]

    for idx, item in enumerate(raw_items):
        prompt_parts.append(f"[{idx}] Title: {item.get('title','')}")
        prompt_parts.append(f"URL: {item.get('url','')}")
        desc = item.get("description") or ""
        if desc:
            prompt_parts.append(f"Description: {desc}")
        prompt_parts.append("")

    prompt = "\n".join(prompt_parts)

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError:
        # On failure, just fall back to the original titles/descriptions.
        return [
            {
                "index": i,
                "title": item.get("title") or "AI update",
                "summary_paragraphs": [
                    (item.get("description") or "").strip()
                ]
                if item.get("description")
                else [],
            }
            for i, item in enumerate(raw_items)
        ]

    text = "".join(block.text for block in msg.content if block.type == "text")  # type: ignore[attr-defined]

    import json

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [
            {
                "index": i,
                "title": item.get("title") or "AI update",
                "summary_paragraphs": [
                    (item.get("description") or "").strip()
                ]
                if item.get("description")
                else [],
            }
            for i, item in enumerate(raw_items)
        ]

    result_map = {entry.get("index"): entry for entry in parsed if isinstance(entry, dict)}
    output: List[dict] = []
    for i, item in enumerate(raw_items):
        enriched = result_map.get(i) or {}
        title = enriched.get("title") or item.get("title") or "AI update"
        paras = enriched.get("summary_paragraphs") or []
        if isinstance(paras, str):
            paras = [paras]
        output.append(
            {
                "title": title,
                "url": item.get("url") or "",
                "summary_paragraphs": [p for p in paras if p],
            }
        )
    return output


def comment_on_social(url: str, raw_text: str | None = None, note: str | None = None) -> str:
    """
    Given a social link and optional raw extracted text / your own note,
    generate a short commentary paragraph in the Brew & AI tone.
    """
    base = [
        "You are helping draft the 'Trending on social' section of a friendly AI newsletter called Brew & AI.",
        "Write ONE short paragraph (2–4 sentences) explaining what this post is about and why it matters or is funny/interesting.",
        "Tone: conversational, smart, accessible to non-technical readers. No jargon.",
        "",
        f"Post URL: {url}",
    ]
    if note:
        base.append(f"Editor note (optional context): {note}")
    if raw_text:
        base.append("Post text or page snippet:")
        base.append(raw_text[:2000])

    prompt = "\n".join(base)

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=250,
            temperature=0.6,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError:
        return note or "Interesting AI-related post worth highlighting."

    text = "".join(block.text for block in msg.content if block.type == "text")  # type: ignore[attr-defined]
    return text.strip() or (note or "Interesting AI-related post worth highlighting.")

