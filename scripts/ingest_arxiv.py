"""Lightweight arXiv ingestion — inserts paper metadata only.

Chunking + embedding happens automatically on the next API startup via the
`_backfill_missing_chunks` hook in `api/main.py`. Kept deliberately
dependency-light so it can run before the API (and the embedder) are up.
"""

import os
import sqlite3
import xml.etree.ElementTree as ET

import requests

DB_PATH = os.getenv("DB_PATH", "data/app.db")
CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.IR"]
PER_CATEGORY = 10

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

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

ns = {"atom": "http://www.w3.org/2005/Atom"}
total_new = 0

for cat in CATEGORIES:
    url = (
        f"http://export.arxiv.org/api/query?search_query=cat:{cat}"
        f"&start=0&max_results={PER_CATEGORY}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )
    res = requests.get(url, timeout=15)
    root = ET.fromstring(res.text)
    entries = root.findall("atom:entry", ns)
    print(f"{cat}: {len(entries)} paper")

    for entry in entries:
        title = entry.find("atom:title", ns).text.strip()
        summary = entry.find("atom:summary", ns).text.strip()
        link = entry.find("atom:id", ns).text.strip()
        published = entry.find("atom:published", ns).text.strip()
        authors = ", ".join(
            a.find("atom:name", ns).text
            for a in entry.findall("atom:author", ns)
        )
        cur.execute(
            "INSERT OR IGNORE INTO papers (title, summary, link, published, category, authors) "
            "VALUES (?,?,?,?,?,?)",
            (title, summary, link, published, cat, authors),
        )
        if cur.rowcount:
            total_new += 1

conn.commit()
conn.close()
print(f"Ingest completato: {total_new} nuovi paper. Embedding verrà calcolato all'avvio dell'API.")
