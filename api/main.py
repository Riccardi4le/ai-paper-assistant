import os
import io
import sqlite3
import threading
import xml.etree.ElementTree as ET

import numpy as np
import faiss
import requests as http_requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv
from pypdf import PdfReader

from api.rag_utils import chunk_text as _chunk_text, CHUNK_SIZE, CHUNK_OVERLAP

# ============================================================
# CONFIGURAZIONE
# ============================================================
load_dotenv()
app = FastAPI()

DB_PATH = os.getenv("DB_PATH", "data/app.db")
FAISS_PATH = os.getenv("FAISS_PATH", "data/faiss.index")
INGEST_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR"]
INGEST_PER_CATEGORY = 10

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMB_DIM = 384
TOP_K_CONTEXT = 5
TOP_K_SEARCH = 60

MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_CHUNKS_PER_UPLOAD = 600

os.makedirs("data", exist_ok=True)

# Embedder: usato per encodare query, abstract e chunk di PDF
embedder = SentenceTransformer(EMB_MODEL)


def _new_index() -> faiss.Index:
    # Inner product su vettori L2-normalizzati == cosine similarity
    return faiss.IndexIDMap(faiss.IndexFlatIP(EMB_DIM))


# FAISS non e' thread-safe per add/search concorrenti: FastAPI esegue gli
# endpoint sync in un threadpool, quindi ogni accesso all'indice passa da qui.
_index_lock = threading.Lock()


if os.path.exists(FAISS_PATH):
    try:
        faiss_index = faiss.read_index(FAISS_PATH)
    except Exception as e:
        print(f"WARN: impossibile leggere {FAISS_PATH} ({e}), ricreo indice vuoto")
        faiss_index = _new_index()
else:
    faiss_index = _new_index()

# Client Groq (free tier) — legge GROQ_API_KEY
LLM_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
client = Groq(max_retries=6) if os.getenv("GROQ_API_KEY") else None

# ============================================================
# MODELLI DATI
# ============================================================
class QuestionRequest(BaseModel):
    question: str
    paper_id: int | None = None

# ============================================================
# DATABASE
# ============================================================
def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _init_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, summary TEXT, link TEXT UNIQUE,
            published TEXT, category TEXT, authors TEXT, pdf_path TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER NOT NULL,
            chunk_idx INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_paper ON chunks(paper_id)")
    conn.commit()


_conn_init = _connect()
try:
    _init_schema(_conn_init)
finally:
    _conn_init.close()

# ============================================================
# EMBEDDING / CHUNKING
# ============================================================
def _embed(texts: list[str]) -> np.ndarray:
    vecs = embedder.encode(
        texts, normalize_embeddings=True, show_progress_bar=False
    )
    return np.asarray(vecs, dtype="float32")


def _persist_index() -> None:
    try:
        faiss.write_index(faiss_index, FAISS_PATH)
    except Exception as e:
        print(f"WARN: write_index fallita: {e}")


def _add_chunks_for_paper(
    conn: sqlite3.Connection, paper_id: int, texts: list[str], persist: bool = True
) -> int:
    """Embedda i testi, li salva in SQLite e li aggiunge a FAISS.

    Con `persist=False` l'indice non viene riscritto su disco: i chiamanti
    batch (ingest, backfill) persistono una sola volta a fine giro.
    """
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return 0
    vecs = _embed(texts)
    cur = conn.cursor()
    chunk_ids: list[int] = []
    for i, (text, vec) in enumerate(zip(texts, vecs)):
        cur.execute(
            "INSERT INTO chunks (paper_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
            (paper_id, i, text, vec.tobytes()),
        )
        chunk_ids.append(cur.lastrowid)
    conn.commit()
    ids_arr = np.asarray(chunk_ids, dtype="int64")
    with _index_lock:
        faiss_index.add_with_ids(vecs, ids_arr)
        if persist:
            _persist_index()
    return len(texts)


