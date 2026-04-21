---
title: AI Paper Assistant
emoji: 📚
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

# 🤖 AI Paper Assistant

**A full-stack RAG application that fetches, indexes, and answers questions about AI/CS scientific papers**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Spaces-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co/spaces)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Overview

**AI Paper Assistant** is a full-stack web app that integrates Machine Learning and Large Language Models to automatically analyze scientific papers in AI and Computer Science.

It downloads papers from arXiv, chunks them, embeds every chunk with a Sentence-Transformer, and indexes the vectors in a local **FAISS** store. At query time, the same embedder turns your question into a vector, FAISS returns the top-k most similar chunks, and a Hugging Face LLM answers grounded in that context.

- 🔍 Semantic search over titles + abstracts (FAISS, cosine similarity)
- 📄 Read paper details and metadata
- 💬 Ask questions and get AI-generated answers via a real **RAG pipeline** (embed → retrieve → generate)
- 📎 Upload a PDF, get it chunked + indexed, then chat with it
- ☁️ Run locally or deploy on **Hugging Face Spaces** for free

> **Low-cost · Open-source · Production-ready**

---

## Architecture

```
ai-paper-assistant/
├── api/
│   ├── main.py               # FastAPI backend — REST API, embedding, FAISS, RAG
│   └── rag_utils.py          # Pure helpers (chunking) — dep-light, unit-tested
├── app/
│   └── streamlit_app.py      # Interactive Streamlit frontend
├── data/
│   ├── app.db                # SQLite (papers + chunks with embedding BLOBs)
│   └── faiss.index           # Persisted FAISS IndexIDMap (auto-created)
├── scripts/
│   ├── ingest_arxiv.py       # Lightweight arXiv ingestion (no PDFs)
│   └── ingest_arxiv_api.py   # Full ingestion with PDF download
├── tests/
│   └── test_chunking.py      # Unit tests (pytest)
├── evals/
│   └── retrieval_eval.py     # recall@k / MRR over the live FAISS index
├── app.py                    # Entry point for Hugging Face Spaces
├── Dockerfile
├── requirements.txt
└── .env.example
```

### RAG Pipeline

```
arXiv / PDF  ─►  chunk (900 chars, 150 overlap)  ─►  MiniLM-L6-v2 embed
                                                           │
                                                           ▼
                                                   FAISS (IndexFlatIP)
                                                           │
                User question ─► embed ─► top-k cosine ─► chunks
                                                           │
                                                           ▼
                                         Qwen2.5-7B (HF Inference) ─► Answer
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit | Interactive web UI |
| **Backend** | FastAPI | REST API & RAG orchestration |
| **LLM** | Qwen2.5-7B-Instruct (Hugging Face) | Grounded Q&A |
| **Embeddings** | Sentence-Transformers (MiniLM-L6-v2, 384-d) | Encode chunks & queries |
| **Vector store** | FAISS (`IndexIDMap` over `IndexFlatIP`) | Top-k cosine retrieval |
| **Database** | SQLite | Paper metadata + chunk text + embedding BLOBs |
| **Hosting** | Hugging Face Spaces (Docker) | Free cloud deployment |

---

## Getting Started

### Prerequisites

```bash
python >= 3.10
pip
```

### Installation

```bash
git clone https://github.com/Riccardi4le/ai-paper-assistant.git
cd ai-paper-assistant
pip install -r requirements.txt
cp .env.example .env   # add your HF token
python app.py
```

### Configuration

Create a `.env` file in the root directory:

```env
HUGGINGFACE_API_TOKEN=your_huggingface_token_here
```

### Run locally

```bash
python app.py
```

The app auto-ingests papers from arXiv on first run if the database is empty.

### Ingest papers manually

```bash
python scripts/ingest_arxiv_api.py
```

Categories indexed by default: `cs.AI`, `cs.CL`, `cs.LG`, `cs.CV`, `cs.IR`

### Run tests

```bash
pip install pytest
pytest tests/ -v
```

### Run retrieval eval

```bash
# Evaluates recall@1 / recall@k / MRR across three query styles
python -m evals.retrieval_eval --limit 50 --k 5
```

---

## Deploy on Hugging Face Spaces

1. Create a new Space (SDK: **Docker**, visibility: **Public**)
2. Add secret `HUGGINGFACE_API_TOKEN` in Space Settings
3. Push the repo — papers are ingested automatically on first boot

---

## How It Works

1. **Ingestion** — Pulls the latest papers from arXiv via the public API (or accepts a PDF upload)
2. **Chunk + embed** — Splits text into overlapping chunks (900 chars, 150 overlap) and encodes them with MiniLM-L6-v2
3. **Index** — Stores chunk text + embedding BLOB in SQLite and adds the vector to a persisted FAISS index (`data/faiss.index`)
4. **Retrieve** — Embeds the user question, runs cosine top-k via FAISS (global) or in-paper (scoped when `paper_id` is set)
5. **Generate** — The retrieved chunks are sent to Qwen2.5-7B-Instruct as grounded context for the final answer
6. **Backfill** — On API startup, any paper missing chunks is embedded automatically; `POST /admin/reindex` rebuilds FAISS from the SQLite source of truth

---

## Roadmap

- [x] Full PDF chunking + FAISS semantic search in the API
- [ ] Daily automated ingestion via GitHub Actions
- [ ] "Related Work" analysis across similar papers (k-NN over FAISS)
- [ ] Email/RSS notifications for new papers in chosen categories
- [ ] User system with favorites and alerts
- [x] Retrieval eval harness (recall@k, MRR) — see `evals/retrieval_eval.py`
- [ ] Answer-faithfulness eval (LLM-as-judge on grounded Q/A)

---

## Author

**Alessandro Riccardi** — Data Scientist & ML Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alessandro-riccardi-83b3b3257/)
[![GitHub](https://img.shields.io/badge/GitHub-Riccardi4le-181717?style=flat-square&logo=github)](https://github.com/Riccardi4le)
