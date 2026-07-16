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
    emergency_keywords = ["chest pain", "difficulty breathing", "unconscious",
                         "stroke", "heart attack", "seizure", "severe bleeding"]
    high_keywords = ["high fever", "vomiting blood", "severe pain",
                    "difficulty swallowing", "confusion"]
    medium_keywords = ["fever", "vomiting", "dizziness", "moderate pain",
                      "persistent cough"]

    symptoms_lower = symptoms.lower()

    if any(kw in symptoms_lower for kw in emergency_keywords):
        return "🚨 EMERGENCY - Needs immediate medical attention."
    elif any(kw in symptoms_lower for kw in high_keywords):
        return "🔴 HIGH RISK - See a doctor within 2-4 hours."
    elif any(kw in symptoms_lower for kw in medium_keywords):
        return "🟡 MEDIUM RISK - See a doctor within 24 hours."
    else:
        return "🟢 LOW RISK - Rest and monitor symptoms."


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


def run_triage_agent(user_message: str, chat_history: list = []) -> str:
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

    if any(kw in user_message.lower() for kw in symptom_keywords):
        risk = assess_risk(user_message)
        specialist = recommend_specialist(user_message)
        ai_response += f"\n\n📊 **Risk Assessment:** {risk}"
        ai_response += f"\n👨‍⚕️ **Recommended Specialist:** {specialist}"

    return ai_response