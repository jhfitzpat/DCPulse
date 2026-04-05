"""Cluster similar articles into topics using token overlap (no embeddings in v1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Set

from src.pipeline.normalize import NormalizedArticle

STOP = frozenset(
    "a an the and or for to of in on at by is are was were be been being it its this that with from as if "
    "will can may would could should about into over after before".split()
)


def _tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class TopicCluster:
    """A cluster of related articles."""

    id: str
    label: str
    articles: List[NormalizedArticle] = field(default_factory=list)

    def token_union(self) -> Set[str]:
        u: Set[str] = set()
        for n in self.articles:
            u |= _tokens(n.normalized_title + " " + n.raw.summary[:500])
        return u


def _published_sort_key(n: NormalizedArticle) -> datetime:
    """Sort key safe for mixed naive/aware/None (e.g. RSS + web search hits)."""
    p = n.raw.published
    if p is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if p.tzinfo is None:
        return p.replace(tzinfo=timezone.utc)
    return p


def _best_label(articles: List[NormalizedArticle]) -> str:
    if not articles:
        return "Unknown"
    # Prefer shortest title from highest-weight source
    sorted_a = sorted(
        articles,
        key=lambda x: (-x.raw.source_weight, len(x.raw.title)),
    )
    return sorted_a[0].raw.title[:120]


def cluster_articles(
    articles: List[NormalizedArticle],
    similarity_threshold: float = 0.12,
) -> List[TopicCluster]:
    """Greedy clustering by Jaccard similarity on title tokens."""
    if not articles:
        return []
    clusters: List[TopicCluster] = []
    cid = 0
    for n in sorted(articles, key=_published_sort_key, reverse=True):
        t_n = _tokens(n.normalized_title)
        merged = False
        for c in clusters:
            t_c = c.token_union()
            sim = jaccard(t_n, t_c)
            if sim >= similarity_threshold:
                c.articles.append(n)
                c.label = _best_label(c.articles)
                merged = True
                break
        if not merged:
            cid += 1
            clusters.append(TopicCluster(id=f"c{cid}", label=n.raw.title[:120], articles=[n]))

    # Merge tiny singletons into nearest cluster if any similarity
    i = 0
    while i < len(clusters):
        c = clusters[i]
        if len(c.articles) == 1 and len(clusters) > 1:
            best_j = 0.0
            best_idx = -1
            tu = c.token_union()
            for j, other in enumerate(clusters):
                if j == i or not other.articles:
                    continue
                sim = jaccard(tu, other.token_union())
                if sim > best_j:
                    best_j = sim
                    best_idx = j
            if best_idx >= 0 and best_j >= similarity_threshold * 0.5:
                clusters[best_idx].articles.extend(c.articles)
                clusters[best_idx].label = _best_label(clusters[best_idx].articles)
                clusters.pop(i)
                continue
        i += 1

    return clusters
