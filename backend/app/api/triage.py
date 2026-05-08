from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.voice import transcribe_audio, text_to_speech
from app.agent.triage_agent import run_triage_agent
from app.services.report_analyzer import analyze_report
from app.models.database import get_db
from app.models.session_model import TriageSession, Message

router = APIRouter()


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
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Get or create session in database
    session = db.query(TriageSession).filter(
        TriageSession.id == request.session_id
    ).first()

    if not session:
        session = TriageSession(
            id=request.session_id,
            language=request.language
        )
        db.add(session)
        db.commit()

    # Get conversation history from database
    messages = db.query(Message).filter(
        Message.session_id == request.session_id
    ).order_by(Message.created_at).all()

    history = [{"role": m.role, "content": m.content} for m in messages]

    # Run agent
    response = run_triage_agent(request.message, history)

    # Save user message to database
    user_msg = Message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)

    # Save assistant message to database
    assistant_msg = Message(
        session_id=request.session_id,
        role="assistant",
        content=response
    )
    db.add(assistant_msg)

    # Update session risk level if mentioned
    if "EMERGENCY" in response:
        session.risk_level = "emergency"
    elif "HIGH RISK" in response:
        session.risk_level = "high"
    elif "MEDIUM RISK" in response:
        session.risk_level = "medium"
    elif "LOW RISK" in response:
        session.risk_level = "low"

    session.updated_at = datetime.utcnow()
    db.commit()

    return {
        "response": response,
        "session_id": request.session_id,
        "history_length": len(history) + 2
    }


@router.get("/sessions")
def get_all_sessions(db: Session = Depends(get_db)):
    """Get all triage sessions — used by doctor dashboard."""
    sessions = db.query(TriageSession).order_by(
        TriageSession.updated_at.desc()
    ).all()

    return [
        {
            "id": s.id,
            "language": s.language,
            "risk_level": s.risk_level,
            "message_count": len(s.messages),
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "last_message": s.messages[-1].content[:100] if s.messages else ""
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get full conversation for a session."""
    session = db.query(TriageSession).filter(
        TriageSession.id == session_id
    ).first()

    if not session:
        return {"error": "Session not found"}

    return {
        "id": session.id,
        "language": session.language,
        "risk_level": session.risk_level,
        "created_at": session.created_at.isoformat(),
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in session.messages
        ]
    }


@router.delete("/session/{session_id}")
def clear_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(TriageSession).filter(
        TriageSession.id == session_id
    ).first()
    if session:
        db.delete(session)
        db.commit()
    return {"status": "session cleared"}


@router.post("/analyze-report")
async def analyze_medical_report(
    file: UploadFile = File(...),
    language: str = "en"
):
    file_bytes = await file.read()
    result = analyze_report(file_bytes, file.filename, language)
    return {
        "analysis": result,
        "filename": file.filename,
        "language": language
    }