import os
import uuid
from datetime import datetime

import fitz
import httpx
import streamlit as st

st.set_page_config(page_title="Student Research Agent", page_icon="🎓", layout="wide")


def _get_backend_url():
    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return os.getenv("BACKEND_URL", "").strip()


BACKEND_URL = _get_backend_url()
TIMEOUT = 120

st.markdown(
    """
<style>
.block-container{padding-top:1.5rem}
.action-badge{display:inline-block;padding:4px 14px;border-radius:12px;font-size:.8rem;font-weight:700;text-transform:uppercase;margin-bottom:.8rem}
.badge-answer{background:#dbeafe;color:#1e40af}
.badge-summarize{background:#dcfce7;color:#166534}
.badge-explain{background:#fef9c3;color:#854d0e}
.badge-quiz{background:#ede9fe;color:#5b21b6}
.badge-viva{background:#fce7f3;color:#9d174d}
.badge-clarify{background:#f1f5f9;color:#475569}
.badge-refuse{background:#fee2e2;color:#991b1b}
.answer-box{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:1.4rem 1.6rem;margin:.8rem 0;line-height:1.8;font-size:1rem;color:#e2e8f0}
.source-card{border-left:4px solid #6366f1;padding:.7rem 1rem;margin:.5rem 0;background:#0f172a;border-radius:0 8px 8px 0;font-size:.85rem;color:#cbd5e1}
.notice{padding:1rem 1.2rem;border-radius:12px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a;margin:.75rem 0}
.warn{padding:1rem 1.2rem;border-radius:12px;background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;margin:.75rem 0}
</style>
""",
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "indexed_file" not in st.session_state:
    st.session_state.indexed_file = None
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0
if "document_text" not in st.session_state:
    st.session_state.document_text = ""
if "pages_data" not in st.session_state:
    st.session_state.pages_data = []


def get_badge(action):
    mapping = {
        "answer_question": ("Answer", "answer"),
        "summarize": ("Summary", "summarize"),
        "explain_simply": ("Simplified", "explain"),
        "generate_quiz": ("Quiz", "quiz"),
        "generate_viva": ("Viva", "viva"),
        "ask_clarification": ("Clarify", "clarify"),
        "refuse_if_no_evidence": ("No Evidence", "refuse"),
    }
    label, css = mapping.get(action, (action.replace("_", " ").title(), "clarify"))
    return f'<span class="action-badge badge-{css}">{label}</span>'


def local_extract_pdf(file_bytes, filename):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    full_text = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages.append({"page": i, "text": text, "document": filename, "score": 1.0})
        full_text.append(f"\n--- Page {i} ---\n{text}")
    doc.close()
    return "\n".join(full_text), pages


def call_backend(endpoint, method="get", **kwargs):
    if not BACKEND_URL:
        return None, "BACKEND_URL is not set"
    url = f"{BACKEND_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        if method == "get":
            r = httpx.get(url, timeout=TIMEOUT)
        elif method == "post_json":
            r = httpx.post(url, json=kwargs.get("json"), timeout=TIMEOUT)
        elif method == "post_file":
            r = httpx.post(url, files=kwargs.get("files"), timeout=TIMEOUT)
        else:
            return None, "Unknown method"
        if r.status_code in (200, 201):
            return r.json(), None
        try:
            detail = r.json().get("detail", r.text[:200])
        except Exception:
            detail = r.text[:200]
        return None, f"Error {r.status_code}: {detail}"
    except httpx.ConnectError:
        return None, f"Cannot connect to backend at {BACKEND_URL}"
    except httpx.TimeoutException:
        return None, "Timeout — try again"
    except Exception as e:
        return None, str(e)


def simple_search(query, pages_data):
    q = query.lower().strip()
    hits = []
    for p in pages_data:
        text = (p.get("text") or "").lower()
        score = 0
        for word in q.split():
            if len(word) > 2 and word in text:
                score += 1
        if score > 0:
            hits.append({**p, "score": score})
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:4]


