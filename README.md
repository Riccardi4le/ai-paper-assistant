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

It downloads papers from arXiv, extracts abstracts and metadata, indexes them in a local vector database, and lets you:

- 🔍 Search papers by keyword
- 📄 Read paper details and metadata
- 💬 Ask questions and get AI-generated summaries via a **RAG pipeline**
- ☁️ Run locally or deploy on **Hugging Face Spaces** for free

> **Low-cost · Open-source · Production-ready**

---

## Architecture

```
ai-paper-assistant/
├── api/
│   └── main.py               # FastAPI backend — REST API + RAG pipeline
├── app/
│   └── streamlit_app.py      # Interactive Streamlit frontend
├── data/
│   ├── app.db                # SQLite database (paper metadata)
│   └── pdfs/                 # Optional local PDFs
├── scripts/
│   └── ingest_arxiv_api.py   # arXiv ingestion script
├── app.py                    # Entry point for Hugging Face Spaces
├── requirements.txt
├── .env                      # Hugging Face token
└── README.md
```

### RAG Pipeline

```
arXiv API → Ingestion → Chunking → Embeddings (MiniLM-L6-v2) → FAISS Index
                                                                      ↓
User Query → Retrieval → Mistral-7B (HuggingFace) → Answer + Citations
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit | Interactive web UI |
| **Backend** | FastAPI | REST API & RAG orchestration |
| **LLM** | Mistral-7B (Hugging Face) | Q&A and summarization |
| **Embeddings** | Sentence-Transformers (MiniLM-L6-v2) | Vector indexing |
| **Vector Store** | FAISS | Semantic search |
| **Database** | SQLite | Paper metadata storage |
| **Hosting** | Hugging Face Spaces | Free cloud deployment |

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
```

### Configuration

Create a `.env` file in the root directory:

```env
HF_TOKEN=your_huggingface_token_here
```

### Run locally

```bash
# Start the FastAPI backend
uvicorn api.main:app --reload

# In a second terminal, start the Streamlit frontend
streamlit run app/streamlit_app.py
```

### Ingest papers from arXiv

```bash
python scripts/ingest_arxiv_api.py
```

Categories indexed by default: `cs.AI`, `cs.CL`, `cs.LG`, `cs.CV`, `cs.IR`, `cs.DS`

---

## How It Works

1. **Ingestion** — The script pulls the latest papers from arXiv via the public API
2. **Indexing** — Text is chunked and converted to embeddings using `MiniLM-L6-v2`
3. **Retrieval** — On each query, FAISS retrieves the most semantically relevant chunks
4. **Generation** — Mistral-7B generates an answer grounded in the retrieved context, with citations

---

## Roadmap

- [ ] Daily automated ingestion via GitHub Actions
- [ ] "Related Work" analysis across similar papers
- [ ] Email/RSS notifications for new papers in chosen categories
- [ ] User system with favorites and alerts
- [ ] RAG quality metrics dashboard

---

## Author

**Alessandro Riccardi** — Data Scientist & ML Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alessandro-riccardi-83b3b3257/)
[![GitHub](https://img.shields.io/badge/GitHub-Riccardi4le-181717?style=flat-square&logo=github)](https://github.com/Riccardi4le)
