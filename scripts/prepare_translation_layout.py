"""Prepare per-service translation folders and a manifest for bulk generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.translation_config import ALL_REQUESTED_LANGUAGES, get_supported_languages
KNOWLEDGE_BASE_ROOT = PROJECT_ROOT / "knowledge_base"
SOURCE_FILES = ("full_guide.txt", "faq.txt", "voice_points.txt")


def list_service_folders() -> List[Path]:
    return sorted(
        folder for folder in KNOWLEDGE_BASE_ROOT.iterdir()
        if folder.is_dir() and any((folder / name).exists() for name in SOURCE_FILES)
    )


def build_manifest() -> Dict:
    services = []

    for service_folder in list_service_folders():
        files = []
        for filename in SOURCE_FILES:
            source_path = service_folder / filename
            if source_path.exists():
                files.append(
                    {
                        "filename": filename,
                        "source_path": str(source_path),
                        "char_count": len(source_path.read_text(encoding="utf-8")),
                    }
                )

        translations_root = service_folder / "translations"
        translations_root.mkdir(exist_ok=True)

        targets = []
        for language in ALL_REQUESTED_LANGUAGES:
            target_dir = translations_root / language.code
            target_dir.mkdir(exist_ok=True)
            targets.append(
                {
                    "code": language.code,
                    "name": language.name,
                    "native_name": language.native_name,
                    "category": language.category,
                    "supported_now": language.supported_now,
                    "notes": language.notes,
                    "target_dir": str(target_dir),
                }
            )

        services.append(
            {
                "service": service_folder.name,
                "source_dir": str(service_folder),
                "files": files,
                "targets": targets,
            }
        )

    return {
        "knowledge_base_root": str(KNOWLEDGE_BASE_ROOT),
        "source_files": list(SOURCE_FILES),
        "supported_now": [
            {"code": lang.code, "name": lang.name, "native_name": lang.native_name}
            for lang in get_supported_languages()
        ],
        "services": services,
    }


def main() -> None:
    manifest = build_manifest()
    output_path = PROJECT_ROOT / "translation_manifest.json"
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Prepared translation folders for {len(manifest['services'])} services.")
    print(f"Manifest written to: {output_path}")
    print(f"Supported-now languages: {len(manifest['supported_now'])}")


if __name__ == "__main__":
    main()
