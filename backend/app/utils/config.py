from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3")
APP_ENV = os.getenv("APP_ENV", "development")

# Falls back to a local SQLite file so the app runs without a Postgres instance.
# Production sets DATABASE_URL to the managed Postgres connection string.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vaidyaai.db")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing — set it in .env or the host's environment")
