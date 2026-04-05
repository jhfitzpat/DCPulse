"""Merge OpenAI web search results into RawArticle list."""

from __future__ import annotations

import logging
from typing import List

from src.config import Config
from src.research.models import SearchHit
from src.research.openai_web_search import fetch_hits_for_query
from src.research.search_planner import run_search_planner
from src.sources.catalog import SourceEntry
from src.sources.collect import RawArticle

log = logging.getLogger(__name__)

# Synthetic catalog entry for merged pipeline scoring
WEB_SEARCH_SOURCE = SourceEntry(
    id="web_search",
    name="OpenAI web search",
    feed_url="https://dc-pulse.local/web-search",
    category="other",
    weight=1.0,
    enabled=True,
)


def hits_to_raw_articles(hits: List[SearchHit]) -> List[RawArticle]:
    out: List[RawArticle] = []
    for h in hits:
        summary = h.snippet.strip()
        if len(summary) > 2000:
            summary = summary[:2000] + "…"
        out.append(
            RawArticle(
                title=h.title[:500],
                link=h.url,
                summary=summary,
                published=None,
                source_id=WEB_SEARCH_SOURCE.id,
                source_name=WEB_SEARCH_SOURCE.name,
                source_category=WEB_SEARCH_SOURCE.category,
                source_weight=WEB_SEARCH_SOURCE.weight,
                feed_url=WEB_SEARCH_SOURCE.feed_url,
                raw_tags=["web_search"],
            )
        )
    return out


def collect_web_search_articles(cfg: Config, week_label: str, rss_headlines: List[str]) -> List[RawArticle]:
    """Planner LLM + OpenAI Responses API (web_search tool); returns additional RawArticles (may be empty)."""
    if not cfg.web_search_enabled:
        return []
    if not cfg.openai_api_key:
        log.warning("Web search skipped: OPENAI_API_KEY required for search planner and Responses API")
        return []
    sample = "\n".join(rss_headlines[:40])
    try:
        plan = run_search_planner(cfg, week_label, sample)
    except Exception as e:
        log.warning("Search planner failed: %s", e)
        return []

    all_hits: List[SearchHit] = []
    seen_urls: set[str] = set()
    for item in plan.queries:
        if not item.q:
            continue
        hits = fetch_hits_for_query(
            cfg,
            item.q,
            min(item.max_results, cfg.search_results_per_query),
        )
        for h in hits:
            if h.url in seen_urls:
                continue
            seen_urls.add(h.url)
            all_hits.append(h)
    log.info("Web search collected %d unique hits from %d queries", len(all_hits), len(plan.queries))
    return hits_to_raw_articles(all_hits)
