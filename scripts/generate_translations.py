"""Bulk-generate translated knowledge-base files using the local NLLB model."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from utils.translation_config import TranslationLanguage, get_supported_languages


SOURCE_FILES = ("full_guide.txt", "faq.txt", "voice_points.txt")
MODEL_NAME = "facebook/nllb-200-distilled-600M"
MODEL_SNAPSHOT = Path.home() / ".cache" / "huggingface" / "hub" / "models--facebook--nllb-200-distilled-600M" / "snapshots" / "f8d333a098d19b4fd9a8b18f94170487ad3f821d"
KNOWLEDGE_BASE_ROOT = PROJECT_ROOT / "knowledge_base"


def iter_service_folders() -> Iterable[Path]:
    for folder in sorted(KNOWLEDGE_BASE_ROOT.iterdir()):
        if folder.is_dir() and any((folder / name).exists() for name in SOURCE_FILES):
            yield folder


def should_translate_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if set(stripped) <= {"=", "-", "_", "*"}:
        return False
    return any(ch.isalpha() for ch in stripped)


def grouped_text_blocks(lines: List[str], max_chars: int = 1200) -> List[tuple[str, str]]:
    """Group consecutive translatable lines into larger blocks for faster inference."""
    result: List[tuple[str, str]] = []
    current: List[str] = []
    current_size = 0

    def flush() -> None:
        nonlocal current, current_size
        if current:
            result.append(("translate", "\n".join(current)))
            current = []
            current_size = 0

    for line in lines:
        if should_translate_line(line):
            next_size = current_size + len(line) + 1
            if current and next_size > max_chars:
                flush()
            current.append(line)
            current_size += len(line) + 1
        else:
            flush()
            result.append(("raw", line))

    flush()
    return result


class LocalTranslator:
    def __init__(self) -> None:
        model_source = str(MODEL_SNAPSHOT) if MODEL_SNAPSHOT.exists() else MODEL_NAME
        local_only = MODEL_SNAPSHOT.exists()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_source, local_files_only=local_only)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_source, local_files_only=local_only)
        self.model.to(self.device)
        self.model.eval()
        self.tokenizer.src_lang = "eng_Latn"

    def translate_blocks(self, blocks: List[tuple[str, str]], target_model_code: str) -> List[tuple[str, str]]:
        pending_idx = [i for i, block in enumerate(blocks) if block[0] == "translate"]
        if not pending_idx:
            return blocks[:]

        output_blocks = blocks[:]
        batch_size = 16 if self.device == "cuda" else 4
        forced_id = self.tokenizer.convert_tokens_to_ids(target_model_code)

        for start in range(0, len(pending_idx), batch_size):
            batch_indices = pending_idx[start:start + batch_size]
            batch_texts = [blocks[i][1] for i in batch_indices]
            encoded = self.tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with torch.no_grad():
                generated = self.model.generate(
                    **encoded,
                    forced_bos_token_id=forced_id,
                    max_new_tokens=384,
                )
            decoded = self.tokenizer.batch_decode(generated, skip_special_tokens=True)
            for idx, translated in zip(batch_indices, decoded):
                output_blocks[idx] = ("translate", translated.strip())

        return output_blocks


def translate_file(translator: LocalTranslator, source_path: Path, target_path: Path, language: TranslationLanguage) -> None:
    original = source_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    blocks = grouped_text_blocks(lines)
    translated_blocks = translator.translate_blocks(blocks, language.model_code or "")
    translated_text = "\n".join(text for _, text in translated_blocks)
    target_path.write_text(translated_text + ("\n" if original.endswith("\n") else ""), encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    translator = LocalTranslator()
    supported = get_supported_languages()
    print(f"Device: {translator.device}")
    print(f"Languages: {len(supported)}")

    for service_folder in iter_service_folders():
        print(f"\n=== {service_folder.name} ===")
        translations_root = service_folder / "translations"
        for language in supported:
            target_dir = translations_root / language.code
            target_dir.mkdir(parents=True, exist_ok=True)
            print(f"  -> {language.name}")
            for filename in SOURCE_FILES:
                source_path = service_folder / filename
                if not source_path.exists():
                    continue
                target_path = target_dir / filename
                translate_file(translator, source_path, target_path, language)
                print(f"     saved {target_path.name}")

    print("\nTranslation generation complete.")


if __name__ == "__main__":
    main()
