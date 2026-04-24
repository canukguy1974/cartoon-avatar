# Sunny Local Cheat Sheet

Quick reference for starting the backend, frontend, and the few things this repo depends on.

## 1) Open a terminal in the repo

```bash
cd /home/canuk/projects/sunny-local
```

## 2) Activate the Python virtual environment

This repo already has a backend venv at `backend/.venv`.

```bash
source backend/.venv/bin/activate
```

If you ever need to recreate it:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

To leave the venv later:

```bash
deactivate
```

## 3) Start the backend

Run this from the repo root after activating the venv:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

What it gives you:

- API base: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Static files: `http://localhost:8000/static/...`

## 4) Start the frontend

The frontend is a plain static HTML file, so the simplest local server is Python's built-in one.

Open a second terminal:

```bash
cd /home/canuk/projects/sunny-local/frontend
python3 -m http.server 8001
```

Then open:

```text
http://localhost:8001/
```

Why port `8001`:

- The backend already uses `8000`
- The frontend page fetches API data from `http://localhost:8000`

## 5) What else you need installed

The backend code expects these to exist on your machine:

- `ffmpeg`
- the bundled Rhubarb binary at `tools/rhubarb/Rhubarb-Lip-Sync-1.14.0-Linux/rhubarb`

If those are missing, avatar generation will fail when you hit `/api/avatar/speak`.

## 6) Useful backend endpoints

- `GET /health` - simple up/down check
- `GET /api/avatar/test` - returns the test audio and mouth cues
- `POST /api/avatar/speak` - generates speech for submitted text

Example request:

```bash
curl -s http://localhost:8000/api/avatar/test
```

## 7) Common workflow

1. Start backend
2. Start frontend
3. Open `http://localhost:8001/`
4. Type text into the input box
5. Click `Play Test`

## 8) Run tests

From the repo root, with the venv active:

```bash
pytest backend/tests
```

## 9) Troubleshooting

- If the frontend loads but the button stays disabled, check that the backend is running on port `8000`.
- If speech generation fails, verify `ffmpeg` is installed and Rhubarb exists at the path above.
- If port `8000` or `8001` is already in use, stop the existing process or pick another free port and update the frontend URLs if needed.
