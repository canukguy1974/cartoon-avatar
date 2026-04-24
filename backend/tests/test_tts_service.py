import os
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.services.tts_service import generate_speech_audio


class TtsServiceTests(IsolatedAsyncioTestCase):
    @patch("app.services.tts_service.uuid4")
    @patch("app.services.tts_service.asyncio.create_subprocess_exec")
    @patch("app.services.tts_service.edge_tts.Communicate")
    async def test_generate_speech_audio_writes_unique_wav_and_returns_static_url(
        self,
        mock_communicate,
        mock_create_subprocess_exec,
        mock_uuid4,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir)
            mp3_path = audio_dir / "speech-abc123.mp3"
            wav_path = audio_dir / "speech-abc123.wav"

            communicator = mock_communicate.return_value

            async def fake_save(path: str) -> None:
                Path(path).write_bytes(b"mp3")

            communicator.save = AsyncMock(side_effect=fake_save)
            mock_uuid4.return_value.hex = "abc123"

            process = AsyncMock()
            process.returncode = 0

            async def fake_communicate():
                wav_path.write_bytes(b"wav")
                return (b"", b"")

            process.communicate.side_effect = fake_communicate
            mock_create_subprocess_exec.return_value = process

            result = await generate_speech_audio("Hello there", audio_dir=audio_dir)

            self.assertEqual(result["audio_url"], "/static/audio/speech-abc123.wav")
            self.assertEqual(result["audio_path"], wav_path)
            self.assertTrue(wav_path.exists())
            self.assertFalse(mp3_path.exists())

    @patch("app.services.tts_service.uuid4")
    @patch("app.services.tts_service.asyncio.create_subprocess_exec")
    @patch("app.services.tts_service.edge_tts.Communicate")
    async def test_generate_speech_audio_prunes_old_generated_files(
        self,
        mock_communicate,
        mock_create_subprocess_exec,
        mock_uuid4,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir)
            communicator = mock_communicate.return_value

            async def fake_save(path: str) -> None:
                Path(path).write_bytes(b"mp3")

            communicator.save = AsyncMock(side_effect=fake_save)
            mock_uuid4.return_value.hex = "new123"

            process = AsyncMock()
            process.returncode = 0

            async def fake_communicate():
                (audio_dir / "speech-new123.wav").write_bytes(b"wav")
                return (b"", b"")

            process.communicate.side_effect = fake_communicate
            mock_create_subprocess_exec.return_value = process

            created_files = []
            base_time = 1_700_000_000
            for index in range(21):
                old_path = audio_dir / f"speech-old-{index:02d}.wav"
                old_path.write_bytes(b"old")
                timestamp = base_time + index
                os.utime(old_path, (timestamp, timestamp))
                created_files.append(old_path)

            result = await generate_speech_audio("Hello there", audio_dir=audio_dir)

            generated_files = sorted(audio_dir.glob("speech-*"))
            self.assertEqual(len(generated_files), 20)
            wav_path = audio_dir / "speech-new123.wav"
            self.assertIn(wav_path, generated_files)
            self.assertNotIn(created_files[0], generated_files)
            self.assertTrue(wav_path.exists())
            self.assertFalse((audio_dir / "speech-new123.mp3").exists())
