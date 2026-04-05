"""Generate two long-form article drafts from the seven-topic digest."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import Config
from src.output.schema import ArticleDraft, WeeklyDigest
from src.pipeline.rank import ScoredCluster

log = logging.getLogger(__name__)


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_article_draft_system_prompt(cfg: Config) -> str:
    parts = [
        "You are a senior Canadian DC pension consultant drafting long-form thought leadership for review.",
        _load_text(cfg.voice_path),
        _load_text(cfg.prompts_dir / "drafting.md"),
        _load_text(cfg.prompts_dir / "article_drafts.md"),
        "",
        "Respond with a single JSON object only. Keys: article_drafts (array).",
        "Do not include markdown fences outside the JSON string values.",
    ]
    return "\n\n".join(p for p in parts if p.strip())


def _supporting_articles_payload(sc: Optional[ScoredCluster]) -> List[Dict[str, Any]]:
    if sc is None:
        return []
    articles: List[Dict[str, Any]] = []
    for n in sc.cluster.articles[:5]:
        pub = n.raw.published
        articles.append(
            {
                "title": n.raw.title,
                "url": n.raw.link,
                "source_name": n.raw.source_name,
                "source_category": n.raw.source_category,
                "published": pub.isoformat() if pub else None,
                "summary_excerpt": (n.raw.summary or "")[:800],
            }
        )
    return articles


def _topic_context_payload(
    digest: WeeklyDigest,
    top_scored: List[ScoredCluster],
) -> List[Dict[str, Any]]:
    topic_payloads: List[Dict[str, Any]] = []
    for idx, topic in enumerate(digest.topics):
        cluster_idx = topic.rank - 1 if 0 < topic.rank <= len(top_scored) else idx
        sc = top_scored[cluster_idx] if 0 <= cluster_idx < len(top_scored) else None
        citations = [
            {
                "title": c.title,
                "url": c.url,
                "publisher": c.publisher,
                "published_date": c.published_date,
            }
            for c in topic.citations
        ]
        topic_payloads.append(
            {
                "rank": topic.rank,
                "topic_title": topic.topic_title,
                "trend_summary": topic.trend_summary,
                "why_matters_dc": topic.why_matters_dc,
                "evidence_momentum": topic.evidence_momentum,
                "best_use": topic.best_use.value,
                "suggested_repost_copy": topic.suggested_repost_copy,
                "suggested_original_angle": topic.suggested_original_angle,
                "example_headlines_or_sources": topic.example_headlines_or_sources,
                "citations": citations,
                "cluster_context": {
                    "cluster_id": sc.cluster.id if sc else None,
                    "cluster_label": sc.cluster.label if sc else None,
                    "rank_score": round(sc.score, 3) if sc else None,
                    "rank_reasons": sc.reasons if sc else None,
                    "supporting_articles": _supporting_articles_payload(sc),
                },
            }
        )
    return topic_payloads


def build_article_draft_user_message(
    cfg: Config,
    digest: WeeklyDigest,
    top_scored: List[ScoredCluster],
) -> str:
    payload = {
        "week_label": digest.week_label,
        "target_drafts": cfg.article_draft_count,
        "target_words_per_draft": cfg.article_draft_target_words,
        "topics": _topic_context_payload(digest, top_scored),
        "best_thought_leadership_month": digest.best_thought_leadership_month,
        "json_schema": {
            "article_drafts": [
                {
                    "topic_title": "string — must match one of the seven topic_title values",
                    "draft_title": "string",
                    "body_markdown": "string — full article in Markdown",
                    "selection_rationale": "string",
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_article_drafts_llm(
    cfg: Config,
    digest: WeeklyDigest,
    top_scored: List[ScoredCluster],
) -> List[ArticleDraft]:
    if not cfg.openai_api_key:
        return []
    system = build_article_draft_system_prompt(cfg)
    user = build_article_draft_user_message(cfg, digest, top_scored)
    client = OpenAI(api_key=cfg.openai_api_key, timeout=cfg.article_draft_timeout_seconds)
    log.info("Article draft model %s", cfg.article_draft_model)
    resp = client.chat.completions.create(
        model=cfg.article_draft_model,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    data = json.loads(text)
    raw_list = data.get("article_drafts") or []
    out: List[ArticleDraft] = []
    for item in raw_list[: cfg.article_draft_count]:
        out.append(ArticleDraft.model_validate(item))
    return out
