import base64
import json
import logging
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.services.llm_service import stream_chat_response
from app.services.rhubarb_service import TEST_WAV, run_rhubarb
from app.services.sentence_service import split_sentences
from app.services.streaming_tts_service import generate_sentence_audio
from app.services.tts_service import generate_speech_audio

# Load .env from the backend directory with override so changes stick on reload.
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=True)

logger = logging.getLogger(__name__)

app = FastAPI(title="Sunny Local Backend")

# ── Load pre-rendered FAQs ──
FAQ_CACHE = []
try:
    faq_path = BACKEND_DIR / "static" / "faqs" / "faqs.json"
    if faq_path.exists():
        FAQ_CACHE = json.loads(faq_path.read_text())
except Exception as e:
    logger.error("Failed to load FAQs: %s", e)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BACKEND_DIR / "static"), name="static")

# ── Sentence boundary pattern for incremental streaming ──
_SENTENCE_END = re.compile(r'[.!?…]\s*$')


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


@app.websocket("/api/avatar/stream")
async def avatar_stream(ws: WebSocket):
    """Stream LLM → sentence split → TTS → visemes over WebSocket.

    Client sends: ``{"text": "user question"}``
    Server sends back a sequence of JSON messages:
      1. ``{"type": "thinking"}`` — immediately
      2. ``{"type": "text_delta", "token": "..."}`` — LLM tokens as they arrive
      3. ``{"type": "audio_chunk", "audio": "<base64>", "mouthCues": [...], ...}``
      4. ``{"type": "done"}`` — after last chunk
    """
    await ws.accept()

    try:
        raw = await ws.receive_text()
        payload = json.loads(raw)
        user_text = (payload.get("text") or "").strip() or "hello there"

        # Immediately tell the client we're thinking.
        await ws.send_json({"type": "thinking"})

        user_lower = user_text.lower()
        matched_faq = None
        for faq in FAQ_CACHE:
            if any(kw in user_lower for kw in faq["keywords"]):
                matched_faq = faq
                break
                
        if matched_faq:
            logger.info("Matched pre-rendered FAQ: %s", matched_faq["text"])
            
            # Instantly stream text delta so it types out fast
            for token in matched_faq["text"].split(" "):
                await ws.send_json({"type": "text_delta", "token": token + " "})
                await asyncio.sleep(0.02)
                
            # Send the pre-rendered audio payload
            try:
                wav_path = BACKEND_DIR / matched_faq["audioUrl"].lstrip("/")
                audio_b64 = base64.b64encode(wav_path.read_bytes()).decode("ascii")
                await ws.send_json({
                    "type": "audio_chunk",
                    "audio": audio_b64,
                    "mouthCues": matched_faq["mouthCues"],
                    "chunkIndex": 0,
                    "duration": 0.0,
                    "sentence": matched_faq["text"],
                })
            except Exception as e:
                logger.error("Failed to send pre-rendered FAQ audio: %s", e)
                
            await ws.send_json({"type": "done", "fullResponse": matched_faq["text"]})
            return

        # ── Stream LLM response, accumulate into sentences ──
        buffer = ""
        chunk_index = 0
        full_response = ""

        async for token in stream_chat_response(user_text):
            full_response += token
            buffer += token

            # Send each token to the frontend for live text display.
            await ws.send_json({"type": "text_delta", "token": token})

            # Use the robust split_sentences to check if we have complete sentences
            sentences = split_sentences(buffer)
            
            # If we have more than 1 sentence, the first ones are definitely complete.
            # We keep the last one in the buffer as it might still be generating.
            if len(sentences) > 1:
                complete_sentences = sentences[:-1]
                buffer = sentences[-1] # keep the trailing incomplete sentence

                for sentence in complete_sentences:
                    if not sentence.strip():
                        continue

                    # Generate TTS + visemes for this sentence.
                    try:
                        audio_result = await generate_sentence_audio(sentence)
                        wav_bytes = audio_result["wav_bytes"]
                        duration = audio_result["duration_seconds"]

                        # Run Rhubarb for viseme cues.
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                            tmp.write(wav_bytes)
                            tmp_path = tmp.name

                        try:
                            rhubarb_data = run_rhubarb(tmp_path)
                            mouth_cues = rhubarb_data.get("mouthCues", [])
                        except Exception as rhubarb_err:
                            logger.warning("Rhubarb failed for chunk %d: %s", chunk_index, rhubarb_err)
                            mouth_cues = []
                        finally:
                            Path(tmp_path).unlink(missing_ok=True)

                        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

                        await ws.send_json({
                            "type": "audio_chunk",
                            "audio": audio_b64,
                            "mouthCues": mouth_cues,
                            "chunkIndex": chunk_index,
                            "duration": duration,
                            "sentence": sentence,
                        })
                        chunk_index += 1

                    except Exception as chunk_err:
                        logger.error("Failed to generate chunk %d: %s", chunk_index, chunk_err)
                        await ws.send_json({
                            "type": "error",
                            "message": f"Chunk {chunk_index} failed: {chunk_err}",
                            "chunkIndex": chunk_index,
                        })

        # ── Flush any remaining text in the buffer ──
        remaining = buffer.strip()
        if remaining:
            try:
                audio_result = await generate_sentence_audio(remaining)
                wav_bytes = audio_result["wav_bytes"]
                duration = audio_result["duration_seconds"]

                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(wav_bytes)
                    tmp_path = tmp.name

                try:
                    rhubarb_data = run_rhubarb(tmp_path)
                    mouth_cues = rhubarb_data.get("mouthCues", [])
                except Exception as rhubarb_err:
                    logger.warning("Rhubarb flush failed: %s", rhubarb_err)
                    mouth_cues = []
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

                audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

                await ws.send_json({
                    "type": "audio_chunk",
                    "audio": audio_b64,
                    "mouthCues": mouth_cues,
                    "chunkIndex": chunk_index,
                    "duration": duration,
                    "sentence": remaining,
                })
            except Exception as flush_err:
                logger.error("Flush chunk failed: %s", flush_err)

        await ws.send_json({"type": "done", "fullResponse": full_response})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
