from __future__ import annotations

import os
from typing import List, Optional
import json

from anthropic import Anthropic, APIStatusError


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


def _extract_json(text: str) -> str:
    """
    Robustly extract a JSON value (object or array) from an LLM response
    that may contain preamble text, markdown code fences, or trailing prose.
    """
    text = text.strip()
    # Strip markdown code fences if present
    if "```" in text:
        parts = text.split("```")
        # parts[1] is the fenced block content (index 1 = inside first pair)
        for part in parts[1::2]:  # every odd part is inside a fence
            candidate = part.lstrip("json").strip()
            if candidate.startswith("{") or candidate.startswith("["):
                return candidate
    # Fall back: find whichever JSON container starts first ({ or [)
    brace_start = text.find("{")
    bracket_start = text.find("[")
    # Determine order: try the one that appears first in the text
    if bracket_start != -1 and (brace_start == -1 or bracket_start < brace_start):
        pairs = (("[", "]"), ("{", "}"))
    else:
        pairs = (("{", "}"), ("[", "]"))
    for start_char, end_char in pairs:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
    return text


def summarize_news_items(raw_items: List[dict]) -> List[dict]:
    """
    Given a list of raw news items ({title, url, description}), return exactly
    up to 3 items with rewritten titles, 2-4 sentence summaries, and a signal line.
    """
    if not raw_items:
        return []

    prompt_parts = [
        "You are helping draft the 'AI in the News' section of a weekly newsletter called Brew & AI.",
        "Audience: non-technical professionals — curious about AI but not specialists.",
        "Tone: conversational, jargon-free, slightly witty. Like a smart friend explaining things over coffee.",
        "",
        "For each news item, write:",
        "1) A broad, accessible headline — no jargon, no acronyms. Plain English.",
        "2) A 2–4 sentence summary. Explain what happened and why it matters in plain language.",
        "   Always answer 'so what?' — don't assume the reader knows why the story is significant.",
        "3) A 'signal' — one sentence on what this means for a regular person or where things are heading.",
        "",
        "Prioritise stories that affect everyday life, widely-used products, or signal big industry shifts.",
        "Avoid: overly technical benchmarks, API pricing, ML research papers, developer-only tooling.",
        "",
        "Return JSON only — no markdown, no commentary — in this exact shape:",
        '[{"index": 0, "url": "original-url-unchanged", "title": "...", "summary_paragraphs": ["para1", "para2"], "signal": "..."}, ...]',
        "IMPORTANT: the 'url' field must be copied exactly from the input — do not modify or omit it.",
        "",
        "Pick the best 3 items from the list below (fewer if there are fewer than 3):",
        "",
    ]

    for idx, item in enumerate(raw_items):
        prompt_parts.append(f"[{idx}] Title: {item.get('title', '')}")
        prompt_parts.append(f"URL: {item.get('url', '')}")
        desc = item.get("description") or ""
        if desc:
            prompt_parts.append(f"Description: {desc[:600]}")
        prompt_parts.append("")

    prompt = "\n".join(prompt_parts)

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError:
        return [
            {
                "index": i,
                "url": item.get("url") or "",
                "title": item.get("title") or "AI update",
                "summary_paragraphs": [(item.get("description") or "").strip()] if item.get("description") else [],
                "signal": "",
            }
            for i, item in enumerate(raw_items[:3])
        ]

    text = _extract_json("".join(block.text for block in msg.content if block.type == "text"))  # type: ignore[attr-defined]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [
            {
                "index": i,
                "url": item.get("url") or "",
                "title": item.get("title") or "AI update",
                "summary_paragraphs": [(item.get("description") or "").strip()] if item.get("description") else [],
                "signal": "",
            }
            for i, item in enumerate(raw_items[:3])
        ]

    # Build a lookup of original URLs so we can validate LLM-returned URLs
    valid_urls = {item.get("url") for item in raw_items if item.get("url")}
    url_to_item = {item.get("url"): item for item in raw_items if item.get("url")}

    output: List[dict] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        # Use the URL the LLM returned (it has the article in context); fall back
        # to index-based lookup only if the returned URL isn't one of our inputs.
        llm_url = entry.get("url") or ""
        if llm_url in valid_urls:
            source_item = url_to_item[llm_url]
        else:
            idx = entry.get("index")
            source_item = raw_items[idx] if isinstance(idx, int) and idx < len(raw_items) else {}
        url = source_item.get("url") or llm_url or ""
        if not url:
            continue
        title = entry.get("title") or source_item.get("title") or "AI update"
        paras = entry.get("summary_paragraphs") or []
        if isinstance(paras, str):
            paras = [paras]
        signal = entry.get("signal") or ""
        output.append(
            {
                "title": title,
                "url": url,
                "summary_paragraphs": [p for p in paras if p],
                "signal": signal,
            }
        )
        if len(output) >= 3:
            break

    return output


