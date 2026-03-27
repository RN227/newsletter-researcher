from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import feedparser
import yaml

from scripts.models import NewsItem
from scripts.utils_history import append_history, get_recent_ids
from scripts.llm_client import summarize_news_items


RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.artificialintelligence-news.com/feed/",
]

NEWS_CONFIG_PATH = Path("config/news_links_pending.yml")


def _load_curated_links() -> List[dict]:
    if not NEWS_CONFIG_PATH.exists():
        return []
    with NEWS_CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("url")]


def _save_curated_links(items: List[dict]) -> None:
    with NEWS_CONFIG_PATH.open("w", encoding="utf-8") as f:
        if items:
            yaml.dump(items, f, allow_unicode=True, default_flow_style=False)
        else:
            f.write("")


def _fetch_rss_candidates(issue_date: datetime) -> List[dict]:
    one_week_ago = issue_date - timedelta(days=7)
    items: List[dict] = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        entries = getattr(feed, "entries", [])
        print(f"[news] RSS {feed_url}: {len(entries)} entries")
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
            items.append({"title": title, "url": link, "description": summary})

    return items


def run(issue_date: datetime) -> List[NewsItem]:
    """
    Build up to 3 AI news items. Curated links (from config) take priority over
    RSS-fetched articles. Both sources are deduplicated against history.
    """
    recent_ids = get_recent_ids("news")

    # 1. Load curated links (user-provided, high priority)
    curated_raw = _load_curated_links()
    curated = [c for c in curated_raw if c.get("url") not in recent_ids]
    print(f"[news] Curated links: {len(curated_raw)} total, {len(curated)} new")

    # 2. Fetch RSS candidates
    rss_candidates = _fetch_rss_candidates(issue_date)
    rss_candidates = [c for c in rss_candidates if c.get("url") not in recent_ids]
    print(f"[news] RSS candidates after dedup: {len(rss_candidates)}")

    # 3. Merge: curated first, then RSS (cap total at 10 for LLM)
    # Normalise curated entries to {title, url, description} shape
    curated_normalised = [
        {
            "title": c.get("title") or "",
            "url": c.get("url") or "",
            "description": c.get("note") or "",
        }
        for c in curated
    ]
    merged = (curated_normalised + rss_candidates)[:10]
    print(f"[news] Sending {len(merged)} candidates to LLM")

    # 4. LLM summarisation
    enriched = summarize_news_items(merged)
    print(f"[news] LLM returned {len(enriched)} summaries")

    # 5. Build NewsItem objects
    items: List[NewsItem] = []
    used_urls: List[str] = []
    for article in enriched:
        url = article.get("url") or ""
        if not url:
            continue
        items.append(
            NewsItem(
                title=article.get("title") or "AI update",
                source_url=url,
                summary_paragraphs=article.get("summary_paragraphs") or [],
                signal=article.get("signal") or None,
            )
        )
        used_urls.append(url)
        if len(items) >= 3:
            break

    # 6. Update history
    append_history("news", used_urls, issue_date.date().isoformat())

    # 7. Remove processed curated items from config YAML
    used_url_set = set(used_urls)
    remaining_curated = [c for c in curated_raw if c.get("url") not in used_url_set]
    if len(remaining_curated) != len(curated_raw):
        _save_curated_links(remaining_curated)
        print(f"[news] Removed {len(curated_raw) - len(remaining_curated)} used items from news config")

    print(f"[news] Final: {len(items)} news items")
    return items
