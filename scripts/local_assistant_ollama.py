import os
import sqlite3
import faiss
import numpy as np
import subprocess
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader

DB_PATH = "data/app.db"
PDF_DIR = "data/pdfs"

# Modello embeddings
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def load_pdf_text(pdf_path):
    """Estrae testo da un PDF"""
    text = ""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        if page.extract_text():
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
    """Crea un indice FAISS"""
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def search(query, chunks, index, top_k=3):
    """Cerca chunk più simili"""
    q_emb = embedder.encode([query], convert_to_numpy=True)
    D, I = index.search(q_emb, top_k)
    results = [chunks[i] for i in I[0]]
    return results


def ask_llm(question, context, model="granite3.3:8b"):
    """Chiede a Ollama (Granite) di rispondere usando i chunk come contesto"""
    prompt = f"""
    Rispondi alla domanda usando SOLO il seguente CONTENUTO:

    {context}

    Domanda: {question}

    Rispondi in italiano, massimo 200 parole.
    Se l'informazione non è nel contenuto, scrivi: "non presente nel paper".
    """

    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        capture_output=True
    )

    if result.stderr:
        print("⚠️ ERRORE OLLAMA:", result.stderr.decode("utf-8"))

    return result.stdout.decode("utf-8")


def choose_paper():
    """Permette all'utente di scegliere una categoria e un paper"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1️⃣ Mostra categorie
    cats = cur.execute("SELECT DISTINCT category FROM papers").fetchall()
    cats = [c[0] for c in cats]
    print("\n📂 Categorie disponibili:")
    for i, c in enumerate(cats, 1):
        print(f"{i}. {c}")

    cat_choice = input("\n👉 Scegli una categoria (numero): ")
    try:
        cat_choice = int(cat_choice) - 1
        category = cats[cat_choice]
    except:
        print("⚠️ Scelta non valida")
        exit()

    # 2️⃣ Mostra paper della categoria
    rows = cur.execute(
        "SELECT id, title, pdf_path FROM papers WHERE category=? AND pdf_path IS NOT NULL ORDER BY published DESC LIMIT 10",
        (category,)
    ).fetchall()

    if not rows:
        print("⚠️ Nessun PDF disponibile per questa categoria")
        exit()

    print(f"\n📑 Paper in {category}:")
    for i, r in enumerate(rows, 1):
        print(f"{i}. {r[1]}")

    paper_choice = input("\n👉 Scegli un paper (numero): ")
    try:
        paper_choice = int(paper_choice) - 1
        paper = rows[paper_choice]
    except:
        print("⚠️ Scelta non valida")
        exit()

    conn.close()
    return paper[2], paper[1]  # pdf_path, title


if __name__ == "__main__":
    # Scegli categoria e paper
    pdf_path, title = choose_paper()
    print(f"\n✅ Hai scelto: {title}")
    print(f"📂 Carico PDF: {pdf_path}")

    # Estrazione testo
    text = load_pdf_text(pdf_path)
    print(f"📄 Estratti {len(text)} caratteri")

    # Chunking
    chunks = chunk_text(text)
    print(f"✂️ Creati {len(chunks)} chunk")

    # Costruzione indice
    index = build_faiss_index(chunks)

    # Loop interattivo
    while True:
        query = input("\n❓ Domanda (oppure 'exit'): ")
        if query.lower() == "exit":
            break

        results = search(query, chunks, index, top_k=3)
        context = "\n\n".join(results)
        answer = ask_llm(query, context)
        print("\n🤖 Assistente IA:")
        print(answer)
