"""WeeklyDigest schema with article drafts."""

from src.output.schema import ArticleDraft, WeeklyDigest


def test_weekly_digest_article_drafts_default():
    d = WeeklyDigest(week_label="2026-W01")
    assert d.article_drafts == []


def test_article_draft_roundtrip():
    d = WeeklyDigest(
        week_label="2026-W01",
        article_drafts=[
            ArticleDraft(
                topic_title="Test",
                draft_title="Title",
                body_markdown="Hello\n\nWorld",
                selection_rationale="Because",
            )
        ],
    )
    assert len(d.article_drafts) == 1
    assert d.article_drafts[0].body_markdown.startswith("Hello")
