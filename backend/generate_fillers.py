import asyncio
import json
from pathlib import Path

from app.services.tts_service import generate_speech_audio
from app.services.rhubarb_service import run_rhubarb

FILLERS = [
    {"id": "filler1", "text": "Hmm, let me check that for you..."},
    {"id": "filler2", "text": "Just one second please..."},
    {"id": "filler3", "text": "I'll look into that right now."},
]

BACKEND_DIR = Path(__file__).resolve().parent
FILLERS_DIR = BACKEND_DIR / "static" / "fillers"

async def main():
    FILLERS_DIR.mkdir(parents=True, exist_ok=True)
    
    metadata = []

    for filler in FILLERS:
        print(f"Generating for: {filler['text']}")
        audio_info = await generate_speech_audio(filler['text'])
        wav_path = Path(audio_info["audio_path"])
        
        rhubarb_data = run_rhubarb(wav_path)
        
        # Save WAV to static/fillers
        dest_wav = FILLERS_DIR / f"{filler['id']}.wav"
        dest_wav.write_bytes(wav_path.read_bytes())
        
        # We also want the duration. We can estimate it or just leave it for the frontend
        
        meta = {
            "id": filler["id"],
            "text": filler["text"],
            "audioUrl": f"/static/fillers/{filler['id']}.wav",
            "mouthCues": rhubarb_data.get("mouthCues", [])
        }
        metadata.append(meta)
        
        # Clean up the generated temp
        wav_path.unlink(missing_ok=True)

    metadata_path = FILLERS_DIR / "fillers.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(f"Fillers generated at {metadata_path}")

if __name__ == "__main__":
    asyncio.run(main())
