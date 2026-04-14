import os
import uuid
import streamlit as st
import fitz  # PyMuPDF
import httpx
from groq import Groq
import re
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Student Research Agent", 
    page_icon="🎓", 
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.block-container {padding-top:1.5rem}
.action-badge {
    display:inline-block; padding:4px 14px; border-radius:12px; 
    font-size:.8rem; font-weight:700; text-transform:uppercase; 
    margin-bottom:.8rem; margin-right:8px;
}
.badge-answer {background:#dbeafe; color:#1e40af}
.badge-summarize {background:#dcfce7; color:#166534}
.badge-explain {background:#fef9c3; color:#854d0e}
.badge-quiz {background:#ede9fe; color:#5b21b6}
.badge-viva {background:#fce7f3; color:#9d174d}
.badge-clarify {background:#f1f5f9; color:#475569}
.badge-refuse {background:#fee2e2; color:#991b1b}
.answer-box {
    background:#1e293b; border:1px solid #334155; border-radius:10px; 
    padding:1.4rem 1.6rem; margin:.8rem 0; line-height:1.8; 
    font-size:1rem; color:#e2e8f0
}
.source-card {
    border-left:4px solid #6366f1; padding:.7rem 1rem; margin:.5rem 0; 
    background:#0f172a; border-radius:0 8px 8px 0; font-size:.85rem; 
    color:#cbd5e1
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "session_id" not in st.session_state: 
    st.session_state.session_id = str(uuid.uuid4())
if "history" not in st.session_state: 
    st.session_state.history = []
if "last_response" not in st.session_state: 
    st.session_state.last_response = None
if "document_text" not in st.session_state: 
    st.session_state.document_text = ""
if "indexed_file" not in st.session_state: 
    st.session_state.indexed_file = None
if "upload_key" not in st.session_state: 
    st.session_state.upload_key = 0
if "pages_data" not in st.session_state: 
    st.session_state.pages_data = []

# Groq client
@st.cache_resource
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("❌ Add GROQ_API_KEY to Streamlit Secrets!")
        return None
    return Groq(api_key=api_key)

client = get_groq_client()

def extract_pdf_text(uploaded_file):
    """Extract text from PDF with page numbers"""
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        pages_data = []
        full_text = ""
        
        for i, page in enumerate(doc):
            text = page.get_text()
            pages_data.append({
                "page": i + 1,
                "text": text,
                "text_preview": text[:200] + "..." if len(text) > 200 else text
            })
            full_text += f"\n--- Page {i+1} ---\n{text}\n"
        
        doc.close()
        return full_text, pages_data, len(pages_data)
    except Exception as e:
        return None, [], 0, f"PDF error: {str(e)}"

def simple_search(query, pages_data):
    """Simple keyword search across pages"""
    results = []
    query_lower = query.lower()
    
    for page_data in pages_data:
        score = len(re.findall(query_lower, page_data["text"].lower()))
        if score > 0:
            results.append({
                "page": page_data["page"],
                "text": page_data["text_preview"],
                "score": score
            })
    
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]

def generate_response(query, mode, document_text, pages_data):
    """Generate AI response based on mode"""
    context = document_text[:8000]  # Limit context size
    
    if not document_text:
        return "refuse_if_no_evidence", "No document loaded. Please upload a PDF first.", []
    
    relevant_pages = simple_search(query, pages_data)
    page_context = "\n".join([f"Page {p['page']}: {p['text']}" for p in relevant_pages])
    
    mode_prompts = {
        "answer": f"Answer this question using ONLY the document context:\n\n{page_context}\n\nQ: {query}",
        "summarize": f"Summarize the key points from this document:\n\n{context}",
        "explain": f"Explain these concepts simply for a student:\n\n{page_context}\n\nQ: {query}",
        "quiz": f"Generate 3-5 quiz questions with answers based on this document:\n\n{context}",
        "viva": f"Generate 3-5 viva/oral exam questions based on this document:\n\n{context}",
        "auto": f"Answer this question using the document: {query}\n\nContext: {page_context}"
    }
    
    prompt = mode_prompts.get(mode, mode_prompts["auto"])
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        
        answer = response.choices[0].message.content
        sources = relevant_pages
        
        # Determine action
        action_map = {
            "answer": "answer_question", "summarize": "summarize",
            "explain": "explain_simply", "quiz": "generate_quiz",
            "viva": "generate_viva"
        }
        action = action_map.get(mode, "answer_question")
        
        return action, answer, sources
    
    except Exception as e:
        return "refuse_if_no_evidence", f"AI error: {str(e)}", []

def get_badge(action):
    """Generate action badge HTML"""
    badges = {
        "answer_question": ("Answer", "answer"),
        "summarize": ("Summary", "summarize"),
        "explain_simply": ("Simplified", "explain"),
        "generate_quiz": ("Quiz", "quiz"),
        "generate_viva": ("Viva", "viva"),
        "refuse_if_no_evidence": ("No Evidence", "refuse")
    }
    label, css = badges.get(action, (action.replace("_", " ").title(), "clarify"))
    return f'<span class="action-badge badge-{css}">{label}</span>'

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Research Agent")
    
    # PDF Upload
    st.markdown("### 📄 Upload PDF")
    uploaded = st.file_uploader(
        "Choose a PDF", 
        type=["pdf"],
        key=f"uploader_{st.session_state.upload_key}"
    )
    
    if uploaded is not None:
        with st.spinner(f"Indexing {uploaded.name}..."):
            document_text, pages_data, num_pages = extract_pdf_text(uploaded)
            
            if document_text:
                st.session_state.document_text = document_text
                st.session_state.pages_data = pages_data
                st.session_state.indexed_file = uploaded.name
                st.session_state.last_response = None
                st.session_state.history = []
                st.session_state.upload_key += 1
                
                st.success(
                    f"✅ **{uploaded.name}**\\n"
                    f"📖 {num_pages} pages indexed\\n"
                    f"💾 Ready for questions!"
                )
                st.rerun()
            else:
                st.error("❌ Failed to process PDF")
    
    # Status
    if st.session_state.indexed_file:
        st.info(f"📄 **Active:** `{st.session_state.indexed_file}`")
        if st.button("🗑️ New PDF", use_container_width=True):
            for key in ["document_text", "indexed_file", "pages_data", "history", "last_response"]:
                st.session_state[key] = "" if key != "upload_key" else st.session_state.upload_key + 1
            st.rerun()
    
    st.divider()
    
    # Recent history
    if st.session_state.history:
        st.markdown("### 🕐 Recent Queries")
        for item in reversed(st.session_state.history[-5:]):
            st.markdown(f"• **{item['action'].replace('_',' ').title()}**: {item['query'][:60]}...")
        
        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.last_response = None
            st.rerun()

# ── MAIN CONTENT ───────────────────────────────────────────────────────────────
st.markdown("# 🎓 Student Research Agent")
st.markdown("**Upload PDF → Ask questions → Get grounded answers with sources**")

MODE_OPTIONS = {
    "🤖 Auto": "auto",
    "❓ Answer": "answer", 
    "📋 Summarize": "summarize",
    "🧩 Explain": "explain",
    "📝 Quiz": "quiz",
    "🎤 Viva": "viva"
}

col1, col2 = st.columns([3, 1])
with col1:
    selected_label = st.radio(
        "Choose task:", 
        list(MODE_OPTIONS.keys()), 
        horizontal=True, 
        label_visibility="collapsed"
    )
with col2:
    st.markdown("**Mode**")

selected_mode = MODE_OPTIONS[selected_label]

st.divider()

# Quick prompts
st.markdown("**🔥 Quick prompts — click to ask instantly:**")
QUICK_PROMPTS = {
    "auto": ["What's this about?", "Main findings?", "Key concepts?"],
    "answer": ["Main hypothesis?", "Methods used?", "Conclusions?"],
    "summarize": ["Full summary", "Key findings", "Conclusions only"],
    "explain": ["Explain simply", "Beginner level", "Break down concepts"],
    "quiz": ["5 quiz questions", "MCQ test", "Practice questions"],
    "viva": ["Viva questions", "Examiner asks", "Oral exam prep"]
}

cols = st.columns(3)
for i, prompt in enumerate(QUICK_PROMPTS.get(selected_mode, QUICK_PROMPTS["auto"])):
    with cols[i % 3]:
        if st.button(prompt, key=f"quick_{selected_mode}_{i}", use_container_width=True):
            if st.session_state.document_text:
                action, answer, sources = generate_response(prompt, selected_mode, 
                                                          st.session_state.document_text, 
                                                          st.session_state.pages_data)
                st.session_state.last_response = {
                    "action": action, "answer": answer, "sources": sources,
                    "confidence": "high" if sources else "medium", "success": True
                }
                st.session_state.history.append({"query": prompt, "action": action})
                st.rerun()

st.divider()

# Custom query
st.markdown("**💭 Or type your own question:**")
query = st.text_area(
    "Your question", 
    height=80,
    placeholder="e.g. 'What are the main findings?' or 'Generate 5 quiz questions'",
    label_visibility="collapsed"
)

col1, col2 = st.columns([3, 1])
with col1:
    if st.button("🚀 Ask Agent", type="primary", use_container_width=True, 
                disabled=not query.strip() or not st.session_state.document_text):
        with st.spinner("Agent thinking..."):
            action, answer, sources = generate_response(
                query, selected_mode, 
                st.session_state.document_text, 
                st.session_state.pages_data
            )
            st.session_state.last_response = {
                "action": action, "answer": answer, "sources": sources,
                "confidence": "high" if sources else "medium", "success": True
            }
            st.session_state.history.append({"query": query.strip(), "action": action})
            st.rerun()

with col2:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.last_response = None
        st.rerun()

# ── RESPONSE DISPLAY ───────────────────────────────────────────────────────────
if st.session_state.last_response:
    resp = st.session_state.last_response
    st.divider()
    
    st.markdown("### 🤖 Agent Response")
    col_b, col_c = st.columns([2, 1])
    with col_b:
        st.markdown(get_badge(resp["action"]), unsafe_allow_html=True)
    with col_c:
        conf_icons = {"high": "🟢 HIGH", "medium": "🟡 MEDIUM", "low": "🔴 LOW"}
        st.markdown(f"**Confidence:** {conf_icons.get(resp.get('confidence', 'low'), '⚪')}")

    if resp["answer"]:
        st.markdown(f'<div class="answer-box">{resp["answer"]}</div>', unsafe_allow_html=True)

    if resp["sources"]:
        st.markdown(f"### 📚 Sources ({len(resp['sources'])} pages)")
        for i, src in enumerate(resp["sources"]):
            with st.expander(
                f"📄 Page {src['page']} · Score {src['score']}", 
                expanded=(i == 0)
            ):
                st.markdown(f'<div class="source-card">{src["text"]}</div>', unsafe_allow_html=True)

    if resp["action"] == "refuse_if_no_evidence":
        st.warning("💡 Upload a PDF first using the sidebar!")
else:
    if not st.session_state.indexed_file:
        st.info("👈 **Step 1:** Upload PDF using sidebar")
    else:
        st.info("✅ **Ready!** Click a quick prompt or type your question above.")

st.divider()
st.caption(f"Session `{st.session_state.session_id[:8]}` · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
