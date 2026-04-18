import json
import subprocess
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]
RHUBARB_BIN = REPO_DIR / "tools" / "rhubarb" / "Rhubarb-Lip-Sync-1.14.0-Linux" / "rhubarb"
TEST_WAV = BACKEND_DIR / "static" / "audio" / "test.wav"


def run_rhubarb(wav_path: Path | str) -> dict:
    audio_path = Path(wav_path)

    if not RHUBARB_BIN.exists():
        raise FileNotFoundError(f"Rhubarb binary not found: {RHUBARB_BIN}")

    if not audio_path.exists():
        raise FileNotFoundError(f"WAV not found: {audio_path}")

    cmd = [
        str(RHUBARB_BIN),
        str(audio_path),
        "--machineReadable",
        "--exportFormat",
        "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
