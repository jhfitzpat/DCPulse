"""Normalize, deduplicate, and filter articles by lookback and relevance."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Set

from src.sources.collect import RawArticle

log = logging.getLogger(__name__)

# Canadian DC / pension relevance boost keywords (lowercase)
DC_KEYWORDS = frozenset(
    {
        "pension",
        "retirement",
        "rrsp",
        "tfsa",
        "cpp",
        "oas",
        "qpp",
        "defined contribution",
        "dc plan",
        "group rrsp",
        "deferred profit",
        "dpsp",
        "benefits",
        "plan sponsor",
        "fiduciary",
        "decumulation",
        "annuit",
        "target date",
        "balanced fund",
        "investment policy",
        "governance",
        "osfi",
        "prpp",
        "vrsp",
        "cap accumulation",
        "financial wellness",
        "member",
    }
)


def _text_blob(a: RawArticle) -> str:
    return f"{a.title} {a.summary}".lower()


def _keyword_hits(text: str) -> int:
    return sum(1 for kw in DC_KEYWORDS if kw in text)


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


@dataclass
class NormalizedArticle:
    """Article after normalization and scoring."""

    raw: RawArticle
    normalized_title: str
    dc_keyword_score: int
    dedupe_key: str


def filter_by_lookback(
    articles: Iterable[RawArticle], lookback_days: int, now: Optional[datetime] = None
) -> List[RawArticle]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    out: List[RawArticle] = []
    for a in articles:
        pub = a.published
        if pub is None:
            out.append(a)
            continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub >= cutoff:
            out.append(a)
    return out


def normalize_and_score(articles: List[RawArticle]) -> List[NormalizedArticle]:
    result: List[NormalizedArticle] = []
    for a in articles:
        blob = _text_blob(a)
        score = _keyword_hits(blob)
        nt = _normalize_title(a.title)
        key = nt[:120] if nt else a.link
        result.append(
            NormalizedArticle(
                raw=a,
                normalized_title=nt,
                dc_keyword_score=score,
                dedupe_key=key,
            )
        )
    return result


def dedupe_by_link_and_title(norm: List[NormalizedArticle]) -> List[NormalizedArticle]:
    seen_links: Set[str] = set()
    seen_keys: Set[str] = set()
    out: List[NormalizedArticle] = []
    for n in sorted(norm, key=lambda x: x.raw.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if n.raw.link in seen_links:
            continue
        if n.dedupe_key in seen_keys and n.dedupe_key:
            continue
        seen_links.add(n.raw.link)
        seen_keys.add(n.dedupe_key)
        out.append(n)
    return out


@dataclass
class ExclusionRules:
    exclude_keywords: List[str] = field(default_factory=list)
    low_relevance_keywords: List[str] = field(default_factory=list)
    skip_topic_substrings: List[str] = field(default_factory=list)


def load_exclusion_rules(path) -> ExclusionRules:
    import yaml
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return ExclusionRules()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return ExclusionRules(
        exclude_keywords=list(data.get("exclude_keywords") or []),
        low_relevance_keywords=list(data.get("low_relevance_keywords") or []),
        skip_topic_substrings=list(data.get("skip_topic_substrings") or []),
    )


def apply_exclusions(norm: List[NormalizedArticle], rules: ExclusionRules) -> List[NormalizedArticle]:
    def bad(a: NormalizedArticle) -> bool:
        blob = _text_blob(a.raw)
        for kw in rules.exclude_keywords:
            if kw.lower() in blob:
                return True
        return False

    return [n for n in norm if not bad(n)]


def drop_low_signal(norm: List[NormalizedArticle], min_dc_score: int = 0) -> List[NormalizedArticle]:
    """Optional: require at least one DC keyword hit when score > 0 articles exist."""
    if not norm:
        return norm
    any_hit = any(n.dc_keyword_score > 0 for n in norm)
    if not any_hit:
        return norm
    return [n for n in norm if n.dc_keyword_score >= min_dc_score]
