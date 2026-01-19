from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import soundfile as sf
from scipy.signal import resample

from openai import OpenAI
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose


def _tts_wav_bytes(client: OpenAI, text: str) -> bytes:
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")

    buf = io.BytesIO()
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        response_format="wav",
    ) as resp:
        for chunk in resp.iter_bytes():
            buf.write(chunk)
    return buf.getvalue()


def _wav_bytes_to_float32(wav: bytes) -> tuple[np.ndarray, int]:
    audio, sr = sf.read(io.BytesIO(wav), dtype="float32")
    if audio.ndim == 1:
        audio = audio[:, None]
    return audio, sr


def _resample_to(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return audio.astype("float32")
    n_in = audio.shape[0]
    n_out = int(round(n_in * (sr_out / sr_in)))
    return resample(audio, n_out, axis=0).astype("float32")


def _match_channels(audio: np.ndarray, ch_out: int) -> np.ndarray:
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


def _float32_to_wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


def _transcribe_wav(client: OpenAI, wav_bytes: bytes) -> str:
    model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    f = io.BytesIO(wav_bytes)
    f.name = "input.wav"
    resp = client.audio.transcriptions.create(model=model, file=f)
    return (getattr(resp, "text", "") or "").strip()


@dataclass
class ReachyMiniRobot:
    """
    Reachy Mini adapter using mini.media for speaker + microphones.
    Connect once, reserve audio devices once, reuse across the whole lesson session.
    """
    media_backend: str = "default"
    _mini: Optional[ReachyMini] = None
    _client: Optional[OpenAI] = None
    _audio_started: bool = False

    def open(self) -> "ReachyMiniRobot":
        if self._client is None:
            self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        if self._mini is None:
            self._mini = ReachyMini(media_backend=self.media_backend)
            # enter context (ReachyMini supports with-block)
            self._mini.__enter__()

        if not self._audio_started:
            self._mini.media.start_recording()
            self._mini.media.start_playing()
            time.sleep(0.5)
            self._flush_audio_buffer()
            self._audio_started = True

        return self

    def close(self) -> None:
        if self._mini is not None and self._audio_started:
            try:
                self._mini.media.stop_recording()
            except Exception:
                pass
            try:
                self._mini.media.stop_playing()
            except Exception:
                pass
            self._audio_started = False

        if self._mini is not None:
            try:
                self._mini.__exit__(None, None, None)
            except Exception:
                pass
            self._mini = None

    def _flush_audio_buffer(self) -> None:
        assert self._mini is not None
        flush_start = time.time()
        while time.time() - flush_start < 0.3:
            _ = self._mini.media.get_audio_sample()
            time.sleep(0.01)

    # --------- expressivity (keep minimal and safe) ---------

    def set_emotion(self, emotion: str) -> None:
        # You can improve this mapping later
        if not self._mini:
            return
        e = (emotion or "").lower().strip()
        try:
            if e in ("happy", "excited", "encouraging"):
                self._mini.goto_target(antennas=np.deg2rad([45, 45]), duration=0.4, method="minjerk")
            elif e in ("sad", "serious", "calm"):
                self._mini.goto_target(antennas=np.deg2rad([-20, -20]), duration=0.4, method="minjerk")
            else:
                self._mini.goto_target(antennas=np.deg2rad([0, 0]), duration=0.3, method="minjerk")
        except Exception:
            pass

    def do_motion(self, motion: str) -> None:
        if not self._mini:
            return
        m = (motion or "").lower().strip()
        try:
            if m in ("nod", "yes"):
                self._mini.goto_target(head=create_head_pose(pitch=10, degrees=True), duration=0.25)
                self._mini.goto_target(head=create_head_pose(pitch=-5, degrees=True), duration=0.25)
                self._mini.goto_target(head=create_head_pose(), duration=0.25)
            elif m in ("shake", "no"):
                self._mini.goto_target(head=create_head_pose(yaw=12, degrees=True), duration=0.25)
                self._mini.goto_target(head=create_head_pose(yaw=-12, degrees=True), duration=0.25)
                self._mini.goto_target(head=create_head_pose(), duration=0.25)
        except Exception:
            pass

    # --------- core I/O ---------

    def say(self, text: str) -> None:
        self.open()
        assert self._mini is not None
        assert self._client is not None

        wav = _tts_wav_bytes(self._client, text)
        audio, sr_in = _wav_bytes_to_float32(wav)

        sr_out = self._mini.media.get_output_audio_samplerate()
        ch_out = self._mini.media.get_output_channels()

        audio = _resample_to(audio, sr_in, sr_out)
        audio = _match_channels(audio, ch_out)

        self._mini.media.push_audio_sample(audio)

        duration = audio.shape[0] / sr_out
        time.sleep(duration + 0.1)

    def _record_seconds(self, seconds: float) -> tuple[np.ndarray, int]:
        assert self._mini is not None

        sr = self._mini.media.get_input_audio_samplerate()
        target_n = int(sr * seconds)

        chunks: list[np.ndarray] = []
        n = 0
        start = time.time()

        while n < target_n and (time.time() - start) < (seconds + 1.5):
            chunk = self._mini.media.get_audio_sample()
            if chunk is None:
                time.sleep(0.01)
                continue
            chunk = np.asarray(chunk, dtype="float32")
            if chunk.ndim == 1:
                chunk = chunk[:, None]
            chunks.append(chunk)
            n += chunk.shape[0]

        if not chunks:
            return np.zeros((0, 2), dtype="float32"), sr

        audio = np.concatenate(chunks, axis=0)
        return audio, sr

    def ask_and_listen_text(self, question: str, record_seconds: float = 6.0) -> str:
        self.open()
        assert self._client is not None

        self.say(question)
        rec, sr = self._record_seconds(record_seconds)

        if rec.size == 0:
            return ""

        # downmix to mono for STT
        if rec.shape[1] > 1:
            rec = rec.mean(axis=1, keepdims=True)

        wav = _float32_to_wav_bytes(rec, sr)
        return _transcribe_wav(self._client, wav)
