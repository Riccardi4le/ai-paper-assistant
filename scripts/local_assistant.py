import os
import sqlite3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

# Percorso DB e PDF
DB_PATH = "data/app.db"
PDF_DIR = "data/pdfs"

# Modello embeddings (piccolo e veloce)
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def load_pdf_text(pdf_path):
    """Estrae il testo da un PDF"""
    text = ""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def chunk_text(text, chunk_size=800, overlap=100):
    """Divide il testo in chunk sovrapposti"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def build_faiss_index(chunks):
    """Crea un indice FAISS dai chunk"""
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index, embeddings


def search(query, chunks, index, top_k=3):
    """Cerca i chunk più simili a una query"""
    q_emb = embedder.encode([query], convert_to_numpy=True)
    D, I = index.search(q_emb, top_k)
    results = [chunks[i] for i in I[0]]
    return results


if __name__ == "__main__":
    # Prendiamo un PDF dal DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    row = cur.execute("SELECT pdf_path FROM papers WHERE pdf_path IS NOT NULL LIMIT 1").fetchone()
    conn.close()

    if not row:
        print("⚠️ Nessun PDF trovato. Esegui prima ingest_arxiv_api.py con download PDF.")
        exit()

    pdf_path = row[0]
    print(f"📂 Carico PDF: {pdf_path}")

    # Estrai testo
    text = load_pdf_text(pdf_path)
    print(f"📄 Testo estratto: {len(text)} caratteri")

    # Chunking
    chunks = chunk_text(text)
    print(f"✂️ Creati {len(chunks)} chunk")

    # Costruisci indice
    index, _ = build_faiss_index(chunks)

    # Query loop
    while True:
        query = input("\n❓ Domanda (oppure 'exit'): ")
        if query.lower() == "exit":
            break
        results = search(query, chunks, index, top_k=3)
        print("\n📌 Risposta basata sui chunk:")
        for r in results:
            print("----")
            print(r.strip()[:400], "...")
