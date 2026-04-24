import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.services.streaming_tts_service import generate_sentence_audio


class StreamingTtsServiceTests(IsolatedAsyncioTestCase):
    @patch("app.services.streaming_tts_service.asyncio.create_subprocess_exec")
    @patch("app.services.streaming_tts_service.edge_tts.Communicate")
    async def test_generate_sentence_audio_returns_wav_bytes_and_duration(
        self,
        mock_communicate,
        mock_create_subprocess_exec,
    ) -> None:
        communicator = mock_communicate.return_value

        # Build a minimal valid WAV header (44 bytes header + 48000 bytes of data)
        # 24000 Hz, mono, 16-bit = 1 second of audio per 48000 bytes
        import struct
        sample_rate = 24000
        num_channels = 1
        bits_per_sample = 16
        data_size = 48000
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        block_align = num_channels * (bits_per_sample // 8)
        wav_header = b"RIFF"
        wav_header += struct.pack("<I", 36 + data_size)
        wav_header += b"WAVE"
        wav_header += b"fmt "
        wav_header += struct.pack("<I", 16)  # chunk size
        wav_header += struct.pack("<H", 1)   # PCM
        wav_header += struct.pack("<H", num_channels)
        wav_header += struct.pack("<I", sample_rate)
        wav_header += struct.pack("<I", byte_rate)
        wav_header += struct.pack("<H", block_align)
        wav_header += struct.pack("<H", bits_per_sample)
        wav_header += b"data"
        wav_header += struct.pack("<I", data_size)
        fake_wav = wav_header + (b"\x00" * data_size)

        async def fake_save(path: str) -> None:
            Path(path).write_bytes(b"fake mp3 data")

        communicator.save = AsyncMock(side_effect=fake_save)

        process = AsyncMock()
        process.returncode = 0

        async def fake_communicate():
            return (b"", b"")

        process.communicate.side_effect = fake_communicate
        mock_create_subprocess_exec.return_value = process

        # Patch tempfile so we can inject our fake WAV
        original_generate = generate_sentence_audio

        with patch("app.services.streaming_tts_service.tempfile.TemporaryDirectory") as mock_tmpdir:
            real_tmpdir = tempfile.mkdtemp()
            mock_tmpdir.return_value.__enter__ = lambda s: real_tmpdir
            mock_tmpdir.return_value.__exit__ = lambda s, *a: None

            # Write fake WAV to where ffmpeg would output
            wav_path = Path(real_tmpdir) / "sentence.wav"
            wav_path.write_bytes(fake_wav)

            result = await generate_sentence_audio("Hello there")

            self.assertIn("wav_bytes", result)
            self.assertIn("duration_seconds", result)
            self.assertEqual(result["wav_bytes"], fake_wav)
            self.assertAlmostEqual(result["duration_seconds"], 1.0, places=1)

            # Cleanup
            import shutil
            shutil.rmtree(real_tmpdir, ignore_errors=True)

    async def test_generate_sentence_audio_rejects_empty_text(self) -> None:
        with self.assertRaises(ValueError):
            await generate_sentence_audio("")

        with self.assertRaises(ValueError):
            await generate_sentence_audio("   ")
