from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.utils.config import GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK_MODEL
from app.rag.medical_rag import retrieve_medical_context
from app.agent.triage_rules import (
    build_fallback_response,
    build_intake_response,
    evaluate_triage,
    should_ask_follow_up,
)
import logging
import re

logger = logging.getLogger(__name__)

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=GROQ_MODEL,
    temperature=0.3
)

fallback_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=GROQ_FALLBACK_MODEL,
    temperature=0.2,
)


def assess_risk(symptoms: str) -> str:
    """Compatibility wrapper around the shared triage framework."""
    return evaluate_triage(symptoms).risk_level or "low"


def recommend_specialist(symptoms: str) -> str:
    """Compatibility wrapper returning a conservative first point of care."""
    return evaluate_triage(symptoms).specialist


SYSTEM_PROMPT = """You are VaidyaAI, a knowledgeable and empathetic AI medical triage assistant.

Conversation style:
- For greetings, thanks, and casual conversation, reply naturally and warmly in 1-2 sentences
- When a user only greets you, welcome them and ask how they are feeling today or whether they want guidance about a health issue
- Do not say that the user has failed to provide symptoms or is "reaching out for help"
- Only use the structured medical format below after the user describes symptoms or asks a health question

After hearing symptoms or a health concern, respond in this structured format:

**Assessment**
Brief summary of what the symptoms suggest.

**Possible Conditions**
- Condition 1 — simple explanation
- Condition 2 — simple explanation

**What You Should Do**
Clear next steps for the patient.

**Recommended Specialist**
Which type of doctor to see.

**Risk Level:** 🟢 Low / 🟡 Medium / 🔴 High / 🚨 Emergency

---
*This is not a diagnosis. Always consult a qualified doctor.*

Rules:
- Ask one compact follow-up round before assessing when duration, severity, measurements, or associated symptoms are missing
- Combine the original symptoms with the follow-up answer before assessing
- After the user answers the intake question, complete the assessment without another routine follow-up round
- Do not delay explicit emergency advice to ask questions
- If the first message already contains enough detail, assess it without unnecessary questioning
- Use simple words — no complex medical jargon
- Respond in the same language the patient uses (Hindi, Kannada, or English)
- Treat risk as provisional when essential red-flag information is missing
- Screen respiratory, cardiac, neurological, digestive, urinary, skin/allergy, eye, injury, pregnancy, mental-health, infection, and general red flags
- Ask exactly one concise safety question relevant to the main symptom category
- Recommend a General Physician or urgent-care clinician first unless symptoms clearly point to a specialist
- Never let a possible diagnosis override explicit emergency warning signs
- Always place Risk Level at the end of the assessment, immediately before the disclaimer
- If emergency symptoms detected, flag immediately at the top"""


GREETING_REPLIES = {
    "en": "Hi! How are you feeling today? Is there any health issue you'd like guidance with?",
    "hi": "नमस्ते! आज आप कैसा महसूस कर रहे हैं? क्या किसी स्वास्थ्य समस्या के बारे में मार्गदर्शन चाहिए?",
    "kn": "ನಮಸ್ಕಾರ! ಇಂದು ನಿಮಗೆ ಹೇಗನಿಸುತ್ತಿದೆ? ಯಾವುದಾದರೂ ಆರೋಗ್ಯ ಸಮಸ್ಯೆಯ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶನ ಬೇಕೇ?",
}


def greeting_reply(message: str) -> str | None:
    """Return an instant, friendly welcome for greeting-only messages."""
    # Strip common sentence punctuation without removing Unicode combining
    # marks, which are part of many Hindi and Kannada characters.
    normalized = message.lower().strip().strip("!.,?।…")
    normalized = re.sub(r"\s+", " ", normalized)

    english_greetings = {
        "hi", "hello", "hey", "hiya", "good morning", "good afternoon",
        "good evening", "how are you", "what's up", "whats up", "sup",
    }
    hindi_greetings = {"नमस्ते", "नमस्कार", "हेलो", "हाय"}
    kannada_greetings = {"ನಮಸ್ಕಾರ", "ಹಲೋ", "ಹಾಯ್"}

    if normalized in hindi_greetings:
        return GREETING_REPLIES["hi"]
    if normalized in kannada_greetings:
        return GREETING_REPLIES["kn"]
    if normalized in english_greetings:
        return GREETING_REPLIES["en"]
    return None


def build_safe_fallback(
    user_message: str,
    risk_level: str | None,
    specialist: str | None,
) -> str:
    """Compatibility wrapper for the provider-independent response builder."""
    triage = evaluate_triage(user_message)
    return build_fallback_response(user_message, triage)


def run_triage_agent(user_message: str, chat_history: list = None) -> dict:
    """
    Runs one turn of triage. Returns the assistant reply plus the structured
    risk level and specialist, so the caller can persist them.
    """
    welcome = greeting_reply(user_message)
    if welcome:
        return {
            "response": welcome,
            "risk_level": None,
            "specialist": None,
        }

    chat_history = chat_history or []
    prior_user_messages = [
        msg["content"]
        for msg in chat_history
        if msg["role"] == "user" and evaluate_triage(msg["content"]).risk_level
    ]
    combined_context = " ".join([*prior_user_messages[-2:], user_message])
    triage = evaluate_triage(combined_context)
    risk_level = triage.risk_level
    specialist = triage.specialist if risk_level else None

    if should_ask_follow_up(user_message, triage, prior_user_messages):
        return {
            "response": build_intake_response(user_message, triage),
            "risk_level": None,
            "specialist": None,
        }

    try:
        medical_context = retrieve_medical_context(combined_context)
    except Exception:
        logger.exception("Medical context retrieval failed; continuing without RAG")
        medical_context = "No specific medical context is currently available."

    system_prompt = f"""{SYSTEM_PROMPT}

Use the following medical knowledge to inform your response:
---MEDICAL CONTEXT---
{medical_context}
---END CONTEXT---

Deterministic safety screen (do not downgrade this urgency):
- Category: {triage.category}
- Provisional risk: {risk_level or 'not assessed'}
- Explicit red flags: {', '.join(triage.matched_red_flags) or 'none stated'}
- Ask this safety question if details are missing: {triage.question}
- First point of care: {triage.specialist}"""

    messages = [SystemMessage(content=system_prompt)]

    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        ai_response = response.content
    except Exception:
        logger.exception("Primary Groq model failed; trying fallback model")
        try:
            response = fallback_llm.invoke(messages)
            ai_response = response.content
        except Exception:
            logger.exception("Fallback Groq model failed; using safe local guidance")
            ai_response = build_fallback_response(user_message, triage)

    # The model already states a risk level inside its structured reply, so the
    # keyword check is used only as a safety net: it prepends a banner when it
    # detects an emergency the model may have understated. Appending a second
    # risk level here would let one reply show two conflicting assessments.
    if risk_level == "emergency":
        ai_response = (
            "🚨 **EMERGENCY — seek immediate medical attention.**\n\n" + ai_response
        )

    return {
        "response": ai_response,
        "risk_level": risk_level,
        "specialist": specialist,
    }
