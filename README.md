# 🎓 Student Research Agent

A production AI agent that processes academic PDFs and answers questions,
generates summaries, simplified explanations, quizzes, and viva questions —
grounded entirely in your uploaded documents.

## Quick Start (3 steps)

### Step 1 — Setup
```bash
cd student-research-agent
python -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your Hugging Face token:
```
HF_API_TOKEN=hf_your_token_here
```
Get a free token at: https://huggingface.co/settings/tokens

### Step 2 — Run backend (Terminal 1)
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3 — Run frontend (Terminal 2)
```bash
streamlit run frontend/app.py
```

Open http://localhost:8501 in your browser.

## Deploy

### Backend → Render
- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Add all `.env` variables in Render dashboard

### Frontend → Streamlit Cloud
- Main file: `frontend/app.py`
- Add secret: `BACKEND_URL = "https://your-render-url.onrender.com"`

## What it does

| Mode | Example |
|---|---|
| Answer | "What is the main hypothesis?" |
| Summarise | "Give me a summary" |
| Explain | "Explain this for a beginner" |
| Quiz | "Generate 5 quiz questions" |
| Viva | "Create viva questions" |

## Stack
FastAPI · FAISS · sentence-transformers · Hugging Face · Streamlit
