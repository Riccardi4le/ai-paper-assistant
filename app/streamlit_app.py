import html
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Timeout (secondi) per le chiamate all'API: senza, la UI resta appesa
# se il backend è bloccato (es. ingest o embedding in corso).
TIMEOUT_SEARCH = 30
TIMEOUT_INGEST = 300
TIMEOUT_UPLOAD = 300
TIMEOUT_RAG = 120

# (label, classe css del badge) per categoria arXiv
CATEGORY_META = {
    "cs.AI": ("Artificial Intelligence", "badge-ai"),
    "cs.LG": ("Machine Learning", "badge-lg"),
    "cs.CL": ("NLP", "badge-cl"),
    "cs.CV": ("Computer Vision", "badge-cv"),
    "cs.IR": ("Information Retrieval", "badge-ir"),
    "upload": ("Caricato da te", "badge-upload"),
}


def esc(value) -> str:
    """Escape HTML: i dati arrivano da arXiv / nomi file utente."""
    return html.escape(str(value or ""), quote=True)


st.set_page_config(
    page_title="AI Paper Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0B1120;
    --surface: #151E31;
    --surface-2: #1E293B;
    --border: #283349;
    --border-strong: #334155;
    --primary: #6366F1;
    --primary-hover: #4F46E5;
    --primary-soft: rgba(99, 102, 241, 0.14);
    --primary-ring: rgba(99, 102, 241, 0.38);
    --text-strong: #F8FAFC;
    --text: #E2E8F0;
    --text-muted: #94A3B8;
    --text-faint: #64748B;
    --radius: 12px;
}

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* ---------- Background ---------- */
.stApp {
    background:
        radial-gradient(1100px 420px at 50% -120px, rgba(99, 102, 241, 0.13), transparent 70%),
        var(--bg);
    color: var(--text);
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: #0E1627;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    color: var(--text-muted);
}

.brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.4rem 0 0.9rem;
}
.brand-logo {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, #6366F1, #22D3EE);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.brand-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--text-strong);
    line-height: 1.2;
}
.brand-sub {
    font-size: 0.72rem;
    color: var(--text-faint);
}

/* Nav (radio) come lista di voci */
[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 4px;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    width: 100%;
    padding: 0.55rem 0.85rem;
    border-radius: 10px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(148, 163, 184, 0.08);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: var(--primary-soft);
    border-color: rgba(99, 102, 241, 0.35);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
    color: #C7D2FE;
    font-weight: 600;
}
/* nasconde il pallino del radio */
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
    display: none;
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
    font-size: 0.875rem;
    color: var(--text);
}

.sidebar-footer {
    font-size: 0.72rem;
    color: var(--text-faint);
    line-height: 1.7;
    margin-top: 1.5rem;
}

/* ---------- Bottoni ---------- */
.stButton > button {
    border-radius: 10px;
    padding: 0.55rem 1.25rem;
    font-weight: 600;
    font-size: 0.875rem;
    width: 100%;
    min-height: 44px;
    transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button[kind="primary"] {
    background: var(--primary);
    color: #FFFFFF;
    border: 1px solid transparent;
}
.stButton > button[kind="primary"]:hover {
    background: var(--primary-hover);
}
.stButton > button[kind="secondary"] {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border-strong);
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--primary);
    color: #C7D2FE;
    background: var(--primary-soft);
}
.stButton > button:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px var(--primary-ring);
}

/* ---------- Input ---------- */
.stTextInput input,
.stNumberInput input {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 10px !important;
    padding: 0.6rem 1rem !important;
    min-height: 44px;
}
.stTextInput input:focus,
.stNumberInput input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-ring) !important;
}
.stTextInput > div > div,
.stNumberInput > div > div {
    background: transparent !important;
    border: none !important;
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface);
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius);
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--primary);
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-muted);
    font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
    color: #A5B4FC !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--primary);
}