def generate_offline_answer(query, mode):
    pages_data = st.session_state.get("pages_data", [])
    document_text = st.session_state.get("document_text", "")
    if not document_text:
        return "refuse_if_no_evidence", "No PDF is loaded. Please upload a document first.", []
    sources = simple_search(query, pages_data)
    context = "\n\n".join([f"Page {s['page']}:\n{s['text'][:1500]}" for s in sources]) or document_text[:6000]
    prompt_map = {
        "answer": f"Answer the question from the PDF context only.\n\nContext:\n{context}\n\nQuestion: {query}",
        "summarize": f"Summarize the PDF content clearly and concisely.\n\nContext:\n{context}",
        "explain": f"Explain the PDF content simply for a student.\n\nContext:\n{context}\n\nQuestion: {query}",
        "quiz": f"Create 5 quiz questions with answers from this PDF.\n\nContext:\n{context}",
        "viva": f"Create 5 viva questions with short model answers from this PDF.\n\nContext:\n{context}",
        "auto": f"Use the PDF context to answer this.\n\nContext:\n{context}\n\nQuestion: {query}",
    }
    prompt = prompt_map.get(mode, prompt_map["auto"])
    api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", "")).strip()
    if not api_key:
        return "refuse_if_no_evidence", "Add GROQ_API_KEY in Streamlit Secrets to enable AI answers.", sources

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )
        answer = resp.choices[0].message.content
        action_map = {
            "answer": "answer_question",
            "summarize": "summarize",
            "explain": "explain_simply",
            "quiz": "generate_quiz",
            "viva": "generate_viva",
            "auto": "answer_question",
        }
        return action_map.get(mode, "answer_question"), answer, sources
    except Exception as e:
        return "refuse_if_no_evidence", f"AI error: {e}", sources


def send_query(query_text, mode):
    query_text = query_text.strip()
    if not query_text:
        return
    with st.spinner("Agent is thinking..."):
        if BACKEND_URL:
            data, err = call_backend(
                "/query",
                method="post_json",
                json={
                    "session_id": st.session_state.session_id,
                    "query": query_text,
                    "mode": mode,
                },
            )
            if err:
                st.warning(f"Backend unavailable, using local mode: {err}")
                action, answer, sources = generate_offline_answer(query_text, mode)
                data = {
                    "action": action,
                    "answer": answer,
                    "sources": sources,
                    "confidence": "high" if sources else "medium",
                    "success": True,
                }
        else:
            action, answer, sources = generate_offline_answer(query_text, mode)
            data = {
                "action": action,
                "answer": answer,
                "sources": sources,
                "confidence": "high" if sources else "medium",
                "success": True,
            }

    st.session_state.last_response = data
    st.session_state.history.append({"query": query_text, "action": data.get("action", "unknown")})
    st.rerun()


with st.sidebar:
    st.markdown("## 🎓 Research Agent")
    if BACKEND_URL:
        health_data, err = call_backend("/health")
        if err:
            st.warning(f"Backend offline: {err}")
        else:
            chunks = health_data.get("checks", {}).get("vectorstore", {}).get("chunks_indexed", 0)
            fname = st.session_state.indexed_file or "none"
            if chunks > 0:
                st.success(f"✅ Online · {chunks} chunks · `{fname}`")
            else:
                st.warning("⚠️ Online · No document indexed yet")
    else:
        st.info("Local mode enabled. Upload + question works inside Streamlit.")
    st.divider()

    st.markdown("### 📄 Upload PDF")
    uploaded = st.file_uploader("Choose a PDF", type=["pdf"], key=f"uploader_{st.session_state.upload_key}")

    if uploaded is not None:
        try:
            with st.spinner(f"Processing {uploaded.name}..."):
                file_bytes = uploaded.getvalue()

                if not file_bytes:
                    st.error("Uploaded file is empty.")
                    st.stop()

                if BACKEND_URL:
                    data, err = call_backend(
                        "/upload",
                        method="post_file",
                        files={"file": (uploaded.name, file_bytes, "application/pdf")},
                    )
                    if err:
                        st.warning(f"Backend upload failed, using local mode: {err}")
                        text, pages = local_extract_pdf(file_bytes, uploaded.name)
                        st.session_state.document_text = text
                        st.session_state.pages_data = pages
                        st.session_state.indexed_file = uploaded.name
                    else:
                        st.session_state.indexed_file = data.get("filename", uploaded.name)
                else:
                    text, pages = local_extract_pdf(file_bytes, uploaded.name)
                    st.session_state.document_text = text
                    st.session_state.pages_data = pages
                    st.session_state.indexed_file = uploaded.name

                st.session_state.last_response = None
                st.session_state.history = []
                st.session_state.upload_key += 1
                st.success(f"✅ {st.session_state.indexed_file} loaded")
                st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")

    if st.session_state.indexed_file:
        st.info(f"📄 Active: `{st.session_state.indexed_file}`")
        if st.button("Upload different PDF", use_container_width=True):
            st.session_state.indexed_file = None
            st.session_state.last_response = None
            st.session_state.history = []
            st.session_state.document_text = ""
            st.session_state.pages_data = []
            st.session_state.upload_key += 1
            st.rerun()

    st.divider()
    if st.session_state.history:
        st.markdown("### 🕐 Recent")
        for item in reversed(st.session_state.history[-5:]):
            st.markdown(f"_{item['action'].replace('_', ' ').title()}_ · {item['query'][:45]}")
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.session_state.last_response = None
            st.rerun()

