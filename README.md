# 🤖 AI Paper Assistant
Un assistente AI che raccoglie, analizza e riassume paper scientifici in modo automatico

# Descrizione
AI Paper Assistant è una web app full-stack che integra Machine Learning e Large Language Models per analizzare automaticamente paper scientifici in ambito AI / Computer Science.
L’app scarica paper da sorgenti come arXiv, ne estrae abstract e metadati, li indicizza in un database locale e permette di:
- cercare paper per parola chiave
- leggere i dettagli del paper
- fare domande o chiedere riassunti con un assistente AI (RAG pipeline)
- funzionare sia in locale che su Hugging Face Spaces

Il progetto è low-cost, open-source e completamente automatizzabile.


# Architettura
ai paper assistant

├── api/
│   └── main.py          # Backend FastAPI (API REST + RAG pipeline)
├── app/
│   └── streamlit_app.py # Frontend interattivo (Streamlit)
├── data/
│   ├── app.db           # Database SQLite (metadati paper)
│   └── pdfs/            # PDF opzionali (solo in locale)
├── scripts/
│   └── ingest_arxiv_api.py  # Script di ingest da arXiv
├── app.py               # Entry point per Hugging Face Spaces
├── requirements.txt     # Dipendenze Python
├── .env                 # Token Hugging Face (non pubblicare)
├── .gitignore
└── README.md


# Tecnologie utilizzate

| Componente       | Tecnologia                | Descrizione                     |
| ---------------- | ------------------------- | ------------------------------- |
| **Frontend**     | Streamlit                 | Interfaccia web interattiva     |
| **Backend**      | FastAPI                   | API REST e orchestrazione       |
| **LLM**          | Mistral-7B (Hugging Face) | Generazione e Q&A sui paper     |
| **Embeddings**   | Sentence-Transformers     | Indicizzazione vettoriale       |
| **Vector Store** | FAISS                     | Ricerca semantica locale        |
| **DB**           | SQLite                    | Storage metadati paper          |
| **Hosting**      | Hugging Face Spaces       | Deploy gratuito e condivisibile |


 # Come funziona

1. Ingestion
Uno script (scripts/ingest_arxiv_api.py) scarica i paper più recenti da arXiv nelle categorie:
cs.AI, cs.CL, cs.LG, cs.CV, cs.IR, cs.DS, ecc.

2. Indicizzazione
I testi vengono estratti, divisi in chunk, e convertiti in embedding con MiniLM-L6-v2.

3. RAG Pipeline
FastAPI gestisce la pipeline di retrieval → generation → risposta con citazioni.

4. Interfaccia utente
Streamlit consente di cercare, filtrare e interrogare l’assistente AI.


# Possibili estensioni future
- Ingestion automatica giornaliera (GitHub Actions)
- Analisi “Related Work” tra paper simili
- Notifiche email o RSS su nuovi paper
- Sistema utenti con preferiti e alert
- Dashboard con metriche di aggiornamento e qualità RAG
