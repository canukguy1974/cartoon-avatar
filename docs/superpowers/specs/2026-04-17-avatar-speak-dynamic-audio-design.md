# Avatar Speak Dynamic Audio Design

## Goal

Refactor the Sunny backend so `POST /api/avatar/speak` generates a fresh WAV file for each submitted text, runs Rhubarb against that specific WAV, and returns the original text, the generated `audioUrl`, and the matching `mouthCues`.

## Current State

- `backend/app/main.py` always returns `/static/audio/test.wav` from `POST /api/avatar/speak`.
- `backend/app/services/rhubarb_service.py` always runs Rhubarb against the fixed `backend/static/audio/test.wav`.
- The frontend already accepts `data.audioUrl` and uses it to set the `<audio>` source, so no animation flow changes are required.

## Design

### TTS service

Add `backend/app/services/tts_service.py` with one focused responsibility: turn submitted text into a unique WAV file saved under `backend/static/audio/`.

Responsibilities:

- Ensure the target audio directory exists.
- Generate a collision-resistant basename for each request.
- Synthesize speech from text with `edge-tts`.
- Convert the generated audio into a final WAV file that Rhubarb can consume.
- Return both the absolute WAV path and the public `/static/audio/<filename>.wav` URL.

The service should remove any temporary intermediate file after conversion succeeds.

### Rhubarb service

Refactor `run_rhubarb()` to accept a WAV path parameter instead of reading a hard-coded file. The function should validate both the Rhubarb binary path and the provided WAV path, then return the parsed JSON output from Rhubarb unchanged.

### API route

Update `POST /api/avatar/speak` to:

1. Read the submitted text.
2. Call the TTS service to create a new WAV file.
3. Call Rhubarb on that generated WAV.
4. Return:
   - `text`
   - `audioUrl`
   - `mouthCues`

`GET /api/avatar/test` can continue to use the sample WAV for smoke-testing, but it should call the refactored `run_rhubarb(test_wav_path)`.

## File Boundaries

- `backend/app/main.py`: HTTP orchestration only.
- `backend/app/services/tts_service.py`: TTS generation, file naming, WAV persistence.
- `backend/app/services/rhubarb_service.py`: Rhubarb invocation for a supplied WAV path.
- `backend/tests/test_avatar_api.py`: route-level tests with service mocks.
- `backend/tests/test_tts_service.py`: service-level tests for file naming and returned URL/path contract.

## Error Handling

- Empty or missing text should fall back to the existing default phrase.
- Missing Rhubarb binary, failed synthesis, failed conversion, or missing generated WAV should surface as route failures rather than silently falling back to `test.wav`.
- The backend must never return `test.wav` from `POST /api/avatar/speak` after this refactor.

## Testing

- Add a failing route test proving `/api/avatar/speak` no longer returns the fixed `test.wav`.
- Add a failing service test proving the TTS service returns a unique WAV URL/path pair and persists the WAV file under `static/audio/`.
- Mock `edge-tts` and Rhubarb in tests so the suite is deterministic and does not require live network speech synthesis.

## Scope

This refactor is intentionally limited to backend service boundaries and the route payload. The frontend should remain unchanged except for continuing to consume the returned dynamic `audioUrl`.