st.markdown("# 🎓 Student Research Agent")
st.markdown("Upload a PDF · Choose a task · Get grounded AI responses")
st.divider()

MODE_OPTIONS = {
    "🤖 Auto": "auto",
    "❓ Answer": "answer",
    "📋 Summarise": "summarize",
    "🧩 Explain simply": "explain",
    "📝 Quiz": "quiz",
    "🎤 Viva": "viva",
}
selected_label = st.radio("Mode", list(MODE_OPTIONS.keys()), horizontal=True, label_visibility="collapsed")
selected_mode = MODE_OPTIONS[selected_label]

st.divider()

QUICK_PROMPTS = {
    "auto": ["Summarise this paper", "What is the main finding?", "Explain the key concepts"],
    "answer": ["What is the main hypothesis?", "What methods were used?", "What are the conclusions?"],
    "summarize": ["Give me a full summary", "Summarise the conclusions", "What are the key findings?"],
    "explain": ["Explain this simply", "What does this mean for a beginner?", "Break down the concepts"],
    "quiz": ["Generate 5 quiz questions", "Create MCQ questions", "Make a practice test"],
    "viva": ["Generate viva questions", "What would an examiner ask?", "Prepare oral exam questions"],
}

st.markdown("**Quick prompts — click to ask instantly:**")
cols = st.columns(3)
for i, prompt in enumerate(QUICK_PROMPTS.get(selected_mode, QUICK_PROMPTS["auto"])):
    with cols[i % 3]:
        if st.button(prompt, key=f"qp_{selected_mode}_{i}", use_container_width=True):
            send_query(prompt, selected_mode)

st.divider()
st.markdown("**Or type your own question:**")
query = st.text_area(
    "Q",
    height=80,
    placeholder="e.g. 'Summarise this paper' or 'Generate 5 quiz questions'",
    label_visibility="collapsed",
)

col1, col2 = st.columns([3, 1])
with col1:
    if st.button("Ask the Agent →", type="primary", use_container_width=True, disabled=not query.strip()):
        send_query(query, selected_mode)
with col2:
    if st.button("Clear", use_container_width=True):
        st.session_state.last_response = None
        st.rerun()

if st.session_state.last_response:
    resp = st.session_state.last_response
    action = resp.get("action", "unknown")
    answer = resp.get("answer", "")
    sources = resp.get("sources", [])
    confidence = resp.get("confidence", "low")

    st.divider()
    st.markdown("### 🤖 Agent Response")
    col_b, col_c = st.columns([2, 1])
    with col_b:
        st.markdown(get_badge(action), unsafe_allow_html=True)
    with col_c:
        icons = {"high": "🟢 HIGH", "medium": "🟡 MEDIUM", "low": "🔴 LOW"}
        st.markdown(f"**Confidence:** {icons.get(confidence, '⚪')}")

    if answer:
        st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)

    if sources:
        st.markdown(f"### 📚 Sources ({len(sources)} chunks)")
        for i, src in enumerate(sources):
            with st.expander(
                f"📄 {src.get('document', '?')} · Page {src.get('page', '?')} · Score {src.get('score', 0):.3f}",
                expanded=(i == 0),
            ):
                st.markdown(f'<div class="source-card">{src.get("text", "")}</div>', unsafe_allow_html=True)

    if action == "refuse_if_no_evidence":
        st.info("Try uploading a new PDF using the sidebar, then ask again.")
else:
    if not st.session_state.indexed_file:
        st.divider()
        st.info("👈 Start by uploading a PDF using the sidebar on the left.")
    else:
        st.divider()
        st.info(f"✅ {st.session_state.indexed_file} is ready. Click a quick prompt or type a question above.")

st.divider()
st.caption(f"Session `{st.session_state.session_id[:8]}` · Backend `{BACKEND_URL or 'local'}` · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
