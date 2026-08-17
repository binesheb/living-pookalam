"""Runtime state shared by the local application services."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RuntimeState:
    running: bool = False
    started_at: datetime | None = None
    active_scene: str = "idle"
    last_event: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        self.running = True
        self.started_at = datetime.now(timezone.utc)

    def stop(self) -> None:
        self.running = False
