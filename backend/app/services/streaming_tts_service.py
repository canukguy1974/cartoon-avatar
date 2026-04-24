"""Generate WAV audio for a single sentence, returning raw bytes."""

import asyncio
import struct
import tempfile
from pathlib import Path
from types import SimpleNamespace

try:
    import edge_tts
except ImportError:  # pragma: no cover
    edge_tts = SimpleNamespace(Communicate=None)


DEFAULT_VOICE = "en-US-AvaNeural"


def _wav_duration_seconds(wav_bytes: bytes) -> float:
    """Parse WAV header to compute duration in seconds."""
    try:
        # Standard WAV: bytes 24-27 = sample rate, bytes 34-35 = bits per sample
        # bytes 40-43 = data chunk size, bytes 22-23 = num channels
        if len(wav_bytes) < 44:
            return 0.0
        num_channels = struct.unpack_from("<H", wav_bytes, 22)[0]
        sample_rate = struct.unpack_from("<I", wav_bytes, 24)[0]
        bits_per_sample = struct.unpack_from("<H", wav_bytes, 34)[0]
        data_size = struct.unpack_from("<I", wav_bytes, 40)[0]
        if sample_rate == 0 or num_channels == 0 or bits_per_sample == 0:
            return 0.0
        bytes_per_sample = bits_per_sample // 8
        total_samples = data_size // (num_channels * bytes_per_sample)
        return total_samples / sample_rate
    except Exception:
        return 0.0


async def generate_sentence_audio(sentence: str) -> dict:
    """Generate WAV audio bytes for a single sentence.

    Returns ``{"wav_bytes": bytes, "duration_seconds": float}``.
    """
    if edge_tts.Communicate is None:
        raise RuntimeError("edge-tts is not installed")

    normalized = (sentence or "").strip()
    if not normalized:
        raise ValueError("Empty sentence")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        mp3_path = tmp / "sentence.mp3"
        wav_path = tmp / "sentence.wav"

        communicator = edge_tts.Communicate(normalized, voice=DEFAULT_VOICE)
        await communicator.save(str(mp3_path))

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i", str(mp3_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "24000",
            str(wav_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_text = stderr.decode().strip() or "ffmpeg conversion failed"
            raise RuntimeError(error_text)

        wav_bytes = wav_path.read_bytes()
        duration = _wav_duration_seconds(wav_bytes)

        return {
            "wav_bytes": wav_bytes,
            "duration_seconds": duration,
        }
