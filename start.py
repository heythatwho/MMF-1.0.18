from pathlib import Path
import os
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parent
venv = ROOT / ".venv"
python = venv / "bin" / "python"
host = os.getenv("MMF_HOST", "0.0.0.0")
port = os.getenv("MMF_PORT", "8005")

if not python.exists():
    subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])

os.chdir(ROOT)
url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
print(f"Starting MMF v1.0.18 at {url} (bind {host})")
if os.getenv("MMF_OPEN_BROWSER", "false").lower() == "true":
    webbrowser.open(url)
subprocess.call([str(python), "-m", "uvicorn", "api.app:app", "--host", host, "--port", port])