def comment_on_social(url: str, raw_text: str | None = None, note: str | None = None) -> str:
    """
    Generate a short commentary paragraph for a social post.
    Commentary must open with a fitting emoji and be 2-3 sentences.
    """
    base = [
        "You are helping draft the 'Trending on Social' section of Brew & AI, a friendly weekly AI newsletter.",
        "Write ONE short paragraph (2–3 sentences) for this social post.",
        "",
        "Rules:",
        "- START with a single fitting emoji on the same line as your first sentence (e.g. '🧑‍💻 Google just...')",
        "  Use an emoji that matches the vibe: 🧑‍💻 tech/product, 📊 industry/data, 😄 funny/relatable,",
        "  🔥 controversial/viral, 🗺 product launch, 💬 debate/opinion, 🤔 thought-provoking.",
        "- Explain: what the post said, why it got attention, and what's interesting/funny about it.",
        "- Lean into the human angle — why did this resonate? What does it say about the moment?",
        "- Tone: lighter and more opinionated than a news story. Slightly cheeky is fine.",
        "- No jargon. Accessible to someone who doesn't follow AI Twitter daily.",
        "- Do NOT mention inability to access links or ask follow-up questions.",
        "- Never output emoji-only lines or separators like ---.",
        "",
        f"Post URL: {url}",
    ]
    if note:
        base.append(f"Editor note (context): {note}")
    if raw_text:
        base.append("Page snippet:")
        base.append(raw_text[:2000])

    prompt = "\n".join(base)

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0.6,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError:
        return note or "Interesting AI-related post worth highlighting."

    text = "".join(block.text for block in msg.content if block.type == "text")  # type: ignore[attr-defined]
    return text.strip() or (note or "Interesting AI-related post worth highlighting.")


