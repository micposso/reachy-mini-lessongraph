from __future__ import annotations

import inspect
import io
import os
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import soundfile as sf
from openai import OpenAI
from reachy_mini import ReachyMini


def _bool_env(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y")


@dataclass
class ReachyMiniRobot:
    """
    USB mode adapter:
      - ReachyMini connects to the local daemon (Zenoh on localhost:7447)
      - TTS via OpenAI -> WAV bytes -> mini.speaker.play_audio(...)
      - STT via mini.microphones.record(...) -> WAV -> OpenAI transcribe

    Notes:
      - localhost_only is deprecated; use connection_mode when available.
      - Keep daemon running in another terminal. :contentReference[oaicite:2]{index=2}
    """

    _mini: Optional[ReachyMini] = None
    _openai: Optional[OpenAI] = None

    def __post_init__(self) -> None:
        # OpenAI client
        self._openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        # Reachy Mini client
        timeout = float(os.getenv("REACHY_CONNECT_TIMEOUT", "10"))
        spawn_daemon = _bool_env("REACHY_SPAWN_DAEMON", "0")

        # Prefer new SDK arg: connection_mode
        sig = inspect.signature(ReachyMini)
        kwargs = {"timeout": timeout, "spawn_daemon": spawn_daemon}

        if "connection_mode" in sig.parameters:
            # USB mode: connect to local daemon
            # The SDK warns localhost_only is deprecated; this is the replacement path.
            kwargs["connection_mode"] = os.getenv("REACHY_CONNECTION_MODE", "localhost_only")
        else:
            # Backward compatible older SDKs
            kwargs["localhost_only"] = True

        self._mini = ReachyMini(**kwargs)

    # ----------------- expressivity -----------------

    def set_emotion(self, emotion: str) -> None:
        e = (emotion or "").lower().strip()
        mini = self._mini

        if not mini:
            return

        # Simple, safe antenna gestures (works well for “emotion” without heavy motion)
        try:
            if e in ("happy", "excited", "encouraging"):
                mini.antennas.goto([1.0, 1.0], duration=0.35)
            elif e in ("sad", "serious", "calm"):
                mini.antennas.goto([-1.0, -1.0], duration=0.35)
            else:
                mini.antennas.goto([0.0, 0.0], duration=0.25)
        except Exception:
            pass

    def do_motion(self, motion: str) -> None:
        m = (motion or "").lower().strip()
        mini = self._mini
        if not mini:
            return

        # Keep motions conservative in USB mode
        try:
            if m in ("nod", "yes"):
                mini.head.look_at(0.3, 0.0, 0.23, duration=0.25)
                mini.head.look_at(0.3, 0.0, 0.30, duration=0.25)
                mini.head.look_at(0.3, 0.0, 0.26, duration=0.25)
            elif m in ("shake", "no"):
                mini.head.look_at(0.3, 0.05, 0.26, duration=0.25)
                mini.head.look_at(0.3, -0.05, 0.26, duration=0.25)
                mini.head.look_at(0.3, 0.0, 0.26, duration=0.25)
        except Exception:
            pass

    # ----------------- audio -----------------

    def _tts_wav_bytes(self, text: str) -> bytes:
        """
        Correct OpenAI TTS handling: stream chunks to bytes (do not bytes(resp)).
        :contentReference[oaicite:3]{index=3}
        """
        assert self._openai is not None
        model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
        voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

        buf = io.BytesIO()
        with self._openai.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="wav",
        ) as resp:
            for chunk in resp.iter_bytes():
                buf.write(chunk)
        return buf.getvalue()

    def say(self, text: str) -> None:
        mini = self._mini
        if not mini:
            return

        wav = self._tts_wav_bytes(text)

        # SDK examples show speaker playback capability. :contentReference[oaicite:4]{index=4}
        # Some SDK builds accept bytes, others accept numpy arrays.
        try:
            mini.speaker.play_audio(wav)
            return
        except Exception:
            pass

        # Fallback: decode wav to float32 array
        audio, _sr = sf.read(io.BytesIO(wav), dtype="float32")
        try:
            mini.speaker.play_audio(np.asarray(audio, dtype="float32"))
        except Exception:
            # Keep graph alive even if speaker path differs on your SDK build
            print("[ReachyMiniRobot] speaker.play_audio failed (check SDK audio type).")

    def listen_wav(self, seconds: float = 5.0) -> bytes:
        """
        Record from Reachy microphones. Different SDK builds return bytes or arrays.
        """
        mini = self._mini
        if not mini:
            return b""

        audio = mini.microphones.record(duration=float(seconds))  # capability documented in SDK guides :contentReference[oaicite:5]{index=5}

        if isinstance(audio, (bytes, bytearray)):
            return bytes(audio)

        arr = np.asarray(audio, dtype="float32")
        buf = io.BytesIO()
        sf.write(buf, arr, samplerate=16000, format="WAV")
        return buf.getvalue()

    def transcribe(self, wav_bytes: bytes) -> str:
        assert self._openai is not None
        model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")

        f = io.BytesIO(wav_bytes)
        f.name = "input.wav"
        resp = self._openai.audio.transcriptions.create(model=model, file=f)
        return (getattr(resp, "text", "") or "").strip()

    def ask_and_listen_text(self, question: str, record_seconds: float = 6.0) -> str:
        self.say(question)
        time.sleep(0.15)
        wav = self.listen_wav(record_seconds)
        return self.transcribe(wav)

    def close(self) -> None:
        # ReachyMini doesn't always require explicit close, but keep it for symmetry.
        self._mini = None
