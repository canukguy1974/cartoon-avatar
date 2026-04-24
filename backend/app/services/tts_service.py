import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

try:
    import edge_tts
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    edge_tts = SimpleNamespace(Communicate=None)


BACKEND_DIR = Path(__file__).resolve().parents[2]
AUDIO_DIR = BACKEND_DIR / "static" / "audio"
DEFAULT_TEXT = "hello there"
DEFAULT_VOICE = "en-US-AvaNeural"
MAX_GENERATED_AUDIO_FILES = 20


def prune_generated_audio_files(audio_dir: Path, keep: int = MAX_GENERATED_AUDIO_FILES) -> None:
    generated_files = [
        path
        for path in audio_dir.glob("speech-*")
        if path.is_file() and path.suffix in {".mp3", ".wav"}
    ]
    generated_files.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)

    for old_path in generated_files[keep:]:
        old_path.unlink(missing_ok=True)


async def generate_speech_audio(text: str, audio_dir: Path | None = None) -> dict:
    if edge_tts.Communicate is None:
        raise RuntimeError("edge-tts is not installed")

    target_dir = audio_dir or AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    normalized_text = (text or "").strip() or DEFAULT_TEXT
    file_stem = f"speech-{uuid4().hex}"
    mp3_path = target_dir / f"{file_stem}.mp3"
    wav_path = target_dir / f"{file_stem}.wav"

    communicator = edge_tts.Communicate(normalized_text, voice=DEFAULT_VOICE)

    generated_successfully = False
    try:
        await communicator.save(str(mp3_path))

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(mp3_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "24000",
            str(wav_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_text = stderr.decode().strip() or "ffmpeg conversion failed"
            raise RuntimeError(error_text)

        generated_successfully = True
        return {
            "audio_path": wav_path,
            "audio_url": f"/static/audio/{wav_path.name}",
        }
    finally:
        mp3_path.unlink(missing_ok=True)
        if generated_successfully:
            prune_generated_audio_files(target_dir)
