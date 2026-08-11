# VaidyaAI 🧬

> AI-powered multilingual medical triage assistant for Indian clinics

VaidyaAI helps patients describe symptoms, get instant triage assessments, and understand medical reports — in English, Hindi, or Kannada.

![VaidyaAI](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![React](https://img.shields.io/badge/React-18-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)

---

## Features

- 🎙️ **Voice Input** — Speak symptoms in English, Hindi, or Kannada (Whisper STT via Groq)
- 🤖 **AI Triage Agent** — LangChain + Groq LLM assesses urgency and recommends specialists
- 📚 **RAG Medical Knowledge** — FAISS vector search over a curated symptom knowledge base
- 📄 **Medical Report Analyser** — Upload blood reports/PDFs, get simple explanations
- 🗣️ **Text-to-Speech** — Agent responses spoken aloud in patient's language
- 🏥 **Doctor Dashboard** — Patient queue with risk levels and full conversation history
- 🗄️ **Persistent sessions** — Conversations stored in Postgres (SQLite by default locally)

### Triage safety model

The LLM produces a structured assessment, and a deterministic keyword check runs
alongside it purely as a safety net — if it detects emergency symptoms the model
may have understated, an emergency banner is prepended to the reply. It never
appends a competing risk level, so a response can't show two different verdicts.
A session's stored risk level only ever escalates, never downgrades.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, React Router, React Markdown |
| Backend | FastAPI, Python 3.10+ |
| AI Agent | LangChain, Groq (Llama 3.3 70B) |
| RAG | FAISS, HuggingFace Embeddings |
| Voice | OpenAI Whisper (STT), gTTS (TTS) |
| Database | PostgreSQL, SQLAlchemy |
| PDF | PyMuPDF |

---

## Project Structure

VaidyaAI/
├── backend/
│   ├── app/
│   │   ├── agent/          # LangChain triage agent
│   │   ├── api/            # FastAPI routes
│   │   ├── models/         # PostgreSQL models
│   │   ├── rag/            # FAISS RAG pipeline
│   │   ├── services/       # Voice, report analyzer
│   │   └── utils/          # Config, helpers
│   └── data/
│       ├── medical_docs/   # Medical knowledge base
│       └── faiss_index/    # Vector index
└── frontend/
└── src/
├── components/     # DnaLogo, Sidebar
├── pages/          # PatientPage, DoctorPage
└── services/       # API client

---

## Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Add to .env
GROQ_API_KEY=your_key
DATABASE_URL=postgresql://postgres:password@localhost:5432/vaidyaai

uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

---

## Screenshots

### Patient Interface
- Home screen with symptom suggestions
- Voice input with live transcription
- Structured AI responses with risk assessment

### Doctor Dashboard  
- Patient queue sorted by risk level
- Full conversation history per session
- Risk analytics overview

---

## Built By

**Dhruv** — Final Year AI & Data Science, CMRIT Bangalore  
GitHub: [@dhruvWorkss](https://github.com/dhruvWorkss)

