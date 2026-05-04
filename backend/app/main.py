from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import triage
from app.utils.config import GROQ_API_KEY, APP_ENV

app = FastAPI(
    title="VaidyaAI",
    description="AI-powered multilingual patient triage system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage.router, prefix="/api/triage", tags=["Triage"])

@app.get("/")
def root():
    return {
        "status": "VaidyaAI backend is running",
        "env": APP_ENV,
        "groq_key_loaded": bool(GROQ_API_KEY)
    }