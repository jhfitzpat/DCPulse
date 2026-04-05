"""Select top N topics and highlight repost candidates."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Tuple

from src.pipeline.cluster import TopicCluster, _tokens
from src.pipeline.rank import ScoredCluster

log = logging.getLogger(__name__)


def select_top_topics(
    ranked: List[ScoredCluster],
    max_topics: int = 7,
    highlight_repost: int = 3,
) -> Tuple[List[ScoredCluster], List[ScoredCluster]]:
    """Return (top topics for digest, subset flagged for repost highlights)."""
    top = ranked[:max_topics]
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
