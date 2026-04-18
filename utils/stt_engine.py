# utils/stt_engine.py

import requests
import streamlit as st


def transcribe_audio(audio_bytes: bytes, lang_code: str = None) -> dict:
    """
    Send audio to Colab Whisper backend.
    No local model. No GPU needed on laptop.
    Returns full transcript text exactly as spoken.
    """

    colab_url = st.session_state.get("backend_url", "")

    if not colab_url or colab_url.strip() == "":
        return {
            "success": False,
            "text": "",
            "error": "no_backend",
            "message": "Colab backend not configured. Please start the Colab notebook."
        }

    try:
        response = requests.post(
            f"{colab_url.rstrip('/')}/transcribe",
            files={
                "audio": ("recording.wav", audio_bytes, "audio/wav")
            },
            data={
                "lang_code": lang_code or ""
            },
            timeout=45
        )

        if response.status_code == 200:
            result = response.json()
            result["success"] = True
            return result
        else:
            return {
                "success": False,
                "text": "",
                "error": "backend_error",
                "message": f"Colab returned HTTP {response.status_code}."
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "text": "",
            "error": "offline",
            "message": "Cannot reach Colab. The notebook may have disconnected."
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "text": "",
            "error": "timeout",
            "message": "Colab is taking too long. GPU may still be loading. Try again in 30 seconds."
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "error": "unknown",
            "message": f"Unexpected error: {str(e)}"
        }