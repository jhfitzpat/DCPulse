"""LLM-driven search query planning."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from openai import OpenAI

from src.config import Config
from src.research.models import SearchPlan, SearchQueryItem

log = logging.getLogger(__name__)


def _load_planner_prompt(cfg: Config) -> str:
    path = cfg.prompts_dir / "web_search_planner.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def run_search_planner(cfg: Config, week_label: str, rss_headline_sample: str) -> SearchPlan:
    """Produce a bounded search plan for trending DC/pension topics."""
    instructions = _load_planner_prompt(cfg)
    schema_hint = {
        "queries": [{"q": "string", "max_results": "integer 1-10"}],
        "notes": "string|null",
    }
    user = json.dumps(
        {
            "week_label": week_label,
            "rss_headline_sample": rss_headline_sample[:6000],
            "hard_limits": {
                "max_queries": cfg.search_max_queries,
                "default_max_results_per_query": cfg.search_results_per_query,
            },
            "output_schema": schema_hint,
        },
        ensure_ascii=False,
        indent=2,
    )
    system = "\n\n".join(
        [
            instructions or "Plan web search queries for Canadian DC pension industry trends.",
            "Respond with a single JSON object only. Queries must be strings suitable for a web search API.",
            f"Include at most {cfg.search_max_queries} queries; each max_results <= {cfg.search_results_per_query}.",
        ]
    )
    model = cfg.search_planner_model
    if not cfg.openai_api_key:
        raise ValueError("OPENAI_API_KEY required for search planner")
    client = OpenAI(api_key=cfg.openai_api_key, timeout=cfg.llm_timeout_seconds)
    log.info("Search planner model %s", model)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    data: Dict[str, Any] = json.loads(text)
    plan = SearchPlan.model_validate(data)
    # Enforce caps in code
    trimmed: list[SearchQueryItem] = []
    for q in plan.queries[: cfg.search_max_queries]:
        mr = min(q.max_results, cfg.search_results_per_query, 20)
        trimmed.append(SearchQueryItem(q=q.q.strip()[:500], max_results=max(1, mr)))
    plan = SearchPlan(queries=trimmed, notes=plan.notes)
    return plan
