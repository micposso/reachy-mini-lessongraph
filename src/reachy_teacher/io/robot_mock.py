from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Emotion = Literal["neutral", "happy", "curious", "encouraging", "serious", "excited", "supportive", "sad", "disappointed", "thinking"]
Motion = Literal["idle", "nod", "shake_head", "shake", "look_at_student", "celebrate", "think", "encourage", "supportive_nod", "dance"]

@dataclass
class RobotMock:
    log: list[tuple[str, str]] = field(default_factory=list)

    def set_emotion(self, emotion: str) -> None:
        self.log.append(("emotion", emotion))
        print(f"🎭 [Robot emotion] {emotion}")

    def do_motion(self, motion: str) -> None:
        self.log.append(("motion", motion))
        print(f"🤸 [Robot motion] {motion}")

    def say(self, text: str) -> None:
        self.log.append(("say", text))
        print(f"\n🤖 [Robot says]\n{text}\n")

    def ask_and_listen_text(self, question: str, record_seconds: float = 10.0) -> str:
        """Ask a question and get typed input (mock version)."""
        self.say(question)
        self.log.append(("listen", f"{record_seconds}s"))
        print(f"🎤 [Listening for {record_seconds}s... (mock - using typed input)]")
        try:
            response = input("[Your answer] > ").strip()
        except EOFError:
            response = ""
        return response