def generate_workflow_from_web(
    signals: List[dict],
    topic: Optional[str] = None,
    examples: Optional[List[dict]] = None,
    draft: Optional[dict] = None,
) -> Optional[dict]:
    """
    Generate the 'AI Workflow of the Week' section.
    If topic is provided it overrides the web signals as the creative brief.
    """
    if not signals and not topic and not draft:
        return None

    prompt_parts = [
        "You are helping write the 'AI Workflow of the Week' section of Brew & AI, a weekly AI newsletter.",
        "Audience: non-technical professionals. No coding, no APIs, no technical setup.",
        "The workflow must be something a regular office worker can run in 30–45 minutes using a free AI chatbot.",
        "",
    ]

    if draft:
        prompt_parts.append(
            "The newsletter author has provided a rough draft or brief below. "
            "Your job is to flesh it out into the full, polished format. "
            "Keep the author's intent and any specific details they've included — "
            "expand on them, don't replace them. Fill in anything missing."
        )
        prompt_parts.append("")
        for key, val in draft.items():
            if key != "id" and val:
                prompt_parts.append(f"{key.upper()}: {val}")
        prompt_parts.append("")
    elif topic:
        prompt_parts.append(f"This week's theme: {topic}")
        prompt_parts.append("Design the workflow specifically around this theme.")
    else:
        prompt_parts.append("Use the web signals below as inspiration for a timely, relevant workflow.")

    prompt_parts += [
        "",
        "AVOID generic, overused ideas like:",
        "- 'summarise your meeting notes'",
        "- 'rewrite this email'",
        "- 'generate a to-do list from your notes'",
        "- anything that only pastes text and asks for a summary",
        "",
        "AIM for workflows that:",
        "- Help someone do something they genuinely couldn't do easily alone",
        "- Involve a clever, non-obvious use of AI",
        "- Feel like a 'why didn't I think of that?' moment",
        "- Solve a real, recurring problem for a specific job role",
        "Good examples: reverse-engineer a competitor's pricing strategy, prep for a difficult negotiation,",
        "build a positioning brief from customer reviews, find holes in your own argument before presenting it,",
        "turn a job description into a salary negotiation script.",
        "",
        "Structure the output with EXACTLY 4 steps following this arc:",
        "  Step 1 — Gather: collect the raw material or context needed",
        "  Step 2 — Prompt: send a clear, structured prompt to the AI",
        "  Step 3 — Refine: tweak the output for your specific role or angle",
        "  Step 4 — Act: turn the output into a concrete deliverable or next action",
        "",
        "Each step must have:",
        "  - A short bold label (e.g. 'Step 1 — Gather your raw material')",
        "  - 3–5 lines of explanation",
        "  - Specific prompt language the reader can copy",
        "",
        "Return JSON only — no markdown fences — in this exact shape:",
        '{"id":"...", "title":"...", "who_for":"...", "domain":"work", "problem":"...", "tools":"...", "steps_codeblock":"Step 1 — Label\\n\\nExplanation...\\n\\nStep 2 — Label\\n\\n..."}',
        "",
        "Field guidance:",
        "  id: a short slug (e.g. 'competitor-pricing-teardown')",
        "  title: one-line description of the workflow",
        "  who_for: specific job roles (e.g. 'Sales leads, account managers, founders')",
        "  problem: 2–4 sentences describing the pain point in relatable terms — the reader should nod and think 'yes, that's me'",
        "  tools: free AI tools needed (e.g. 'ChatGPT, Claude, or Gemini — free tier is fine')",
        "  steps_codeblock: all 4 steps as plain text (not JSON), with a blank line between each step",
        "",
    ]

    if examples:
        prompt_parts.append(
            "Here are examples of past workflows from this newsletter. "
            "Match their tone, depth, specificity, and format closely — "
            "but create something entirely new and different in topic:"
        )
        for ex in examples[:3]:
            prompt_parts.append(f"  Title: {ex.get('title', '')}")
            prompt_parts.append(f"  Who for: {ex.get('who_for', '')}")
            prompt_parts.append(f"  Problem: {ex.get('problem', '')}")
            prompt_parts.append(f"  Tools: {ex.get('tools', '')}")
            prompt_parts.append("")

    if signals and not topic:
        prompt_parts.append("Web signals (use as inspiration for topic relevance):")
        for idx, s in enumerate(signals[:8]):
            prompt_parts.append(f"[{idx}] {s.get('title', '')} | {s.get('url', '')}")
            desc = s.get("description") or ""
            if desc:
                prompt_parts.append(f"Summary: {desc[:400]}")
            prompt_parts.append("")

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            temperature=0.5,
            messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
        )
    except APIStatusError as e:
        print(f"[workflow] API error: {e}")
        return None

    raw = "".join(block.text for block in msg.content if block.type == "text")  # type: ignore[attr-defined]
    print(f"[workflow] Raw LLM response length: {len(raw)} chars")
    text = _extract_json(raw)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[workflow] JSON parse error: {e}")
        print(f"[workflow] Extracted text: {text[:300]}")
        return None
    if not isinstance(parsed, dict):
        print(f"[workflow] Expected dict, got {type(parsed).__name__}")
        return None
    # Normalize: LLM may return "steps" instead of "steps_codeblock"
    if "steps" in parsed and "steps_codeblock" not in parsed:
        parsed["steps_codeblock"] = parsed.pop("steps")
    return parsed


