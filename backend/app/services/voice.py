import tempfile
import os
from groq import Groq
from gtts import gTTS
from app.utils.config import GROQ_API_KEY, WHISPER_MODEL

# Transcription runs on Groq's hosted Whisper rather than a local model.
# Running whisper locally pulled in torch (~2GB) and downloaded weights on first
# request, which made the container too heavy to deploy on a small instance.
client = Groq(api_key=GROQ_API_KEY)


def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Takes raw audio bytes, sends them to Groq's Whisper endpoint,
    returns transcribed text + detected language.
    """
    result = client.audio.transcriptions.create(
        file=("recording.wav", audio_bytes),
        model=WHISPER_MODEL,
        response_format="verbose_json",
    )

    return {
        "text": (result.text or "").strip(),
        # verbose_json reports the detected language, e.g. "hi", "kn", "en"
        "language": getattr(result, "language", "en") or "en",
    }


def text_to_speech(text: str, language: str = "en") -> bytes:
    """
    Converts text to speech using gTTS.
    Returns audio as bytes so FastAPI can send it back to the browser.
    """
    # Whisper sometimes reports full names ("hindi") rather than codes ("hi"),
    # so both spellings map to the same gTTS code.
    lang_map = {
        "hi": "hi", "hindi": "hi",
        "kn": "kn", "kannada": "kn",
        "en": "en", "english": "en",
    }
    lang = lang_map.get((language or "en").lower(), "en")

    tts = gTTS(text=text, lang=lang, slow=False)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tts.save(tmp.name)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)
