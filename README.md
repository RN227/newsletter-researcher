## Brew & AI – Newsletter Drafting Pipeline

Each Saturday at 09:00 UTC, GitHub Actions runs the pipeline and commits a Markdown draft to `newsletters/`. You can also trigger it manually from the Actions tab.

The draft covers all five newsletter sections: **AI in the News**, **Trending on Social**, **AI Workflow of the Week**, **Try This Out — Prompts**, and **Weekly Reads**, plus a ready-to-copy **LinkedIn post**.

---

## Your weekly inputs

During the week, update these files via the GitHub web UI (or locally). After each run, used items are automatically removed — so you'll need to re-populate them for the next issue.

---

### `config/news_links_pending.yml` — AI in the News

Paste up to ~5 article links you want considered for the news section. These take priority over RSS-fetched articles. Claude rewrites everything in the newsletter's tone — your `note` is just context to guide it.

```yaml
- title: Optional headline (Claude will rewrite it anyway)
  url: https://...
  note: Optional angle or context for Claude
```

**Example:**
```yaml
- title: Palantir now US military?
  url: https://www.reuters.com/technology/pentagon-adopt-palantir-ai-...
  note: Palantir is now the default AI platform for the US military

- title: Ads now live on ChatGPT
  url: https://www.reuters.com/business/media-telecom/openai-expand-ads-...
  note: OpenAI has rolled out ads to free users in the US
```

If this file is empty, the pipeline falls back to RSS feeds automatically.

---

### `config/social_links_pending.yml` — Trending on Social

Add 3–4 social posts you want featured. Claude writes a 2–3 sentence commentary for each.

```yaml
- platform: x                  # or: linkedin, instagram, etc.
  handle: username              # without the @
  url: https://x.com/...
  note: Why this post is interesting or what angle to take
```

**Example:**
```yaml
- platform: x
  handle: katiemiller
  url: https://x.com/KatieMiller/status/...
  note: AI going off the rails — what happened to guardrails?

- platform: x
  handle: claudeai
  url: https://x.com/claudeai/status/...
  note: Claude can now control your computer — shipping daily
```

---

### `config/weekly_reads_pending.yml` — Weekly Reads

Add 3 links. Claude fetches each page and writes a 1–2 sentence editorial description.

```yaml
- title: Display title for the link
  url: https://...
```

**Example:**
```yaml
- title: The next billion of AI
  url: https://www.a16z.news/p/the-sovereign-wall-why-ais-next-billion?

- title: ChatGPT curing cancer?
  url: https://x.com/paul_conyngham/status/...

- title: OpenAI's automated researcher
  url: https://www.technologyreview.com/2026/03/20/...
```

---

### `config/workflows.yml` — AI Workflow of the Week

Add a rough draft of a workflow you want featured. Claude fleshes it out into the full 4-step format. Your entry can be as sparse as a title and a few notes — Claude does the rest.

If this file is empty, Claude generates a workflow from scratch using past issues as style references.

```yaml
- id: short-slug              # unique, no spaces (e.g. competitor-teardown)
  title: One-line description of the workflow
  who_for: Job roles this helps (e.g. "Sales leads, marketers, founders")
  problem: 1–2 sentences on the pain point in plain language
  tools: Free AI tools needed (e.g. "ChatGPT, Claude, or Gemini")
  steps: |                    # rough notes — Claude will rewrite these
    1. First rough step
    2. Second rough step
    ...
```

**Example:**
```yaml
- id: claude-cowork-doc-review
  title: Review any document in your downloads folder without uploading it
  who_for: Anyone who receives contracts, agreements, or dense documents
  problem: Uploading files to AI is just enough friction that most people don't bother
  tools: Claude Desktop (Pro or Max)
  steps: |
    1. Download Claude Desktop and connect your downloads folder
    2. Ask Claude to pull up the file and flag anything unusual
    3. Ask follow-up questions on specific clauses
    4. Get a list of questions to send back before signing
```

Used entries are automatically removed after each run.

---

### `config/weekly_theme.yml` — Optional Theme Override

Set a topic to guide the Workflow or Prompt sections this week. Leave blank to let Claude choose based on news signals.

```yaml
workflow_topic: ""   # e.g. "competitive intelligence for sales teams"
prompt_topic: ""     # e.g. "help me think through a career decision"
```

---

## How the pipeline works

1. **News** — merges your curated links with RSS feeds, picks the best 3, rewrites in newsletter tone.
2. **Social** — fetches each post page, writes emoji-led commentary for each.
3. **Workflow** — if you added a draft entry, Claude polishes it into the 4-step format. If not, Claude generates one from scratch.
4. **Prompt** — Claude generates a "You are my..." persona prompt, guided by the theme if set.
5. **Reads** — fetches each page, writes a 1–2 sentence editorial description.
6. **LinkedIn post** — generated automatically from the issue's highlights.

All content goes through Claude before appearing in the draft — nothing is published raw.

---

## Setup

Add your Anthropic API key as a GitHub Actions secret:

**Settings → Secrets and variables → Actions → New repository secret**
Name: `ANTHROPIC_API_KEY`
