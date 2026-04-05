"""Tests for article draft payload grounding."""

from __future__ import annotations

import json
from pathlib import Path

from src.config import Config
from src.llm.article_drafts import build_article_draft_user_message
from src.output.schema import BestUse, SourceCitation, TopicDigest, WeeklyDigest
from src.pipeline.cluster import TopicCluster
from src.pipeline.normalize import NormalizedArticle
from src.pipeline.rank import ScoredCluster
from src.sources.collect import RawArticle


def _cfg(tmp_path: Path) -> Config:
    data_dir = tmp_path / "data"
    return Config(
        dry_run=False,
        log_level="INFO",
        lookback_days=14,
        max_topics=7,
        highlight_repost_count=3,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        llm_timeout_seconds=120.0,
        skip_llm=False,
        email_to=None,
        email_from=None,
        smtp_host=None,
        smtp_port=587,
        smtp_user=None,
        smtp_password=None,
        smtp_use_tls=True,
        smtp_use_ssl=False,
        email_subject_prefix="DC Pulse Weekly",
        web_search_enabled=False,
        web_search_responses_model="gpt-4o",
        search_planner_model="gpt-4o-mini",
        search_max_queries=5,
        search_results_per_query=5,
        deep_research_enabled=True,
        deep_research_model="gpt-4o-mini",
        article_drafts_enabled=True,
        article_draft_count=2,
        article_draft_target_words=900,
        article_draft_timeout_seconds=300.0,
        article_draft_model="gpt-4o-mini",
        usage_history_enabled=True,
        usage_history_weeks=12,
        usage_history_path=data_dir / "weekly_usage.json",
        data_dir=data_dir,
        sources_path=data_dir / "sources.yml",
        exclusions_path=data_dir / "topic_exclusions.yml",
        prompts_dir=tmp_path / "src" / "prompts",
        voice_path=tmp_path / "src" / "voice" / "profile.md",
    )


def _scored_cluster(cluster_id: str, label: str, url: str) -> ScoredCluster:
    raw = RawArticle(
        title=f"{label} article",
        link=url,
        summary="A detailed summary about sponsor decisions, decumulation, and governance.",
        published=None,
        source_id=cluster_id,
        source_name="Test Source",
        source_category="trade_media",
        source_weight=1.5,
        feed_url="https://example.com/feed",
    )
    normalized = NormalizedArticle(
        raw=raw,
        normalized_title=label.lower(),
        dc_keyword_score=3,
        dedupe_key=label.lower(),
    )
    cluster = TopicCluster(id=cluster_id, label=label, articles=[normalized])
    return ScoredCluster(cluster=cluster, score=7.25, reasons="recency=4.00; dc=0.75")


def test_article_draft_payload_includes_citations_and_supporting_articles(tmp_path: Path):
    cfg = _cfg(tmp_path)
    top_scored = [
        _scored_cluster("c1", "First cluster", "https://example.com/first"),
        _scored_cluster("c2", "Second cluster", "https://example.com/second"),
    ]
    digest = WeeklyDigest(
        week_label="2026-W14",
        topics=[
            TopicDigest(
                rank=2,
                topic_title="Decumulation choices need better committee framing",
                trend_summary="Sponsors are seeing more pressure to turn retirement-income strategy into a practical governance discussion.",
                why_matters_dc="Committees may need to reassess how default design and decumulation support fit together.",
                evidence_momentum="Trade coverage and consulting commentary both point to more focus on post-retirement design.",
                best_use=BestUse.THOUGHT_LEADERSHIP,
                suggested_repost_copy="Useful signal for committees reviewing retirement-income support.",
                suggested_original_angle="Explain how committees can evaluate decumulation readiness without overcomplicating the lineup.",
                example_headlines_or_sources=["Canadian benefits trade coverage"],
                citations=[
                    SourceCitation(
                        title="Second cluster article",
                        url="https://example.com/second",
                        publisher="Test Source",
                        published_date="2026-04-01",
                    )
                ],
            )
        ],
        best_thought_leadership_month=["Decumulation choices need better committee framing"],
    )

    payload = json.loads(build_article_draft_user_message(cfg, digest, top_scored))
    topic = payload["topics"][0]

    assert topic["topic_title"] == "Decumulation choices need better committee framing"
    assert topic["citations"][0]["url"] == "https://example.com/second"
    assert topic["cluster_context"]["cluster_id"] == "c2"
    assert topic["cluster_context"]["cluster_label"] == "Second cluster"
    assert topic["cluster_context"]["supporting_articles"][0]["url"] == "https://example.com/second"
    assert "summary_excerpt" in topic["cluster_context"]["supporting_articles"][0]
