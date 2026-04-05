"""Trusted source registry loaded from data/sources.yml."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List

import yaml
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class SourceEntry(BaseModel):
    """One RSS or feed source."""

    id: str
    name: str
    feed_url: str
    category: str = Field(default="general", description="regulator, media, consultant, asset_manager, other")
    weight: float = Field(default=1.0, ge=0.0, le=5.0)
    enabled: bool = True


class SourceCatalog(BaseModel):
    sources: List[SourceEntry] = Field(default_factory=list)

    def enabled_sources(self) -> List[SourceEntry]:
        return [s for s in self.sources if s.enabled]


def load_catalog(path: Path) -> SourceCatalog:
    if not path.exists():
        log.warning("sources.yml not found at %s; using empty catalog", path)
        return SourceCatalog(sources=[])
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(raw, dict) and "sources" in raw:
        return SourceCatalog.model_validate(raw)
    if isinstance(raw, list):
        return SourceCatalog(sources=[SourceEntry.model_validate(x) for x in raw])
    raise ValueError(f"Invalid sources.yml structure at {path}")
