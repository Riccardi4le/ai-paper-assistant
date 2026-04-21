import os
import sys
import sqlite3
import subprocess
import time
import requests

DB_PATH = "data/app.db"


def db_is_empty():
    if not os.path.exists(DB_PATH):
        return True
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True


def wait_for_api(url, retries=15, delay=2):
    for _ in range(retries):
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


if db_is_empty():
    print("📥 Database vuoto — eseguo ingest da arXiv...")
    subprocess.run([sys.executable, "scripts/ingest_arxiv.py"], check=False)

api_proc = subprocess.Popen([
    "uvicorn", "api.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
])

print("⏳ Attendo avvio FastAPI...")
if wait_for_api("http://127.0.0.1:8000/"):
    print("✅ FastAPI pronto")
else:
    print("⚠️ FastAPI non risponde, continuo comunque...")

subprocess.call([
    "streamlit", "run", "app/streamlit_app.py",
    "--server.port=7860",
    "--server.address=0.0.0.0",
    "--server.enableXsrfProtection=false",
    "--server.enableCORS=false",
])
