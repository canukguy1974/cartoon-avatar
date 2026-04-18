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
