from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.utils.config import GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK_MODEL
from app.rag.medical_rag import retrieve_medical_context
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
    """
    Deterministic keyword triage. Returns a normalised level —
    "emergency" | "high" | "medium" | "low" — matching the doctor dashboard.
    """
    emergency_keywords = ["chest pain", "difficulty breathing", "unconscious",
                         "stroke", "heart attack", "seizure", "severe bleeding"]
    high_keywords = ["high fever", "vomiting blood", "severe pain",
                    "difficulty swallowing", "confusion"]
    medium_keywords = ["fever", "vomiting", "dizziness", "moderate pain",
                      "persistent cough"]

    symptoms_lower = symptoms.lower()

    if any(kw in symptoms_lower for kw in emergency_keywords):
        return "emergency"
    elif any(kw in symptoms_lower for kw in high_keywords):
        return "high"
    elif any(kw in symptoms_lower for kw in medium_keywords):
        return "medium"
    else:
        return "low"


def recommend_specialist(symptoms: str) -> str:
    symptoms_lower = symptoms.lower()

    if any(kw in symptoms_lower for kw in ["chest", "heart", "palpitation"]):
        return "Cardiologist (heart specialist)"
    elif any(kw in symptoms_lower for kw in ["breathe", "lung", "cough", "asthma"]):
        return "Pulmonologist (lung specialist)"
    elif any(kw in symptoms_lower for kw in ["stomach", "vomit", "diarrhea", "abdomen"]):
        return "Gastroenterologist (digestive specialist)"
    elif any(kw in symptoms_lower for kw in ["headache", "seizure", "memory", "dizzy"]):
        return "Neurologist (brain and nerve specialist)"
    elif any(kw in symptoms_lower for kw in ["skin", "rash", "itch"]):
        return "Dermatologist (skin specialist)"
    else:
        return "General Physician for initial evaluation"


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

**Risk Level:** 🟢 Low / 🟡 Medium / 🔴 High / 🚨 Emergency

**What You Should Do**
Clear next steps for the patient.

**Recommended Specialist**
Which type of doctor to see.

---
*This is not a diagnosis. Always consult a qualified doctor.*

Rules:
- Never ask more than ONE follow-up question
- After 1 patient message with symptoms, give a full structured assessment
- Use simple words — no complex medical jargon
- Respond in the same language the patient uses (Hindi, Kannada, or English)
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


def build_safe_fallback(risk_level: str | None, specialist: str | None) -> str:
    """Provide conservative guidance when hosted AI services are unavailable."""
    labels = {
        "low": "🟢 Low",
        "medium": "🟡 Medium",
        "high": "🔴 High",
        "emergency": "🚨 Emergency",
    }

    if risk_level == "emergency":
        action = (
            "Call your local emergency number or go to the nearest emergency "
            "department now. Do not drive yourself if you feel faint or very unwell."
        )
    elif risk_level == "high":
        action = (
            "Please arrange urgent medical assessment today. If symptoms worsen, "
            "seek emergency care immediately."
        )
    elif risk_level == "medium":
        action = (
            "Rest, stay hydrated if you can, and arrange a medical consultation "
            "soon—especially if symptoms persist or worsen."
        )
    else:
        action = (
            "Monitor your symptoms, rest, and stay hydrated. Consult a clinician "
            "if the problem persists, worsens, or worries you."
        )

    risk_text = labels.get(risk_level, "Not yet assessed")
    specialist_text = specialist or "General Physician for initial evaluation"

    return f"""**Assessment**
I can provide basic safety guidance, but the detailed AI assessment is temporarily limited.

**Risk Level:** {risk_text}

**What You Should Do**
{action}

**Recommended Specialist**
{specialist_text}

---
*This is not a diagnosis. Always consult a qualified doctor.*"""


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

    symptom_keywords = ["pain", "fever", "cough", "vomit", "headache",
                       "breath", "dizzy", "rash", "bleed", "chest"]
    mentions_symptoms = any(kw in user_message.lower() for kw in symptom_keywords)
    risk_level = assess_risk(user_message) if mentions_symptoms else None
    specialist = recommend_specialist(user_message) if mentions_symptoms else None

    try:
        medical_context = retrieve_medical_context(user_message)
    except Exception:
        logger.exception("Medical context retrieval failed; continuing without RAG")
        medical_context = "No specific medical context is currently available."

    system_prompt = f"""{SYSTEM_PROMPT}

Use the following medical knowledge to inform your response:
---MEDICAL CONTEXT---
{medical_context}
---END CONTEXT---"""

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
            ai_response = build_safe_fallback(risk_level, specialist)

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
