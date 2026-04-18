# utils/state_manager.py - FIXED
# get_current_tts_text now correctly reads from whichever tab is active

import streamlit as st


def initialize_session_state():
    defaults = {
        "selected_service":    "Caste Certificate",
        "service_folder":      "caste_certificate",
        "service_loaded":      False,
        "selected_language":   "English",
        "current_lang_code":   "en",
        "current_lang_name":   "english",
        "device_mode":         "💻 Laptop / Full View",
        "active_tab":          "steps",
        "steps_chunk_index":   0,
        "steps_chunks":        [],
        "steps_total_chunks":  0,
        "guide_section_index": 0,
        "guide_sections":      [],
        "guide_total_sections":0,
        "faq_page_index":      0,
        "faq_groups":          [],
        "faq_total_pages":     0,
        "raw_voice_points":    "",
        "raw_full_guide":      "",
        "raw_faq":             "",
        "service_name":        "",
        "service_overview":    "",
        "tts_speed":           1.0,
        "last_audio_bytes":    None,
        "last_transcript":     "",
        "last_answer":         "",
        "last_chunks_used":    [],
        "stuck_mode":          False,
        "backend_url":         "",
        "backend_status":      "unknown",
        "gemini_api_key":      "",
        "_faq_page_text":      "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_all_navigation():
    st.session_state.steps_chunk_index   = 0
    st.session_state.guide_section_index = 0
    st.session_state.faq_page_index      = 0
    st.session_state.stuck_mode          = False
    st.session_state.last_transcript     = ""
    st.session_state.last_answer         = ""
    st.session_state.last_chunks_used    = []
    st.session_state._faq_page_text      = ""

def reset_steps():
    reset_all_navigation()


def go_next(tab):
    if tab == "steps":
        if st.session_state.steps_chunk_index < st.session_state.steps_total_chunks - 1:
            st.session_state.steps_chunk_index += 1
    elif tab == "full_guide":
        if st.session_state.guide_section_index < st.session_state.guide_total_sections - 1:
            st.session_state.guide_section_index += 1
    elif tab == "faq":
        if st.session_state.faq_page_index < st.session_state.faq_total_pages - 1:
            st.session_state.faq_page_index += 1


def go_previous(tab):
    if tab == "steps":
        if st.session_state.steps_chunk_index > 0:
            st.session_state.steps_chunk_index -= 1
    elif tab == "full_guide":
        if st.session_state.guide_section_index > 0:
            st.session_state.guide_section_index -= 1
    elif tab == "faq":
        if st.session_state.faq_page_index > 0:
            st.session_state.faq_page_index -= 1


def stuck_action():
    st.session_state.stuck_mode = not st.session_state.stuck_mode


def get_current_visible_text() -> str:
    """Returns the text currently visible on screen for the active tab."""
    tab = st.session_state.active_tab

    if tab == "steps":
        chunks = st.session_state.get("steps_chunks", [])
        idx = st.session_state.get("steps_chunk_index", 0)
        if chunks and idx < len(chunks):
            chunk = chunks[idx]
            pts = chunk.get("display_points", [])
            sec = chunk.get("section", "")
            if pts:
                return sec + "\n" + "\n".join(pts)
            return chunk.get("text", "")

    elif tab == "full_guide":
        sections = st.session_state.get("guide_sections", [])
        idx = st.session_state.get("guide_section_index", 0)
        if sections and idx < len(sections):
            s = sections[idx]
            return f"{s.get('title', '')}\n\n{s.get('content', '')}"

    elif tab == "faq":
        # Return stored FAQ page text (set by render_faq before buttons)
        return st.session_state.get("_faq_page_text", "")

    return ""


def get_current_tts_text() -> str:
    """
    Returns the text to speak for the Read button.
    CRITICAL: reads from the ACTIVE TAB only.
    Steps tab → reads step points
    Full Guide tab → reads section content  
    FAQ tab → reads FAQ pairs on current page
    """
    return get_current_visible_text()


def get_progress() -> tuple:
    tab = st.session_state.active_tab
    if tab == "steps":
        idx   = st.session_state.get("steps_chunk_index", 0)
        total = st.session_state.get("steps_total_chunks", 1)
    elif tab == "full_guide":
        idx   = st.session_state.get("guide_section_index", 0)
        total = st.session_state.get("guide_total_sections", 1)
    elif tab == "faq":
        idx   = st.session_state.get("faq_page_index", 0)
        total = st.session_state.get("faq_total_pages", 1)
    else:
        return 0, 1, 0.0
    fraction = (idx + 1) / max(total, 1)
    return idx, total, fraction