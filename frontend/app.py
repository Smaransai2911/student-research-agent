import os, uuid, httpx, streamlit as st

st.set_page_config(page_title="Student Research Agent", page_icon="🎓", layout="wide")

def _get_backend_url():
    try: return st.secrets["BACKEND_URL"]
    except: return os.getenv("BACKEND_URL", "http://localhost:8000")

BACKEND_URL = _get_backend_url()
TIMEOUT = 120

st.markdown("""<style>
.block-container{padding-top:1.5rem}
.action-badge{display:inline-block;padding:4px 14px;border-radius:12px;font-size:.8rem;font-weight:700;text-transform:uppercase;margin-bottom:.8rem}
.badge-answer{background:#dbeafe;color:#1e40af}.badge-summarize{background:#dcfce7;color:#166534}
.badge-explain{background:#fef9c3;color:#854d0e}.badge-quiz{background:#ede9fe;color:#5b21b6}
.badge-viva{background:#fce7f3;color:#9d174d}.badge-clarify{background:#f1f5f9;color:#475569}
.badge-refuse{background:#fee2e2;color:#991b1b}
.answer-box{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:1.4rem 1.6rem;margin:.8rem 0;line-height:1.8;font-size:1rem;color:#e2e8f0}
.source-card{border-left:4px solid #6366f1;padding:.7rem 1rem;margin:.5rem 0;background:#0f172a;border-radius:0 8px 8px 0;font-size:.85rem;color:#cbd5e1}
</style>""", unsafe_allow_html=True)

if "session_id"      not in st.session_state: st.session_state.session_id      = str(uuid.uuid4())
if "history"         not in st.session_state: st.session_state.history         = []
if "last_response"   not in st.session_state: st.session_state.last_response   = None
if "indexed_file"    not in st.session_state: st.session_state.indexed_file    = None
if "upload_key"      not in st.session_state: st.session_state.upload_key      = 0

def get_badge(action):
    m = {"answer_question":("Answer","answer"),"summarize":("Summary","summarize"),
         "explain_simply":("Simplified","explain"),"generate_quiz":("Quiz","quiz"),
         "generate_viva":("Viva","viva"),"ask_clarification":("Clarify","clarify"),
         "refuse_if_no_evidence":("No Evidence","refuse")}
    label, css = m.get(action,(action,"clarify"))
    return f'<span class="action-badge badge-{css}">{label}</span>'

def call(endpoint, method="get", **kwargs):
    url = f"{BACKEND_URL}/{endpoint.lstrip('/')}"
    try:
        if method == "get": r = httpx.get(url, timeout=TIMEOUT)
        elif method == "post_json": r = httpx.post(url, json=kwargs.get("json"), timeout=TIMEOUT)
        elif method == "post_file": r = httpx.post(url, files=kwargs.get("files"), timeout=TIMEOUT)
        else: return None, "Unknown method"
        if r.status_code in (200,201): return r.json(), None
        try: detail = r.json().get("detail", r.text[:200])
        except: detail = r.text[:200]
        return None, f"Error {r.status_code}: {detail}"
    except httpx.ConnectError: return None, f"Cannot connect to backend at {BACKEND_URL}"
    except httpx.TimeoutException: return None, "Timeout — try again in 30 seconds"
    except Exception as e: return None, str(e)

def send_query(query_text, mode):
    if not query_text.strip(): return
    with st.spinner("Agent is thinking…"):
        data, err = call("/query", method="post_json", json={
            "session_id": st.session_state.session_id,
            "query": query_text.strip(),
            "mode": mode,
        })
    if err: st.error(f"Query failed: {err}")
    else:
        st.session_state.last_response = data
        st.session_state.history.append({"query": query_text.strip(), "action": data.get("action","unknown")})
        st.rerun()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Research Agent")
    health_data, err = call("/health")
    if err:
        st.error(f"Backend offline: {err}")
    else:
        chunks = health_data.get("checks",{}).get("vectorstore",{}).get("chunks_indexed",0)
        fname  = st.session_state.indexed_file or "none"
        if chunks > 0:
            st.success(f"✅ Online · **{chunks} chunks** · `{fname}`")
        else:
            st.warning("⚠️ Online · No document indexed yet")
    st.divider()

    st.markdown("### 📄 Upload PDF")
    uploaded = st.file_uploader(
        "Choose a PDF", type=["pdf"],
        key=f"uploader_{st.session_state.upload_key}"
    )

    if uploaded is not None:
        with st.spinner(f"Indexing {uploaded.name}..."):
            file_bytes = uploaded.read()
            data, err  = call("/upload", method="post_file",
                              files={"file": (uploaded.name, file_bytes, "application/pdf")})
        if err:
            st.error(f"Upload failed: {err}")
        else:
            st.session_state.indexed_file  = data.get("filename", uploaded.name)
            st.session_state.last_response = None
            st.session_state.history       = []
            st.session_state.upload_key   += 1
            st.success(
                f"✅ **{data.get('filename')}**\n\n"
                f"{data.get('pages_parsed',0)} pages · {data.get('chunks_created',0)} chunks"
            )
            st.rerun()

    if st.session_state.indexed_file:
        st.info(f"📄 Active: `{st.session_state.indexed_file}`")
        if st.button("Upload different PDF", use_container_width=True):
            st.session_state.indexed_file  = None
            st.session_state.upload_key   += 1
            st.session_state.last_response = None
            st.rerun()

    st.divider()
    if st.session_state.history:
        st.markdown("### 🕐 Recent")
        for item in reversed(st.session_state.history[-5:]):
            st.markdown(f"_{item['action'].replace('_',' ').title()}_ · {item['query'][:45]}")
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.session_state.last_response = None
            st.rerun()

