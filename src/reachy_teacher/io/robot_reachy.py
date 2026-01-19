from __future__ import annotations

import inspect
import io
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import soundfile as sf
from scipy.signal import resample
from openai import OpenAI
from reachy_mini import ReachyMini


def _bool_env(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y")


def _resample_audio(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Resample audio to target sample rate."""
    if sr_in == sr_out:
        return audio
    n_in = audio.shape[0]
    n_out = int(round(n_in * (sr_out / sr_in)))
    return resample(audio, n_out, axis=0).astype("float32")


def _match_channels(audio: np.ndarray, ch_out: int) -> np.ndarray:
    """Ensure audio has the target number of channels."""
    if audio.ndim == 1:
        audio = audio[:, None]
    ch_in = audio.shape[1]
    if ch_in == ch_out:
        return audio.astype("float32")
    if ch_out == 1:
        return audio.mean(axis=1, keepdims=True).astype("float32")
    if ch_out == 2 and ch_in == 1:
        return np.repeat(audio, 2, axis=1).astype("float32")
    if ch_in > ch_out:
        return audio[:, :ch_out].astype("float32")
    pad = np.zeros((audio.shape[0], ch_out - ch_in), dtype="float32")
    return np.concatenate([audio, pad], axis=1).astype("float32")


@dataclass
class ReachyMiniRobot:
    """
    USB mode adapter:
      - ReachyMini connects to the local daemon (Zenoh on localhost:7447)
      - TTS via OpenAI -> WAV bytes -> mini.media.push_audio_sample(...)
      - STT via mini.media.get_audio_sample() -> WAV -> OpenAI transcribe

    Notes:
      - localhost_only is deprecated; use connection_mode when available.
      - Keep daemon running in another terminal.
    """

    _mini: Optional[ReachyMini] = field(default=None, repr=False)
    _openai: Optional[OpenAI] = field(default=None, repr=False)
    _audio_started: bool = field(default=False, repr=False)

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
            kwargs["connection_mode"] = os.getenv("REACHY_CONNECTION_MODE", "localhost_only")
        else:
            kwargs["localhost_only"] = True

        self._mini = ReachyMini(**kwargs)
        self._start_audio()

    def _start_audio(self) -> None:
        """Start audio recording and playback devices."""
        if self._mini and not self._audio_started:
            try:
                self._mini.media.start_recording()
                self._mini.media.start_playing()
                self._audio_started = True

                # Wait for audio devices to stabilize
                time.sleep(0.5)

                # Flush stale audio samples from buffer
                flush_start = time.time()
                while time.time() - flush_start < 0.3:
                    chunk = self._mini.media.get_audio_sample()
                    if chunk is None:
                        time.sleep(0.01)
            except Exception as e:
                print(f"[ReachyMiniRobot] Failed to start audio: {e}")

    def _stop_audio(self) -> None:
        """Stop audio devices."""
        if self._mini and self._audio_started:
            try:
                self._mini.media.stop_recording()
                self._mini.media.stop_playing()
                self._audio_started = False
            except Exception:
                pass

    # ----------------- expressivity -----------------

    def set_emotion(self, emotion: str) -> None:
        e = (emotion or "").lower().strip()
        mini = self._mini

        if not mini:
            return

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
        """Generate TTS audio using OpenAI."""
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
        """Play TTS audio through Reachy's speaker using media API."""
        mini = self._mini
        if not mini:
            return

        wav = self._tts_wav_bytes(text)
        audio, sr_in = sf.read(io.BytesIO(wav), dtype="float32")

        # Get output device parameters
        try:
            sr_out = mini.media.get_output_audio_samplerate()
            ch_out = mini.media.get_output_channels()
        except Exception as e:
            print(f"[ReachyMiniRobot] Failed to get audio params: {e}")
            return

        # Resample and match channels
        audio = _resample_audio(audio, sr_in, sr_out)
        audio = _match_channels(audio, ch_out)

        # Play audio (non-blocking)
        try:
            mini.media.push_audio_sample(audio)
            # Wait for playback to complete
            duration = audio.shape[0] / sr_out
            time.sleep(duration + 0.1)
        except Exception as e:
            print(f"[ReachyMiniRobot] push_audio_sample failed: {e}")

    def listen_wav(self, seconds: float = 5.0) -> bytes:
        """Record from Reachy microphones using media API."""
        mini = self._mini
        if not mini:
            return b""

        try:
            sr = mini.media.get_input_audio_samplerate()
        except Exception:
            sr = 44100

        target_n = int(sr * seconds)
        chunks: list[np.ndarray] = []
        n = 0
        start = time.time()

        while n < target_n and (time.time() - start) < (seconds + 1.5):
            try:
                chunk = mini.media.get_audio_sample()
            except Exception:
                time.sleep(0.01)
                continue

            if chunk is None:
                time.sleep(0.01)
                continue

            chunk = np.asarray(chunk, dtype="float32")
            if chunk.ndim == 1:
                chunk = chunk[:, None]
            chunks.append(chunk)
            n += chunk.shape[0]

        if not chunks:
            return b""

        audio = np.concatenate(chunks, axis=0)

        # Downmix to mono for transcription
        if audio.shape[1] > 1:
            audio = audio.mean(axis=1, keepdims=True)

        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        return buf.getvalue()

    def transcribe(self, wav_bytes: bytes) -> str:
        """Transcribe WAV audio using OpenAI Whisper."""
        if not wav_bytes:
            return ""

        assert self._openai is not None
        model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")

        f = io.BytesIO(wav_bytes)
        f.name = "input.wav"
        resp = self._openai.audio.transcriptions.create(model=model, file=f)
        return (getattr(resp, "text", "") or "").strip()

    def ask_and_listen_text(self, question: str, record_seconds: float = 6.0) -> str:
        """Ask a question via TTS and listen for response."""
        self.say(question)
        time.sleep(0.15)
        wav = self.listen_wav(record_seconds)
        return self.transcribe(wav)

    def close(self) -> None:
        """Clean up resources."""
        self._stop_audio()
        self._mini = None
