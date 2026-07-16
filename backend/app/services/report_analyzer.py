import fitz  # pymupdf
import os
from app.utils.config import GROQ_API_KEY, GROQ_MODEL
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=GROQ_MODEL,
    temperature=0.3
)

REPORT_SYSTEM_PROMPT = """You are VaidyaAI, a medical report analyst. Your job is to explain medical reports in simple, easy-to-understand language.

When given a medical report, you must:

1. **Summary** — One paragraph explaining what this report is about in simple words

2. **Key Values Explained** — For each test result:
   - Test name in simple words
   - The patient's value
   - Normal range
   - What it means (Normal ✅ / Slightly High ⚠️ / High 🔴 / Low 🔵)
   - Simple explanation of what this value means for health

3. **Overall Assessment** — Is the patient healthy? Any concerns?

4. **What To Do Next** — Simple action steps

Rules:
- NEVER use complex medical jargon without explaining it
- Use emojis to make it easy to scan
- Be reassuring but honest
- Always recommend consulting a doctor
- Respond in the language the patient requests"""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        return f"Could not extract text from PDF: {str(e)}"


def extract_text_from_image(image_bytes: bytes) -> str:
    """For image files, return a message to use text extraction."""
    return "Image report uploaded. Please describe the key values you see."


def analyze_report(file_bytes: bytes, filename: str, language: str = "en") -> str:
    """
    Main function — takes file bytes, extracts text,
    sends to LLM for analysis, returns explanation.
    """
    # Extract text based on file type
    filename_lower = filename.lower()

    if filename_lower.endswith('.pdf'):
        report_text = extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith(('.jpg', '.jpeg', '.png')):
        report_text = "Image file uploaded. I'll analyze based on the filename and common report formats."
    elif filename_lower.endswith('.txt'):
        report_text = file_bytes.decode('utf-8', errors='ignore')
    else:
        report_text = file_bytes.decode('utf-8', errors='ignore')

    if not report_text or len(report_text) < 20:
        return "I couldn't extract text from this file. Please try uploading a text-based PDF or type the values manually."

    # Truncate if too long (LLM context limit)
    if len(report_text) > 4000:
        report_text = report_text[:4000] + "\n...[Report truncated for analysis]"

    lang_instruction = {
        'en': 'Respond in English.',
        'hi': 'हिंदी में जवाब दें।',
        'kn': 'ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ.',
    }.get(language, 'Respond in English.')

    messages = [
        SystemMessage(content=f"{REPORT_SYSTEM_PROMPT}\n\n{lang_instruction}"),
        HumanMessage(content=f"Please analyze this medical report and explain it in simple words:\n\n{report_text}")
    ]

    response = llm.invoke(messages)
    return response.content