"""Select top N topics and highlight repost candidates."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Set, Tuple

from src.pipeline.cluster import TopicCluster, _tokens
from src.pipeline.rank import ScoredCluster
from src.pipeline.usage_history import canonical_url

log = logging.getLogger(__name__)


def pick_top_topics(
    ranked: List[ScoredCluster],
    max_topics: int,
    blocked_urls: Set[str],
) -> List[ScoredCluster]:
    """
    Greedy selection in rank order: prefer clusters whose primary URL is not in blocked_urls,
    then fill from remaining ranked clusters (may reuse previously featured URLs).
    """
    if max_topics <= 0:
        return []
    blocked = {canonical_url(u) for u in blocked_urls if u}
    picked: List[ScoredCluster] = []
    picked_ids: Set[str] = set()

    for sc in ranked:
        if len(picked) >= max_topics:
            break
        url, _ = primary_article_for_cluster(sc.cluster)
        if canonical_url(url) not in blocked:
            picked.append(sc)
            picked_ids.add(sc.cluster.id)

    if len(picked) < max_topics:
        log.warning(
            "Only %d clusters with unused primary URLs; filling to %d from ranked list (reusing featured URLs).",
            len(picked),
            max_topics,
        )
        for sc in ranked:
            if len(picked) >= max_topics:
                break
            if sc.cluster.id in picked_ids:
                continue
            picked.append(sc)
            picked_ids.add(sc.cluster.id)

    return picked


def select_top_topics(
    ranked: List[ScoredCluster],
    max_topics: int = 7,
    highlight_repost: int = 3,
    blocked_urls: Set[str] | None = None,
) -> Tuple[List[ScoredCluster], List[ScoredCluster]]:
    """Return (top topics for digest, subset flagged for repost highlights)."""
    blocked = blocked_urls if blocked_urls is not None else set()
    top = pick_top_topics(ranked, max_topics, blocked)
    # Heuristic: prefer clusters with media/third-party URLs and multiple sources for repost
    repost_pool: List[ScoredCluster] = []
    for s in top:
        cats = {n.raw.source_category for n in s.cluster.articles}
        if len(s.cluster.articles) >= 1 and ("media" in cats or "consultant" in cats or "asset_manager" in cats):
            repost_pool.append(s)
    # Fall back to top by score
    if len(repost_pool) < highlight_repost:
        repost_pool = list(top)
    highlights = repost_pool[:highlight_repost]
    return top, highlights


def primary_article_for_cluster(cluster: TopicCluster) -> Tuple[str, str]:
    """Pick the article whose title best matches the cluster label (then recency, DC score)."""
    label_toks = _tokens(cluster.label)
    media = [n for n in cluster.articles if n.raw.source_category == "media"]
    pool = media or cluster.articles

    def score(n):
        overlap = len(label_toks & _tokens(n.normalized_title))
        pub = n.raw.published or datetime.min.replace(tzinfo=timezone.utc)
        return (overlap, n.dc_keyword_score, pub)

    best = max(pool, key=score)
    return best.raw.link, best.raw.title
