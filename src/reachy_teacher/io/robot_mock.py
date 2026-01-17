from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Emotion = Literal["neutral","happy","curious","encouraging","serious"]
Motion = Literal["idle","nod","shake_head","look_at_student","celebrate","think"]

@dataclass
class RobotMock:
    log: list[tuple[str, str]] = field(default_factory=list)

    def set_emotion(self, emotion: Emotion) -> None:
        self.log.append(("emotion", emotion))
        print(f"[Robot emotion] {emotion}")

    def do_motion(self, motion: Motion) -> None:
        self.log.append(("motion", motion))
        print(f"[Robot motion] {motion}")

    def say(self, text: str) -> None:
        self.log.append(("say", text))
        print(f"\n[Robot]\n{text}\n")
