"""Conservative, provider-independent safety triage rules.

This module does not diagnose. It identifies explicit red flags, selects a
provisional urgency, asks one category-relevant safety question, and recommends
an appropriate first point of care.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TriageResult:
    risk_level: str | None
    category: str
    specialist: str
    question: str
    action: str
    matched_red_flags: tuple[str, ...] = ()
    provisional: bool = True


CATEGORY_TERMS = {
    "mental_health": ("suicid", "self harm", "kill myself", "overdose", "hopeless"),
    "pregnancy": ("pregnan", "fetal", "baby movement", "postpartum"),
    "cardiac": ("chest", "heart", "palpitation", "pressure in my chest"),
    "respiratory": ("breath", "wheez", "asthma", "lung", "cough"),
    "neurological": ("headache", "migraine", "seizure", "weakness", "numb", "dizzy", "confusion"),
    "digestive": ("stomach", "abdomen", "abdominal", "vomit", "diarrhea", "constipation", "nausea"),
    "urinary": ("urine", "urinating", "pee", "kidney", "flank", "burning urination"),
    "skin_allergy": ("rash", "itch", "hives", "skin", "swelling"),
    "eye": ("eye", "vision", "sight"),
    "injury": ("injury", "fell", "fall", "sprain", "fracture", "cut", "burn"),
    "infection": ("fever", "temperature", "chills", "infection"),
}


EMERGENCY_FLAGS = {
    "difficulty breathing": ("difficulty breathing", "can't breathe", "cannot breathe", "gasping"),
    "blue or grey lips": ("blue lips", "grey lips", "gray lips"),
    "chest pain or pressure": ("chest pain", "chest pressure", "crushing chest"),
    "loss of consciousness": ("unconscious", "passed out", "not waking", "fainted and"),
    "stroke-like symptoms": ("face droop", "one sided weakness", "one-sided weakness", "slurred speech"),
    "seizure": ("seizure", "convulsion"),
    "sudden severe headache": ("worst headache", "sudden severe headache", "thunderclap headache"),
    "meningitis warning signs": ("neck stiffness", "non-fading rash", "rash does not fade"),
    "severe bleeding": ("severe bleeding", "bleeding won't stop", "bleeding will not stop"),
    "internal bleeding": ("vomiting blood", "coughing blood", "black tarry stool"),
    "severe allergic reaction": ("swollen tongue", "tongue swelling", "tongue is swelling", "swollen lips", "lips are swelling", "throat closing", "anaphylaxis"),
    "immediate self-harm risk": ("kill myself", "end my life", "suicide plan", "suicidal", "took an overdose", "overdose now"),
    "pregnancy emergency": ("pregnant and heavy bleeding", "pregnant with severe pain", "no fetal movement"),
    "sudden vision loss": ("sudden vision loss", "suddenly can't see", "suddenly cannot see"),
}


HIGH_URGENCY_TERMS = (
    "high fever", "severe pain", "persistent vomiting", "can't keep fluids down",
    "cannot keep fluids down", "blood in stool", "blood in urine", "confusion",
    "difficulty swallowing", "rapidly spreading rash", "dehydrated", "very drowsy",
)

MEDIUM_URGENCY_TERMS = (
    "fever", "vomiting", "diarrhea", "dizziness", "persistent cough",
    "moderate pain", "worsening", "infection", "palpitation", "burning urination",
)

SYMPTOM_TERMS = tuple(
    dict.fromkeys(
        term
        for terms in CATEGORY_TERMS.values()
        for term in terms
    )
) + ("pain", "bleed", "tired", "fatigue", "unwell", "sick")


QUESTIONS = {
    "cardiac": "Is the discomfort severe or accompanied by shortness of breath, sweating, fainting, or pain spreading to your arm, jaw, or back?",
    "respiratory": "Are you short of breath at rest, unable to speak full sentences, or noticing blue or grey lips?",
    "neurological": "Did this start suddenly, or do you have confusion, fainting, seizure, new weakness, numbness, neck stiffness, or trouble speaking?",
    "digestive": "Can you keep fluids down, and is there blood, black stool, severe localised pain, a swollen abdomen, or fainting?",
    "urinary": "Do you also have fever, back or side pain, vomiting, visible blood, difficulty passing urine, or pregnancy?",
    "skin_allergy": "Do you have trouble breathing, swelling of the face, lips or tongue, blistering or peeling skin, fever, or a rapidly spreading rash?",
    "eye": "Was there sudden vision loss, severe eye pain, chemical exposure, injury, or new weakness or trouble speaking?",
    "injury": "Is there heavy bleeding, a visible deformity, loss of feeling, inability to use the area, head injury, or loss of consciousness?",
    "pregnancy": "Is there heavy bleeding, severe abdominal pain, fainting, severe headache, breathing difficulty, or reduced fetal movement?",
    "mental_health": "Are you in immediate danger, or thinking about harming yourself or someone else right now?",
    "infection": "What is the measured temperature and duration, and is there confusion, breathing difficulty, neck stiffness, a non-fading rash, severe dehydration, or extreme drowsiness?",
    "general": "How severe is it, when did it start, is it worsening, and are there any breathing problems, fainting, confusion, severe pain, or heavy bleeding?",
}


SPECIALISTS = {
    "eye": "General Physician or eye-care clinician for initial evaluation",
    "pregnancy": "Obstetric clinician or urgent-care service",
    "mental_health": "Mental-health professional or emergency service, depending on immediate safety",
    "injury": "General Physician or urgent-care clinician for initial evaluation",
}


NEGATION_RE = re.compile(r"\b(no|not|without|denies|never|dont|don't|do not)\b")


def _is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 35):start]
    words = prefix.split()
    return bool(NEGATION_RE.search(" ".join(words[-5:])))


def _contains(text: str, phrase: str) -> bool:
    start = text.find(phrase)
    while start >= 0:
        if not _is_negated(text, start):
            return True
        start = text.find(phrase, start + len(phrase))
    return False


def _category(text: str) -> str:
    scores = {
        category: sum(1 for term in terms if _contains(text, term))
        for category, terms in CATEGORY_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


def evaluate_triage(message: str) -> TriageResult:
    text = re.sub(r"\s+", " ", message.lower()).strip()
    category = _category(text)
    red_flags = tuple(
        label
        for label, phrases in EMERGENCY_FLAGS.items()
        if any(_contains(text, phrase) for phrase in phrases)
    )

    mentions_symptom = any(_contains(text, term) for term in SYMPTOM_TERMS)
    if red_flags:
        risk = "emergency"
    elif any(_contains(text, term) for term in HIGH_URGENCY_TERMS):
        risk = "high"
    elif any(_contains(text, term) for term in MEDIUM_URGENCY_TERMS):
        risk = "medium"
    elif mentions_symptom:
        risk = "low"
    else:
        risk = None

    if risk == "emergency":
        action = (
            "Seek emergency care now or call your local emergency number. "
            "Do not drive yourself if you feel faint, confused, or severely unwell."
        )
        specialist = "Emergency department or local emergency service"
        provisional = False
    elif risk == "high":
        action = (
            "Arrange urgent in-person medical assessment today. If symptoms worsen "
            "or any emergency warning sign appears, seek emergency care immediately."
        )
        specialist = SPECIALISTS.get(category, "General Physician or urgent-care clinician")
        provisional = True
    elif risk == "medium":
        action = (
            "Contact a clinician promptly, monitor symptoms, and seek urgent help if "
            "they worsen or any emergency warning sign appears."
        )
        specialist = SPECIALISTS.get(category, "General Physician or urgent-care clinician")
        provisional = True
    else:
        action = (
            "Monitor the problem and arrange routine medical advice if it persists, "
            "worsens, or concerns you."
        )
        specialist = SPECIALISTS.get(category, "General Physician for initial evaluation")
        provisional = True

    return TriageResult(
        risk_level=risk,
        category=category,
        specialist=specialist,
        question=QUESTIONS.get(category, QUESTIONS["general"]),
        action=action,
        matched_red_flags=red_flags,
        provisional=provisional,
    )


def build_fallback_response(message: str, triage: TriageResult) -> str:
    labels = {
        "low": "🟢 Low",
        "medium": "🟡 Medium",
        "high": "🔴 High",
        "emergency": "🚨 Emergency",
        None: "Not yet assessed",
    }
    qualifier = " — provisional" if triage.provisional else ""
    risk_text = f"{labels[triage.risk_level]}{qualifier}"

    if triage.risk_level == "emergency":
        safety_section = (
            "\n\n**Warning Signs Detected**\n"
            + ", ".join(triage.matched_red_flags)
        )
    else:
        safety_section = f"\n\n**One Important Safety Question**\n{triage.question}"

    return f"""**Assessment**
Based on the information provided, this is a safety-focused provisional triage assessment. More details are needed to understand the cause.

**Risk Level:** {risk_text}{safety_section}

**What You Should Do**
{triage.action}

**Who to Contact**
{triage.specialist}

---
*This is not a diagnosis. If you feel seriously unwell or unsafe, seek urgent in-person care.*"""
