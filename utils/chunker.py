# utils/chunker.py
# Splits knowledge base files into chunks for embedding
# Handles three file formats:
#   full_guide.txt  — sections with === dividers and numbered headings
#   faq.txt         — Question: / Answer: pairs
#   voice_points.txt — SECTION A: headings with numbered points

import re
from typing import List, Dict


# ─────────────────────────────────────────────────────
# FULL GUIDE CHUNKER
# Splits on === dividers and numbered section headings
# ─────────────────────────────────────────────────────

def chunk_full_guide(text: str, max_words: int = 200, overlap_words: int = 30) -> List[Dict]:
    """
    Splits full_guide.txt into semantic chunks.

    Detects section boundaries marked by:
      ================================================
      1. SECTION TITLE
      ================================================

    Each section becomes one or more chunks depending on length.
    Overlap carries last N words of previous chunk into next.
    """
    chunks = []

    # Split on === divider lines (4+ equals signs)
    divider_pattern = re.compile(r"={4,}")
    section_pattern = re.compile(r"^\s*\d+\.\s+.+", re.MULTILINE)

    # Force newlines before section numbers if merged by translation
    text = re.sub(r'(?<=\S)\s+(?=\d+\.\s+[A-Z])', '\n', text)
    
    # Find all section blocks between dividers
    parts = divider_pattern.split(text)

    current_section_title = "Introduction"
    buffer = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check if this part is a section title line (short, no body text)
        lines = part.split("\n")
        first_line = lines[0].strip()

        # Detect numbered section title: "1. WHAT IS A LEARNER'S LICENCE?"
        if re.match(r"^\d+\.\s+.+", first_line) and len(lines) <= 3:
            current_section_title = first_line
            # Remaining lines after the title are body content
            body = "\n".join(lines[1:]).strip()
            if body:
                buffer.append((current_section_title, body))
        else:
            # This is body content — associate with current section title
            buffer.append((current_section_title, part))

    # Now chunk each buffer entry by word count
    for title, body in buffer:
        words = body.split()
        if not words:
            continue

        if len(words) <= max_words:
            # Small enough to be one chunk
            chunks.append({
                "source": "full_guide",
                "section": title,
                "text": f"{title}\n\n{body}",
                "word_count": len(words)
            })
        else:
            # Split into overlapping sub-chunks
            start = 0
            while start < len(words):
                end = min(start + max_words, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "source": "full_guide",
                    "section": title,
                    "text": f"{title}\n\n{chunk_text}",
                    "word_count": len(chunk_words)
                })
                if end == len(words):
                    break
                start = end - overlap_words

    return chunks


# ─────────────────────────────────────────────────────
# FAQ CHUNKER
# Each Q+A pair becomes one chunk (highest retrieval priority)
# ─────────────────────────────────────────────────────

def chunk_faq(text: str) -> List[Dict]:
    """
    Splits faq.txt into individual Q+A chunks.

    Format expected:
      Question: text here
      Answer: text here

    Each pair becomes one chunk. These are highest priority
    because the question text closely matches user queries.
    """
    chunks = []
    lines = text.split("\n")

    current_q = ""
    current_a = ""
    collecting_answer = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith("question:"):
            # Save previous pair if exists
            if current_q and current_a:
                chunks.append({
                    "source": "faq",
                    "section": "FAQ",
                    "text": f"Question: {current_q}\nAnswer: {current_a}",
                    "word_count": len((current_q + current_a).split())
                })
            current_q = line[len("question:"):].strip()
            current_a = ""
            collecting_answer = False

        elif line.lower().startswith("answer:"):
            current_a = line[len("answer:"):].strip()
            collecting_answer = True

        elif collecting_answer:
            # Multi-line answer continuation
            current_a += " " + line

    # Save last pair
    if current_q and current_a:
        chunks.append({
            "source": "faq",
            "section": "FAQ",
            "text": f"Question: {current_q}\nAnswer: {current_a}",
            "word_count": len((current_q + current_a).split())
        })

    return chunks


# ─────────────────────────────────────────────────────
# VOICE POINTS CHUNKER
# Groups numbered points under each SECTION heading
# ─────────────────────────────────────────────────────

def chunk_voice_points(text: str, points_per_chunk: int = 8) -> List[Dict]:
    """
    Splits voice_points.txt into display chunks.

    Format expected:
      SECTION A: HEADING TEXT
      1. point one
      2. point two
      ...
      SECTION B: NEXT HEADING
      ...

    Groups points_per_chunk numbered points per chunk.
    This is also used for the UI step navigation.
    """
    chunks = []
    # Force newlines before numbers if merged by translation
    text = re.sub(r'(?<=\S)\s+(?=\d+\.\s)', '\n', text)
    lines = text.split("\n")

    current_section = "General"
    current_points = []

    section_pattern = re.compile(r"^SECTION\s+[A-Z]+:\s*(.+)", re.IGNORECASE)
    point_pattern = re.compile(r"^\d+\.\s+.+")

    def flush_points(section, points, points_per_chunk):
        """Break accumulated points into display chunks."""
        result = []
        for i in range(0, len(points), points_per_chunk):
            batch = points[i:i + points_per_chunk]
            result.append({
                "source": "voice_points",
                "section": section,
                "text": f"{section}\n\n" + "\n".join(batch),
                "word_count": len(" ".join(batch).split()),
                "display_points": batch
            })
        return result

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        section_match = section_pattern.match(line_stripped)
        if section_match:
            # Flush current points before starting new section
            if current_points:
                chunks.extend(flush_points(current_section, current_points, points_per_chunk))
                current_points = []
            current_section = line_stripped  # Keep full "SECTION A: HEADING" as label
            continue

        if point_pattern.match(line_stripped):
            current_points.append(line_stripped)

    # Flush remaining points
    if current_points:
        chunks.extend(flush_points(current_section, current_points, points_per_chunk))

    return chunks


# ─────────────────────────────────────────────────────
# MASTER CHUNKER
# Processes all three files for one service
# ─────────────────────────────────────────────────────

def chunk_service_files(
    full_guide_text: str = "",
    faq_text: str = "",
    voice_points_text: str = "",
) -> List[Dict]:
    """
    Chunks all three files for a service.
    Returns combined list with source labels.
    FAQ chunks are ordered first (highest retrieval priority).
    """
    all_chunks = []

    # FAQ first — closest match to user questions
    if faq_text.strip():
        faq_chunks = chunk_faq(faq_text)
        all_chunks.extend(faq_chunks)

    # Full guide — detailed content
    if full_guide_text.strip():
        guide_chunks = chunk_full_guide(full_guide_text)
        all_chunks.extend(guide_chunks)

    # Voice points — step navigation content
    if voice_points_text.strip():
        voice_chunks = chunk_voice_points(voice_points_text)
        all_chunks.extend(voice_chunks)

    return all_chunks


# ─────────────────────────────────────────────────────
# VOICE POINTS DISPLAY CHUNKER (for UI navigation only)
# Returns chunks sized for clean page display
# ─────────────────────────────────────────────────────

def get_display_chunks(voice_points_text: str, laptop_mode: bool = True) -> List[Dict]:
    """
    Returns voice_points chunks sized for display.
    Laptop: 8 points per page
    Phone:  5 points per page
    """
    points_per_chunk = 8 if laptop_mode else 5
    return chunk_voice_points(voice_points_text, points_per_chunk=points_per_chunk)