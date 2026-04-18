# app.py - STABLE VERSION
# Fixes: correct tab tracking for TTS, FAQ read button, quota-safe Gemini usage

import streamlit as st
import os
from pathlib import Path

from utils.parser import (
    parse_full_guide_sections, parse_faq_pairs, parse_voice_point_chunks,
    group_faq_for_display, extract_service_name, extract_overview, load_service_folder,
)
from utils.state_manager import (
    initialize_session_state, reset_all_navigation,
    go_next, go_previous, stuck_action,
    get_current_visible_text, get_current_tts_text, get_progress,
)
from utils.tts_engine import synthesize_speech
from utils.colab_config import get_backend_url_from_sheet, check_backend_health
from utils.knowledge_router import get_folder

st.set_page_config(page_title="Government Service Assistant", page_icon="🧭", layout="wide")

def inject_premium_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }
            /* Gradient Title */
            h1 {
                background: linear-gradient(90deg, #4F46E5, #9333EA);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 700 !important;
            }
            /* Button Hover Scaling */
            .stButton > button {
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                border-radius: 8px;
            }
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
            }
            /* Progress Bar Styling */
            .stProgress > div > div > div > div {
                background-color: #4F46E5;
            }
            /* Custom Cards */
            .service-card {
                padding: 1.5rem;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
                background: #FFFFFF;
                transition: all 0.3s ease;
                margin-bottom: 1rem;
                text-align: center;
            }
            .service-card:hover {
                border-color: #4F46E5;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            }
            .answer-card {
                background-color: #F9FAFB;
                border-left: 5px solid #4F46E5;
                padding: 1.5rem;
                border-radius: 4px 12px 12px 4px;
                margin: 1.5rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
        </style>
    """, unsafe_allow_html=True)

inject_premium_css()
initialize_session_state()

# ── AUTO-DETECT SERVICES ─────────────────────────────────────
def scan_knowledge_base(root="knowledge_base"):
    kb = Path(root)
    if not kb.exists():
        return {}
    services = {}
    for folder in sorted(kb.iterdir()):
        if not folder.is_dir():
            continue
        has = any((folder/f).exists() and (folder/f).stat().st_size > 50
                  for f in ["full_guide.txt","faq.txt","voice_points.txt"])
        if has:
            services[folder.name.replace("_"," ").title()] = folder.name
    return services

SERVICES     = scan_knowledge_base()
if not SERVICES:
    SERVICES = {"Caste Certificate": "caste_certificate"}
SERVICE_NAMES = list(SERVICES.keys())

# ── API KEY ──────────────────────────────────────────────────
if not st.session_state.get("gemini_api_key"):
    try:
        st.session_state.gemini_api_key = (
            st.secrets.get("api_keys",{}).get("gemini_api_key","")
            or os.getenv("GEMINI_API_KEY","")
        )
    except Exception:
        pass

# ── BACKEND URL ──────────────────────────────────────────────
@st.cache_data(ttl=30)
def auto_load_backend_url():
    return get_backend_url_from_sheet()

@st.cache_data(ttl=30)
def auto_load_agent_url():
    from utils.colab_config import get_agent_url_from_sheet
    return get_agent_url_from_sheet()

_config = auto_load_backend_url()
if _config.get("url") and not st.session_state.get("backend_url"):
    st.session_state.backend_url = _config["url"]

_agent_config = auto_load_agent_url()
if _agent_config.get("url") and not st.session_state.get("agent_backend_url"):
    st.session_state.agent_backend_url = _agent_config["url"]


# ── LANGUAGES ────────────────────────────────────────────────
LANGUAGE_OPTIONS = [
    "English","Hindi","Telugu","Tamil","Malayalam","Kannada","Bengali",
    "Marathi","Gujarati","Punjabi","Odia","Urdu","Assamese","Nepali",
    "Arabic","Chinese","Spanish","French","German","Portuguese","Russian",
    "Japanese","Korean","Turkish","Vietnamese","Thai","Indonesian",
]
LANG_CODE_MAP = {
    "English":"en","Hindi":"hi","Telugu":"te","Tamil":"ta","Malayalam":"ml",
    "Kannada":"kn","Bengali":"bn","Marathi":"mr","Gujarati":"gu","Punjabi":"pa",
    "Odia":"or","Urdu":"ur","Assamese":"as","Nepali":"ne","Arabic":"ar",
    "Chinese":"zh","Spanish":"es","French":"fr","German":"de","Portuguese":"pt",
    "Russian":"ru","Japanese":"ja","Korean":"ko","Turkish":"tr","Vietnamese":"vi",
    "Thai":"th","Indonesian":"id",
}

# ── SERVICE LOADING ──────────────────────────────────────────
def load_selected_service():
    service_display = st.session_state.selected_service
    folder = SERVICES.get(service_display) or get_folder(service_display)
    if not folder:
        folder = service_display.lower().replace(" ","_")

    laptop_mode = "Phone" not in st.session_state.get("device_mode","Laptop")

    try:
        lang_code = st.session_state.get("current_lang_code", "en")
        files = load_service_folder(folder, lang_code=lang_code)
    except Exception as e:
        st.error(f"Could not load '{folder}': {e}")
        st.session_state.service_loaded = True
        return

    fg  = files.get("full_guide","")
    faq = files.get("faq","")
    vp  = files.get("voice_points","")

    st.session_state.raw_full_guide   = fg
    st.session_state.raw_faq          = faq
    st.session_state.raw_voice_points = vp
    st.session_state.service_folder   = folder

    guide_sections = parse_full_guide_sections(fg)  if fg.strip()  else []
    faq_pairs      = parse_faq_pairs(faq)            if faq.strip() else []
    steps_chunks   = parse_voice_point_chunks(vp, laptop_mode=laptop_mode) if vp.strip() else []
    fpp            = 5 if laptop_mode else 3
    faq_groups     = group_faq_for_display(faq_pairs, pairs_per_chunk=fpp)

    st.session_state.steps_chunks         = steps_chunks
    st.session_state.steps_total_chunks   = max(len(steps_chunks),1)
    st.session_state.guide_sections       = guide_sections
    st.session_state.guide_total_sections = max(len(guide_sections),1)
    st.session_state.faq_groups           = faq_groups
    st.session_state.faq_total_pages      = max(len(faq_groups),1)
    st.session_state.service_name         = extract_service_name(fg) if fg.strip() else service_display
    st.session_state.service_overview     = extract_overview(fg)     if fg.strip() else ""
    st.session_state.service_loaded       = True
    reset_all_navigation()

# ── TTS ──────────────────────────────────────────────────────
def speak_text(text: str):
    """Speak given text using currently selected language."""
    if not text or not text.strip():
        st.warning("No content to read.")
        return
    lang_code = st.session_state.get("current_lang_code","en")
    speed     = st.session_state.get("tts_speed",1.0)
    with st.spinner("🔊 Generating audio..."):
        audio = synthesize_speech(text=text[:2000], lang_code=lang_code, speed=speed)
    if audio:
        st.audio(audio, format="audio/mp3", autoplay=True)
    else:
        st.warning("Audio unavailable. Check internet connection.")

def repeat_current(tab_name=None):
    """Read whatever is currently visible on the active tab."""
    if not tab_name:
        tab_name = st.session_state.get("active_tab", "steps")
        
    if tab_name == "steps":
        text = st.session_state.get("_current_steps_text", "")
    elif tab_name == "full_guide":
        text = st.session_state.get("_current_guide_text", "")
    elif tab_name == "faq":
        text = st.session_state.get("_faq_page_text", "")
    else:
        text = ""

    if not text.strip():
        st.warning("Nothing to read on this page.")
        return
    speak_text(text)

# ── GEMINI CALL ───────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _call_gemini_answer(user_text: str, context: str, service: str, language: str):
    """Single Gemini call for one user question. Never called on page render."""
    api_key = st.session_state.get("gemini_api_key","")
    if not api_key:
        return "Please add your Gemini API key to .streamlit/secrets.toml", ""

    try:
        from groq import Groq
        import json
        client = Groq(api_key="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")
        prompt = f"""You are a helpful Indian government service assistant.
Service: {service}. Answer in {language} language.

PAGE CONTENT (answer only from this):
{context[:2000]}

USER QUESTION: "{user_text}"

If the answer is in the content above, answer clearly in {language}.
If not found, say so in {language}.

Return ONLY valid JSON:
{{"answer_full": "answer here in {language}", "answer_voice": "short 2-3 sentence version in {language}"}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return data.get("answer_full",""), data.get("answer_voice","")
    except Exception as e:
        err = str(e)
        if "429" in err:
            return "⚠️ Groq API quota exhausted.", "API quota exceeded."
        return f"Error: {err}", "Please try again."

# ── HANDLE QUERY ──────────────────────────────────────────────
def handle_query(user_text: str, tab_name: str = "steps"):
    if not user_text.strip():
        return

    service    = st.session_state.selected_service
    language   = st.session_state.get("current_lang_name","english")
    lang_code  = st.session_state.get("current_lang_code","en")
    
    if tab_name == "steps":
        visible = st.session_state.get("_current_steps_text", "")
    elif tab_name == "full_guide":
        visible = st.session_state.get("_current_guide_text", "")
    elif tab_name == "faq":
        visible = st.session_state.get("_faq_page_text", "")
    else:
        visible = ""

    # Navigation check — no API call needed
    from utils.rag_engine import _check_navigation
    nav = _check_navigation(user_text)
    if nav:
        cmd = nav.get("command")
        st.info(nav.get("answer_full",""))
        if cmd == "next":       go_next(tab_name);              st.rerun()
        elif cmd == "previous": go_previous(tab_name);          st.rerun()
        elif cmd == "home":     reset_all_navigation(); st.rerun()
        elif cmd == "help":     stuck_action();         st.rerun()
        elif cmd == "repeat":   repeat_current(tab_name)
        return

    # Check RAG embeddings
    from utils.embeddings_store import embeddings_exist
    folder  = st.session_state.get("service_folder","")
    has_emb = embeddings_exist(folder) if folder else False

    with st.status("🧠 Processing your question...", expanded=True) as status:
        st.write(f"📝 You asked: *{user_text}*")

        if has_emb:
            st.write("🔍 Searching with RAG...")
            from utils.rag_engine import process_rag_query
            result = process_rag_query(
                user_question=user_text, service_display_name=service,
                language=language, current_visible_text=visible,
                active_tab=st.session_state.get("active_tab","steps"),
            )
            answer_full  = result.get("answer_full","")
            answer_voice = result.get("answer_voice", answer_full)
        else:
            st.write(f"💬 Answering from page content in {language}...")
            # Use ALL raw content for this service, not just visible chunk
            all_content = (
                st.session_state.get("raw_voice_points","") + "\n" +
                st.session_state.get("raw_full_guide","") + "\n" +
                st.session_state.get("raw_faq","")
            )
            context = all_content[:3000] if all_content.strip() else visible
            answer_full, answer_voice = _call_gemini_answer(user_text, context, service, language)

        st.write("🔊 Generating audio...")
        audio = synthesize_speech(
            text=str(answer_full)[:2000],
            lang_code=lang_code,
            speed=st.session_state.get("tts_speed",1.0)
        )
        status.update(label="✅ Done!", state="complete", expanded=False)

    safe_answer = answer_full.replace('\n', '<br>')
    st.markdown(f'<div class="answer-card"><b>💬 Assistant ({language}):</b><br><br>{safe_answer}</div>', unsafe_allow_html=True)
    if audio:
        st.audio(audio, format="audio/mp3", autoplay=True)
    else:
        st.caption("Audio unavailable.")

    st.session_state.last_transcript = user_text
    st.session_state.last_answer     = str(answer_full)

# ── VOICE INPUT ───────────────────────────────────────────────
def show_voice_input(tab_name, key_suffix=""):
    st.divider()
    st.subheader("🎙 Ask Anything")
    backend_ok = bool(st.session_state.get("backend_url",""))
    lang_name  = st.session_state.get("selected_language","English")
    lang_code  = st.session_state.get("current_lang_code","en")

    st.caption(f"🌐 Language: **{lang_name}** — answers & TTS in {lang_name}")

    if not backend_ok:
        st.warning("⚠️ Voice needs Colab GPU backend. Type below instead.")

    mic_ok = False
    try:
        from audio_recorder_streamlit import audio_recorder
        mic_ok = True
    except Exception:
        pass

    audio_bytes = None
    if mic_ok and backend_ok:
        audio_bytes = audio_recorder(
            text="🎙 Click to Record", recording_color="#e74c3c",
            neutral_color="#6C63FF", icon_name="microphone", icon_size="2x",
            pause_threshold=2.5, sample_rate=16000, key=f"rec_{key_suffix}"
        )
    elif not backend_ok:
        st.caption("🎙 Start Colab to enable microphone.")

    st.caption(f"— Type in {lang_name} or any language —")
    col1, col2 = st.columns([4,1])
    with col1:
        txt = st.text_input("Query:", placeholder=f"Type in {lang_name}...",
                            label_visibility="collapsed", key=f"txt_{key_suffix}")
    with col2:
        btn = st.button("▶ Send", use_container_width=True, key=f"btn_{key_suffix}")

    if btn and txt and txt.strip():
        handle_query(txt.strip(), tab_name)
    
    audio_key = f"last_audio_bytes_{key_suffix}"
    if audio_bytes and audio_bytes != st.session_state.get(audio_key):
        st.session_state[audio_key] = audio_bytes
        from utils.stt_engine import transcribe_audio
        with st.status("🎙 Transcribing...", expanded=True) as ss:
            r = transcribe_audio(audio_bytes, lang_code=lang_code)
            if not r["success"]:
                ss.update(label="❌ Failed", state="error")
                err = r.get("error","")
                if err == "no_backend":
                    st.error("Colab not connected. Start Colab notebook.")
                else:
                    st.error(r.get("message","Unknown error"))
                return
            t = r.get("text","").strip()
            if not t:
                ss.update(label="⚠️ No speech detected", state="error")
                st.warning("No speech detected. Speak clearly and try again.")
                return
            ss.update(label=f"✅ Heard: {t}", state="complete")
        handle_query(t, tab_name)

    if st.session_state.get("last_transcript") and st.session_state.get("last_answer"):
        with st.expander("📝 Last Exchange", expanded=False):
            st.write(f"**You:** {st.session_state.last_transcript}")
            st.write(f"**Answer:** {st.session_state.last_answer}")

# ── NAV BUTTONS ───────────────────────────────────────────────
def show_nav(tab_name, pfx=""):
    phone = "Phone" in st.session_state.get("device_mode","")
    if phone:
        if st.button("🔊 Read This Page", use_container_width=True, key=f"read_{pfx}"):
            repeat_current(tab_name)
        c1,c2 = st.columns(2)
        with c1: st.button("⬅️ Prev", on_click=go_previous, args=(tab_name,), use_container_width=True, key=f"prev_{pfx}")
        with c2: st.button("➡️ Next", on_click=go_next,     args=(tab_name,), use_container_width=True, key=f"next_{pfx}")
        st.button("🆘 Stuck", on_click=stuck_action, use_container_width=True, key=f"stk_{pfx}")
    else:
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.button("⬅️ Previous",  on_click=go_previous,   args=(tab_name,), use_container_width=True, key=f"prev_{pfx}")
        with c2: 
            if st.button("🔊 Read", use_container_width=True, key=f"read_{pfx}"):
                repeat_current(tab_name)
        with c3: st.button("➡️ Next",      on_click=go_next,        args=(tab_name,), use_container_width=True, key=f"next_{pfx}")
        with c4: st.button("🆘 I'm Stuck", on_click=stuck_action,   use_container_width=True, key=f"stk_{pfx}")

def show_progress():
    idx,total,frac = get_progress()
    labels = {"steps":"Step","full_guide":"Section","faq":"Page"}
    lbl = labels.get(st.session_state.get("active_tab","steps"),"Page")
    st.progress(frac)
    st.caption(f"{lbl} {idx+1} of {max(total,1)}")

def show_stuck():
    if st.session_state.get("stuck_mode"):
        with st.container(border=True):
            st.warning("🆘 Need Help?")
            import re
            fg = st.session_state.get("raw_full_guide","")
            m = re.search(r"COMMON\s+ERRORS?.+?(.*?)(?=={4,}|\Z)",fg,re.DOTALL|re.IGNORECASE) if fg else None
            if m: st.markdown(m.group(1).strip()[:1000])
            else: st.info("Ask your question in the text box below.")
            st.button("✕ Close", on_click=stuck_action, key="cls_stuck")

# ── THREE TABS ────────────────────────────────────────────────

def render_steps():
    # Set active tab FIRST — this is what Read button uses
    st.session_state.active_tab = "steps"
    chunks = st.session_state.get("steps_chunks",[])
    idx    = st.session_state.get("steps_chunk_index",0)

    if not chunks:
        vp = st.session_state.get("raw_voice_points","")
        if not vp.strip():
            st.warning("⚠️ voice_points.txt is empty for this service.")
        else:
            st.error("Could not parse voice_points.txt")
            with st.expander("Raw content (first 500 chars)"):
                st.text(vp[:500])
        show_voice_input("s"); return

    st.caption(f"**Step {idx+1} of {len(chunks)}**")
    show_progress()
    chunk = chunks[min(idx, len(chunks)-1)]

    # Store current chunk text for TTS — BEFORE nav buttons
    sec = chunk.get("section","")
    pts = chunk.get("display_points",[])
    txt = chunk.get("text","")
    if pts:
        st.session_state["_current_steps_text"] = sec + "\n" + "\n".join(pts)
    else:
        st.session_state["_current_steps_text"] = txt

    with st.container(border=True):
        if sec: st.markdown(f"**{sec}**")
        if pts:
            for p in pts: st.markdown(f"- {p}")
        elif txt: st.markdown(txt)

    show_nav("steps", "s")
    show_stuck()
    show_voice_input("steps", "s")


def render_guide():
    # Set active tab FIRST
    st.session_state.active_tab = "full_guide"
    sections = st.session_state.get("guide_sections",[])
    idx      = st.session_state.get("guide_section_index",0)

    if not sections:
        fg = st.session_state.get("raw_full_guide","")
        if not fg.strip():
            st.warning("⚠️ full_guide.txt is empty for this service.")
        else:
            st.error("Could not parse full_guide.txt")
            with st.expander("Raw content (first 500 chars)"):
                st.text(fg[:500])
        show_voice_input("g"); return

    st.caption(f"**Page {idx+1} of {len(sections)}**")
    show_progress()
    sec = sections[min(idx, len(sections)-1)]
    title   = sec.get("title","")
    content = sec.get("content","")

    # Store current section text for TTS — BEFORE nav buttons
    st.session_state["_current_guide_text"] = f"{title}\n\n{content}"

    with st.container(border=True):
        if title: st.markdown(f"### {title}")
        st.markdown(content)

    show_nav("full_guide", "g")
    show_stuck()
    show_voice_input("full_guide", "g")


def render_faq():
    # Set active tab FIRST
    st.session_state.active_tab = "faq"
    groups = st.session_state.get("faq_groups",[])
    idx    = st.session_state.get("faq_page_index",0)

    if not groups:
        faq = st.session_state.get("raw_faq","")
        if not faq.strip():
            st.warning("⚠️ faq.txt is empty for this service.")
        else:
            st.warning("Could not parse faq.txt — check Question:/Answer: format")
            st.markdown(faq[:3000])
        show_voice_input("f"); return

    show_progress()
    grp = groups[min(idx, len(groups)-1)]

    # Build and store FAQ page text for TTS — BEFORE nav buttons
    faq_parts = []
    with st.container(border=True):
        for i, pair in enumerate(grp):
            q = pair.get("question","")
            a = pair.get("answer","")
            faq_parts.append(f"Question: {q}. Answer: {a}.")
            with st.expander(f"❓ {q}", expanded=(i==0)):
                st.markdown(a)

    # Store for TTS
    st.session_state["_faq_page_text"] = " ".join(faq_parts)

    # Read button for FAQ — uses stored text
    if st.button("🔊 Read This FAQ Page", use_container_width=True, key="faq_read_btn"):
        speak_text(st.session_state.get("_faq_page_text",""))

    c1,c2,c3 = st.columns(3)
    with c1: st.button("⬅️ Previous", on_click=go_previous, args=("faq",), use_container_width=True, key="faq_prev")
    with c2: st.button("🆘 Stuck",    on_click=stuck_action, use_container_width=True, key="faq_stk")
    with c3: st.button("➡️ Next",     on_click=go_next,      args=("faq",), use_container_width=True, key="faq_next")

    show_stuck()
    show_voice_input("faq", "f")


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Controls")
    st.divider()

    st.subheader("🎙️ Voice Server")
    if _config.get("url"):
        h = check_backend_health(_config["url"])
        if h["alive"]:
            st.success("✅ Voice Online")
        else:
            st.error("❌ Voice Offline")
            st.caption(h.get("message",""))
    else:
        st.warning("⚠️ Voice Not detected")

    with st.expander("Voice URL (Manual)"):
        mu = st.text_input("ngrok URL (Whisper):", placeholder="https://xxxx.ngrok-free.app", key="mu_voice")
        if mu and mu.strip():
            st.session_state.backend_url = mu.strip()
            st.success("Set!")

    st.subheader("🧠 Agent Server")
    if _agent_config.get("url"):
        ah = check_backend_health(_agent_config["url"])
        if ah["alive"]:
            st.success("✅ Agent Online")
        else:
            st.error("❌ Agent Offline")
            st.caption(ah.get("message",""))
    else:
        st.warning("⚠️ Agent Not detected")

    with st.expander("Agent URL (Manual)"):
        ma = st.text_input("ngrok URL (Agent):", placeholder="https://xxxx.ngrok-free.app", key="mu_agent")
        if ma and ma.strip():
            st.session_state.agent_backend_url = ma.strip()
            st.success("Set!")

    if st.button("🔄 Refresh Servers"): st.cache_data.clear(); st.rerun()
    st.divider()

    SERVICE_OPTIONS = ["🏠 Home"] + SERVICE_NAMES
    cur_svc = st.session_state.get("selected_service", "🏠 Home")
    if cur_svc not in SERVICE_OPTIONS: cur_svc = "🏠 Home"
    
    sel_svc = st.selectbox("🎯 Service", SERVICE_OPTIONS,
                           index=SERVICE_OPTIONS.index(cur_svc))
    if sel_svc != st.session_state.get("selected_service"):
        st.session_state.selected_service = sel_svc
        st.session_state.service_loaded   = False
        st.rerun()
    st.divider()

    saved_lang = st.session_state.get("selected_language","English")
    if saved_lang not in LANGUAGE_OPTIONS: saved_lang = "English"
    sel_lang = st.selectbox("🌐 Language", LANGUAGE_OPTIONS,
                            index=LANGUAGE_OPTIONS.index(saved_lang))
    if sel_lang != st.session_state.get("selected_language"):
        st.session_state.selected_language = sel_lang
        st.session_state.current_lang_code = LANG_CODE_MAP.get(sel_lang,"en")
        st.session_state.current_lang_name = sel_lang.lower()
        st.session_state.service_loaded = False
        st.rerun()

    cur_name = st.session_state.get("current_lang_name","english").title()
    cur_code = st.session_state.get("current_lang_code","en")
    st.caption(f"Active: **{cur_name}** ({cur_code})")
    st.caption("Answers + TTS speak in this language.")
    st.caption("Page content stays in English.")
    st.divider()

    modes = ["💻 Laptop / Full View","📱 Phone & Voice Mode"]
    cur_mode = st.session_state.get("device_mode", modes[0])
    if cur_mode not in modes: cur_mode = modes[0]
    sel_mode = st.radio("📱 Mode", modes, index=modes.index(cur_mode))
    if sel_mode != st.session_state.get("device_mode"):
        st.session_state.device_mode    = sel_mode
        st.session_state.service_loaded = False
        st.rerun()
    st.divider()

    st.session_state.tts_speed = st.slider(
        "🔊 Speed", 0.8, 1.5,
        value=st.session_state.get("tts_speed",1.0), step=0.1, format="%.1f×"
    )
    st.divider()

    st.caption("🔧 RAG Status")
    folder = st.session_state.get("service_folder","")
    if folder:
        from utils.embeddings_store import embeddings_exist
        if embeddings_exist(folder):
            st.success("✅ Embeddings ready")
        else:
            st.warning("⚠️ Not built yet")
            st.caption("Run: python scripts/build_embeddings.py")
    st.caption(f"📁 {len(SERVICES)} services found")

# ── MAIN ──────────────────────────────────────────────────────
if "selected_service" not in st.session_state:
    st.session_state.selected_service = "🏠 Home"

# Auto-load if service selected and not home
if st.session_state.selected_service != "🏠 Home" and not st.session_state.get("service_loaded"):
    with st.spinner(f"Loading {st.session_state.selected_service}..."):
        load_selected_service()

st.title("🧭 Government Service Assistant")
st.caption("Step-by-step guidance · Voice-enabled Multi-lingual Support")

if not SERVICES:
    st.error("❌ No services found in knowledge_base/")
elif st.session_state.selected_service == "🏠 Home":
    st.markdown("### 📋 Available Services")
    st.write("Welcome! Select a service below to get started with step-by-step guidance.")
    
    # 3-column Grid for Home Screen
    cols = st.columns(3)
    for i, svc in enumerate(SERVICE_NAMES):
        with cols[i % 3]:
            st.markdown(f"""
                <div class="service-card">
                    <h3 style="margin:0;">📄</h3>
                    <div style="font-weight:600; font-size:1.1em; margin:10px 0;">{svc}</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"View {svc}", key=f"svc_btn_{i}", use_container_width=True):
                st.session_state.selected_service = svc
                st.session_state.service_loaded = False
                st.rerun()
else:
    svc_name = st.session_state.get("service_name", st.session_state.selected_service)
    st.subheader(f"📋 {svc_name}")

    ov = st.session_state.get("service_overview","")
    if ov:
        with st.expander("ℹ️ About this service"):
            st.info(ov)

    tab1, tab2, tab3 = st.tabs(["🎤 Steps","📄 Full Guide","❓ FAQ"])
    with tab1: render_steps()
    with tab2: render_guide()
    with tab3: render_faq()