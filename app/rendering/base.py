"""Rendering backend contract."""

from abc import ABC, abstractmethod
from typing import Any


class Renderer(ABC):
    """Output backend interface used by the experience layer."""

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def render(self, frame: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError
