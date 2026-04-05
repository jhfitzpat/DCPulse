"""Generate WeeklyDigest via OpenAI from ranked clusters, with rule-grounded prompts."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import Config
from src.output.schema import (
    BestUse,
    RepostHighlight,
    SourceCitation,
    TopicDigest,
    WeeklyDigest,
)
from src.pipeline.rank import ScoredCluster
from src.pipeline.select import primary_article_for_cluster

log = logging.getLogger(__name__)


def _week_label(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_system_prompt(cfg: Config) -> str:
    parts = [
        "You are an AI research assistant for a Canadian defined contribution pension consulting practice.",
        _load_text(cfg.voice_path),
        _load_text(cfg.prompts_dir / "ideation.md"),
        _load_text(cfg.prompts_dir / "research.md"),
        _load_text(cfg.prompts_dir / "repost_copy.md"),
        _load_text(cfg.prompts_dir / "drafting.md"),
        "",
        "You MUST respond with a single JSON object matching the schema described in the user message.",
        "Do not include markdown fences. Do not add commentary outside JSON.",
    ]
    return "\n\n".join(p for p in parts if p.strip())


def _cluster_to_dict(sc: ScoredCluster) -> Dict[str, Any]:
    c = sc.cluster
    arts = []
    for n in c.articles:
        pub = n.raw.published
        arts.append(
            {
                "title": n.raw.title,
                "url": n.raw.link,
                "source_name": n.raw.source_name,
                "source_category": n.raw.source_category,
                "published": pub.isoformat() if pub else None,
                "summary_excerpt": (n.raw.summary or "")[:800],
            }
        )
    return {
        "cluster_id": c.id,
        "working_label": c.label,
        "rank_score": round(sc.score, 3),
        "rank_reasons": sc.reasons,
        "articles": arts,
    }


def build_user_message(
    top_scored: List[ScoredCluster],
    highlight_scored: List[ScoredCluster],
    week_label: str,
) -> str:
    schema_hint = {
        "week_label": "string (use the provided week label)",
        "intro": "string, optional 2-3 sentences",
        "topics": [
            {
                "rank": "integer 1-7",
                "topic_title": "string",
                "trend_summary": "string, 2-4 sentences",
                "why_matters_dc": "string",
                "evidence_momentum": "string",
                "best_use": "Repost | Thought leadership | Both",
                "suggested_repost_copy": "string, 50-80 words",
                "suggested_original_angle": "string",
                "example_headlines_or_sources": ["string", "..."],
                "citations": [{"title": "string", "url": "string", "publisher": "string|null", "published_date": "string|null"}],
            }
        ],
        "repost_highlights": [
            {
                "topic_title": "string (must align with one topic)",
                "primary_article_url": "string (must be one of the article URLs in that topic)",
                "primary_article_title": "string",
                "why_repost": "string",
                "repost_copy_angle_a": "string, distinct angle",
                "repost_copy_angle_b": "string, distinct angle",
            }
        ],
        "best_repost_this_week": ["string"],
        "best_thought_leadership_month": ["string"],
        "topics_to_avoid": ["string"],
        "low_confidence_note": "string|null — use if coverage is thin or fewer than 7 strong topics",
    }
    payload = {
        "week_label": week_label,
        "clusters_for_digest": [_cluster_to_dict(s) for s in top_scored],
        "highlight_cluster_ids": [s.cluster.id for s in highlight_scored],
        "constraints": {
            "max_topics": 7,
            "num_highlights": len(highlight_scored),
            "must_include_repost_angles_for_each_highlight": True,
        },
        "json_schema": schema_hint,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_digest_with_llm(
    cfg: Config,
    top_scored: List[ScoredCluster],
    highlight_scored: List[ScoredCluster],
) -> WeeklyDigest:
    week_label = _week_label()
    system = build_system_prompt(cfg)
    user = build_user_message(top_scored, highlight_scored, week_label)
    client = OpenAI(api_key=cfg.openai_api_key, timeout=cfg.llm_timeout_seconds)
    log.info("Calling OpenAI model %s", cfg.openai_model)
    resp = client.chat.completions.create(
        model=cfg.openai_model,
        temperature=0.35,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    data = json.loads(text)
    digest = WeeklyDigest.model_validate(data)
    # Ensure week_label from pipeline; cap list lengths
    digest = digest.model_copy(
        update={
            "week_label": week_label,
            "topics": digest.topics[: cfg.max_topics],
            "repost_highlights": digest.repost_highlights[: cfg.highlight_repost_count],
        }
    )
    return _enforce_constraints(cfg, digest, highlight_scored)


def _enforce_constraints(
    cfg: Config,
    digest: WeeklyDigest,
    highlight_scored: List[ScoredCluster],
) -> WeeklyDigest:
    """Align highlights with selected clusters when the model drifts."""
    if len(digest.topics) > cfg.max_topics:
        digest = digest.model_copy(update={"topics": digest.topics[: cfg.max_topics]})
    fixed_highlights: List[RepostHighlight] = []
    for i, sc in enumerate(highlight_scored[: cfg.highlight_repost_count]):
        url, title = primary_article_for_cluster(sc.cluster)
        existing = digest.repost_highlights[i] if i < len(digest.repost_highlights) else None
        if existing:
            fixed_highlights.append(
                RepostHighlight(
                    topic_title=sc.cluster.label[:200],
                    primary_article_url=url,
                    primary_article_title=title,
                    why_repost=existing.why_repost,
                    repost_copy_angle_a=existing.repost_copy_angle_a,
                    repost_copy_angle_b=existing.repost_copy_angle_b,
                )
            )
        else:
            fixed_highlights.append(
                RepostHighlight(
                    topic_title=sc.cluster.label[:200],
                    primary_article_url=url,
                    primary_article_title=title,
                    why_repost="Enable full LLM output or review cluster articles for repost rationale.",
                    repost_copy_angle_a="(Generated highlight placeholder — run with OPENAI_API_KEY for full copy.)",
                    repost_copy_angle_b="(Second angle placeholder.)",
                )
            )
    return digest.model_copy(update={"repost_highlights": fixed_highlights})


def fallback_digest_without_llm(
    cfg: Config,
    top_scored: List[ScoredCluster],
    highlight_scored: List[ScoredCluster],
    note: str,
) -> WeeklyDigest:
    """Deterministic digest when LLM is skipped or unavailable."""
    week_label = _week_label()
    topics: List[TopicDigest] = []
    for i, sc in enumerate(top_scored[: cfg.max_topics], start=1):
        c = sc.cluster
        cites: List[SourceCitation] = []
        for n in c.articles[:5]:
            pub = n.raw.published
            cites.append(
                SourceCitation(
                    title=n.raw.title,
                    url=n.raw.link,
                    publisher=n.raw.source_name,
                    published_date=pub.date().isoformat() if pub else None,
                )
            )
        topics.append(
            TopicDigest(
                rank=i,
                topic_title=c.label[:200],
                trend_summary="Clustered from recent RSS items; run with OPENAI_API_KEY for narrative summaries.",
                why_matters_dc="Review citations for sponsor and committee relevance to Canadian DC plans.",
                evidence_momentum=f"Automated score {sc.score:.2f} ({sc.reasons}).",
                best_use=BestUse.BOTH,
                suggested_repost_copy="Add OPENAI_API_KEY to generate concise repost commentary aligned to your voice.",
                suggested_original_angle="Develop a plan-sponsor checklist or governance questions tied to this theme.",
                example_headlines_or_sources=[n.raw.title for n in c.articles[:3]],
                citations=cites,
            )
        )
    highlights: List[RepostHighlight] = []
    for sc in highlight_scored[: cfg.highlight_repost_count]:
        url, title = primary_article_for_cluster(sc.cluster)
        highlights.append(
            RepostHighlight(
                topic_title=sc.cluster.label[:200],
                primary_article_url=url,
                primary_article_title=title,
                why_repost="Selected by source weight and category heuristic; refine with LLM when available.",
                repost_copy_angle_a="Angle A: Frame what plan sponsors should watch on their next committee agenda.",
                repost_copy_angle_b="Angle B: Frame member communication and default design implications (educational).",
            )
        )
    return WeeklyDigest(
        week_label=week_label,
        intro=note,
        topics=topics,
        repost_highlights=highlights,
        best_repost_this_week=[h.topic_title for h in highlights],
        best_thought_leadership_month=[t.topic_title for t in topics[:3]],
        topics_to_avoid=["Run LLM pass for curated 'avoid' list based on current chatter."],
        low_confidence_note="LLM disabled or unavailable; narratives are placeholders. Enable OPENAI_API_KEY for full digest.",
    )
