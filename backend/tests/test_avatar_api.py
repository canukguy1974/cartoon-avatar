import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from app.main import app


class AvatarSpeakApiTests(IsolatedAsyncioTestCase):
    @patch("app.main.run_rhubarb")
    @patch("app.main.generate_speech_audio")
    async def test_avatar_speak_returns_generated_audio_url_and_matching_cues(
        self,
        mock_generate_speech_audio,
        mock_run_rhubarb,
    ) -> None:
        mock_generate_speech_audio.return_value = {
            "audio_path": "/tmp/generated.wav",
            "audio_url": "/static/audio/generated.wav",
        }
        mock_run_rhubarb.return_value = {
            "mouthCues": [{"start": 0.0, "end": 0.4, "value": "A"}],
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/avatar/speak", json={"text": "Hello there"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "text": "Hello there",
                "audioUrl": "/static/audio/generated.wav",
                "mouthCues": [{"start": 0.0, "end": 0.4, "value": "A"}],
            },
        )
        mock_generate_speech_audio.assert_called_once_with("Hello there")
        mock_run_rhubarb.assert_called_once_with("/tmp/generated.wav")


class AvatarStreamWebSocketTests(IsolatedAsyncioTestCase):
    @patch("app.main.run_rhubarb")
    @patch("app.main.generate_sentence_audio")
    async def test_websocket_stream_sends_thinking_then_chunks_then_done(
        self,
        mock_generate_sentence_audio,
        mock_run_rhubarb,
    ) -> None:
        fake_wav = b"RIFF" + b"\x00" * 40
        mock_generate_sentence_audio.return_value = {
            "wav_bytes": fake_wav,
            "duration_seconds": 0.5,
        }
        mock_run_rhubarb.return_value = {
            "mouthCues": [{"start": 0.0, "end": 0.3, "value": "B"}],
        }

        async with AsyncClient(
            transport=ASGIWebSocketTransport(app=app),
            base_url="http://testserver",
        ) as client:
            async with aconnect_ws(
                "http://testserver/api/avatar/stream",
                client,
            ) as ws:
                await ws.send_text(json.dumps({"text": "Hello."}))

                # First message: thinking
                msg1 = json.loads(await ws.receive_text())
                self.assertEqual(msg1["type"], "thinking")

                # Second message: audio_chunk
                msg2 = json.loads(await ws.receive_text())
                self.assertEqual(msg2["type"], "audio_chunk")
                self.assertEqual(msg2["chunkIndex"], 0)
                self.assertIn("audio", msg2)
                self.assertIn("mouthCues", msg2)
                self.assertEqual(msg2["sentence"], "Hello.")

                # Third message: done
                msg3 = json.loads(await ws.receive_text())
                self.assertEqual(msg3["type"], "done")

    @patch("app.main.run_rhubarb")
    @patch("app.main.generate_sentence_audio")
    async def test_websocket_stream_handles_multiple_sentences(
        self,
        mock_generate_sentence_audio,
        mock_run_rhubarb,
    ) -> None:
        fake_wav = b"RIFF" + b"\x00" * 40
        mock_generate_sentence_audio.return_value = {
            "wav_bytes": fake_wav,
            "duration_seconds": 0.5,
        }
        mock_run_rhubarb.return_value = {
            "mouthCues": [],
        }

        async with AsyncClient(
            transport=ASGIWebSocketTransport(app=app),
            base_url="http://testserver",
        ) as client:
            async with aconnect_ws(
                "http://testserver/api/avatar/stream",
                client,
            ) as ws:
                await ws.send_text(json.dumps({"text": "Hello there. How are you?"}))

                msg1 = json.loads(await ws.receive_text())
                self.assertEqual(msg1["type"], "thinking")

                # Two sentences = two chunks
                chunk1 = json.loads(await ws.receive_text())
                self.assertEqual(chunk1["type"], "audio_chunk")
                self.assertEqual(chunk1["chunkIndex"], 0)

                chunk2 = json.loads(await ws.receive_text())
                self.assertEqual(chunk2["type"], "audio_chunk")
                self.assertEqual(chunk2["chunkIndex"], 1)

                done = json.loads(await ws.receive_text())
                self.assertEqual(done["type"], "done")