/* ---------- Hero ---------- */
.hero {
    padding: 2.1rem 0 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.6rem;
}
.hero h1 {
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    margin-bottom: 0.3rem;
    color: var(--text-strong) !important;
}
.hero .accent {
    background: linear-gradient(90deg, #818CF8, #22D3EE);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.hero p {
    color: var(--text-muted);
    font-size: 0.92rem;
    margin: 0;
}

/* ---------- Card paper ---------- */
.paper-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.4rem;
    margin-bottom: 0.9rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.paper-card:hover {
    border-color: rgba(99, 102, 241, 0.55);
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
}
.paper-title {
    font-size: 1rem;
    font-weight: 600;
    color: #A5B4FC;
    text-decoration: none;
    line-height: 1.45;
}
a.paper-title:hover {
    color: #C7D2FE;
    text-decoration: underline;
}
.paper-meta {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin: 0.45rem 0 0.7rem;
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
}
.paper-abstract {
    font-size: 0.875rem;
    color: var(--text-muted);
    line-height: 1.65;
    margin: 0;
}

/* ---------- Badge categorie ---------- */
.badge {
    border-radius: 999px;
    padding: 0.16rem 0.65rem;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid;
    white-space: nowrap;
}
.badge-ai     { color: #A5B4FC; background: rgba(99, 102, 241, 0.12);  border-color: rgba(99, 102, 241, 0.40); }
.badge-lg     { color: #6EE7B7; background: rgba(16, 185, 129, 0.10);  border-color: rgba(16, 185, 129, 0.35); }
.badge-cl     { color: #FCD34D; background: rgba(245, 158, 11, 0.10);  border-color: rgba(245, 158, 11, 0.35); }
.badge-cv     { color: #7DD3FC; background: rgba(14, 165, 233, 0.10);  border-color: rgba(14, 165, 233, 0.35); }
.badge-ir     { color: #F9A8D4; background: rgba(236, 72, 153, 0.10);  border-color: rgba(236, 72, 153, 0.35); }
.badge-upload { color: #C4B5FD; background: rgba(139, 92, 246, 0.10);  border-color: rgba(139, 92, 246, 0.35); }
.badge-default{ color: var(--text-muted); background: rgba(148, 163, 184, 0.10); border-color: rgba(148, 163, 184, 0.30); }

/* ---------- Chat ---------- */
[data-testid="stChatMessage"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.5rem 0.9rem;
    margin-bottom: 0.6rem;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: var(--primary-soft);
    border-color: rgba(99, 102, 241, 0.30);
}
[data-testid="stChatInput"] > div {
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 12px;
}
[data-testid="stChatInput"] textarea {
    color: var(--text);
    background: transparent;
}
[data-testid="stChatInput"]:focus-within > div {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-ring);
}

/* ---------- Vari ---------- */
h1 { color: var(--text-strong) !important; font-weight: 700 !important; }
h2, h3 { color: var(--text) !important; font-weight: 600 !important; }
hr { border-color: var(--border); margin: 1rem 0; }

[data-testid="stAlert"] {
    border-radius: 10px;
}

.results-count {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 1rem;
}
.results-count strong { color: #A5B4FC; }

.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-faint);
    font-size: 0.9rem;
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius);
    margin-top: 1rem;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
}
</style>
""", unsafe_allow_html=True)


def category_badge(category: str) -> str:
    if not category:
        return ""
    label, badge_class = CATEGORY_META.get(category, (category, "badge-default"))
    return f"<span class='badge {badge_class}'>{esc(label)}</span>"


def render_paper_card(p: dict, abstract_chars: int = 320) -> None:
    link = p.get("link") or ""
    title_html = (
        f"<a class='paper-title' href='{esc(link)}' target='_blank' rel='noopener'>{esc(p.get('title'))}</a>"
        if link.startswith("http")
        else f"<span class='paper-title'>{esc(p.get('title'))}</span>"
    )
    abstract = (p.get("abstract") or "").strip()
    if len(abstract) > abstract_chars:
        abstract = abstract[:abstract_chars].rstrip() + "…"
    st.markdown(
        f"<div class='paper-card'>"
        f"{title_html}"
        f"<div class='paper-meta'>"
        f"<span>ID {esc(p.get('id'))}</span>"
        f"<span>{esc(str(p.get('published') or '')[:10])}</span>"
        f"{category_badge(p.get('category') or '')}"
        f"</div>"
        f"<p class='paper-abstract'>{esc(abstract)}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def api_error_detail(response) -> str:
    try:
        return response.json().get("detail", f"Errore API ({response.status_code})")
    except Exception:
        return f"Errore API ({response.status_code})"


# --- Sidebar ---
with st.sidebar:
    st.markdown(
        "<div class='brand'>"
        "<div class='brand-logo'>"
        "<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='white' "
        "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/>"
        "<path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/>"
        "</svg>"
        "</div>"
        "<div>"
        "<div class='brand-name'>AI Paper Assistant</div>"
        "<div class='brand-sub'>RAG su paper arXiv</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Sezione",
        ["Ricerca Paper", "Carica Paper", "Chat con l'assistente"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    if st.button("Aggiorna paper da arXiv", type="primary"):
        with st.spinner("Scarico nuovi paper..."):
            try:
                r = requests.post(f"{API_URL}/papers/ingest", timeout=TIMEOUT_INGEST)
                if r.status_code == 200:
                    st.session_state["ingest_result"] = r.json()
                else:
                    st.error(api_error_detail(r))
            except requests.Timeout:
                st.error("L'aggiornamento sta impiegando troppo tempo. Riprova.")
            except Exception as e:
                st.error(f"Errore di connessione: {e}")
    st.markdown(
        "<div class='sidebar-footer'>"
        "Fonti: arXiv<br>"
        "Artificial Intelligence · Machine Learning<br>"
        "NLP · Computer Vision · Information Retrieval"
        "</div>",
        unsafe_allow_html=True,
    )


# --- Pagina 1: Ricerca Paper ---
if page == "Ricerca Paper":
    st.markdown(
        "<div class='hero'>"
        "<h1>Ricerca <span class='accent'>Paper Scientifici</span></h1>"
        "<p>Cerca tra i paper più recenti da arXiv su AI, ML, NLP e Computer Vision</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Mostra risultato ingest se disponibile
    if "ingest_result" in st.session_state:
        data = st.session_state["ingest_result"]
        n = data["new_papers"]
        papers = data.get("papers", [])
        if n == 0:
            st.info("Nessun nuovo paper trovato — il database è già aggiornato.")
        else:
            st.success(f"Aggiunti {n} nuovi paper!")
            from collections import defaultdict
            by_cat = defaultdict(list)
            for p in papers:
                by_cat[p["category"]].append(p)
            tab_labels = [CATEGORY_META.get(c, (c, ""))[0] for c in by_cat.keys()]
            tabs = st.tabs(tab_labels)
            for tab, cat in zip(tabs, by_cat.keys()):
                with tab:
                    for p in by_cat[cat]:
                        render_paper_card(p, abstract_chars=200)
        if st.button("Chiudi", key="close_ingest", type="secondary"):
            del st.session_state["ingest_result"]
            st.rerun()
        st.markdown("---")

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        q = st.text_input(
            "Ricerca",
            placeholder="Cerca per argomento, es. \"transformer efficiency\"...",
            label_visibility="collapsed",
        )
    with col_btn:
        search = st.button("Cerca", type="primary")

    if search or q:
        with st.spinner("Ricerca in corso..."):
            try:
                r = requests.get(
                    f"{API_URL}/papers/search", params={"q": q}, timeout=TIMEOUT_SEARCH
                )
                papers = r.json() if r.status_code == 200 else None
                if papers is None:
                    st.error(api_error_detail(r))
                elif papers:
                    st.markdown(
                        f"<p class='results-count'>Trovati <strong>{len(papers)}</strong> risultati</p>",
                        unsafe_allow_html=True,
                    )
                    for p in papers:
                        render_paper_card(p)
                else:
                    st.markdown(
                        "<div class='empty-state'>Nessun risultato trovato.<br>"
                        "Prova con altre parole chiave o aggiorna i paper da arXiv.</div>",
                        unsafe_allow_html=True,
                    )
            except requests.Timeout:
                st.error("La ricerca sta impiegando troppo tempo. Riprova.")
            except Exception as e:
                st.error(f"Errore di connessione: {e}")


# --- Pagina 2: Carica Paper ---
elif page == "Carica Paper":
    st.markdown(
        "<div class='hero'>"
        "<h1>Carica un <span class='accent'>Paper PDF</span></h1>"
        "<p>Carica un file PDF e chatta con l'assistente sul suo contenuto (max 25 MB)</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Seleziona un file PDF",
        type=["pdf"],
        label_visibility="visible",
    )

    if uploaded_file is not None:
        with st.spinner("Analisi del PDF in corso..."):
            try:
                r = requests.post(
                    f"{API_URL}/papers/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    timeout=TIMEOUT_UPLOAD,
                )
                if r.status_code == 200:
                    data = r.json()
                    st.success(
                        f"Paper caricato con successo! "
                        f"**ID: {data['paper_id']}** · {data['pages']} pagine"
                    )
                    if data.get("truncated"):
                        st.warning(
                            "Il documento è molto lungo: è stata indicizzata solo la prima parte."
                        )
                    st.markdown(
                        f"<div class='paper-card'>"
                        f"<span class='paper-title'>{esc(data['title'])}</span>"
                        f"<div class='paper-meta'>"
                        f"<span>ID {esc(data['paper_id'])}</span>"
                        f"{category_badge('upload')}"
                        f"</div>"
                        f"<p class='paper-abstract'>"
                        f"Usa l'ID <strong>{esc(data['paper_id'])}</strong> nella sezione "
                        f"<em>Chat con l'assistente</em> per fare domande su questo paper."
                        f"</p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state["last_uploaded_id"] = data["paper_id"]
                else:
                    st.error(api_error_detail(r))
            except requests.Timeout:
                st.error("Il caricamento sta impiegando troppo tempo. Prova con un PDF più piccolo.")
            except Exception as e:
                st.error(f"Errore di connessione: {e}")

    if "last_uploaded_id" in st.session_state:
        st.markdown("---")
        st.markdown(
            f"<p class='results-count'>"
            f"Ultimo paper caricato: ID <strong>{esc(st.session_state['last_uploaded_id'])}</strong> — "
            f"vai su <em>Chat con l'assistente</em> per interrogarlo.</p>",
            unsafe_allow_html=True,
        )


# --- Pagina 3: Chat ---
elif page == "Chat con l'assistente":
    st.markdown(
        "<div class='hero'>"
        "<h1>Chat con <span class='accent'>l'Assistente AI</span></h1>"
        "<p>Fai domande su un paper specifico — l'AI risponde basandosi sul suo contenuto</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_id, _ = st.columns([2, 5])
    with col_id:
        paper_id = st.number_input("ID del paper", min_value=1, step=1)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Di cosa parla?", type="secondary"):
            st.session_state["quick_question"] = "Di cosa parla questo paper?"
    with col2:
        if st.button("Riassumi", type="secondary"):
            st.session_state["quick_question"] = "Riassumi questo paper in modo chiaro e conciso."
    with col3:
        if st.button("Metodologia", type="secondary"):
            st.session_state["quick_question"] = "Qual è la metodologia usata in questo paper?"

    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if not st.session_state["messages"]:
        st.markdown(
            "<div class='empty-state'>Nessun messaggio ancora.<br>"
            "Inserisci l'ID di un paper e scrivi una domanda, oppure usa i pulsanti rapidi.</div>",
            unsafe_allow_html=True,
        )

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Scrivi la tua domanda...") or st.session_state.pop("quick_question", None)

    if question:
        st.session_state["messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("L'assistente sta pensando..."):
                try:
                    r = requests.post(
                        f"{API_URL}/rag/answer",
                        json={"question": question, "paper_id": int(paper_id)},
                        timeout=TIMEOUT_RAG,
                    )
                    if r.status_code == 200:
                        answer = r.json().get("answer", "Nessuna risposta.")
                    else:
                        answer = api_error_detail(r)
                except requests.Timeout:
                    answer = "La risposta sta impiegando troppo tempo. Riprova."
                except Exception as e:
                    answer = f"Errore di connessione: {e}"

            st.write(answer)
            st.session_state["messages"].append({"role": "assistant", "content": answer})
