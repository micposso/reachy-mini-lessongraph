from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class RobotConfig:
    backend: str = "mock"  # "mock" | "reachy"
    reachy_host: Optional[str] = None  # if you use network connection


class Robot(Protocol):
    def set_emotion(self, emotion: str) -> None: ...
    def do_motion(self, motion: str) -> None: ...
    def say(self, text: str) -> None: ...
    def ask_and_listen_text(self, question: str, record_seconds: float = 5.0) -> str: ...
    def close(self) -> None: ...
