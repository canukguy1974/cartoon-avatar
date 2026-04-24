import asyncio
import json
from pathlib import Path

from app.services.tts_service import generate_speech_audio
from app.services.rhubarb_service import run_rhubarb

FAQS = [
    {
        "keywords": ["website", "online", "url", "web address"],
        "text": "You can find all our information online at tangerine.ca.",
    },
    {
        "keywords": ["account", "open", "register", "sign up"],
        "text": "You can open a new account in minutes by downloading the Tangerine app or visiting our website.",
    },
    {
        "keywords": ["balance", "check my account", "information", "details"],
        "text": "To view your account details and balance, just log into the Tangerine app.",
    },
    {
        "keywords": ["hello", "hi", "hey", "how are you"],
        "text": "Hi there! I'm doing great. How can I help you with your banking today?",
    }
]

BACKEND_DIR = Path(__file__).resolve().parent
FAQ_DIR = BACKEND_DIR / "static" / "faqs"

async def main():
    FAQ_DIR.mkdir(parents=True, exist_ok=True)
    
    metadata = []

    for i, faq in enumerate(FAQS):
        print(f"Generating FAQ {i}: {faq['text']}")
        audio_info = await generate_speech_audio(faq['text'])
        wav_path = Path(audio_info["audio_path"])
        
        rhubarb_data = run_rhubarb(wav_path)
        
        dest_wav = FAQ_DIR / f"faq_{i}.wav"
        dest_wav.write_bytes(wav_path.read_bytes())
        
        meta = {
            "id": f"faq_{i}",
            "keywords": faq["keywords"],
            "text": faq["text"],
            "audioUrl": f"/static/faqs/faq_{i}.wav",
            "mouthCues": rhubarb_data.get("mouthCues", [])
        }
        metadata.append(meta)
        
        wav_path.unlink(missing_ok=True)

    metadata_path = FAQ_DIR / "faqs.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(f"FAQs generated at {metadata_path}")

if __name__ == "__main__":
    asyncio.run(main())
