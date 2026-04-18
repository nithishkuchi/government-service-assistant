# utils/knowledge_router.py
# Maps service display names to folder names
# Reads the three knowledge base files for any service
# Handles missing files gracefully

from pathlib import Path
from typing import Dict, Optional, Tuple


# ─────────────────────────────────────────────────────
# SERVICE DISPLAY NAME → FOLDER NAME MAPPING
# ─────────────────────────────────────────────────────

SERVICE_FOLDER_MAP = {
    "PAN Card Application":       "pan_card",
    "Aadhaar Card":               "aadhaar",
    "Passport Application":       "passport",
    "Driving Licence":            "driving_license",
    "Learner's Licence":          "learner_license",
    "Voter ID Card":              "voter_card",
    "Birth Certificate":          "birth_certificate",
    "Death Certificate":          "death_certificate",
    "Caste Certificate":          "caste_certificate",
    "Income Certificate":         "income_certificate",
    "EWS Certificate":            "ews_certificate",
}

# Reverse map: folder name → display name
FOLDER_SERVICE_MAP = {v: k for k, v in SERVICE_FOLDER_MAP.items()}

# All display names in order for dropdown
SERVICE_NAMES = list(SERVICE_FOLDER_MAP.keys())


# ─────────────────────────────────────────────────────
# GET FOLDER FOR A SERVICE
# ─────────────────────────────────────────────────────

def get_folder(service_display_name: str) -> Optional[str]:
    """Returns folder name for a service display name."""
    return SERVICE_FOLDER_MAP.get(service_display_name)


def get_display_name(folder_name: str) -> str:
    """Returns display name for a folder name."""
    return FOLDER_SERVICE_MAP.get(folder_name, folder_name.replace("_", " ").title())


# ─────────────────────────────────────────────────────
# READ SERVICE FILES
# ─────────────────────────────────────────────────────

def read_service_files(
    service_display_name: str,
    knowledge_base_root: str = "knowledge_base"
) -> Dict[str, str]:
    """
    Reads all three knowledge base files for a service.

    Returns dict with keys: full_guide, faq, voice_points
    Missing files return empty string (handled gracefully).
    """
    folder = get_folder(service_display_name)
    if not folder:
        return {"full_guide": "", "faq": "", "voice_points": "", "error": f"Unknown service: {service_display_name}"}

    service_path = Path(knowledge_base_root) / folder
    if not service_path.exists():
        return {"full_guide": "", "faq": "", "voice_points": "", "error": f"Folder not found: {service_path}"}

    result = {"full_guide": "", "faq": "", "voice_points": "", "folder": folder}

    for file_key, filename in [("full_guide", "full_guide.txt"), ("faq", "faq.txt"), ("voice_points", "voice_points.txt")]:
        file_path = service_path / filename
        if file_path.exists():
            result[file_key] = file_path.read_text(encoding="utf-8")
        else:
            print(f"WARNING: {filename} not found for {service_display_name}")

    return result


def read_service_files_by_folder(
    folder_name: str,
    knowledge_base_root: str = "knowledge_base"
) -> Dict[str, str]:
    """Same as read_service_files but accepts folder name directly."""
    display_name = get_display_name(folder_name)
    return read_service_files(display_name, knowledge_base_root)


# ─────────────────────────────────────────────────────
# GET SERVICE OVERVIEW
# Extracts the overview/intro from full_guide.txt
# ─────────────────────────────────────────────────────

def get_service_overview(full_guide_text: str) -> str:
    """
    Extracts overview section from full_guide.txt.
    Looks for OVERVIEW or WHAT IS sections.
    Falls back to first 300 chars if not found.
    """
    import re
    # Try OVERVIEW section
    match = re.search(r"OVERVIEW[:\s]+(.*?)(?=={4,}|\Z)", full_guide_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()[:500]

    # Try WHAT IS section (first numbered section)
    match = re.search(r"={4,}\s*\n\s*1\..+?\n={4,}\s*\n(.+?)(?=={4,}|\Z)", full_guide_text, re.DOTALL)
    if match:
        return match.group(1).strip()[:500]

    # Fallback
    return full_guide_text.strip()[:300]


# ─────────────────────────────────────────────────────
# LIST ALL SERVICES WITH EMBEDDING STATUS
# ─────────────────────────────────────────────────────

def get_all_service_status(knowledge_base_root: str = "knowledge_base") -> Dict:
    """
    Returns status of all services — which have embeddings built.
    Useful for the build script and diagnostics.
    """
    from utils.embeddings_store import embeddings_exist

    status = {}
    for display_name, folder in SERVICE_FOLDER_MAP.items():
        folder_path = Path(knowledge_base_root) / folder
        status[display_name] = {
            "folder": folder,
            "folder_exists": folder_path.exists(),
            "embeddings_built": embeddings_exist(folder, knowledge_base_root),
            "files": {
                "full_guide": (folder_path / "full_guide.txt").exists(),
                "faq": (folder_path / "faq.txt").exists(),
                "voice_points": (folder_path / "voice_points.txt").exists(),
            }
        }
    return status