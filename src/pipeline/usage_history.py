"""Rolling-window history of primary article URLs featured in weekly digests.

Ephemeral CI runners (e.g. GitHub Actions) do not persist the repo between runs unless you
commit ``weekly_usage.json``, use a cache step, or set ``DC_PULSE_DATA_DIR`` to a persistent path.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Set

if TYPE_CHECKING:
    from src.config import Config
    from src.pipeline.rank import ScoredCluster
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

log = logging.getLogger(__name__)


def canonical_url(url: str) -> str:
    """Normalize URL for stable comparisons (host lowercased, fragment stripped, path trimmed)."""
    raw = (url or "").strip()
    if not raw:
        return ""
    p = urlparse(raw)
    if not p.netloc:
        return raw
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    if not host:
        return raw
    port = p.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    else:
        netloc = host
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    # Sort query keys for stability when order varies
    q = parse_qsl(p.query, keep_blank_values=True)
    query = urlencode(sorted(q)) if q else ""
    return urlunparse((scheme, netloc, path, "", query, ""))


def _parse_week_label(wl: str) -> tuple[int, int] | None:
    """Parse 'YYYY-Www' ISO week label to (year, week)."""
    wl = (wl or "").strip()
    if len(wl) < 7 or "W" not in wl:
        return None
    try:
        y_str, w_str = wl.split("-W", 1)
        return int(y_str), int(w_str)
    except ValueError:
        return None


def _week_monday(year: int, week: int) -> datetime:
    return datetime.fromisocalendar(year, week, 1).replace(tzinfo=timezone.utc)


def blocked_urls_in_window(
    weeks: Dict[str, Any],
    now: datetime | None = None,
    window_weeks: int = 12,
) -> Set[str]:
    """
    Union of primary_urls from history weeks whose Monday falls within the last
    `window_weeks` ISO-week periods (day-based cutoff from current week's Monday).
    """
    now = now or datetime.now(timezone.utc)
    if window_weeks <= 0:
        return set()
    y, w, _ = now.isocalendar()
    current_monday = _week_monday(y, w)
    cutoff = current_monday - timedelta(weeks=window_weeks)

    out: Set[str] = set()
    for label, payload in weeks.items():
        parsed = _parse_week_label(label)
        if not parsed:
            continue
        wy, ww = parsed
        try:
            monday = _week_monday(wy, ww)
        except ValueError:
            continue
        if monday < cutoff:
            continue
        if monday > current_monday:
            continue
        urls = payload.get("primary_urls") if isinstance(payload, dict) else None
        if not urls:
            continue
        for u in urls:
            if isinstance(u, str) and u.strip():
                out.add(canonical_url(u))
    return out


def load_usage_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"weeks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Could not read usage history %s: %s", path, e)
        return {"weeks": {}}
    weeks = data.get("weeks")
    if not isinstance(weeks, dict):
        return {"weeks": {}}
    return {"weeks": weeks}


def record_week(
    path: Path,
    week_label: str,
    primary_urls: List[str],
    prune_older_than_weeks: int | None = None,
) -> None:
    """Append or replace entry for week_label; optionally prune old week keys."""
    data = load_usage_file(path)
    weeks: Dict[str, Any] = dict(data["weeks"])
    canon = [canonical_url(u) for u in primary_urls if u and u.strip()]
    weeks[week_label] = {"primary_urls": canon}

    if prune_older_than_weeks is not None and prune_older_than_weeks > 0:
        y, w, _ = datetime.now(timezone.utc).isocalendar()
        current_monday = _week_monday(y, w)
        cutoff = current_monday - timedelta(weeks=prune_older_than_weeks + 4)
        keep: Dict[str, Any] = {}
        for label, payload in weeks.items():
            parsed = _parse_week_label(label)
            if not parsed:
                keep[label] = payload
                continue
            wy, ww = parsed
            try:
                monday = _week_monday(wy, ww)
            except ValueError:
                keep[label] = payload
                continue
            if monday >= cutoff:
                keep[label] = payload
        weeks = keep

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"weeks": weeks}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("Recorded %d primary URLs for %s in %s", len(canon), week_label, path)


def maybe_record_weekly_usage(
    cfg: "Config",
    top: List["ScoredCluster"],
    week_label: str,
    max_topics: int,
) -> None:
    """Persist primary URLs for this week unless disabled or dry-run."""
    if not cfg.usage_history_enabled or cfg.dry_run:
        return
    if not top:
        return
    from src.pipeline.select import primary_article_for_cluster

    urls: List[str] = []
    for sc in top[:max_topics]:
        url, _ = primary_article_for_cluster(sc.cluster)
        urls.append(url)
    record_week(
        cfg.usage_history_path,
        week_label,
        urls,
        prune_older_than_weeks=cfg.usage_history_weeks + 8,
    )
