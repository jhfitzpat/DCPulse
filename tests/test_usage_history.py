"""Usage history URL canonicalization, rolling window, and selection."""

from datetime import datetime, timezone
from typing import List, Tuple

from src.pipeline.cluster import TopicCluster
from src.pipeline.normalize import normalize_and_score
from src.pipeline.normalize import ExclusionRules
from src.pipeline.rank import score_cluster
from src.pipeline.select import pick_top_topics
from src.pipeline.usage_history import (
    blocked_urls_in_window,
    canonical_url,
    record_week,
    load_usage_file,
)
from src.sources.collect import RawArticle


def _raw(
    title: str,
    link: str,
    category: str = "media",
) -> RawArticle:
    return RawArticle(
        title=title,
        link=link,
        summary="summary",
        published=datetime(2026, 1, 15, tzinfo=timezone.utc),
        source_id="s1",
        source_name="Test",
        source_category=category,
        source_weight=1.0,
        feed_url="https://example.com/feed",
    )


def _cluster(cid: str, label: str, links: List[Tuple[str, str]]) -> TopicCluster:
    arts = []
    for title, link in links:
        raw = _raw(title, link)
        norm = normalize_and_score([raw])[0]
        arts.append(norm)
    return TopicCluster(id=cid, label=label, articles=arts)


def test_canonical_url_strips_fragment_and_host_case():
    u = "HTTPS://Example.COM/path/?b=2&a=1#frag"
    c = canonical_url(u)
    assert "#" not in c
    assert "example.com" in c
    assert "a=1" in c and "b=2" in c


def test_canonical_url_empty():
    assert canonical_url("") == ""


def test_blocked_urls_in_window_respects_rolling_window():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    weeks = {"2025-W01": {"primary_urls": ["https://old.example/a"]}}
    blocked = blocked_urls_in_window(weeks, now=now, window_weeks=12)
    assert canonical_url("https://old.example/a") not in blocked


def test_blocked_urls_in_window_includes_current_iso_week():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    y, w, _ = now.isocalendar()
    label = f"{y}-W{w:02d}"
    weeks = {label: {"primary_urls": ["https://thisweek.example/x"]}}
    blocked = blocked_urls_in_window(weeks, now=now, window_weeks=12)
    assert canonical_url("https://thisweek.example/x") in blocked


def test_blocked_urls_in_window_zero_window():
    assert blocked_urls_in_window({"2026-W01": {"primary_urls": ["https://x.com"]}}, window_weeks=0) == set()


def test_record_week_roundtrip(tmp_path):
    p = tmp_path / "weekly_usage.json"
    record_week(p, "2026-W10", ["https://a.com/x", "https://b.com/y"], prune_older_than_weeks=None)
    data = load_usage_file(p)
    assert "2026-W10" in data["weeks"]
    assert len(data["weeks"]["2026-W10"]["primary_urls"]) == 2


def test_pick_top_topics_prefers_unblocked():
    clusters = [
        _cluster("c1", "Alpha", [("A", "https://blocked.example/1")]),
        _cluster("c2", "Beta", [("B", "https://fresh.example/2")]),
        _cluster("c3", "Gamma", [("C", "https://fresh.example/3")]),
    ]
    rules = ExclusionRules()
    ranked = [score_cluster(c, rules) for c in clusters]
    blocked = {canonical_url("https://blocked.example/1")}
    picked = pick_top_topics(ranked, max_topics=2, blocked_urls=blocked)
    assert len(picked) == 2
    # First ranked was blocked; expect Beta, Gamma
    assert picked[0].cluster.id == "c2"
    assert picked[1].cluster.id == "c3"


def test_pick_top_topics_fills_when_all_blocked():
    clusters = [
        _cluster("c1", "A", [("T", "https://x.com/1")]),
        _cluster("c2", "B", [("T", "https://x.com/2")]),
    ]
    rules = ExclusionRules()
    ranked = [score_cluster(c, rules) for c in clusters]
    blocked = {canonical_url("https://x.com/1"), canonical_url("https://x.com/2")}
    picked = pick_top_topics(ranked, max_topics=2, blocked_urls=blocked)
    assert len(picked) == 2
    assert {p.cluster.id for p in picked} == {"c1", "c2"}
