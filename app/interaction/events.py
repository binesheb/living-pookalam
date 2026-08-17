"""Semantic events produced by perception/hardware adapters."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class InteractionEvent:
    type: str
    source: str = "unknown"
    zone: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
