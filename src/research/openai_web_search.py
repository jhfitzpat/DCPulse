"""Execute web search via OpenAI Responses API built-in ``web_search`` tool (no Tavily)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List

from openai import OpenAI

from src.config import Config
from src.research.models import SearchHit

log = logging.getLogger(__name__)


def _response_output_text(resp: Any) -> str:
    t = (getattr(resp, "output_text", None) or "").strip()
    if t:
        return t
    for item in getattr(resp, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for c in getattr(item, "content", None) or []:
            if getattr(c, "type", None) == "output_text":
                tx = getattr(c, "text", None) or ""
                if tx.strip():
                    return tx.strip()
    return ""


def _parse_hits_json(text: str) -> List[dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    # Strip optional markdown fence
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)```\s*$", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find outermost JSON object
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            log.warning("Could not parse JSON from web search response")
            return []
        data = json.loads(m.group(0))
    hits = data.get("hits")
    if not isinstance(hits, list):
        return []
    return [h for h in hits if isinstance(h, dict)]


def fetch_hits_for_query(cfg: Config, query: str, max_results: int) -> List[SearchHit]:
    """
    Run one web search session via Responses API with tools=[{"type": "web_search"}].
    The model must return JSON: {"hits":[{"title","url","snippet"},...]}.
    """
    if not cfg.openai_api_key:
        return []
    client = OpenAI(api_key=cfg.openai_api_key, timeout=min(cfg.llm_timeout_seconds, 180.0))
    instructions = (
        "You have access to the web_search tool. Use it to find current, credible pages "
        "relevant to the query (Canadian DC pensions, benefits, recordkeeping, consultants, "
        "asset managers, or indexed LinkedIn/public commentary when useful).\n\n"
        "After searching, respond with ONLY a single JSON object (no markdown fences) of the form:\n"
        '{"hits":[{"title":"string","url":"https://...","snippet":"string"}]}\n'
        f"Include at most {max_results} distinct articles. Snippets under 500 characters. "
        "Every url must be a real http(s) URL from search results."
    )
    user_block = f"{instructions}\n\nSearch query:\n{query}"
    log.info("OpenAI web search (Responses API) model=%s query=%r", cfg.web_search_responses_model, query[:80])
    try:
        resp = client.responses.create(
            model=cfg.web_search_responses_model,
            tools=[{"type": "web_search"}],
            input=user_block,
            temperature=0.2,
            max_output_tokens=8192,
        )
    except Exception as e:
        log.warning("OpenAI Responses web search failed: %s", e)
        return []

    text = _response_output_text(resp)
    if not text:
        log.warning("Empty output_text from Responses API")
        return []

    out: List[SearchHit] = []
    for row in _parse_hits_json(text):
        title = str(row.get("title") or "").strip() or "Untitled"
        url = str(row.get("url") or "").strip()
        snippet = str(row.get("snippet") or row.get("summary") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        out.append(SearchHit(title=title[:500], url=url, snippet=snippet[:4000]))
        if len(out) >= max_results:
            break
    return out
