"""Email rendering with article drafts."""

from src.output.render_email import _draft_body_html, render_html, render_text
from src.output.schema import ArticleDraft, WeeklyDigest


def _minimal_digest() -> WeeklyDigest:
    return WeeklyDigest(
        week_label="2026-W01",
        intro="Intro",
        topics=[],
        repost_highlights=[],
        best_repost_this_week=[],
        best_thought_leadership_month=[],
        topics_to_avoid=[],
        article_drafts=[
            ArticleDraft(
                topic_title="Topic A",
                draft_title="Draft title",
                body_markdown="Para one.\n\nPara two.",
                selection_rationale="Strong TL angle",
            )
        ],
    )


def test_render_text_includes_draft_section():
    text = render_text(_minimal_digest())
    assert "Full-length article drafts" in text
    assert "Draft title" in text
    assert "Para one" in text


def test_render_html_includes_draft_section():
    html = render_html(_minimal_digest())
    assert "editorial review" in html
    assert "Draft title" in html


def test_draft_body_html_heading():
    h = _draft_body_html("## Sub\n\nBody line.")
    assert "Sub" in h
    assert "Body line" in h
