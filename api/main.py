import os
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# ============================================================
# CONFIGURAZIONE
# ============================================================
load_dotenv()
app = FastAPI()
DB_PATH = "data/app.db"

# Modello embeddings (usato per ricerca semantica)
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Client Hugging Face
HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
client = InferenceClient(model="mistralai/Mistral-7B-Instruct-v0.3", token=HF_TOKEN)

# ============================================================
# MODELLI DATI
# ============================================================
class QuestionRequest(BaseModel):
    question: str

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


def get_context():
    """Recupera il testo di contesto dai paper"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT summary FROM papers LIMIT 10").fetchall()
    conn.close()
    return "\n\n".join([r[0] for r in rows if r[0]])

# ============================================================
# FUNZIONE PRINCIPALE AI 
# ============================================================
def ask_llm(question: str, context: str):
    """
    Interroga Mistral su Hugging Face con un prompt raffinato.
    Se la risposta è già chiara, salta la rifinitura per risparmiare tempo.
    """

    messages = [
        {
            "role": "system",
            "content": (
                "Sei un assistente accademico che riassume e spiega paper scientifici "
                "in italiano chiaro, corretto e professionale. "
                "Scrivi con grammatica impeccabile e tono accademico, ma comprensibile."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Contenuto del paper:\n\n{context}\n\n"
                f"Domanda: {question}\n\n"
                "Rispondi solo usando queste informazioni. "
                "Se la risposta non è nel testo, scrivi: 'L'informazione non è presente nel paper'."
            ),
        },
    ]

    try:
        # === GENERAZIONE PRINCIPALE ===
        completion = client.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            messages=messages,
            max_tokens=350,
        )
        raw_answer = completion.choices[0].message["content"].strip()

        # Pulizia base
        for tag in ["[/INST]", "[/ASST]", "<s>", "</s>"]:
            raw_answer = raw_answer.replace(tag, "")
        raw_answer = raw_answer.strip()

        # === SE NECESSARIO, RIFINITURA ===
        if len(raw_answer.split()) < 20 or any(c in raw_answer for c in ["[", "]", "<", ">"]):
            refine_messages = [
                {
                    "role": "system",
                    "content": (
                        "Agisci come un correttore professionale di testi accademici in italiano. "
                        "Riscrivi il testo in forma fluida e grammaticale, mantenendo lo stesso significato."
                    ),
                },
                {"role": "user", "content": raw_answer},
            ]

            refinement = client.chat.completions.create(
                model="mistralai/Mistral-7B-Instruct-v0.3",
                messages=refine_messages,
                max_tokens=250,
            )

            refined_text = refinement.choices[0].message["content"].strip()
            return refined_text

        return raw_answer

    except Exception as e:
        print(" ERRORE HF:", e)
        return "Errore durante la generazione della risposta."

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
    context = get_context()
    answer = ask_llm(req.question, context)
    return {"answer": answer}

@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon"}
