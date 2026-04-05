"""Structured output contract for weekly digest (Pydantic models)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BestUse(str, Enum):
    REPOST = "Repost"
    THOUGHT_LEADERSHIP = "Thought leadership"
    BOTH = "Both"


class SourceCitation(BaseModel):
    """A cited article backing a topic."""

    title: str = Field(..., description="Article headline")
    url: str = Field(..., description="Canonical URL")
    publisher: Optional[str] = Field(None, description="Outlet or organization")
    published_date: Optional[str] = Field(None, description="ISO date if known")


class RepostHighlight(BaseModel):
    """One of the three highlighted repost opportunities."""

    topic_title: str
    primary_article_url: str
    primary_article_title: str
    why_repost: str = Field(..., description="Why this is worth reposting this week")
    repost_copy_angle_a: str = Field(..., description="First distinct angle (50-120 words)")
    repost_copy_angle_b: str = Field(..., description="Second distinct angle (50-120 words)")

    @field_validator("primary_article_url")
    @classmethod
    def url_ok(cls, v: str) -> str:
        if not v or not v.startswith(("http://", "https://")):
            raise ValueError("primary_article_url must be http(s)")
        return v


class TopicDigest(BaseModel):
    """One ranked trend topic in the digest."""

    rank: int = Field(..., ge=1, le=10)
    topic_title: str
    trend_summary: str = Field(..., description="2-4 sentences")
    why_matters_dc: str = Field(..., description="Why it matters to Canadian DC sponsors/consultants")
    evidence_momentum: str = Field(..., description="Evidence of trend momentum")
    best_use: BestUse
    suggested_repost_copy: str = Field(
        ...,
        description="Short repost commentary (50-80 words) for this topic",
    )
    suggested_original_angle: str = Field(..., description="Thought leadership angle")
    example_headlines_or_sources: List[str] = Field(
        default_factory=list,
        description="3-5 example headlines or source types to review",
    )
    citations: List[SourceCitation] = Field(default_factory=list)


class ArticleDraft(BaseModel):
    """Full-length article draft for editorial review (not auto-published)."""

    topic_title: str = Field(..., description="Topic from the weekly digest this draft extends")
    draft_title: str = Field(..., description="Working title for the article")
    body_markdown: str = Field(..., description="Full draft body in Markdown")
    selection_rationale: str = Field(
        default="",
        description="Why this topic was chosen for a long-form piece this week",
    )


class WeeklyDigest(BaseModel):
    """Full weekly email payload."""

    week_label: str = Field(..., description="e.g. 2026-W14")
    intro: str = Field(default="", description="Optional one-paragraph intro")
    topics: List[TopicDigest] = Field(default_factory=list, max_length=7)
    repost_highlights: List[RepostHighlight] = Field(default_factory=list, max_length=3)
    best_repost_this_week: List[str] = Field(
        default_factory=list,
        description="Short bullets: best topics to repost",
    )
    best_thought_leadership_month: List[str] = Field(
        default_factory=list,
        description="Best topics for original thought leadership this month",
    )
    topics_to_avoid: List[str] = Field(
        default_factory=list,
        description="Overplayed or low-relevance topics",
    )
    low_confidence_note: Optional[str] = Field(
        None,
        description="If fewer than max topics or weak coverage, explain here",
    )
    article_drafts: List[ArticleDraft] = Field(
        default_factory=list,
        description="Full-length drafts for review; typically two thought-leadership pieces per week",
    )

    @field_validator("topics")
    @classmethod
    def cap_topics(cls, v: List[Any]) -> List[Any]:
        return v[:7]


def digest_to_dict(d: WeeklyDigest) -> Dict[str, Any]:
    return d.model_dump(mode="json")