def _backfill_missing_chunks() -> int:
    """Calcola chunks+embedding per i paper che non ne hanno ancora."""
    conn = _connect()
    try:
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT p.id, p.title, p.summary FROM papers p
            LEFT JOIN chunks c ON c.paper_id = p.id
            WHERE c.id IS NULL
        """).fetchall()
        count = 0
        for pid, title, summary in rows:
            text = ((title or "") + "\n\n" + (summary or "")).strip()
            pieces = _chunk_text(text)
            if pieces and _add_chunks_for_paper(conn, pid, pieces, persist=False):
                count += 1
        if count:
            with _index_lock:
                _persist_index()
        return count
    finally:
        conn.close()

# ============================================================
# RETRIEVAL
# ============================================================
def _fetch_papers_by_ids(conn: sqlite3.Connection, paper_ids: list[int]) -> dict[int, dict]:
    if not paper_ids:
        return {}
    placeholders = ",".join("?" * len(paper_ids))
    rows = conn.execute(
        f"SELECT id, title, summary, link, published, category FROM papers WHERE id IN ({placeholders})",
        paper_ids,
    ).fetchall()
    return {
        r[0]: {
            "id": r[0], "title": r[1], "abstract": r[2], "link": r[3],
            "published": r[4], "category": r[5],
        }
        for r in rows
    }


def semantic_search_papers(q: str, limit: int = 20) -> list[dict]:
    query_vec = _embed([q])
    with _index_lock:
        if faiss_index.ntotal == 0:
            return []
        k = min(max(limit * 3, TOP_K_SEARCH), int(faiss_index.ntotal))
        scores, ids = faiss_index.search(query_vec, k)
    pairs = [(int(cid), float(s)) for cid, s in zip(ids[0], scores[0]) if cid != -1]
    if not pairs:
        return []

    conn = _connect()
    try:
        chunk_ids = [cid for cid, _ in pairs]
        placeholders = ",".join("?" * len(chunk_ids))
        rows = conn.execute(
            f"SELECT id, paper_id FROM chunks WHERE id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        chunk_to_paper = {r[0]: r[1] for r in rows}

        paper_best: dict[int, float] = {}
        for cid, score in pairs:
            pid = chunk_to_paper.get(cid)
            if pid is None:
                continue
            if pid not in paper_best or score > paper_best[pid]:
                paper_best[pid] = score

        ranked = sorted(paper_best.items(), key=lambda x: -x[1])[:limit]
        paper_ids = [pid for pid, _ in ranked]
        meta = _fetch_papers_by_ids(conn, paper_ids)
        return [meta[pid] for pid in paper_ids if pid in meta]
    finally:
        conn.close()


def get_papers(q: str = "") -> list[dict]:
    if q:
        results = semantic_search_papers(q, limit=20)
        if results:
            return results
        # Fallback LIKE solo se l'indice è ancora vuoto (cold start)

    conn = _connect()
    try:
        sql = "SELECT id, title, summary, link, published, category FROM papers"
        params: list[str] = []
        if q:
            sql += " WHERE title LIKE ? OR summary LIKE ?"
            params = [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY published DESC LIMIT 20"
        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "id": r[0], "title": r[1], "abstract": r[2], "link": r[3],
                "published": r[4], "category": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


def retrieve_context(question: str, paper_id: int | None = None, k: int = TOP_K_CONTEXT) -> str:
    query_vec = _embed([question])[0]
    conn = _connect()
    try:
        if paper_id:
            rows = conn.execute(
                "SELECT id, text, embedding FROM chunks WHERE paper_id = ?",
                (paper_id,),
            ).fetchall()
            if not rows:
                paper = conn.execute(
                    "SELECT title, summary FROM papers WHERE id = ?", (paper_id,)
                ).fetchone()
                if paper:
                    text = ((paper[0] or "") + "\n\n" + (paper[1] or "")).strip()
                    pieces = _chunk_text(text)
                    if pieces:
                        _add_chunks_for_paper(conn, paper_id, pieces)
                        rows = conn.execute(
                            "SELECT id, text, embedding FROM chunks WHERE paper_id = ?",
                            (paper_id,),
                        ).fetchall()
            if not rows:
                return ""
            vecs = np.vstack([np.frombuffer(r[2], dtype="float32") for r in rows])
            scores = vecs @ query_vec
            top_idx = np.argsort(-scores)[: min(k, len(rows))]
            return "\n\n".join(rows[i][1] for i in top_idx)

        with _index_lock:
            if faiss_index.ntotal == 0:
                return ""
            k_eff = min(k, int(faiss_index.ntotal))
            _, ids = faiss_index.search(query_vec.reshape(1, -1), k_eff)
        chunk_ids = [int(i) for i in ids[0] if i != -1]
        if not chunk_ids:
            return ""
        placeholders = ",".join("?" * len(chunk_ids))
        rows = conn.execute(
            f"SELECT id, text FROM chunks WHERE id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        by_id = {r[0]: r[1] for r in rows}
        return "\n\n".join(by_id[cid] for cid in chunk_ids if cid in by_id)
    finally:
        conn.close()

# ============================================================
# INGEST ARXIV
# ============================================================
def run_ingest() -> dict:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    new_papers: list[dict] = []
    conn = _connect()
    try:
        _init_schema(conn)
        cur = conn.cursor()
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
                if cur.rowcount:
                    paper_id = cur.lastrowid
                    conn.commit()
                    text = (title + "\n\n" + summary).strip()
                    _add_chunks_for_paper(conn, paper_id, _chunk_text(text), persist=False)
                    new_papers.append({
                        "id": paper_id,
                        "title": title,
                        "link": link,
                        "published": published[:10],
                        "category": cat,
                        "authors": authors,
                        "abstract": summary[:200],
                    })
        conn.commit()
    finally:
        conn.close()
    if new_papers:
        with _index_lock:
            _persist_index()
    return {"count": len(new_papers), "papers": new_papers}

# ============================================================
# LLM
# ============================================================
def ask_llm(question: str, context: str) -> str:
    if not context.strip():
        return "Non presente nel paper"
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
            "content": f"Contenuto del paper:\n{context[:4000]}\n\nDomanda: {question}",
        },
    ]
    try:
        if client is None:
            raise RuntimeError("GROQ_API_KEY non impostata")
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            # gpt-oss ragiona prima di rispondere: i token di reasoning contano nel limite
            max_tokens=400 + 1024,
            temperature=0.4,
            extra_body={"reasoning_effort": "low"},
        )
        answer = completion.choices[0].message.content
        if not answer:
            raise RuntimeError("Risposta vuota dal modello")
        return answer.strip()
    except Exception as e:
        # Log interno completo, ma niente dettagli implementativi al client
        print(f"ERRORE LLM: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail="Il servizio di generazione non e' al momento disponibile. Riprova tra qualche istante.",
        )

# ============================================================
# STARTUP HOOK
# ============================================================
@app.on_event("startup")
def _on_startup() -> None:
    try:
        n = _backfill_missing_chunks()
        if n:
            print(f"Backfill: calcolati embedding per {n} paper")
    except Exception as e:
        print(f"Backfill fallito: {e}")

# ============================================================
# ENDPOINTS
# ============================================================
@app.get("/")
def root():
    return {
        "message": "API attiva - usa /papers/search o /rag/answer",
        "indexed_chunks": int(faiss_index.ntotal),
    }


@app.get("/papers/search")
def search_papers(q: str = ""):
    return get_papers(q=q)


@app.post("/rag/answer")
def rag_answer(req: QuestionRequest):
    context = retrieve_context(req.question, req.paper_id)
    answer = ask_llm(req.question, context)
    return {"answer": answer}


@app.post("/papers/ingest")
def ingest_papers():
    try:
        result = run_ingest()
    except Exception as e:
        print(f"ERRORE ingest: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail="Ingest da arXiv fallito. Riprova piu' tardi.",
        )
    return {"status": "ok", "new_papers": result["count"], "papers": result["papers"]}


@app.post("/papers/upload")
async def upload_paper(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo file PDF sono accettati.")
    try:
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File troppo grande: il limite e' {MAX_UPLOAD_MB} MB.",
            )
        reader = PdfReader(io.BytesIO(contents))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            raise HTTPException(status_code=422, detail="Impossibile estrarre testo dal PDF.")
        title = file.filename.removesuffix(".pdf")
        abstract = text[:4000]
        pieces = _chunk_text(text)
        truncated = len(pieces) > MAX_CHUNKS_PER_UPLOAD
        if truncated:
            pieces = pieces[:MAX_CHUNKS_PER_UPLOAD]
        conn = _connect()
        try:
            _init_schema(conn)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO papers (title, summary, link, published, category, authors) VALUES (?,?,?,?,?,?)",
                (title, abstract, f"upload://{file.filename}", "uploaded", "upload", ""),
            )
            paper_id = cur.lastrowid
            conn.commit()
            chunks_added = _add_chunks_for_paper(conn, paper_id, pieces)
        finally:
            conn.close()
        return {
            "status": "ok",
            "paper_id": paper_id,
            "title": title,
            "pages": len(reader.pages),
            "chunks": chunks_added,
            "truncated": truncated,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reindex")
def reindex():
    """Ricostruisce l'indice FAISS dai chunk salvati in SQLite."""
    global faiss_index
    conn = _connect()
    try:
        rows = conn.execute("SELECT id, embedding FROM chunks").fetchall()
    finally:
        conn.close()

    new_idx = _new_index()
    if rows:
        ids = np.asarray([r[0] for r in rows], dtype="int64")
        vecs = np.vstack([np.frombuffer(r[1], dtype="float32") for r in rows]).astype("float32")
        new_idx.add_with_ids(vecs, ids)
    with _index_lock:
        faiss_index = new_idx
        _persist_index()
    backfilled = _backfill_missing_chunks()
    return {
        "status": "ok",
        "indexed": int(faiss_index.ntotal),
        "backfilled_papers": backfilled,
    }


@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon"}
