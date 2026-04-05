"""Rank topic clusters by recency, source diversity, and DC signal."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from src.pipeline.cluster import TopicCluster
from src.pipeline.normalize import ExclusionRules, _text_blob

log = logging.getLogger(__name__)


@dataclass
class ScoredCluster:
    cluster: TopicCluster
    score: float
    reasons: str


def _latest_pub(cluster: TopicCluster) -> Optional[datetime]:
    dates = [n.raw.published for n in cluster.articles if n.raw.published]
    if not dates:
        return None
    return max(dates)


def _days_old(latest: Optional[datetime], now: datetime) -> float:
    if latest is None:
        return 30.0
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    delta = now - latest
    return max(0.0, delta.total_seconds() / 86400.0)


def score_cluster(cluster: TopicCluster, rules: ExclusionRules, now: Optional[datetime] = None) -> ScoredCluster:
    now = now or datetime.now(timezone.utc)
    reasons_parts: List[str] = []

    # Penalize low-relevance keywords in cluster blob
    blob = " ".join(_text_blob(n.raw) for n in cluster.articles)
    penalty = 0.0
    for kw in rules.low_relevance_keywords:
        if kw.lower() in blob.lower():
            penalty += 0.5
            reasons_parts.append(f"low_rel:{kw}")

    latest = _latest_pub(cluster)
    days = _days_old(latest, now)
    recency = 10.0 / (1.0 + days * 0.3)
    reasons_parts.append(f"recency={recency:.2f}")

    # Source diversity
    source_ids = {n.raw.source_id for n in cluster.articles}
    diversity = min(3.0, len(source_ids)) * 0.4
    reasons_parts.append(f"diversity={diversity:.2f}")

    # Weighted article count
    w = sum(n.raw.source_weight for n in cluster.articles)
    weight_score = min(5.0, w * 0.15)
    reasons_parts.append(f"weight={weight_score:.2f}")

    # DC keyword signal
    dc = sum(n.dc_keyword_score for n in cluster.articles)
    dc_score = min(4.0, dc * 0.25)
    reasons_parts.append(f"dc={dc_score:.2f}")

    # Regulator boost
    reg_boost = 0.0
    for n in cluster.articles:
        if n.raw.source_category == "regulator":
            reg_boost += 0.8
    reg_boost = min(2.0, reg_boost)
    if reg_boost:
        reasons_parts.append(f"reg={reg_boost:.2f}")

    score = recency + diversity + weight_score + dc_score + reg_boost - penalty
    return ScoredCluster(cluster=cluster, score=score, reasons="; ".join(reasons_parts))


def rank_clusters(clusters: Iterable[TopicCluster], rules: ExclusionRules) -> List[ScoredCluster]:
    scored = [score_cluster(c, rules) for c in clusters]
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
