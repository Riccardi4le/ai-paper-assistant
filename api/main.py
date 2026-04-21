import os
import io
import sqlite3
import xml.etree.ElementTree as ET
import requests as http_requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from pypdf import PdfReader

# ============================================================
# CONFIGURAZIONE
# ============================================================
load_dotenv()
app = FastAPI()
DB_PATH = "data/app.db"
INGEST_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR"]
INGEST_PER_CATEGORY = 10

# Modello embeddings (usato per ricerca semantica)
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Client Hugging Face (legge HUGGINGFACE_API_TOKEN o HF_TOKEN)
HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_TOKEN")
client = InferenceClient(model="Qwen/Qwen2.5-7B-Instruct", token=HF_TOKEN)

# ============================================================
# MODELLI DATI
# ============================================================
class QuestionRequest(BaseModel):
    question: str
    paper_id: int | None = None

# ============================================================
# FUNZIONI DATABASE
# ============================================================
def get_papers(q: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sql = "SELECT id, title, summary, link, published, category FROM papers"
    params = []
    if q:
        sql += " WHERE title LIKE ? OR summary LIKE ?"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY published DESC LIMIT 20"
    rows = cur.execute(sql, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "title": r[1],
            "abstract": r[2],
            "link": r[3],
            "published": r[4],
            "category": r[5],
        })
    return results


def run_ingest() -> int:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, summary TEXT, link TEXT UNIQUE,
            published TEXT, category TEXT, authors TEXT, pdf_path TEXT
        )
    """)
    new_count = 0
    for cat in INGEST_CATEGORIES:
        url = (
            f"http://export.arxiv.org/api/query?search_query=cat:{cat}"
            f"&start=0&max_results={INGEST_PER_CATEGORY}"
            f"&sortBy=submittedDate&sortOrder=descending"
        )
        res = http_requests.get(url, timeout=15)
        root = ET.fromstring(res.text)
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip()
            summary = entry.find("atom:summary", ns).text.strip()
            link = entry.find("atom:id", ns).text.strip()
            published = entry.find("atom:published", ns).text.strip()
            authors = ", ".join(
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
            )
            cur.execute(
                "INSERT OR IGNORE INTO papers (title, summary, link, published, category, authors) VALUES (?,?,?,?,?,?)",
                (title, summary, link, published, cat, authors),
            )
            new_count += cur.rowcount
    conn.commit()
    conn.close()
    return new_count


def get_context(paper_id: int | None = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if paper_id:
        rows = cur.execute("SELECT summary FROM papers WHERE id = ?", (paper_id,)).fetchall()
    else:
        rows = cur.execute("SELECT summary FROM papers LIMIT 10").fetchall()
    conn.close()
    return "\n\n".join([r[0] for r in rows if r[0]])

# ============================================================
# FUNZIONE PRINCIPALE AI 
# ============================================================
def ask_llm(question: str, context: str):
    messages = [
        {
            "role": "system",
            "content": (
                "Sei un assistente accademico. Rispondi in italiano chiaro e professionale "
                "basandoti solo sul contenuto fornito. "
                "Se l'informazione non e' presente scrivi: 'Non presente nel paper'."
            ),
        },
        {
            "role": "user",
            "content": f"Contenuto del paper:\n{context[:2000]}\n\nDomanda: {question}",
        },
    ]
    try:
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=messages,
            max_tokens=400,
            temperature=0.4,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERRORE HF: {type(e).__name__}: {e}")
        return f"Errore: {type(e).__name__} — {str(e)[:200]}"

# ============================================================
# ENDPOINTS API
# ============================================================
@app.get("/")
def root():
    return {"message": "API attiva  - usa /papers/search o /rag/answer"}

@app.get("/papers/search")
def search_papers(q: str = ""):
    return get_papers(q=q)

@app.post("/rag/answer")
def rag_answer(req: QuestionRequest):
    context = get_context(req.paper_id)
    answer = ask_llm(req.question, context)
    return {"answer": answer}

@app.post("/papers/ingest")
def ingest_papers():
    try:
        new_count = run_ingest()
        return {"status": "ok", "new_papers": new_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/papers/upload")
async def upload_paper(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo file PDF sono accettati.")
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()
        if not text:
            raise HTTPException(status_code=422, detail="Impossibile estrarre testo dal PDF.")
        title = file.filename.replace(".pdf", "")
        summary = text[:4000]
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, summary TEXT, link TEXT UNIQUE,
                published TEXT, category TEXT, authors TEXT, pdf_path TEXT
            )
        """)
        cur.execute(
            "INSERT INTO papers (title, summary, link, published, category, authors) VALUES (?,?,?,?,?,?)",
            (title, summary, f"upload://{file.filename}", "uploaded", "upload", ""),
        )
        paper_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"status": "ok", "paper_id": paper_id, "title": title, "pages": len(reader.pages)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon"}
