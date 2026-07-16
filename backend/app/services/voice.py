import whisper
import tempfile
import os
from gtts import gTTS

# Load Whisper model once at startup — "base" is fast and accurate enough
# Options: tiny, base, small, medium, large (larger = more accurate but slower)
model = whisper.load_model("base")

def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Takes raw audio bytes, saves to a temp file,
    runs Whisper on it, returns transcribed text + detected language.
    """
    # Save audio bytes to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Whisper transcribes and also detects the language automatically
        result = model.transcribe(tmp_path)
        return {
            "text": result["text"].strip(),
            "language": result["language"]  # returns "hi", "kn", "en" etc.
        }
    finally:
        # Always clean up the temp file
        os.unlink(tmp_path)


def text_to_speech(text: str, language: str = "en") -> bytes:
    """
    Converts text to speech using gTTS.
    Returns audio as bytes so FastAPI can send it back to the browser.
    """
    # Map Whisper language codes to gTTS language codes
    lang_map = {
        "hi": "hi",   # Hindi
        "kn": "kn",   # Kannada
        "en": "en",   # English
    }
    lang = lang_map.get(language, "en")

    tts = gTTS(text=text, lang=lang, slow=False)

    # Save to temp file, read bytes, delete
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tts.save(tmp.name)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)