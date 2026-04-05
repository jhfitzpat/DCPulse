"""JSON parsing for OpenAI web search output."""

from src.research.openai_web_search import _parse_hits_json


def test_parse_plain_json():
    raw = '{"hits":[{"title":"A","url":"https://x.com","snippet":"S"}]}'
    rows = _parse_hits_json(raw)
    assert len(rows) == 1
    assert rows[0]["url"] == "https://x.com"


def test_parse_fenced_json():
    raw = '```json\n{"hits":[]}\n```'
    rows = _parse_hits_json(raw)
    assert rows == []