def generate_prompt_from_web(
    signals: List[dict], topic: Optional[str] = None
) -> Optional[dict]:
    """
    Generate the 'Try This Out — Prompts' section.
    If topic is provided it overrides the web signals as the creative brief.
    Signals are optional — Claude can generate a good prompt without them.
    """
    prompt_parts = [
        "You are helping write the 'Try This Out — Prompts' section of Brew & AI, a weekly AI newsletter.",
        "Audience: non-technical professionals who want to use AI in daily or weekly routines.",
        "The prompt must work in any free AI chatbot (ChatGPT, Claude, Gemini).",
        "",
    ]

    if topic:
        prompt_parts.append(f"This week's theme: {topic}")
        prompt_parts.append("Design the prompt specifically around this theme.")
    elif signals:
        prompt_parts.append("Use the web signals below as inspiration.")
    else:
        prompt_parts.append("Generate a creative, timely prompt based on your knowledge of current AI trends.")

    prompt_parts += [
        "",
        "Rules for the prompt_text:",
        "- MUST open with 'You are my [character/persona]...'",
        "- The persona should be slightly dramatic or fun — not just 'assistant' or 'expert'",
        "  Good examples: 'You are my brutally honest career coach', 'You are my slightly unhinged",
        "  personal brand strategist', 'You are my no-nonsense startup investor on a bad day'",
        "- The prompt should ask the user a series of questions FIRST (to gather context),",
        "  then produce a structured, useful output",
        "- Aim for prompts that feel fun to try, not just useful — the reader should want to run it immediately",
        "",
        "AVOID: meeting summaries, email rewrites, generic to-do lists, anything boring",
        "AIM for: career moments, life decisions, personal strategy, creative challenges,",
        "  anything that produces a surprising or delightful output",
        "",
        "Return JSON only — no markdown fences — in this exact shape:",
        '{"id":"...", "title":"...", "cadence":"weekly", "intro":"...", "description":"...", "prompt_text":"..."}',
        "",
        "Field guidance:",
        "  id: a short slug (e.g. 'brutal-career-coach')",
        "  title: short name for the prompt (e.g. 'The Brutal Career Coach')",
        "  cadence: 'weekly' or 'as needed'",
        "  intro: ONE sentence to intro the prompt in the newsletter",
        "         (e.g. 'This week — turn an AI into your slightly unhinged career reality-check.')",
        "  description: 1–2 sentences explaining what the prompt does and who it's for",
        "  prompt_text: the full copy-paste prompt, opening with 'You are my...'",
        "",
    ]

    if signals and not topic:
        prompt_parts.append("Web signals:")
        for idx, s in enumerate(signals[:8]):
            prompt_parts.append(f"[{idx}] {s.get('title', '')} | {s.get('url', '')}")
            desc = s.get("description") or ""
            if desc:
                prompt_parts.append(f"Summary: {desc[:400]}")
            prompt_parts.append("")

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            temperature=0.7,
            messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
        )
    except APIStatusError as e:
        print(f"[prompt] API error: {e}")
        return None

    raw = "".join(block.text for block in msg.content if block.type == "text")  # type: ignore[attr-defined]
    print(f"[prompt] Raw LLM response length: {len(raw)} chars")
    text = _extract_json(raw)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[prompt] JSON parse error: {e}")
        print(f"[prompt] Extracted text: {text[:300]}")
        return None
    if not isinstance(parsed, dict):
        print(f"[prompt] Expected dict, got {type(parsed).__name__}")
        return None
    return parsed


