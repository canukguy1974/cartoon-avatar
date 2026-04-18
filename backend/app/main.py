from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.services.rhubarb_service import TEST_WAV, run_rhubarb
from app.services.tts_service import generate_speech_audio

BACKEND_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title="Sunny Local Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BACKEND_DIR / "static"), name="static")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/avatar/test")
def avatar_test():
    try:
        rhubarb_data = run_rhubarb(TEST_WAV)
        return {
            "text": "How can I assist you today?",
            "audioUrl": "/static/audio/test.wav",
            "mouthCues": rhubarb_data.get("mouthCues", []),
            "metadata": rhubarb_data.get("metadata", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/avatar/speak")
async def avatar_speak(req: Request):
    body = await req.json()
    text = (body.get("text") or "").strip() or "hello there"
    audio_info = await generate_speech_audio(text)
    rhubarb_data = run_rhubarb(audio_info["audio_path"])

    return {
        "text": text,
        "audioUrl": audio_info["audio_url"],
        "mouthCues": rhubarb_data.get("mouthCues", []),
    }
