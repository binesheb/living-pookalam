"""Final-day readiness and safe-start rules."""
from __future__ import annotations

from dataclasses import dataclass, field

from .product_pipeline import OutputSpec, PipelineHealth, SystemMode


@dataclass
class FinalDayController:
    output: OutputSpec = field(default_factory=OutputSpec)
    mode: SystemMode = SystemMode.SETUP

    def can_run_show(self, health: PipelineHealth) -> bool:
        return health.ready and self.output.width == 1920 and self.output.height == 1080

    def start(self, health: PipelineHealth) -> bool:
        if not self.can_run_show(health):
            self.mode = SystemMode.SAFE
            return False
        self.mode = SystemMode.SHOW
        return True

    def stop(self) -> None:
        self.mode = SystemMode.SAFE

    def recover(self) -> None:
        self.mode = SystemMode.SETUP
