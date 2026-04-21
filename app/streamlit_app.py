import streamlit as st
import requests

# URL API
API_URL = "http://127.0.0.1:8000"

# Configurazione pagina
st.set_page_config(page_title="AI Paper Assistant", page_icon="📚", layout="wide")

# Titolo principale
st.title("📚 Paper Scientifici con Assistente IA")
st.write("Cerca e analizza paper scientifici con un modello AI open-source da Hugging Face 🤖")

# Sidebar di navigazione
with st.sidebar:
    st.header("🔍 Navigazione")
    page = st.selectbox("Seleziona sezione", ["Ricerca Paper", "Chat con l’assistente"])

# -----------------------------------------------------------------------------
# PAGINA 1 — RICERCA PAPER
# -----------------------------------------------------------------------------
if page == "Ricerca Paper":
    st.subheader("🔎 Cerca paper scientifici")

    q = st.text_input("Inserisci una parola chiave", "")

    if st.button("Cerca"):
        with st.spinner("🔎 Ricerca in corso..."):
            try:
                r = requests.get(f"{API_URL}/papers/search", params={"q": q})
                papers = r.json()

                if papers:
                    st.success(f"Trovati {len(papers)} paper!")
                    for p in papers:
                        st.markdown(f"### [{p['title']}]({p['link']})")
                        st.caption(f"🗓️ Pubblicato: {p['published']} • ID: {p['id']}")
                        st.write(p["abstract"])
                        st.divider()
                else:
                    st.warning("Nessun risultato trovato.")
            except Exception as e:
                st.error(f"Errore nella connessione: {e}")

# -----------------------------------------------------------------------------
# PAGINA 2 — CHAT CON L’ASSISTENTE
# -----------------------------------------------------------------------------
elif page == "Chat con l’assistente":
    st.subheader("💬 Chat con l’assistente AI")

    # Selezione paper
    paper_id = st.number_input("Inserisci l'ID del paper", min_value=1, step=1)

    # Pulsanti rapidi
    st.write("Puoi iniziare con una delle seguenti domande:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📘 Di cosa parla questo paper?"):
            st.session_state["quick_question"] = "Di cosa parla questo paper?"
    with col2:
        if st.button("🧠 Riassumi questo paper"):
            st.session_state["quick_question"] = "Riassumi questo paper."

    # Chat
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

        # Richiesta all’API
        try:
            with st.spinner("💬 L’assistente sta rispondendo..."):
                r = requests.post(f"{API_URL}/rag/answer", json={
                    "question": question,
                    "paper_id": paper_id
                })

                if r.status_code == 200:
                    answer = r.json().get("answer", "Nessuna risposta ricevuta.")
                else:
                    answer = f"Errore API ({r.status_code})"

                st.session_state["messages"].append({"role": "assistant", "content": answer})

                with st.chat_message("assistant"):
                    st.write(answer)

        except Exception as e:
            st.error(f"Errore durante la richiesta: {e}")
