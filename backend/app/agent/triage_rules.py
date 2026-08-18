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
    "skin_allergy": ("rash", "itch", "hives", "skin", "swelling", "swollen"),
    "eye": ("eye", "vision", "sight"),
    "injury": ("injury", "fell", "fall", "sprain", "fracture", "cut", "burn"),
    "infection": ("fever", "temperature", "chills", "infection"),
}


EMERGENCY_FLAGS = {
    "difficulty breathing": ("difficulty breathing", "can't breathe", "cannot breathe", "gasping"),
    "blue or grey lips": ("blue lips", "grey lips", "gray lips"),
    "severe chest pressure": ("crushing chest", "crushing pressure", "heavy chest pressure"),
    "loss of consciousness": ("unconscious", "passed out", "not waking", "fainted and"),
    "stroke-like symptoms": ("face droop", "one sided weakness", "one-sided weakness", "slurred speech"),
    "seizure": ("seizure", "convulsion"),
    "sudden severe headache": ("worst headache", "sudden severe headache", "thunderclap headache"),
    "meningitis warning signs": ("non-fading rash", "rash does not fade"),
    "severe bleeding": ("severe bleeding", "bleeding won't stop", "bleeding will not stop"),
    "internal bleeding": ("vomiting blood", "coughing blood", "black tarry stool"),
    "severe allergic reaction": ("swollen tongue", "tongue swelling", "tongue is swelling", "throat closing", "anaphylaxis"),
    "immediate self-harm risk": ("kill myself", "end my life", "suicide plan", "suicidal", "took an overdose", "overdose now"),
    "pregnancy emergency": ("pregnant and heavy bleeding", "pregnant with severe pain", "no fetal movement"),
    "sudden vision loss": ("sudden vision loss", "suddenly can't see", "suddenly cannot see"),
}


