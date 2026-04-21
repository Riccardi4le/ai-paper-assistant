# AI Paper Assistant

App per esplorare, riassumere e interrogare paper scientifici da arXiv con un modello AI open-source.

## Stack

| Componente | Tecnologia |
|------------|------------|
| Frontend   | Streamlit  |
| Backend    | FastAPI    |
| LLM        | Hugging Face Inference API (Mistral-7B) |
| Hosting    | Hugging Face Spaces |
| Database   | SQLite     |

## Deploy su Hugging Face Spaces

1. Crea uno Space di tipo **Streamlit** (o **Docker** per maggiore controllo)
2. Imposta il secret: `HUGGINGFACE_API_TOKEN` nelle impostazioni dello Space
3. Fai push del repo — al primo avvio viene eseguito automaticamente l'ingest da arXiv

## Avvio locale

```bash
pip install -r requirements.txt
cp .env.example .env   # inserisci il tuo token HF
python app.py
```

## Struttura

```
api/          FastAPI backend (RAG + ricerca paper)
app/          Streamlit frontend
scripts/      Script di ingest da arXiv
data/         SQLite database
```
