# utils/rag_engine.py
# Uses google-genai with gemini-2.0-flash

import os
import json
import requests
import streamlit as st
from typing import List, Dict, Tuple, Optional


from utils.embeddings_store import load_embeddings, find_top_chunks
from utils.knowledge_router import get_folder

_embeddings_cache: Dict[str, Dict] = {}

def _get_service_embeddings(service_folder, knowledge_base_root="knowledge_base"):
    if service_folder not in _embeddings_cache:
        data = load_embeddings(service_folder, knowledge_base_root)
        if data:
            _embeddings_cache[service_folder] = data
    return _embeddings_cache.get(service_folder)

def clear_cache():
    _embeddings_cache.clear()

def _get_gemini_key():
    key = st.session_state.get("gemini_api_key", "")
    if not key:
        try:
            key = st.secrets.get("api_keys", {}).get("gemini_api_key", "")
        except Exception:
            pass
    if not key:
        key = os.getenv("GEMINI_API_KEY", "")
    return key

def _get_client():
    from google import genai
    return genai.Client(api_key=_get_gemini_key())

from groq import Groq

def _get_groq_client():
    return Groq(api_key="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")

def _generate(prompt: str) -> str:
    """Single function to call Groq — model name in one place."""
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq Error: {e}")
        return ""

def _generate_json(prompt: str) -> dict:
    """Call Groq and parse JSON response."""
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        raw = response.choices[0].message.content.strip()
        import json
        return json.loads(raw)
    except Exception as e:
        print(f"Groq JSON Error: {e}")
        return {}