HIGH_URGENCY_TERMS = (
    "chest pain", "chest pressure", "high fever", "severe pain", "persistent vomiting", "can't keep fluids down",
    "cannot keep fluids down", "blood in stool", "blood in urine", "confusion",
    "difficulty swallowing", "rapidly spreading rash", "dehydrated", "very drowsy",
    "neck stiffness", "swollen lips", "lips are swollen", "lips are swelling",
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

POSSIBLE_CATEGORIES = {
    "cardiac": (
        "Chest-wall or muscle irritation — more likely when movement or pressing the area changes the pain",
        "Indigestion or reflux — may cause burning discomfort related to meals or lying down",
        "Heart or lung causes — important to rule out when pain is persistent, exertional, pressure-like, or occurs with other warning signs",
    ),
    "respiratory": (
        "A viral respiratory illness",
        "Airway irritation or asthma",
        "A lung infection or another cause that needs examination if breathing is affected",
    ),
    "neurological": (
        "A common headache pattern such as tension headache or migraine",
        "Dehydration, poor sleep, infection, or medication effects",
        "A neurological cause that needs urgent assessment if warning signs are present",
    ),
    "digestive": (
        "Indigestion, reflux, constipation, or a short-lived stomach illness",
        "Inflammation or infection in the digestive system",
        "Another abdominal condition that may require examination if pain is severe or localised",
    ),
    "general": (
        "A common temporary illness or irritation",
        "An infection, inflammation, or medication-related effect",
        "Another cause that may need an examination if it persists or worsens",
    ),
}

URGENT_WARNING_SIGNS = {
    "cardiac": "Call emergency services for persistent or crushing pressure, trouble breathing, fainting, cold sweating, severe dizziness, or pain spreading to the arm, jaw, back, or stomach.",
    "respiratory": "Seek emergency help for severe breathlessness, inability to speak full sentences, blue or grey lips, confusion, fainting, or rapidly worsening symptoms.",
    "neurological": "Seek emergency help for a sudden worst-ever headache, seizure, fainting, confusion, new weakness or numbness, trouble speaking, or fever with neck stiffness.",
    "digestive": "Seek urgent help for severe or localised pain, a rigid or swollen abdomen, fainting, vomiting blood, black stool, or inability to keep fluids down.",
    "general": "Seek urgent help for breathing difficulty, fainting, confusion, severe or rapidly worsening pain, heavy bleeding, or feeling dangerously unwell.",
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
    red_flags = list(
        label
        for label, phrases in EMERGENCY_FLAGS.items()
        if any(_contains(text, phrase) for phrase in phrases)
    )

    # Chest discomfort has several possible causes. Escalate it immediately only
    # when the message also contains a concerning heart/lung warning sign; an
    # isolated report is screened with focused questions before assigning risk.
    has_chest_discomfort = any(
        _contains(text, phrase)
        for phrase in ("chest pain", "chest pressure", "chest discomfort")
    )
    cardiac_warning_signs = (
        "shortness of breath", "sweating", "fainting", "fainted",
        "pain spreading", "pain radiating", "jaw pain", "left arm pain",
    )
    if (
        has_chest_discomfort
        and any(_contains(text, phrase) for phrase in cardiac_warning_signs)
        and "chest discomfort with concerning symptoms" not in red_flags
    ):
        red_flags.append("chest discomfort with concerning symptoms")

    # Some individual symptoms are ambiguous. Escalate combinations that form
    # a clearer emergency pattern, while allowing isolated mentions to receive
    # the category-specific safety questions first.
    has_neck_stiffness = _contains(text, "neck stiffness")
    has_infection_sign = any(
        _contains(text, phrase) for phrase in ("fever", "high temperature", "non-fading rash")
    )
    if has_neck_stiffness and has_infection_sign and "possible meningitis warning signs" not in red_flags:
        red_flags.append("possible meningitis warning signs")

    red_flags = tuple(red_flags)

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


DETAIL_PATTERNS = {
    "duration": re.compile(
        r"\b(today|yesterday|since|for (?:about )?\d+|\d+\s*(?:minutes?|hours?|days?|weeks?)|"
        r"(?:a|an|one)\s+(?:minute|hour|day|week)(?:\s+ago)?)\b"
    ),
    "severity": re.compile(r"\b(mild|moderate|severe|worst|\d{1,2}\s*/\s*10)\b"),
    "measurement": re.compile(r"\b\d{2,3}(?:\.\d+)?\s*(?:°\s*)?[fc]\b"),
    "associated": re.compile(
        r"\b(with|also|along with|but no|without|denies|vomit|rash|stiff|weak|breath)\b"
    ),
    "course": re.compile(r"\b(better|worse|worsening|improving|same|comes? and goes?|constant)\b"),
}

SAFETY_ANSWER_RE = re.compile(
    r"\b(no|none|without|denies|breath|sweat|faint|dizz|weak|numb|blood|rash|spread|radiat)\b"
)

CATEGORY_DETAIL_RE = {
    "cardiac": re.compile(
        r"\b(sharp|stabbing|pin|pressure|squeez|burning|ache|movement|press|touch|"
        r"breath|eat|meal|exert|walk|exercise|rest|spread|radiat)\b"
    ),
    "respiratory": re.compile(r"\b(rest|walking|exercise|wheez|phlegm|sputum|cough|breath)\b"),
    "neurological": re.compile(r"\b(sudden|gradual|light|sound|vision|weak|numb|speech|stiff)\b"),
    "digestive": re.compile(r"\b(eat|meal|stool|bowel|vomit|nausea|bloat|burning|cramp)\b"),
    "urinary": re.compile(r"\b(urine|pee|burn|frequency|blood|flank|back|fever)\b"),
    "skin_allergy": re.compile(r"\b(spread|itch|pain|blister|peel|swelling|new food|medicine)\b"),
}


def missing_details(message: str, category: str) -> list[str]:
    """Return only the essential history fields still absent from the conversation."""
    text = message.lower()
    missing = []
    if not DETAIL_PATTERNS["duration"].search(text):
        missing.append("duration")
    if not DETAIL_PATTERNS["severity"].search(text):
        missing.append("severity")
    if not DETAIL_PATTERNS["course"].search(text):
        missing.append("course")
    if not SAFETY_ANSWER_RE.search(text):
        missing.append("safety")
    category_pattern = CATEGORY_DETAIL_RE.get(category)
    if category_pattern and not category_pattern.search(text):
        missing.append("character")
    if (
        category == "infection" or any(term in text for term in ("fever", "temperature", "chills"))
    ) and not DETAIL_PATTERNS["measurement"].search(text):
        missing.append("measurement")
    return missing


def has_enough_initial_detail(message: str) -> bool:
    """True when an initial message already supplies multiple useful details."""
    category = _category(message.lower())
    missing = missing_details(message, category)
    return "duration" not in missing and "severity" not in missing and len(missing) <= 2


def should_ask_follow_up(
    message: str,
    triage: TriageResult,
    prior_user_messages: list[str] | None = None,
    intake_rounds: int = 0,
) -> bool:
    """Ask at most two focused rounds, stopping as soon as essentials are present."""
    prior_user_messages = prior_user_messages or []
    if triage.risk_level in (None, "emergency"):
        return False
    if intake_rounds >= 2:
        return False
    context = " ".join([*prior_user_messages, message])
    missing = missing_details(context, triage.category)
    if not missing:
        return False
    if intake_rounds == 0:
        return not has_enough_initial_detail(context)
    # A second round is reserved for genuinely incomplete replies, especially
    # missing timing, severity, or a response to the red-flag safety screen.
    return any(field in missing for field in ("duration", "severity", "safety"))


def build_intake_response(
    message: str,
    triage: TriageResult,
    missing: list[str] | None = None,
    round_number: int = 1,
) -> str:
    missing = missing or missing_details(message, triage.category)
    questions = []
    if "duration" in missing or "severity" in missing or "course" in missing:
        questions.append("When did it start, how strong is it from 0–10, and is it improving, worsening, constant, or coming and going?")
    if "measurement" in missing:
        questions.append("What is the measured temperature?")
    if "character" in missing and triage.category == "cardiac":
        questions.append("Where exactly is it, what does it feel like, and does breathing, movement, pressing the area, eating, or exertion change it?")
    elif "character" in missing:
        questions.append("Where is the problem and what does it feel like or look like?")
    if "safety" in missing:
        questions.append(triage.question)

    heading = "**A few important questions**" if round_number == 1 else "**One last clarification**"
    intro = (
        "I want to understand this before assigning a risk level."
        if round_number == 1
        else "Your description helps, but a few safety details are still missing."
    )
    question_text = "\n".join(f"- {question}" for question in questions[:3])
    return f"""{heading}
{intro}

{question_text}

Please answer together in one message. If any symptom feels severe or rapidly worsening, seek urgent in-person care now."""


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
        safety_section = ""

    possibilities = POSSIBLE_CATEGORIES.get(
        triage.category,
        POSSIBLE_CATEGORIES["general"],
    )
    possibilities_text = "\n".join(f"- {item}" for item in possibilities)
    warning_text = URGENT_WARNING_SIGNS.get(
        triage.category,
        URGENT_WARNING_SIGNS["general"],
    )

    return f"""**Assessment**
Your symptoms can have several causes, and a chat cannot confirm which one is responsible. The safest next step depends on the pattern, severity, duration, and warning signs you reported.
{safety_section}

**What It Could Be**
{possibilities_text}

**What To Do Now**
{triage.action}

**Get Urgent Help Now If**
{warning_text}

**Who To Contact**
{triage.specialist}

**Risk Level:** {risk_text}

---
*This is not a diagnosis. If you feel seriously unwell or unsafe, seek urgent in-person care.*"""
