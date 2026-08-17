"""Experience state machine foundation."""

from app.interaction.events import InteractionEvent


class ExperienceEngine:
    """Owns scene transitions without knowing about physical hardware."""

    def __init__(self, default_scene: str = "idle") -> None:
        self.active_scene = default_scene

    def handle(self, event: InteractionEvent) -> str:
        if event.type == "SCENE_REQUEST":
            requested = event.payload.get("scene")
            if isinstance(requested, str) and requested:
                self.active_scene = requested
        return self.active_scene
