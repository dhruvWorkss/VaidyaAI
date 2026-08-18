from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.utils.config import GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK_MODEL
from app.rag.medical_rag import retrieve_medical_context
from app.agent.triage_rules import (
    build_fallback_response,
    build_intake_response,
    evaluate_triage,
    missing_details,
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


SYSTEM_PROMPT = """You are VaidyaAI, a careful, conversational medical guidance assistant.

Conversation style:
- For greetings, thanks, and casual conversation, reply naturally and warmly in 1-2 sentences
- When a user only greets you, welcome them and ask how they are feeling today or whether they want guidance about a health issue
- Do not say that the user has failed to provide symptoms or is "reaching out for help"
- Only use the structured medical format below after the user describes symptoms or asks a health question

After enough essential information is available, respond in this format:

**Assessment**
Summarize what the person reported, what is reassuring or concerning, and the limits of a chat assessment. Do not use filler such as "based on the information provided."

**What It Could Be**
- Give 2–4 plausible categories from common to important, each with a short reason tied to the reported details
- Say "could" or "may"; never present a diagnosis as certain

**What To Do Now**
Give practical next steps appropriate to the urgency. Avoid medication doses and avoid treatment that depends on an unconfirmed diagnosis.

**Get Urgent Help Now If**
List the specific warning signs relevant to this symptom. Do not merely say "if warning signs appear."

**Who To Contact**
Recommend the most appropriate first point of care.

**Risk Level:** 🟢 Low / 🟡 Medium / 🔴 High / 🚨 Emergency — add one short reason

---
*This is not a diagnosis. Always consult a qualified doctor.*

Rules:
- The application handles follow-up collection before calling you; do not ask another routine question in a completed assessment
- Use all conversation history, not only the latest sentence
- Directly acknowledge the latest detail in natural language
- Distinguish common possibilities from dangerous possibilities without creating false reassurance or alarm
- Do not delay explicit emergency advice to ask questions
- Use simple words — no complex medical jargon
- Respond in the same language the patient uses (Hindi, Kannada, or English)
- Treat risk as provisional when essential red-flag information is missing
- Recommend a General Physician or urgent-care clinician first unless symptoms clearly point to a specialist
- Never let a possible diagnosis override explicit emergency warning signs
- Always place Risk Level at the end of the assessment, immediately before the disclaimer
- If emergency symptoms are detected, put immediate action at the top
- Never claim that reflux, gas, anxiety, or muscle strain is the cause of chest pain; describe these only as possibilities when the pattern fits"""


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
    conversation_start = 0
    for index in range(len(chat_history) - 1, -1, -1):
        msg = chat_history[index]
        if msg["role"] == "assistant" and (
            "**Assessment**" in msg["content"]
            or "🚨 **EMERGENCY" in msg["content"]
        ):
            conversation_start = index + 1
            break
    recent_history = chat_history[conversation_start:]
    prior_user_messages = [
        msg["content"]
        for msg in recent_history
        if msg["role"] == "user" and greeting_reply(msg["content"]) is None
    ]
    combined_context = " ".join([*prior_user_messages[-6:], user_message])
    triage = evaluate_triage(combined_context)
    risk_level = triage.risk_level
    specialist = triage.specialist if risk_level else None

    intake_rounds = sum(
        1
        for msg in recent_history
        if msg["role"] == "assistant"
        and (
            "**A few important questions**" in msg["content"]
            or "**One last clarification**" in msg["content"]
        )
    )
    missing = missing_details(combined_context, triage.category)
    if should_ask_follow_up(
        user_message,
        triage,
        prior_user_messages,
        intake_rounds=intake_rounds,
    ):
        return {
            "response": build_intake_response(
                combined_context,
                triage,
                missing=missing,
                round_number=intake_rounds + 1,
            ),
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
- Essential details still unstated: {', '.join(missing) or 'none'}
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
