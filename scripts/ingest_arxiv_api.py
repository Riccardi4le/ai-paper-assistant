import requests
import sqlite3
import os
import xml.etree.ElementTree as ET

DB_PATH = "data/app.db"
PDF_DIR = "data/pdfs"
os.makedirs("data", exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR", "cs.DS"]

ns = {"atom": "http://www.w3.org/2005/Atom"}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    summary TEXT,
    link TEXT UNIQUE,
    published TEXT,
    category TEXT,
    authors TEXT,
    pdf_path TEXT
)
""")

for cat in CATEGORIES:
    url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
    res = requests.get(url)
    root = ET.fromstring(res.text)

    entries = root.findall("atom:entry", ns)
    print(f"📥 {len(entries)} paper trovati in {cat}")

    for entry in entries:
        title = entry.find("atom:title", ns).text.strip()
        summary = entry.find("atom:summary", ns).text.strip()
        link = entry.find("atom:id", ns).text.strip()
        published = entry.find("atom:published", ns).text.strip()
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        authors_str = ", ".join(authors)

        # Link PDF (arXiv -> sostituiamo abs con pdf)
        pdf_url = link.replace("abs", "pdf") + ".pdf"
        pdf_filename = os.path.join(PDF_DIR, pdf_url.split("/")[-1])

        # Scarica PDF se non esiste
        if not os.path.exists(pdf_filename):
            try:
                r_pdf = requests.get(pdf_url, timeout=15)
                if r_pdf.status_code == 200:
                    with open(pdf_filename, "wb") as f:
                        f.write(r_pdf.content)
                    print(f"✅ Scaricato PDF: {pdf_filename}")
                else:
                    print(f"⚠️ Errore download {pdf_url}")
                    pdf_filename = None
            except Exception as e:
                print(f"⚠️ Errore: {e}")
                pdf_filename = None

        cur.execute("""
            INSERT OR IGNORE INTO papers (title, summary, link, published, category, authors, pdf_path)
            VALUES (?,?,?,?,?,?,?)
        """, (title, summary, link, published, cat, authors_str, pdf_filename))

conn.commit()
conn.close()
print("✅ Ingest completato con PDF")

