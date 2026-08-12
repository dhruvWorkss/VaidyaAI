# VaidyaAI 🧬

> AI-powered multilingual medical triage assistant for Indian clinics

VaidyaAI helps patients describe symptoms, get instant triage assessments, and understand medical reports — in English, Hindi, or Kannada.

**🌐 [Live demo](https://vaidya-ai-lovat.vercel.app)** · [API](https://vaidyaai-api.onrender.com)

![VaidyaAI](https://img.shields.io/badge/Status-Live-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11-blue) ![React](https://img.shields.io/badge/React-18-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

> The API runs on a free instance that sleeps after 15 minutes idle, so the first
> reply after a quiet period takes ~50 seconds. Replies after that are fast.

---

## Features

- 🎙️ **Voice Input** — Speak symptoms in English, Hindi, or Kannada (Whisper via Groq)
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

Conversation history is rebuilt from the database on every turn rather than held
in memory, so context survives a restart and stays consistent across workers.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, React Router, React Markdown |
| Backend | FastAPI, Python 3.11 |
| AI Agent | LangChain, Groq (Llama 3.3 70B) |
| RAG | FAISS + fastembed (MiniLM-L6-v2 via ONNX) |
| Voice | Groq Whisper large-v3 (STT), gTTS (TTS) |
| Database | PostgreSQL / SQLite, SQLAlchemy |
| PDF | PyMuPDF |
| Hosting | Vercel (frontend), Render (API) |

Embeddings run through fastembed's ONNX runtime rather than sentence-transformers
so the container doesn't need torch — that's the difference between a ~2 GB image
and a ~250 MB one, which is what makes it deployable on a small free instance.

---

## Project Structure

```
VaidyaAI/
├── backend/
│   ├── app/
│   │   ├── agent/          # LangChain triage agent + risk assessment
│   │   ├── api/            # FastAPI routes
│   │   ├── models/         # SQLAlchemy models, session/message tables
│   │   ├── rag/            # FAISS retrieval pipeline
│   │   ├── services/       # Voice (STT/TTS), report analyser
│   │   └── utils/          # Config
│   ├── data/
│   │   ├── medical_docs/   # Symptom knowledge base (source text)
│   │   └── faiss_index/    # Prebuilt vector index
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/     # DnaLogo, Sidebar
        ├── pages/          # PatientPage, DoctorPage
        └── services/api.js # Single API client
```

---

## API

All routes are prefixed with `/api/triage`.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/chat` | Send a message, get a triage response |
| `POST` | `/transcribe` | Audio → text (auto-detects language) |
| `POST` | `/speak` | Text → speech audio |
| `POST` | `/analyze-report` | Upload a PDF/text report, get a plain-language explanation |
| `GET` | `/sessions` | All sessions with risk level and message count |
| `GET` | `/sessions/{id}` | One session with its full conversation |
| `DELETE` | `/session/{id}` | Delete a session |

```bash
curl -X POST https://vaidyaai-api.onrender.com/api/triage/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"I have chest pain","session_id":"demo","language":"en"}'
```

---

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows

pip install -r requirements.txt

cp .env.example .env          # then add your GROQ_API_KEY

uvicorn app.main:app --reload
```

Runs at `http://localhost:8000`. Only `GROQ_API_KEY` is required — without
`DATABASE_URL` it falls back to a local SQLite file, and tables are created on
first boot.

### Frontend

```bash
cd frontend
npm install
npm start
```

Runs at `http://localhost:3000` and talks to `localhost:8000` by default.

### Environment variables

| Variable | Required | Default |
|---|---|---|
| `GROQ_API_KEY` | **yes** | — |
| `GROQ_MODEL` | no | `llama-3.3-70b-versatile` |
| `WHISPER_MODEL` | no | `whisper-large-v3` |
| `DATABASE_URL` | no | local SQLite file |
| `ALLOWED_ORIGINS` | no | `localhost:3000,localhost:5173` |
| `REACT_APP_API_URL` | frontend, in production | `http://localhost:8000/api` |

`REACT_APP_API_URL` must include the `/api` suffix, and Create React App bakes it
in at build time — changing it requires a rebuild, not just a restart.

---

## Deployment

The backend ships as a container; `backend/Dockerfile` works on Render, Railway or
Fly without changes and reads `$PORT` from the host. Set `GROQ_API_KEY` and
`ALLOWED_ORIGINS` (your frontend's origin) in the host's environment.

The frontend is a static CRA build — point the host at `frontend/` and set
`REACT_APP_API_URL` to the deployed API base.

---

## Disclaimer

VaidyaAI provides triage guidance only. It is not a diagnosis and does not replace
a qualified doctor. Every response carries this disclaimer, and emergency symptoms
are flagged for immediate medical attention.
