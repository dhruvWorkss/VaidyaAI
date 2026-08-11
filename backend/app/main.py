from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import triage
from app.models.database import create_tables
from app.utils.config import GROQ_API_KEY, APP_ENV
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates the sessions/messages tables if they don't exist yet, so a fresh
    # database works on first boot without a manual migration step.
    create_tables()
    yield


app = FastAPI(
    title="VaidyaAI",
    description="AI-powered multilingual patient triage system",
    version="1.0.0",
    lifespan=lifespan,
)

# Comma-separated list, e.g. "https://vaidya-ai-lovat.vercel.app,http://localhost:3000"
allowed_origins = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage.router, prefix="/api/triage", tags=["Triage"])


@app.get("/")
def root():
    return {
        "status": "VaidyaAI backend is running",
        "env": APP_ENV,
        "groq_key_loaded": bool(GROQ_API_KEY),
    }
