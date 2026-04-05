"""Generate two long-form article drafts from the seven-topic digest."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

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


def build_article_draft_user_message(
    cfg: Config,
    digest: WeeklyDigest,
    top_scored: List[ScoredCluster],
) -> str:
    cluster_labels = [{"cluster_id": s.cluster.id, "label": s.cluster.label} for s in top_scored]
    payload = {
        "week_label": digest.week_label,
        "target_drafts": cfg.article_draft_count,
        "target_words_per_draft": cfg.article_draft_target_words,
        "topics": [
            {
                "rank": t.rank,
                "topic_title": t.topic_title,
                "trend_summary": t.trend_summary,
                "best_use": t.best_use.value,
                "suggested_original_angle": t.suggested_original_angle,
            }
            for t in digest.topics
        ],
        "cluster_labels": cluster_labels,
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
