from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3")
APP_ENV = os.getenv("APP_ENV", "development")

# Falls back to a local SQLite file so the app runs without a Postgres instance.
# Uses `or` rather than a getenv default because hosting dashboards commonly
# leave the variable defined but empty, which would otherwise reach create_engine
# as "" and fail at import.
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./vaidyaai.db"

# Managed Postgres providers still hand out legacy "postgres://" URLs, which
# SQLAlchemy 2.x refuses to parse.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing — set it in .env or the host's environment")