def embed_query(text: str) -> list | None:
    """
    Embed user query using the Colab embedding server.
    Falls back to Gemini only if Colab server is not available.
    """
    # Try Colab embedding server first (unlimited, no API key needed)
    colab_url = ""
    try:
        colab_url = st.session_state.get("agent_backend_url", "")
    except Exception:
        pass

    if colab_url:
        try:
            headers = {"ngrok-skip-browser-warning": "true"}
            response = requests.post(
                f"{colab_url.rstrip('/')}/embed",
                json={"text": text},
                headers=headers,
                timeout=15
            )
            if response.status_code == 200:
                return response.json().get("embedding")
        except Exception as e:
            print(f"Colab embed failed on {colab_url}, trying Gemini: {e}")

    # Fallback: Gemini embeddings (rate limited but works without Colab)
    if not _get_gemini_key():
        return None
    try:
        client = _get_client()
        result = client.models.embed_content(
            model="models/text-embedding-004",
            contents=text,
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Gemini embedding error: {e}")
        return None


def embed_document(text: str) -> Optional[List[float]]:
    return embed_query(text)

def retrieve_chunks(user_question, service_display_name, top_k=3,
                    knowledge_base_root="knowledge_base"):
    if not _get_gemini_key():
        return [], "no_key"
    folder = get_folder(service_display_name)
    if not folder:
        return [], "error"
    service_data = _get_service_embeddings(folder, knowledge_base_root)
    if not service_data:
        return [], "no_embeddings"
    query_embedding = embed_query(user_question)
    if not query_embedding:
        return [], "error"
    top_chunks = find_top_chunks(query_embedding, service_data, top_k=top_k)
    return top_chunks, "ok"

def format_chunks_for_prompt(chunks):
    if not chunks:
        return "No relevant content found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "").upper()
        score  = chunk.get("similarity_score", 0)
        text   = chunk.get("text", "")
        parts.append(f"[SOURCE {i} — {source} | relevance: {score:.2f}]\n{text}")
    return "\n\n---\n\n".join(parts)

def get_grounded_answer(user_question, chunks, service_name, language="english",
                        current_visible_text="", active_tab="steps"):
    if not _get_gemini_key():
        return {"answer_full": "Gemini API key not configured.",
                "answer_voice": "API key missing.", "used_chunks": 0, "confidence": 0.0}

    context = format_chunks_for_prompt(chunks)
    current_context = ""
    if current_visible_text:
        current_context = f"\nCURRENTLY VISIBLE:\n{current_visible_text[:500]}\n"

    prompt = f"""You are a helpful assistant for Indian government services.
Service: {service_name}. Language: {language}.
{current_context}
KNOWLEDGE BASE (answer ONLY from this):
{context}

USER QUESTION: "{user_question}"

RULES:
- Answer ONLY from the content above
- Answer in {language} language
- If not found: say so in {language}

Return ONLY valid JSON:
{{"answer_full":"detailed answer in {language}","answer_voice":"short 2-3 sentence version in {language}","confidence":0.85}}"""

    try:
        result = _generate_json(prompt)
        result["used_chunks"] = len(chunks)
        return result
    except Exception as e:
        print(f"Gemini error: {e}")
        return {"answer_full": f"Error: {e}", "answer_voice": "Please try again.",
                "used_chunks": len(chunks), "confidence": 0.0}

def translate_text(text: str, target_language: str) -> str:
    """Translate text to target language using Gemini."""
    if not text.strip():
        return text
    if target_language.lower() == "english":
        return text
    try:
        prompt = f"""Translate the following text to {target_language}.
Keep formatting, bullet points, and structure intact.
Return ONLY the translated text, nothing else.

TEXT TO TRANSLATE:
{text}"""
        return _generate(prompt)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

# Navigation detection
NAV_KEYWORDS = {
    "next":     ["next","continue","forward","आगे","అగళా","முன்னே","ਅਗਲਾ","এগিয়ে","aage"],
    "previous": ["back","previous","पीछे","వెనక్కి","பின்னே","ਪਿੱਛੇ","পিছনে","peeche"],
    "repeat":   ["repeat","again","फिर","మళ్ళీ","மீண்டும்","ਦੁਬਾਰਾ","আবার","dobara"],
    "help":     ["help","stuck","confused","मदद","సహాయం","உதவி","ਮਦਦ","সাহায্য"],
    "home":     ["home","start","menu","होम","హోమ్","முகப்பு","ਹੋਮ","হোম"],
}
NAV_RESPONSES = {
    "next":     "Moving to the next step.",
    "previous": "Going back to the previous step.",
    "repeat":   "Let me read that again for you.",
    "help":     "Opening the help section.",
    "home":     "Taking you back to the start.",
}

def _check_navigation(text: str):
    t = text.lower().strip()
    for cmd, keywords in NAV_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return {"intent":"navigate","command":cmd,
                    "answer_full":NAV_RESPONSES.get(cmd,"Navigating."),
                    "answer_voice":NAV_RESPONSES.get(cmd,"Navigating."),
                    "chunks_used":[],"retrieval_status":"skipped","method":"navigation"}
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def process_rag_query(user_question, service_display_name, language="english",
                      current_visible_text="", active_tab="steps", top_k=3,
                      knowledge_base_root="knowledge_base"):
    nav = _check_navigation(user_question)
    if nav:
        return nav

    chunks, status = retrieve_chunks(user_question, service_display_name,
                                     top_k=top_k, knowledge_base_root=knowledge_base_root)

    if status in ("no_embeddings", "no_key", "error"):
        msg = {
            "no_embeddings": "Knowledge base not indexed. Run build_embeddings.py first.",
            "no_key": "Gemini API key not configured.",
            "error": "Retrieval error. Try again."
        }.get(status, "Unknown error.")
        return {"intent":"question","command":None,"answer_full":msg,
                "answer_voice":msg,"chunks_used":[],"retrieval_status":status,"method":"fallback"}

    answer_result = get_grounded_answer(user_question, chunks, service_display_name,
                                        language, current_visible_text, active_tab)
    return {"intent":"question","command":None,
            "answer_full":  answer_result.get("answer_full",""),
            "answer_voice": answer_result.get("answer_voice",""),
            "confidence":   answer_result.get("confidence",0.0),
            "chunks_used":  chunks,
            "retrieval_status": status, "method":"rag"}