from pathlib import Path
from unittest import TestCase


class FrontendAvatarMarkupTests(TestCase):
    def test_frontend_uses_overlay_renderer_and_explicit_viseme_map(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn('id="baseHead"', html)
        self.assertIn('id="mouthOverlay"', html)
        self.assertIn("const visemeMap = {", html)
        self.assertIn('A: "./mouths/X.png"', html)
        self.assertIn("preloadImages()", html)

    def test_frontend_has_websocket_streaming(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn("WebSocket", html)
        self.assertIn("/api/avatar/stream", html)
        self.assertIn("audio_chunk", html)

    def test_frontend_has_idle_animations(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn("idle", html)
        self.assertIn("breathing", html.lower().replace("breath", "breath"))
        self.assertIn("breathScale", html)
        self.assertIn("swayX", html)
        self.assertIn("isBlinking", html)

    def test_frontend_has_fallback_mouth_animation(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn("FALLBACK_VISEMES", html)
        self.assertIn("startFallbackMouth", html)
        self.assertIn("stopFallbackMouth", html)

    def test_frontend_has_audio_context(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn("AudioContext", html)
        self.assertIn("decodeAudioData", html)
        self.assertIn("enqueueChunk", html)

    def test_frontend_has_state_management(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn("setState", html)
        self.assertIn('"idle"', html)
        self.assertIn('"thinking"', html)
        self.assertIn('"speaking"', html)
