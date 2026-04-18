# scripts/build_embeddings.py
# Run this ONCE after setting up knowledge base files.
# Builds embeddings.json for all 11 services.
#
# Usage:
#   python scripts/build_embeddings.py
#
# Requires:
#   - GEMINI_API_KEY in .streamlit/secrets.toml OR environment variable
#   - All knowledge_base/service_name/ folders with their .txt files
#
# Time: ~10-15 minutes for all 11 services
# API calls: ~600-900 total (within Gemini free tier)

import sys
import os
import time
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from utils.chunker import chunk_service_files
from utils.embeddings_store import save_embeddings
from utils.knowledge_router import SERVICE_FOLDER_MAP, read_service_files_by_folder


# ─────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────

KNOWLEDGE_BASE_ROOT = "knowledge_base"
DELAY_BETWEEN_CHUNKS = 0.5   # seconds between embedding API calls (rate limit safety)
DELAY_BETWEEN_SERVICES = 3.0 # seconds between services


# ─────────────────────────────────────────────────────
# GET API KEY
# ─────────────────────────────────────────────────────

def get_api_key() -> str:
    # Try environment variable first
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        return key

    # Try secrets.toml
    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists():
        content = secrets_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if "gemini_api_key" in line.lower():
                parts = line.split("=", 1)
                if len(parts) == 2:
                    val = parts[1].strip().strip('"').strip("'")
                    if val:
                        return val

    return ""


# ─────────────────────────────────────────────────────
# EMBED ONE CHUNK
# ─────────────────────────────────────────────────────

def embed_chunk(text: str, api_key: str) -> list:
    """Calls Gemini embedding API for one chunk."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]


# ─────────────────────────────────────────────────────
# PROCESS ONE SERVICE
# ─────────────────────────────────────────────────────

def process_service(folder_name: str, api_key: str) -> dict:
    """
    Reads all three files for a service, chunks them,
    embeds each chunk, saves embeddings.json.

    Returns stats dict.
    """
    print(f"\n{'='*50}")
    print(f"Processing: {folder_name}")
    print(f"{'='*50}")

    # Read files
    service_path = Path(KNOWLEDGE_BASE_ROOT) / folder_name
    if not service_path.exists():
        print(f"  SKIP — folder not found: {service_path}")
        return {"status": "skipped", "reason": "folder_not_found"}

    def read_file(filename):
        path = service_path / filename
        if path.exists():
            text = path.read_text(encoding="utf-8")
            print(f"  Read {filename}: {len(text)} characters")
            return text
        else:
            print(f"  MISSING: {filename}")
            return ""

    full_guide_text  = read_file("full_guide.txt")
    faq_text         = read_file("faq.txt")
    voice_points_text = read_file("voice_points.txt")

    if not full_guide_text and not faq_text and not voice_points_text:
        print(f"  SKIP — no content files found")
        return {"status": "skipped", "reason": "no_files"}

    # Chunk all files
    print(f"\n  Chunking files...")
    chunks = chunk_service_files(
        full_guide_text=full_guide_text,
        faq_text=faq_text,
        voice_points_text=voice_points_text
    )
    print(f"  Total chunks: {len(chunks)}")

    # Count by source
    source_counts = {}
    for c in chunks:
        src = c.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in source_counts.items():
        print(f"    {src}: {count} chunks")

    # Embed each chunk
    print(f"\n  Embedding {len(chunks)} chunks (this takes a few minutes)...")
    embeddings = []
    failed = 0

    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        if not text.strip():
            embeddings.append([])
            continue

        try:
            embedding = embed_chunk(text, api_key)
            embeddings.append(embedding)

            if (i + 1) % 10 == 0:
                print(f"    Progress: {i+1}/{len(chunks)}")

            time.sleep(DELAY_BETWEEN_CHUNKS)

        except Exception as e:
            print(f"    ERROR on chunk {i}: {e}")
            embeddings.append([])
            failed += 1
            time.sleep(2.0)  # Longer wait on error

    # Save embeddings
    print(f"\n  Saving embeddings.json...")
    success = save_embeddings(
        service_folder=folder_name,
        chunks=chunks,
        embeddings=embeddings,
        knowledge_base_root=KNOWLEDGE_BASE_ROOT
    )

    if success:
        print(f"  DONE — {len(chunks)} chunks saved ({failed} failed)")
    else:
        print(f"  ERROR — save failed")

    return {
        "status": "done" if success else "error",
        "total_chunks": len(chunks),
        "failed": failed,
        "by_source": source_counts
    }


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("KNOWLEDGE BASE EMBEDDING BUILDER")
    print("=" * 60)

    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("\nERROR: No Gemini API key found.")
        print("Add it to .streamlit/secrets.toml:")
        print('  [api_keys]')
        print('  gemini_api_key = "your_key_here"')
        print("OR set environment variable:")
        print('  export GEMINI_API_KEY=your_key_here')
        sys.exit(1)

    print(f"\nAPI Key: Found (starts with {api_key[:8]}...)")
    print(f"Knowledge base root: {KNOWLEDGE_BASE_ROOT}/")

    # Check which services exist
    all_folders = list(SERVICE_FOLDER_MAP.values())
    existing = [f for f in all_folders if (Path(KNOWLEDGE_BASE_ROOT) / f).exists()]
    missing = [f for f in all_folders if f not in existing]

    print(f"\nServices found: {len(existing)}")
    print(f"Services missing: {len(missing)}")

    if missing:
        print(f"Missing folders: {missing}")

    if not existing:
        print("\nERROR: No service folders found in knowledge_base/")
        sys.exit(1)

    # Confirm before starting
    print(f"\nAbout to embed {len(existing)} services.")
    print(f"Estimated time: {len(existing) * 3}-{len(existing) * 6} minutes")
    print(f"Estimated API calls: {len(existing) * 60}-{len(existing) * 90}")
    print(f"\nPress Enter to start, or Ctrl+C to cancel...")
    input()

    # Process each service
    results = {}
    start_time = time.time()

    for i, folder in enumerate(existing):
        try:
            result = process_service(folder, api_key)
            results[folder] = result

            if i < len(existing) - 1:
                print(f"\n  Waiting {DELAY_BETWEEN_SERVICES}s before next service...")
                time.sleep(DELAY_BETWEEN_SERVICES)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"\nFATAL ERROR for {folder}: {e}")
            results[folder] = {"status": "error", "reason": str(e)}

    # Summary
    elapsed = int(time.time() - start_time)
    print(f"\n{'='*60}")
    print(f"BUILD COMPLETE — {elapsed//60}m {elapsed%60}s")
    print(f"{'='*60}")

    done = [f for f, r in results.items() if r.get("status") == "done"]
    errors = [f for f, r in results.items() if r.get("status") == "error"]
    skipped = [f for f, r in results.items() if r.get("status") == "skipped"]

    print(f"Done:    {len(done)} services")
    print(f"Errors:  {len(errors)} services")
    print(f"Skipped: {len(skipped)} services")

    if errors:
        print(f"\nFailed services: {errors}")
        print("Re-run the script to retry failed services.")

    print(f"\nYou can now run: streamlit run app.py")


if __name__ == "__main__":
    main()