"""Pydantic models for LLM search planning and provider hits."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SearchQueryItem(BaseModel):
    q: str = Field(..., description="Search query string")
    max_results: int = Field(default=5, ge=1, le=20)


class SearchPlan(BaseModel):
    queries: List[SearchQueryItem] = Field(default_factory=list)
    notes: Optional[str] = None


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str
