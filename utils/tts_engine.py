# utils/tts_engine.py
# Fixed voice map — correct voices for all Indian languages
# Falls back gracefully when voice not available

import requests
import asyncio
import io
import streamlit as st


# Verified working edge-tts voices
TTS_VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-MadhurNeural",
    "te": "te-IN-MohanNeural",
    "ta": "ta-IN-ValluvarNeural",
    "ml": "ml-IN-MidhunNeural",
    "kn": "kn-IN-GaganNeural",
    "bn": "bn-IN-BashkarNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-NiranjanNeural",
    "pa": "pa-IN-OjaswanthNeural",
    "ur": "ur-PK-AsadNeural",
    "ar": "ar-SA-ZariyahNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "tr": "tr-TR-EmelNeural",
    "pt": "pt-BR-FranciscaNeural",
    "vi": "vi-VN-HoaiMyNeural",
    "th": "th-TH-PremwadeeNeural",
    "id": "id-ID-GadisNeural",
    # Fallbacks for languages without edge-tts support
    "or": "en-IN-NeerjaNeural",
    "as": "en-IN-NeerjaNeural",
    "ne": "hi-IN-MadhurNeural",
    "sa": "hi-IN-MadhurNeural",
    "sd": "ur-PK-AsadNeural",
    "si": "en-IN-NeerjaNeural",
}

# gTTS supported language codes
GTTS_LANGS = {
    "en","hi","te","ta","ml","kn","bn","mr","gu","pa",
    "fr","de","es","pt","ru","ja","ko","zh","ar","tr","vi","th","id"
}

def synthesize_speech(text: str, lang_code: str = "en", speed: float = 1.0) -> bytes | None:
    """
    Convert text to speech.
    Priority: Colab TTS → edge-tts → gTTS → None
    
    IMPORTANT: lang_code must match the language of the text.
    If text is in Telugu, lang_code must be "te".
    If text is in Hindi, lang_code must be "hi".
    """
    import re
    if not text or not text.strip():
        return None
    
    # Strip markdown symbols like asterisks, bold/italics, hashes, etc.
    text = re.sub(r'[*_#~`>]+', '', text)

    if len(text) > 2000:
        text = text[:2000] + "..."

    # Layer 1: Colab TTS
    colab_url = st.session_state.get("backend_url", "")
    if colab_url:
        try:
            response = requests.post(
                f"{colab_url.rstrip('/')}/tts",
                json={"text": text, "lang_code": lang_code, "speed": speed},
                timeout=30
            )
            if response.status_code == 200 and len(response.content) > 100:
                return response.content
        except Exception:
            pass

    # Layer 2: edge-tts
    try:
        import edge_tts
        import asyncio
        
        voice = TTS_VOICE_MAP.get(lang_code, TTS_VOICE_MAP["en"])
        percent = int((speed - 1.0) * 100)
        rate = f"+{percent}%" if percent >= 0 else f"{percent}%"

        async def _synth():
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        audio = asyncio.run(_synth())
        if audio and len(audio) > 100:
            return audio
    except Exception as e:
        print(f"edge-tts failed: {e}")

    # Layer 3: gTTS
    try:
        from gtts import gTTS
        gtts_lang = lang_code if lang_code in GTTS_LANGS else "en"
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_bytes = buf.read()
        if len(audio_bytes) > 100:
            return audio_bytes
    except Exception as e:
        print(f"gTTS failed: {e}")

    return None