from __future__ import annotations

import io
import os
import time

import numpy as np
import soundfile as sf
from scipy.signal import resample

from openai import OpenAI
from reachy_mini import ReachyMini


def tts_wav_bytes(client: OpenAI, text: str) -> bytes:
    """OpenAI TTS -> WAV bytes (streamed)."""
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


def wav_bytes_to_float32(wav: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV bytes -> (samples float32, sample_rate)."""
    audio, sr = sf.read(io.BytesIO(wav), dtype="float32")
    if audio.ndim == 1:
        audio = audio[:, None]  # (N,1)
    return audio, sr


def resample_to(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Resample audio to sr_out using scipy.signal.resample."""
    if sr_in == sr_out:
        return audio
    n_in = audio.shape[0]
    n_out = int(round(n_in * (sr_out / sr_in)))
    return resample(audio, n_out, axis=0).astype("float32")


def match_channels(audio: np.ndarray, ch_out: int) -> np.ndarray:
    """Ensure audio has ch_out channels (1 or 2)."""
    ch_in = audio.shape[1]
    if ch_in == ch_out:
        return audio.astype("float32")
    if ch_out == 1:
        # downmix to mono
        return audio.mean(axis=1, keepdims=True).astype("float32")
    if ch_out == 2 and ch_in == 1:
        return np.repeat(audio, 2, axis=1).astype("float32")
    # fallback: truncate or pad
    if ch_in > ch_out:
        return audio[:, :ch_out].astype("float32")
    pad = np.zeros((audio.shape[0], ch_out - ch_in), dtype="float32")
    return np.concatenate([audio, pad], axis=1).astype("float32")


def play_tts(mini: ReachyMini, client: OpenAI, text: str) -> None:
    """Generate TTS and play through Reachy's speaker."""
    print(f"  Generating TTS for: '{text}'")
    wav = tts_wav_bytes(client, text)
    audio, sr_in = wav_bytes_to_float32(wav)

    sr_out = mini.media.get_output_audio_samplerate()
    ch_out = mini.media.get_output_channels()

    print(f"  Audio: {sr_in}Hz -> {sr_out}Hz, {audio.shape[1]}ch -> {ch_out}ch")

    audio = resample_to(audio, sr_in, sr_out)
    audio = match_channels(audio, ch_out)

    mini.media.push_audio_sample(audio)

    # push_audio_sample is non-blocking; wait for playback duration
    duration = audio.shape[0] / sr_out
    print(f"  Playing {duration:.1f}s of audio...")
    time.sleep(duration + 0.1)


def record_seconds(mini: ReachyMini, seconds: float) -> tuple[np.ndarray, int]:
    """Record for ~seconds by polling get_audio_sample()."""
    sr = mini.media.get_input_audio_samplerate()
    target_n = int(sr * seconds)

    chunks: list[np.ndarray] = []
    n = 0
    start = time.time()

    while n < target_n and (time.time() - start) < (seconds + 1.5):
        chunk = mini.media.get_audio_sample()
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


def float32_to_wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    """Convert float32 numpy array to WAV bytes."""
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


def transcribe_wav(client: OpenAI, wav_bytes: bytes) -> str:
    """Transcribe WAV bytes using OpenAI Whisper."""
    model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    f = io.BytesIO(wav_bytes)
    f.name = "input.wav"
    resp = client.audio.transcriptions.create(model=model, file=f)
    return (getattr(resp, "text", "") or "").strip()


def main():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    print("Connecting to Reachy Mini...")
    with ReachyMini() as mini:
        print("Connected! Starting voice test...\n")

        # Start audio devices
        print("Starting audio recording and playback...")
        mini.media.start_recording()
        mini.media.start_playing()

        try:
            # Play TTS prompt
            print("\n[1] Playing TTS prompt...")
            play_tts(mini, client, "Voice test. Please say: hello Reachy.")

            # Record response
            print("\n[2] Recording for 4 seconds...")
            rec, sr = record_seconds(mini, 4.0)
            print(f"  Recorded {rec.shape[0]} samples at {sr}Hz")

            # Debug: check signal levels
            print(f"  Signal min: {rec.min():.6f}, max: {rec.max():.6f}")
            print(f"  Signal RMS: {np.sqrt(np.mean(rec**2)):.6f}")

            # Downmix to mono for STT
            if rec.shape[1] > 1:
                rec_mono = rec.mean(axis=1, keepdims=True)
            else:
                rec_mono = rec

            wav = float32_to_wav_bytes(rec_mono, sr)

            # Debug: save recorded audio to file for inspection
            debug_path = "debug_recording.wav"
            with open(debug_path, "wb") as f:
                f.write(wav)
            print(f"  Saved recording to: {debug_path}")

            # Transcribe
            print("\n[3] Transcribing...")
            text = transcribe_wav(client, wav)
            print(f"  Transcribed: '{text}'")

            # Play back what was heard
            print("\n[4] Playing response...")
            response = f"I heard: {text if text else 'nothing clear'}"
            play_tts(mini, client, response)

            print("\nVoice test complete!")

        finally:
            print("\nStopping audio devices...")
            mini.media.stop_recording()
            mini.media.stop_playing()


if __name__ == "__main__":
    main()
