# Meridian

AI-powered city digital twin platform with:
- map-based intervention editing (`frontend/map_generation`)
- simulation API (`backend/main.py`)
- scenario compare, policy bundles, and PDF export

## Fastest way to run (recommended)

### 1) Prerequisites
- Python 3.10+
- Internet access (Mapbox/Open-Meteo/FEMA/TomTom/Groq APIs)

### 2) Configure environment
From project root:

```bash
cp .env.example .env
```

Set at least:
- `GROQ_API_KEY` for natural-language parser
- `TOMTOM_KEY` for traffic integration

### 3) Start everything with one command
From project root:

```bash
python3 run_demo.py
```

Then open:
- `http://127.0.0.1:8000/home.html`

The script will:
- create `.venv` if needed
- install backend dependencies
- run backend on `127.0.0.1:8001`
- run frontend static server on `127.0.0.1:8000`

Press `Ctrl+C` to stop both.

## Manual run (if you prefer separate terminals)

### Terminal A (backend)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```

### Terminal B (frontend)
```bash
cd frontend/map_generation
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000/home.html`.

## Notes for sharing with judges/teammates
- Keep `.env` out of git.
- Share `.env.example` plus setup steps.
- The frontend map UI is in `frontend/map_generation/home.html` and `index.html`.
