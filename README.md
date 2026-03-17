## Brew & AI – Newsletter Drafting Pipeline

This repo contains an automated pipeline that prepares a first-pass draft of the **Brew & AI** newsletter each week.

The pipeline runs via **GitHub Actions** and:

- Collects **fresh AI news** from the last week.
- Uses your curated **social links** and **Weekly Reads**.
- Rotates through a library of **AI workflows** and **fun prompts** without repeating them too often.
- Writes a single **Markdown draft** (plus an optional CSV of links) that you can review and paste into Beehive.

Content for **AI in the news** and **Trending on social** is generated with Anthropic Claude using the `ANTHROPIC_API_KEY` secret in GitHub Actions.

### Weekly workflow (your inputs)

During the week, update these files via the GitHub web UI:

- `config/social_links_pending.yml` – up to ~8–10 social posts you might feature.
- `config/weekly_reads_pending.yml` – 3–10 links you may want in **Weekly Reads**.
- Optionally: `config/workflows.yml` and `config/prompts.yml` – reusable workflow/prompt ideas (don’t need weekly edits).

On Saturday at 09:00 (GitHub Actions cron, in UTC) or whenever you trigger the workflow manually, GitHub Actions will:

1. Run the newsletter pipeline.
2. Generate a new draft Markdown file under `newsletters/`.
3. (Optionally) generate a CSV summarizing AI in the news, social, and Weekly Reads links in the same folder.

### GitHub Actions secret

In your GitHub repo:

- Go to **Settings → Secrets and variables → Actions → New repository secret**.
- Add a secret named `ANTHROPIC_API_KEY` with your Anthropic API key.

The workflow reads this secret and uses Claude to:

- Turn raw news feeds into Brew & AI-style titles and summaries.
- Turn your social links (from `config/social_links_pending.yml`) into short commentary paragraphs.

You then:

1. Open the latest draft under `drafts/`.
2. For **AI in the news** and **Trending on social**, pick your favourite 2–3 items from the 5 suggestions by deleting the rest.
3. Make any light copy edits.
4. Paste the content into Beehive and publish.

