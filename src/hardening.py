"""Coverage and quality guardrails for weekly digest output."""

from __future__ import annotations

from typing import List

from src.config import Config
from src.output.schema import WeeklyDigest


def augment_low_confidence(
    digest: WeeklyDigest,
    cfg: Config,
    raw_article_count: int,
    cluster_count: int,
) -> WeeklyDigest:
    """Append human-readable notes when signals are weak."""
    parts: List[str] = []
    if digest.low_confidence_note:
        parts.append(digest.low_confidence_note)
    if raw_article_count < 8:
        parts.append(
            f"Low feed volume ({raw_article_count} articles in lookback); verify RSS URLs in data/sources.yml."
        )
    if cluster_count < 3 and raw_article_count >= 8:
        parts.append("Few distinct topic clusters; feeds may overlap heavily or keyword overlap is low.")
    if len(digest.topics) < cfg.max_topics:
        parts.append(
            f"Only {len(digest.topics)} topics surfaced (cap is {cfg.max_topics}); narratives may be thinner than usual."
        )
    if not parts:
        return digest
    merged = " ".join(parts)
    return digest.model_copy(update={"low_confidence_note": merged})
