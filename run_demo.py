#!/usr/bin/env python3
"""One-command local launcher for the hackathon demo.

- Creates local venv (.venv) if needed
- Installs backend dependencies
- Starts backend API on http://127.0.0.1:8001
- Starts static frontend on http://127.0.0.1:8000/home.html
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQ_FILE = ROOT / "backend" / "requirements.txt"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        return
    if ENV_EXAMPLE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print("[setup] Created .env from .env.example. Fill in keys before full demo.")
    else:
        print("[warn] .env.example not found; continuing without env template.")


def ensure_venv() -> None:
    if VENV_DIR.exists() and venv_python().exists():
        return
    print("[setup] Creating virtual environment in .venv ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT)


def install_requirements() -> None:
    py = str(venv_python())
    print("[setup] Installing backend dependencies ...")
    subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT)
    subprocess.check_call([py, "-m", "pip", "install", "-r", str(REQ_FILE)], cwd=ROOT)


def launch() -> int:
    py = str(venv_python())

    backend_cmd = [
        py,
        "-m",
        "uvicorn",
        "main:app",
        "--app-dir",
        "backend",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
    ]

    frontend_cmd = [
        py,
        "-m",
        "http.server",
        "8000",
    ]

    print("[run] Starting backend on http://127.0.0.1:8001")
    backend_proc = subprocess.Popen(backend_cmd, cwd=ROOT)
    time.sleep(1.0)

    print("[run] Starting frontend on http://127.0.0.1:8000/home.html")
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=ROOT / "frontend" / "map_generation")

    print("\nDemo is running:")
    print("- Frontend: http://127.0.0.1:8000/home.html")
    print("- Backend:  http://127.0.0.1:8001/docs")
    print("\nPress Ctrl+C to stop both servers.\n")

    try:
        while True:
            if backend_proc.poll() is not None:
                print("[error] Backend exited unexpectedly.")
                return backend_proc.returncode or 1
            if frontend_proc.poll() is not None:
                print("[error] Frontend server exited unexpectedly.")
                return frontend_proc.returncode or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[stop] Shutting down servers...")
        for proc in (frontend_proc, backend_proc):
            if proc.poll() is None:
                proc.terminate()
        for proc in (frontend_proc, backend_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        return 0


def main() -> int:
    ensure_env_file()
    ensure_venv()
    install_requirements()
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
