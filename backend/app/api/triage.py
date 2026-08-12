from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.voice import transcribe_audio, text_to_speech
from app.services.report_analyzer import analyze_report
from app.agent.triage_agent import run_triage_agent
from app.models.database import get_db
from app.models.session_model import TriageSession, Message

router = APIRouter()

# Ordered most severe first, so a session's stored risk only ever escalates.
RISK_ORDER = ["low", "medium", "high", "emergency"]


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    language: str = "en"


def _escalate(current: str | None, incoming: str | None) -> str | None:
    """Keeps the highest risk level seen across a session."""
    if incoming is None:
        return current
    if current is None:
        return incoming
    return max(current, incoming, key=lambda r: RISK_ORDER.index(r)
               if r in RISK_ORDER else -1)


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


@router.post("/analyze-report")
async def analyze_report_route(file: UploadFile = File(...), language: str = "en"):
    """Extracts text from an uploaded report and explains it in plain language."""
    file_bytes = await file.read()
    analysis = analyze_report(file_bytes, file.filename or "report", language)
    return {"analysis": analysis}


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    session = db.get(TriageSession, request.session_id)
    if session is None:
        session = TriageSession(id=request.session_id, language=request.language)
        db.add(session)
        db.flush()

    # Conversation history is rebuilt from the database rather than kept in
    # memory, so context survives a restart and multiple workers stay consistent.
    history = [
        {"role": m.role, "content": m.content}
        for m in sorted(session.messages, key=lambda m: m.id)
    ]

    result = run_triage_agent(request.message, history)

    db.add(Message(session_id=session.id, role="user", content=request.message))
    db.add(Message(session_id=session.id, role="assistant", content=result["response"]))

    session.risk_level = _escalate(session.risk_level, result["risk_level"])
    if result["specialist"]:
        session.specialist = result["specialist"]
    session.language = request.language
    session.updated_at = datetime.utcnow()

    db.commit()

    return {
        "response": result["response"],
        "session_id": session.id,
        "risk_level": session.risk_level,
        "specialist": session.specialist,
        "history_length": len(history) + 2,
    }


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(TriageSession).order_by(TriageSession.updated_at.desc()).all()

    out = []
    for s in sessions:
        msgs = sorted(s.messages, key=lambda m: m.id)
        last_user = next(
            (m.content for m in reversed(msgs) if m.role == "user"), ""
        )
        out.append({
            "id": s.id,
            "language": s.language,
            "risk_level": s.risk_level,
            "specialist": s.specialist,
            "message_count": len(msgs),
            "last_message": last_user,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return out


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(TriageSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "language": session.language,
        "risk_level": session.risk_level,
        "specialist": session.specialist,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in sorted(session.messages, key=lambda m: m.id)
        ],
    }


@router.delete("/session/{session_id}")
def clear_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(TriageSession, session_id)
    if session is not None:
        db.delete(session)
        db.commit()
    return {"status": "session cleared"}
