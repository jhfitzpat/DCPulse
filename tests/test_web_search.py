"""Web search hit mapping (no live API)."""

from src.research.models import SearchHit
from src.research.web_search import hits_to_raw_articles


def test_hits_to_raw_articles():
    hits = [
        SearchHit(title="T", url="https://example.com/a", snippet="S" * 100),
    ]
    raw = hits_to_raw_articles(hits)
    assert len(raw) == 1
    assert raw[0].link == "https://example.com/a"
    assert raw[0].source_id == "web_search"
