# Avatar Speak Dynamic Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the backend so `/api/avatar/speak` generates a new WAV per request, runs Rhubarb against it, and returns the matching dynamic audio URL and mouth cues.

**Architecture:** Add a dedicated TTS service that owns unique filename generation and WAV creation under `static/audio`, make the Rhubarb service accept an explicit WAV path, and keep the FastAPI route as a thin orchestration layer. Verify behavior with route and service tests that mock external integrations.

**Tech Stack:** FastAPI, Python 3.12, `edge-tts`, `ffmpeg`, Rhubarb Lip Sync, `unittest`

---

### Task 1: Add failing route coverage for dynamic audio responses

**Files:**
- Create: `backend/tests/test_avatar_api.py`
- Test: `backend/tests/test_avatar_api.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class AvatarSpeakApiTests(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("app.main.run_rhubarb")
    @patch("app.main.generate_speech_audio")
    def test_avatar_speak_returns_generated_audio_url_and_matching_cues(
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

        response = self.client.post("/api/avatar/speak", json={"text": "Hello there"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "text": "Hello there",
                "audioUrl": "/static/audio/generated.wav",
                "mouthCues": [{"start": 0.0, "end": 0.4, "value": "A"}],
            },
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m unittest tests.test_avatar_api.AvatarSpeakApiTests.test_avatar_speak_returns_generated_audio_url_and_matching_cues -v`
Expected: FAIL because `generate_speech_audio` does not exist and the route still returns `/static/audio/test.wav`.

- [ ] **Step 3: Write minimal implementation**

```python
from app.services.tts_service import generate_speech_audio


@app.post("/api/avatar/speak")
async def avatar_speak(req: Request):
    body = await req.json()
    text = body.get("text", "hello there")

    audio_info = await generate_speech_audio(text)
    rhubarb_data = run_rhubarb(audio_info["audio_path"])

    return {
        "text": text,
        "audioUrl": audio_info["audio_url"],
        "mouthCues": rhubarb_data.get("mouthCues", []),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m unittest tests.test_avatar_api.AvatarSpeakApiTests.test_avatar_speak_returns_generated_audio_url_and_matching_cues -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_avatar_api.py backend/app/main.py
git commit -m "test: cover dynamic avatar speak response"
```

### Task 2: Add failing TTS service coverage for unique WAV generation

**Files:**
- Create: `backend/tests/test_tts_service.py`
- Create: `backend/app/services/tts_service.py`
- Test: `backend/tests/test_tts_service.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m unittest tests.test_tts_service.TtsServiceTests.test_generate_speech_audio_writes_unique_wav_and_returns_static_url -v`
Expected: FAIL because `tts_service.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
import asyncio
from pathlib import Path
from uuid import uuid4

import edge_tts


async def generate_speech_audio(text: str, audio_dir: Path | None = None) -> dict:
    target_dir = audio_dir or Path(__file__).resolve().parents[2] / "static" / "audio"
    target_dir.mkdir(parents=True, exist_ok=True)

    file_stem = f"speech-{uuid4().hex}"
    mp3_path = target_dir / f"{file_stem}.mp3"
    wav_path = target_dir / f"{file_stem}.wav"

    communicator = edge_tts.Communicate(text or "hello there")
    await communicator.save(str(mp3_path))

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(mp3_path),
        str(wav_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stderr.decode() or "ffmpeg conversion failed")

    mp3_path.unlink(missing_ok=True)
    return {"audio_path": wav_path, "audio_url": f"/static/audio/{wav_path.name}"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m unittest tests.test_tts_service.TtsServiceTests.test_generate_speech_audio_writes_unique_wav_and_returns_static_url -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_tts_service.py backend/app/services/tts_service.py
git commit -m "feat: add edge tts audio generation service"
```

### Task 3: Refactor Rhubarb service to accept explicit WAV paths

**Files:**
- Modify: `backend/app/services/rhubarb_service.py`
- Test: `backend/tests/test_avatar_api.py`

- [ ] **Step 1: Write the failing test**

```python
        mock_run_rhubarb.assert_called_once_with("/tmp/generated.wav")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m unittest tests.test_avatar_api.AvatarSpeakApiTests.test_avatar_speak_returns_generated_audio_url_and_matching_cues -v`
Expected: FAIL because `run_rhubarb()` is still called without a path.

- [ ] **Step 3: Write minimal implementation**

```python
def run_rhubarb(wav_path: Path | str) -> dict:
    audio_path = Path(wav_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"WAV not found: {audio_path}")

    cmd = [
        str(RHUBARB_BIN),
        str(audio_path),
        "--machineReadable",
        "--exportFormat",
        "json",
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m unittest tests.test_avatar_api.AvatarSpeakApiTests.test_avatar_speak_returns_generated_audio_url_and_matching_cues -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rhubarb_service.py backend/tests/test_avatar_api.py
git commit -m "refactor: run rhubarb against generated wav files"
```

### Task 4: Add runtime dependency and verify the backend flow

**Files:**
- Create: `backend/requirements.txt`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/tts_service.py`

- [ ] **Step 1: Write the dependency file**

```text
fastapi==0.136.0
uvicorn==0.44.0
httpx==0.28.1
edge-tts==6.1.18
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && .venv/bin/pip install -r requirements.txt`
Expected: `Successfully installed edge-tts ...`

- [ ] **Step 3: Run focused verification**

Run: `cd backend && .venv/bin/python -m unittest tests.test_avatar_api tests.test_tts_service -v`
Expected: PASS

- [ ] **Step 4: Run a manual route smoke test**

Run: `cd backend && .venv/bin/python - <<'PY'\nfrom fastapi.testclient import TestClient\nfrom app.main import app\nclient = TestClient(app)\nprint(client.post('/api/avatar/speak', json={'text': 'Sunny says hello'}).json())\nPY`
Expected: JSON containing a non-`test.wav` `audioUrl` and a `mouthCues` array.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/main.py backend/app/services/tts_service.py backend/app/services/rhubarb_service.py backend/tests
git commit -m "feat: generate dynamic avatar speech audio"
```
