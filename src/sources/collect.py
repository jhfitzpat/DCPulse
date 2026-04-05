"""Collect articles from RSS feeds defined in the catalog."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional

import feedparser
import httpx

from src.sources.catalog import SourceEntry

log = logging.getLogger(__name__)

USER_AGENT = "DCPulseWeekly/0.1 (+https://github.com)"


@dataclass
class RawArticle:
    """Normalized article from a feed."""

    title: str
    link: str
    summary: str
    published: Optional[datetime]
    source_id: str
    source_name: str
    source_category: str
    source_weight: float
    feed_url: str
    raw_tags: List[str] = field(default_factory=list)


def _parse_published(entry: Any) -> Optional[datetime]:
    if entry.get("published_parsed"):
        try:
            t = entry.published_parsed
            return datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, tzinfo=timezone.utc)
        except Exception:
            pass
    if entry.get("updated_parsed"):
        try:
            t = entry.updated_parsed
            return datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, tzinfo=timezone.utc)
        except Exception:
            pass
    if entry.get("published"):
        try:
            return parsedate_to_datetime(entry.published)
        except Exception:
            pass
    return None


def _fetch_feed_xml(url: str, timeout: float = 30.0) -> Optional[str]:
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            return r.text
    except Exception as e:
        log.warning("HTTP fetch failed for %s: %s", url, e)
        return None


def parse_feed_content(content: str, source: SourceEntry) -> List[RawArticle]:
    parsed = feedparser.parse(content)
    out: List[RawArticle] = []
    for entry in getattr(parsed, "entries", []) or []:
        title = (entry.get("title") or "").strip() or "Untitled"
        link = (entry.get("link") or "").strip()
        if not link:
            continue
        summary = ""
        if entry.get("summary"):
            summary = (entry.summary or "").strip()
        elif entry.get("description"):
            summary = (entry.description or "").strip()
        if len(summary) > 2000:
            summary = summary[:2000] + "…"
        published = _parse_published(entry)
        tags = []
        if entry.get("tags"):
            for t in entry.tags:
                if isinstance(t, dict) and t.get("term"):
                    tags.append(str(t["term"]))
        out.append(
            RawArticle(
                title=title,
                link=link,
                summary=summary,
                published=published,
                source_id=source.id,
                source_name=source.name,
                source_category=source.category,
                source_weight=source.weight,
                feed_url=source.feed_url,
                raw_tags=tags,
            )
        )
    return out


def parse_feed_xml(content: str, source: SourceEntry) -> List[RawArticle]:
    """Alias for parse_feed_content (tests and external callers)."""
    return parse_feed_content(content, source)


def collect_from_source(source: SourceEntry, httpx_fetch: bool = True) -> List[RawArticle]:
    if not source.enabled:
        return []
    if httpx_fetch:
        xml = _fetch_feed_xml(source.feed_url)
        if xml is None:
            return []
        return parse_feed_content(xml, source)
    # Fallback: feedparser may fetch URL directly
    parsed = feedparser.parse(source.feed_url)
    out: List[RawArticle] = []
    for entry in getattr(parsed, "entries", []) or []:
        title = (entry.get("title") or "").strip() or "Untitled"
        link = (entry.get("link") or "").strip()
        if not link:
            continue
        summary = (entry.get("summary") or entry.get("description") or "").strip()
        if len(summary) > 2000:
            summary = summary[:2000] + "…"
        published = _parse_published(entry)
        tags = []
        if entry.get("tags"):
            for t in entry.tags:
                if isinstance(t, dict) and t.get("term"):
                    tags.append(str(t["term"]))
        out.append(
            RawArticle(
                title=title,
                link=link,
                summary=summary,
                published=published,
                source_id=source.id,
                source_name=source.name,
                source_category=source.category,
                source_weight=source.weight,
                feed_url=source.feed_url,
                raw_tags=tags,
            )
        )
    return out


def collect_all(sources: List[SourceEntry]) -> List[RawArticle]:
    all_a: List[RawArticle] = []
    for s in sources:
        try:
            articles = collect_from_source(s, httpx_fetch=True)
            if not articles:
                articles = collect_from_source(s, httpx_fetch=False)
            log.info("Source %s: %d articles", s.id, len(articles))
            all_a.extend(articles)
        except Exception as e:
            log.exception("Failed source %s: %s", s.id, e)
    return all_a
