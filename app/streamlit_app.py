import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Paper Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* Background */
.stApp {
    background: #0F172A;
    color: #E2E8F0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #1E293B;
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #CBD5E1 !important;
}

/* Buttons */
.stButton > button {
    background: #6366F1;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.25rem;
    font-weight: 500;
    font-size: 0.875rem;
    transition: background 0.2s ease, transform 0.1s ease;
    width: 100%;
}
.stButton > button:hover {
    background: #4F46E5;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0px);
}

/* Text Input */
.stTextInput > div > div > input {
    background: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 0.6rem 1rem;
}
.stTextInput > div > div > input:focus {
    border-color: #6366F1;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.25);
}

/* Number Input */
.stNumberInput > div > div > input {
    background: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 8px;
}

/* Selectbox */
.stSelectbox > div > div {
    background: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 8px;
}

/* Divider */
hr {
    border-color: #334155;
    margin: 1rem 0;
}

/* Paper card */
.paper-card {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.paper-card:hover {
    border-color: #6366F1;
    box-shadow: 0 4px 20px rgba(99,102,241,0.15);
}
.paper-title {
    font-size: 1rem;
    font-weight: 600;
    color: #818CF8;
    text-decoration: none;
    line-height: 1.4;
}
.paper-title:hover { color: #A5B4FC; }
.paper-meta {
    font-size: 0.75rem;
    color: #64748B;
    margin: 0.35rem 0 0.75rem;
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
}
.paper-badge {
    background: #1D2D50;
    color: #818CF8;
    border: 1px solid #3730A3;
    border-radius: 999px;
    padding: 0.15rem 0.6rem;
    font-size: 0.7rem;
    font-weight: 500;
}
.paper-abstract {
    font-size: 0.875rem;
    color: #94A3B8;
    line-height: 1.65;
}

/* Chat */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border-radius: 12px;
    margin-bottom: 0.5rem;
}

/* Chat input */
[data-testid="stChatInput"] > div {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
}
[data-testid="stChatInput"] textarea {
    color: #E2E8F0;
    background: transparent;
}

/* Titles */
h1 { color: #F1F5F9 !important; font-weight: 700 !important; }
h2, h3 { color: #CBD5E1 !important; font-weight: 600 !important; }

/* Hero header */
.hero {
    padding: 2rem 0 1.5rem;
    border-bottom: 1px solid #1E293B;
    margin-bottom: 1.5rem;
}
.hero h1 { font-size: 1.75rem !important; margin-bottom: 0.25rem; }
.hero p { color: #64748B; font-size: 0.9rem; margin: 0; }
</style>
""", unsafe_allow_html=True)


# --- Sidebar ---
with st.sidebar:
    st.markdown("## AI Paper Assistant")
    st.markdown("---")
    page = st.selectbox(
        "Sezione",
        ["Ricerca Paper", "Chat con l'assistente"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    if st.button("Aggiorna paper da arXiv"):
        with st.spinner("Scarico nuovi paper..."):
            try:
                r = requests.post(f"{API_URL}/papers/ingest")
                if r.status_code == 200:
                    data = r.json()
                    if data["status"] == "ok":
                        st.success(f"Aggiunti {data['new_papers']} nuovi paper!")
                    else:
                        st.error(f"Errore: {data.get('message')}")
                else:
                    st.error(f"Errore API ({r.status_code})")
            except Exception as e:
                st.error(f"Errore: {e}")
    st.markdown(
        "<p style='font-size:0.75rem;color:#475569;margin-top:2rem'>"
        "Fonti: arXiv · cs.AI · cs.LG · cs.CL · cs.CV · cs.IR"
        "</p>",
        unsafe_allow_html=True,
    )


# --- Pagina 1: Ricerca Paper ---
if page == "Ricerca Paper":
    st.markdown(
        "<div class='hero'>"
        "<h1>Ricerca Paper Scientifici</h1>"
        "<p>Cerca tra i paper piu recenti da arXiv su AI, ML, NLP e Computer Vision</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        q = st.text_input("", placeholder="Cerca per parola chiave...", label_visibility="collapsed")
    with col_btn:
        search = st.button("Cerca")

    if search or q:
        with st.spinner("Ricerca in corso..."):
            try:
                r = requests.get(f"{API_URL}/papers/search", params={"q": q})
                papers = r.json()

                if papers:
                    st.markdown(
                        f"<p style='color:#64748B;font-size:0.85rem;margin-bottom:1rem'>"
                        f"Trovati <strong style='color:#818CF8'>{len(papers)}</strong> risultati</p>",
                        unsafe_allow_html=True,
                    )
                    for p in papers:
                        category = p.get("category") or ""
                        badge = f"<span class='paper-badge'>{category}</span>" if category else ""
                        st.markdown(
                            f"<div class='paper-card'>"
                            f"<a class='paper-title' href='{p['link']}' target='_blank'>{p['title']}</a>"
                            f"<div class='paper-meta'>"
                            f"<span>ID {p['id']}</span>"
                            f"<span>{p.get('published','')[:10]}</span>"
                            f"{badge}"
                            f"</div>"
                            f"<p class='paper-abstract'>{p['abstract'][:320]}...</p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.warning("Nessun risultato trovato.")
            except Exception as e:
                st.error(f"Errore di connessione: {e}")


# --- Pagina 2: Chat ---
elif page == "Chat con l'assistente":
    st.markdown(
        "<div class='hero'>"
        "<h1>Chat con l'Assistente AI</h1>"
        "<p>Fai domande su un paper specifico - l'AI risponde basandosi sul suo contenuto</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_id, _ = st.columns([2, 5])
    with col_id:
        paper_id = st.number_input("ID del paper", min_value=1, step=1)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Di cosa parla?"):
            st.session_state["quick_question"] = "Di cosa parla questo paper?"
    with col2:
        if st.button("Riassumi"):
            st.session_state["quick_question"] = "Riassumi questo paper in modo chiaro e conciso."
    with col3:
        if st.button("Metodologia"):
            st.session_state["quick_question"] = "Qual e' la metodologia usata in questo paper?"

    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

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
                    )
                    answer = r.json().get("answer", "Nessuna risposta.") if r.status_code == 200 else f"Errore API ({r.status_code})"
                except Exception as e:
                    answer = f"Errore di connessione: {e}"

            st.write(answer)
            st.session_state["messages"].append({"role": "assistant", "content": answer})
