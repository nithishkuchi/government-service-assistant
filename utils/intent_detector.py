# utils/intent_detector.py
# COMPLETELY REWRITTEN
# Now Gemini actually ANSWERS the question instead of just classifying it
# The knowledge base content is passed to Gemini so it gives real answers

import requests
import json
import os
import streamlit as st


def process_utterance(
    text: str,
    language: str = "english",
    current_screen: str = "home",
    current_step: int = 0,
    total_steps: int = 5,
    current_step_content: str = "",
    service_name: str = "",
) -> tuple[dict, str]:
    """
    Process what user said and return a REAL answer.
    
    KEY CHANGE: We now pass the actual step content to Gemini
    so Gemini can answer from the knowledge base, not just classify.
    
    Priority:
    1. Colab NLU endpoint
    2. Local Gemini API call  
    3. Keyword fallback (navigation only)
    """

    # Layer 1: Try Colab NLU endpoint
    colab_url = st.session_state.get("backend_url", "")
    if colab_url:
        try:
            response = requests.post(
                f"{colab_url.rstrip('/')}/nlu",
                json={
                    "text": text,
                    "language": language,
                    "current_screen": current_screen,
                    "current_step": current_step,
                    "total_steps": total_steps,
                    "current_step_content": current_step_content,
                    "service_name": service_name,
                },
                timeout=20
            )
            if response.status_code == 200:
                result = response.json()
                # Only reject if confidence extremely low
                if result.get("confidence", 0) >= 0.3:
                    return result, "gemini_colab"
        except Exception:
            pass

    # Layer 2: Local Gemini API call
    gemini_key = (
        st.session_state.get("gemini_api_key", "")
        or os.getenv("GEMINI_API_KEY", "")
    )
    if gemini_key:
        result = _call_gemini_locally(
            text, language, current_screen,
            current_step, total_steps,
            current_step_content, service_name,
            gemini_key
        )
        if result:
            return result, "gemini_local"

    # Layer 3: Keyword fallback — navigation only
    result = _keyword_fallback(text)
    return result, "keyword"


def _call_gemini_locally(
    text, language, screen, step, total,
    step_content, service_name, api_key
):
    """
    FIXED: Gemini now reads the actual knowledge base content
    and gives a real answer, not just a classification.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={
                "temperature": 0.3,
                "response_mime_type": "application/json"
            }
        )

        # Build context from current step content
        context_section = ""
        if step_content:
            context_section = f"""
CURRENT STEP CONTENT FROM KNOWLEDGE BASE:
{step_content}

Use the above content to answer the user's question accurately.
"""

        prompt = f"""You are a helpful government service assistant for India.
You help citizens understand how to apply for government documents.

SERVICE: {service_name}
CURRENT STEP: {step} of {total}
USER LANGUAGE: {language}
{context_section}

USER SAID: "{text}"

INSTRUCTIONS:
- If user is asking a question about the service or step, answer it using the knowledge base content above
- If user wants to navigate (next, previous, back, home), set intent to navigate
- Give your answer in {language} language
- Keep answer under 100 words, clear and helpful
- Do NOT say "I don't know" — use the content provided to answer
- Do NOT classify into rigid boxes — just answer what was asked

Return ONLY valid JSON:
{{
  "intent": "navigate" or "question" or "unknown",
  "command": "next" or "previous" or "repeat" or "help" or "home" or null,
  "service": null,
  "answer": "your helpful answer in {language} here",
  "confidence": 0.85,
  "reasoning": "one line why"
}}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Clean markdown if present
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        result = json.loads(raw.strip())
        return result

    except Exception as e:
        print(f"Gemini error: {e}")
        return None


def _keyword_fallback(text: str) -> dict:
    """
    Only handles navigation keywords.
    For questions — returns unknown so caller shows step content.
    """
    t = text.lower()

    NAV_KEYWORDS = {
        "next": [
            "next", "continue", "forward", "आगे", "अगला",
            "నెక్స్ట్", "తదుపరి", "முன்னே", "அடுத்து",
            "മുന്നോട്ട്", "ਅਗਲਾ", "ಮುಂದೆ", "এগিয়ে"
        ],
        "previous": [
            "back", "previous", "पीछे", "वापस", "వెనక్కి",
            "பின்னே", "പിന്നോട്ട്", "ਪਿੱਛੇ", "ಹಿಂದೆ", "পিছনে"
        ],
        "repeat": [
            "repeat", "again", "फिर", "दुबारा", "మళ్ళీ",
            "மீண்டும்", "ਦੁਬਾਰਾ", "ಮತ್ತೊಮ್ಮೆ", "আবার"
        ],
        "help": [
            "help", "stuck", "confused", "मदद", "सहायता",
            "సహాయం", "உதவி", "സഹായം", "ਮਦਦ", "ಸಹಾಯ", "সাহায্য"
        ],
        "home": [
            "home", "start", "menu", "होम", "मेनू",
            "హోమ్", "முகப்பு", "ഹോം", "ਹੋਮ", "ಹೋಮ್", "হোম"
        ],
    }

    for cmd, words in NAV_KEYWORDS.items():
        if any(w in t for w in words):
            return {
                "intent": "navigate",
                "command": cmd,
                "service": None,
                "answer": None,
                "confidence": 0.75,
                "reasoning": f"Keyword match: {cmd}"
            }

    return {
        "intent": "unknown",
        "command": None,
        "service": None,
        "answer": None,
        "confidence": 0.2,
        "reasoning": "No keyword match"
    }