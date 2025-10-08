import os
import subprocess

# Avvia FastAPI in background (porta 8000)
os.environ["UVICORN_PORT"] = "8000"
subprocess.Popen(["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"])

# Avvia Streamlit come frontend principale (porta standard 7860 su HF)
subprocess.call(["streamlit", "run", "app/streamlit_app.py", "--server.port=7860"])