def summarize_reads_items(raw_items: List[dict]) -> List[dict]:
    """
    Given a list of {title, url, snippet} dicts, return {title, url, source_domain, description}.
    Writes 1-2 sentence editorial descriptions for each read.
    """
    if not raw_items:
        return []

    prompt_parts = [
        "You are helping write the 'Weekly Reads' section of Brew & AI, a weekly AI newsletter.",
        "Audience: non-technical professionals. Curated for quality over volume.",
        "",
        "For each article, produce:",
        "1) source_domain — the domain of the article (e.g. 'techcrunch.com', 'x.com'). Extract from the URL.",
        "2) description — 1–2 sentences: what is the piece about, and why is it worth reading?",
        "   The reader should be able to decide in 2 sentences whether it's for them.",
        "   No jargon. No hype. Editorial, no-nonsense tone.",
        "",
        "Return JSON only — no markdown fences — in this exact shape:",
        '[{"index": 0, "source_domain": "...", "description": "..."}, ...]',
        "",
        "Articles:",
        "",
    ]

    for idx, item in enumerate(raw_items):
        prompt_parts.append(f"[{idx}] Title: {item.get('title', '')}")
        prompt_parts.append(f"URL: {item.get('url', '')}")
        snippet = item.get("snippet") or ""
        if snippet:
            prompt_parts.append(f"Snippet: {snippet[:800]}")
        prompt_parts.append("")

    prompt = "\n".join(prompt_parts)

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError:
        return _fallback_reads(raw_items)

    text = _extract_json("".join(block.text for block in msg.content if block.type == "text"))  # type: ignore[attr-defined]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_reads(raw_items)

    result_map = {entry.get("index"): entry for entry in parsed if isinstance(entry, dict)}
    output: List[dict] = []
    for i, item in enumerate(raw_items):
        enriched = result_map.get(i) or {}
        output.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "source_domain": enriched.get("source_domain") or _extract_domain(item.get("url") or ""),
                "description": enriched.get("description") or "",
            }
        )
    return output


def _fallback_reads(raw_items: List[dict]) -> List[dict]:
    return [
        {
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "source_domain": _extract_domain(item.get("url") or ""),
            "description": "",
        }
        for item in raw_items
    ]


def generate_linkedin_post(draft_summary: dict) -> str:
    """
    Generate a short LinkedIn post summarising this newsletter edition.
    draft_summary contains: issue_number, issue_date, news_titles,
    social_highlights, workflow_title, prompt_title, reads_titles.
    """
    prompt_parts = [
        "You are helping promote Brew & AI, a weekly newsletter that makes AI simple for non-technical professionals.",
        "Write a short LinkedIn post to announce this week's edition.",
        "",
        "Rules:",
        "- 3–5 sentences max. Punchy, conversational, not corporate.",
        "- Mention 2–3 specific highlights from the issue to give people a reason to click.",
        "- End with a natural call to action and this subscribe link: mail.brewandai.com",
        "- Do NOT use hashtags unless they feel completely natural (max 2 if used).",
        "- Tone: smart, friendly, like a person — not a brand account.",
        "- Do not use phrases like 'In this edition' or 'This week's issue' as the opening line.",
        "  Open with the most interesting thing from the issue instead.",
        "",
        "This edition's content:",
    ]

    if draft_summary.get("issue_number"):
        prompt_parts.append(f"Issue: #{draft_summary['issue_number']} — {draft_summary.get('issue_date', '')}")
    if draft_summary.get("news_titles"):
        prompt_parts.append(f"News stories: {', '.join(draft_summary['news_titles'])}")
    if draft_summary.get("social_highlights"):
        prompt_parts.append(f"Social highlights: {', '.join(draft_summary['social_highlights'])}")
    if draft_summary.get("workflow_title"):
        prompt_parts.append(f"Workflow of the week: {draft_summary['workflow_title']}")
    if draft_summary.get("prompt_title"):
        prompt_parts.append(f"Prompt of the week: {draft_summary['prompt_title']}")
    if draft_summary.get("reads_titles"):
        prompt_parts.append(f"Weekly reads: {', '.join(draft_summary['reads_titles'])}")

    client = _client()
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0.7,
            messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
        )
    except APIStatusError:
        return f"New edition of Freshly Brewed is out — your weekly AI digest. Read it at mail.brewandai.com"

    text = "".join(block.text for block in msg.content if block.type == "text")  # type: ignore[attr-defined]
    return text.strip() or f"New edition of Freshly Brewed is out. Read it at mail.brewandai.com"


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lstrip("www.") or url
    except Exception:
        return url
