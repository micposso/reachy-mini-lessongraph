from __future__ import annotations

import os
import time
from typing import Optional

try:
    from reachy_mini import ReachyMini
    from reachy_mini.utils import create_head_pose
except Exception as e:  # pragma: no cover
    ReachyMini = None
    create_head_pose = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


class ReachyMiniRobot:
    """
    Minimal adapter compatible with your existing RobotMock calls:
      - set_emotion(str)
      - do_motion(str)
      - say(str)

    It tries to use Reachy Mini's native audio if exposed by the SDK.
    Otherwise it falls back to printing (so you can keep testing without breaking).
    """

    def __init__(self) -> None:
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "reachy-mini is not available. Run: uv add reachy-mini"
            ) from _IMPORT_ERROR
        self._mini: Optional[ReachyMini] = None

    def __enter__(self) -> "ReachyMiniRobot":
        # Most examples use the context manager pattern for ReachyMini. :contentReference[oaicite:2]{index=2}
        self._mini = ReachyMini()
        self._mini.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._mini is not None:
            self._mini.__exit__(exc_type, exc, tb)
            self._mini = None

    def _require(self) -> ReachyMini:
        if self._mini is None:
            raise RuntimeError("ReachyMiniRobot not connected. Use: with ReachyMiniRobot() as robot:")
        return self._mini

    # ---------- expressivity ----------
    def set_emotion(self, emotion: str) -> None:
        """
        Map your lesson emotion labels to a small head pose or built-in behavior if present.
        Keep it conservative for safety.
        """
        mini = self._require()

        e = (emotion or "").lower().strip()

        # If the SDK exposes a higher-level emotion API, use it.
        # (We keep this defensive because SDK APIs evolve.)
        for attr in ("set_emotion", "emotion", "emotions"):
            obj = getattr(mini, attr, None)
            if callable(obj):
                try:
                    obj(e)
                    return
                except Exception:
                    pass

        # Fallback: small expressive head motions
        if create_head_pose is None:
            return

        if e in ("happy", "excited"):
            mini.goto_target(head=create_head_pose(z=8, roll=10, degrees=True, mm=True), duration=0.5)
        elif e in ("sad", "concerned"):
            mini.goto_target(head=create_head_pose(z=-6, roll=-8, degrees=True, mm=True), duration=0.6)
        elif e in ("curious", "question"):
            mini.goto_target(head=create_head_pose(z=6, roll=-12, degrees=True, mm=True), duration=0.6)
        else:
            mini.goto_target(head=create_head_pose(z=0, roll=0, degrees=True, mm=True), duration=0.4)

    def do_motion(self, motion: str) -> None:
        """
        Map your lesson motion labels to safe head movements.
        """
        mini = self._require()
        m = (motion or "").lower().strip()

        if create_head_pose is None:
            return

        if m in ("nod", "yes"):
            mini.goto_target(head=create_head_pose(z=6, degrees=True, mm=True), duration=0.25)
            mini.goto_target(head=create_head_pose(z=-4, degrees=True, mm=True), duration=0.25)
            mini.goto_target(head=create_head_pose(z=2, degrees=True, mm=True), duration=0.25)
        elif m in ("shake", "no"):
            mini.goto_target(head=create_head_pose(roll=12, degrees=True, mm=True), duration=0.25)
            mini.goto_target(head=create_head_pose(roll=-12, degrees=True, mm=True), duration=0.25)
            mini.goto_target(head=create_head_pose(roll=0, degrees=True, mm=True), duration=0.25)
        elif m in ("look_left",):
            mini.goto_target(head=create_head_pose(roll=18, degrees=True, mm=True), duration=0.4)
        elif m in ("look_right",):
            mini.goto_target(head=create_head_pose(roll=-18, degrees=True, mm=True), duration=0.4)
        else:
            # tiny idle movement
            mini.goto_target(head=create_head_pose(z=2, degrees=True, mm=True), duration=0.3)

    # ---------- voice ----------
    def say(self, text: str) -> None:
        """
        Speak through Reachy if the SDK exposes an audio API.
        Otherwise fall back to console print (keeps graph working).
        """
        mini = self._require()
        t = (text or "").strip()
        if not t:
            return

        # Try likely speech methods (defensive)
        for fn_name in ("say", "speak", "tts"):
            fn = getattr(mini, fn_name, None)
            if callable(fn):
                try:
                    fn(t)
                    return
                except Exception:
                    pass

        # Try nested audio/speaker object patterns
        for obj_name in ("audio", "speaker", "sound"):
            obj = getattr(mini, obj_name, None)
            if obj is None:
                continue
            for fn_name in ("say", "speak", "play_tts", "tts"):
                fn = getattr(obj, fn_name, None)
                if callable(fn):
                    try:
                        fn(t)
                        return
                    except Exception:
                        pass

        # Fallback: do not break the lesson loop
        print(f"[ReachyMiniRobot SAY] {t}")
        # Small pause to approximate speaking time (optional)
        if os.getenv("REACHY_FAKE_SPEECH_DELAY", "1") == "1":
            time.sleep(min(2.0, 0.03 * len(t)))
