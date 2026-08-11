FROM python:3.11-slim

# build-essential is needed to compile a few wheels; ffmpeg is no longer
# required since transcription moved to Groq's hosted Whisper.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway and Render both inject $PORT at runtime — do not hardcode 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