# ── MAIN ──────────────────────────────────────────────────────────────────────
st.markdown("# 🎓 Student Research Agent")
st.markdown("Upload a PDF · Choose a task · Get grounded AI responses")
st.divider()

MODE_OPTIONS = {
    "🤖 Auto":"auto","❓ Answer":"answer","📋 Summarise":"summarize",
    "🧩 Explain simply":"explain","📝 Quiz":"quiz","🎤 Viva":"viva",
}
selected_label = st.radio("Mode", list(MODE_OPTIONS.keys()), horizontal=True, label_visibility="collapsed")
selected_mode  = MODE_OPTIONS[selected_label]

st.divider()

QUICK_PROMPTS = {
    "auto":      ["Summarise this paper","What is the main finding?","Explain the key concepts"],
    "answer":    ["What is the main hypothesis?","What methods were used?","What are the conclusions?"],
    "summarize": ["Give me a full summary","Summarise the conclusions","What are the key findings?"],
    "explain":   ["Explain this simply","What does this mean for a beginner?","Break down the concepts"],
    "quiz":      ["Generate 5 quiz questions","Create MCQ questions","Make a practice test"],
    "viva":      ["Generate viva questions","What would an examiner ask?","Prepare oral exam questions"],
}

st.markdown("**Quick prompts — click to ask instantly:**")
cols = st.columns(3)
for i, prompt in enumerate(QUICK_PROMPTS.get(selected_mode, QUICK_PROMPTS["auto"])):
    with cols[i % 3]:
        if st.button(prompt, key=f"qp_{selected_mode}_{i}", use_container_width=True):
            send_query(prompt, selected_mode)

st.divider()
st.markdown("**Or type your own question:**")
query = st.text_area("Q", height=80,
    placeholder="e.g. 'Summarise this paper' or 'Generate 5 quiz questions'",
    label_visibility="collapsed")

col1, col2 = st.columns([3,1])
with col1:
    if st.button("Ask the Agent →", type="primary", use_container_width=True, disabled=not query.strip()):
        send_query(query, selected_mode)
with col2:
    if st.button("Clear", use_container_width=True):
        st.session_state.last_response = None
        st.rerun()

# ── RESPONSE ──────────────────────────────────────────────────────────────────
if st.session_state.last_response:
    resp       = st.session_state.last_response
    action     = resp.get("action","unknown")
    answer     = resp.get("answer","")
    sources    = resp.get("sources",[])
    confidence = resp.get("confidence","low")
    success    = resp.get("success",False)

    st.divider()
    st.markdown("### 🤖 Agent Response")
    col_b, col_c = st.columns([2,1])
    with col_b: st.markdown(get_badge(action), unsafe_allow_html=True)
    with col_c:
        icons = {"high":"🟢 HIGH","medium":"🟡 MEDIUM","low":"🔴 LOW"}
        st.markdown(f"**Confidence:** {icons.get(confidence,'⚪')}")

    if answer:
        st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)

    if sources:
        st.markdown(f"### 📚 Sources ({len(sources)} chunks)")
        for i, src in enumerate(sources):
            with st.expander(f"📄 {src.get('document','?')} · Page {src.get('page','?')} · Score {src.get('score',0):.3f}", expanded=(i==0)):
                st.markdown(f'<div class="source-card">{src.get("text","")}</div>', unsafe_allow_html=True)

    if action == "refuse_if_no_evidence":
        st.info("💡 Try: upload a new PDF using the sidebar, then ask your question again.")

else:
    if not st.session_state.indexed_file:
        st.divider()
        st.info("👈 **Start by uploading a PDF** using the sidebar on the left.")
    else:
        st.divider()
        st.info(f"✅ **{st.session_state.indexed_file}** is indexed. Click a quick prompt or type a question above.")

st.divider()
st.caption(f"Session `{st.session_state.session_id[:8]}` · Backend `{BACKEND_URL}`")
