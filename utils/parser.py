# utils/parser.py - FIXED
# FAQ parser now handles both formats:
#   "Question: ..."  and  "1. Question: ..."

import re
from pathlib import Path
from typing import List, Dict, Optional
from utils.chunker import get_display_chunks


def load_service_folder(service_folder: str, knowledge_base_root: str = "knowledge_base", lang_code: str = "en") -> Dict[str, str]:
    base_path = Path(knowledge_base_root) / service_folder
    
    if lang_code and lang_code != "en":
        target_path = base_path / "translations" / lang_code
        path = target_path if target_path.exists() else base_path
    else:
        path = base_path
        
    result = {}
    for key, filename in [("full_guide","full_guide.txt"),("faq","faq.txt"),("voice_points","voice_points.txt")]:
        file_path = path / filename
        # Fallback to English if translation file is missing
        if not file_path.exists() and path != base_path:
            file_path = base_path / filename
        result[key] = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    return result


def parse_full_guide_sections(text: str) -> List[Dict]:
    sections = []
    divider = re.compile(r"={4,}")
    parts = divider.split(text)
    current_number = 0
    current_title = "Introduction"

    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue

        lines = part.split("\n")
        first_line = lines[0].strip()
        title_match = re.match(r"^(\d+)\.\s+(.+)", first_line)

        if title_match and len(lines) <= 3:
            current_number = int(title_match.group(1))
            current_title = first_line
            i += 1
            while i < len(parts):
                body = parts[i].strip()
                if body:
                    sections.append({"number": current_number, "title": current_title, "content": body})
                    i += 1
                    break
                i += 1
        else:
            if part:
                sections.append({"number": current_number, "title": current_title, "content": part})
            i += 1

    if not sections and text.strip():
        sections.append({"number": 1, "title": "Service Information", "content": text.strip()})

    return sections


def parse_faq_pairs(text: str) -> List[Dict]:
    pairs = []
    # Force line breaks before numbered points if they were merged by translation
    text = re.sub(r'(?<=\S)\s+(?=\d+\.\s)', '\n', text)
    lines = text.split("\n")
    
    # Fast check for explicit English markers
    has_explicit = any(line.lower().strip().startswith(("question:", "q:", "answer:", "a:")) for line in lines)
    if has_explicit:
        current_q, current_a = "", ""
        collecting_answer = False
        for line in lines:
            line = line.strip()
            if not line: continue
            line_no_num = re.sub(r"^\d+\.\s+", "", line)
            
            low = line_no_num.lower()
            if low.startswith("question:") or low.startswith("q:"):
                if current_q and current_a: pairs.append({"question": current_q, "answer": current_a.strip()})
                idx = 9 if low.startswith("question:") else 2
                current_q = line_no_num[idx:].strip()
                current_a = ""
                collecting_answer = False
            elif low.startswith("answer:") or low.startswith("a:"):
                idx = 7 if low.startswith("answer:") else 2
                current_a = line_no_num[idx:].strip()
                collecting_answer = True
            elif collecting_answer:
                current_a += " " + line
        if current_q and current_a: pairs.append({"question": current_q, "answer": current_a.strip()})
        return pairs

    # Fallback 1: Numbered blocks or question marks
    blocks = []
    current_block = []
    for line in lines:
        line = line.strip()
        if not line: continue
        # Ignore cosmetic translators adding header lines
        if re.match(r'^[=*-]{4,}$', line): continue
        if line.lower() in ["faqs", "faq"]: continue
            
        if re.match(r"^\d+\.\s+", line) or line.endswith("?"):
            if current_block: blocks.append(current_block)
            current_block = [re.sub(r"^\d+\.\s+", "", line)]
        else:
            current_block.append(line)
    if current_block: blocks.append(current_block)
    
    for block in blocks:
        if len(block) >= 2:
            pairs.append({"question": block[0], "answer": " ".join(block[1:])})
        elif len(block) == 1:
            pairs.append({"question": block[0], "answer": block[0]})
            
    # Fallback 2: Alternating Empty-line paragraphs
    if not pairs:
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i in range(0, len(paras)-1, 2):
            pairs.append({"question": paras[i], "answer": paras[i+1]})

    return pairs


def parse_voice_point_chunks(text: str, laptop_mode: bool = True) -> List[Dict]:
    return get_display_chunks(text, laptop_mode=laptop_mode)


def group_faq_for_display(pairs: List[Dict], pairs_per_chunk: int = 5) -> List[List[Dict]]:
    groups = []
    for i in range(0, len(pairs), pairs_per_chunk):
        groups.append(pairs[i:i + pairs_per_chunk])
    return groups


def extract_service_name(full_guide_text: str) -> str:
    match = re.search(r"SERVICE\s+NAME[:\s]+(.+)", full_guide_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Government Service"


def extract_overview(full_guide_text: str) -> str:
    match = re.search(r"OVERVIEW[:\s]+(.*?)(?=={4,}|\Z)", full_guide_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()[:600]
    sections = parse_full_guide_sections(full_guide_text)
    if sections:
        return sections[0]["content"][:600]
    return full_guide_text.strip()[:400]