from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

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
