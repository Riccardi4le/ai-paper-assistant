import requests
import sqlite3
import os
import xml.etree.ElementTree as ET

DB_PATH = "data/app.db"
os.makedirs("data", exist_ok=True)

# API URL: ultimi 10 paper in cs.AI
url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"
res = requests.get(url)
root = ET.fromstring(res.text)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    summary TEXT,
    link TEXT UNIQUE,
    published TEXT
)
""")

ns = {"atom": "http://www.w3.org/2005/Atom"}

for entry in root.findall("atom:entry", ns):
    title = entry.find("atom:title", ns).text.strip()
    summary = entry.find("atom:summary", ns).text.strip()
    link = entry.find("atom:id", ns).text.strip()
    published = entry.find("atom:published", ns).text.strip()

    cur.execute("INSERT OR IGNORE INTO papers (title, summary, link, published) VALUES (?,?,?,?)",
                (title, summary, link, published))

conn.commit()
conn.close()

print("✅ Ingest completato con API arXiv")
