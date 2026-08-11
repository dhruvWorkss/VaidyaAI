from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.utils.config import GROQ_API_KEY, GROQ_MODEL
from app.rag.medical_rag import retrieve_medical_context

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=GROQ_MODEL,
    temperature=0.3
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

After hearing symptoms, always respond in this structured format:

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


def run_triage_agent(user_message: str, chat_history: list = None) -> dict:
    """
    Runs one turn of triage. Returns the assistant reply plus the structured
    risk level and specialist, so the caller can persist them.
    """
    chat_history = chat_history or []
    medical_context = retrieve_medical_context(user_message)

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

    response = llm.invoke(messages)
    ai_response = response.content

    symptom_keywords = ["pain", "fever", "cough", "vomit", "headache",
                       "breath", "dizzy", "rash", "bleed", "chest"]
    mentions_symptoms = any(kw in user_message.lower() for kw in symptom_keywords)

    risk_level = assess_risk(user_message) if mentions_symptoms else None
    specialist = recommend_specialist(user_message) if mentions_symptoms else None

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