from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.voice import transcribe_audio, text_to_speech
from app.agent.triage_agent import run_triage_agent

router = APIRouter()

conversation_store = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    language: str = "en"


@router.get("/health")
def health_check():
    return {"status": "triage service is healthy"}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    result = transcribe_audio(audio_bytes)
    return {"text": result["text"], "language": result["language"]}


@router.post("/speak")
async def speak(text: str, language: str = "en"):
    audio_bytes = text_to_speech(text, language)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/chat")
async def chat(request: ChatRequest):
    history = conversation_store.get(request.session_id, [])
    response = run_triage_agent(request.message, history)

    # Update history
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": response})
    conversation_store[request.session_id] = history

    return {
        "response": response,
        "session_id": request.session_id,
        "history_length": len(history)
    }


@router.delete("/session/{session_id}")
def clear_session(session_id: str):
    conversation_store.pop(session_id, None)
    return {"status": "session cleared"}

{
  "message": "I have a severe headache and fever since yesterday",
  "session_id": "test123",
  "language": "en"
}