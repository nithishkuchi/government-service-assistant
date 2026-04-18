# scripts/build_embeddings_colab.py
# Builds embeddings.json for all services using your Colab embedding server.
# Run this ONCE after setting up the Colab server.
#
# Usage:
#   python scripts/build_embeddings_colab.py --url https://xxxx.ngrok-free.app
#   (Make sure you use the AGENT URL, not the Whisper URL!)
#
# This replaces the old build_embeddings.py which used Gemini (rate limited).
# This version uses your Agent Colab GPU — unlimited, fast, free.

import sys
import os
import time
import json
import argparse
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from utils.chunker import chunk_service_files
from utils.embeddings_store import save_embeddings
from utils.knowledge_router import SERVICE_FOLDER_MAP

KNOWLEDGE_BASE_ROOT = "knowledge_base"
BATCH_SIZE = 32  # Embed this many chunks at once for speed


def embed_batch_via_colab(texts: list, colab_url: str) -> list:
    """Send a batch of texts to the Colab server and get back embeddings."""
    try:
        headers = {"ngrok-skip-browser-warning": "true"}
        response = requests.post(
            f"{colab_url.rstrip('/')}/embed_batch",
            json={"texts": texts},
            headers=headers,
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("embeddings", [])
        else:
            try:
                err_msg = response.json().get("error", str(response.text))
            except:
                err_msg = response.text
            print(f"    Server error: {response.status_code} - {err_msg}")
            return [[] for _ in texts]
    except Exception as e:
        print(f"    Connection error: {e}")
        return [[] for _ in texts]


def process_service(folder_name: str, colab_url: str) -> dict:
    print(f"\n{'='*50}")
    print(f"Processing: {folder_name}")
    print(f"{'='*50}")

    service_path = Path(KNOWLEDGE_BASE_ROOT) / folder_name
    if not service_path.exists():
        print(f"  SKIP — folder not found")
        return {"status": "skipped"}

    def read_file(filename):
        path = service_path / filename
        if path.exists():
            text = path.read_text(encoding="utf-8")
            print(f"  ✓ {filename}: {len(text)} chars")
            return text
        print(f"  ✗ MISSING: {filename}")
        return ""

    full_guide  = read_file("full_guide.txt")
    faq         = read_file("faq.txt")
    voice_pts   = read_file("voice_points.txt")

    if not full_guide and not faq and not voice_pts:
        print("  SKIP — no content")
        return {"status": "skipped"}

    # Chunk all files
    chunks = chunk_service_files(full_guide_text=full_guide, faq_text=faq, voice_points_text=voice_pts)
    print(f"\n  Chunks to embed: {len(chunks)}")

    # Embed in batches
    all_embeddings = []
    texts = [c.get("text", "") for c in chunks]

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        print(f"  Embedding batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1} ({len(batch)} chunks)...", end="", flush=True)
        embeddings = embed_batch_via_colab(batch, colab_url)
        all_embeddings.extend(embeddings)
        print(f" ✓")

    # Save
    success = save_embeddings(
        service_folder=folder_name,
        chunks=chunks,
        embeddings=all_embeddings,
        knowledge_base_root=KNOWLEDGE_BASE_ROOT
    )

    status = "done" if success else "error"
    print(f"  {'✅ DONE' if success else '❌ FAILED'} — {len(chunks)} chunks saved")
    return {"status": status, "chunks": len(chunks)}


def main():
    parser = argparse.ArgumentParser(description="Build embeddings using Colab server")
    parser.add_argument("--url", required=True, help="Colab ngrok URL e.g. https://xxxx.ngrok-free.app")
    args = parser.parse_args()

    colab_url = args.url.rstrip("/")

    print("=" * 60)
    print("EMBEDDING BUILDER (Colab GPU Version)")
    print("=" * 60)

    # Check server health
    print(f"\nChecking Colab server: {colab_url}")
    try:
        headers = {"ngrok-skip-browser-warning": "true"}
        health = requests.get(f"{colab_url}/health", headers=headers, timeout=10).json()
        print(f"✅ Server OK — Model: {health.get('model','?')} | Device: {health.get('device','?').upper()}")
        print(f"   Embedding dimension: {health.get('dimension','?')}")
    except Exception as e:
        print(f"❌ Cannot reach Colab server: {e}")
        print("   Make sure all 4 Colab cells are running before you run this script!")
        sys.exit(1)

    # Find all service folders
    all_folders = list(SERVICE_FOLDER_MAP.values())
    existing = [f for f in all_folders if (Path(KNOWLEDGE_BASE_ROOT) / f).exists()]

    print(f"\nServices found: {len(existing)}")
    print(f"Estimated time: ~{len(existing) * 1}-{len(existing) * 2} minutes (GPU is fast!)")
    print(f"\nStarting automatic build...")

    results = {}
    start = time.time()

    for folder in existing:
        try:
            results[folder] = process_service(folder, colab_url)
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
            break
        except Exception as e:
            print(f"\nFATAL ERROR for {folder}: {e}")
            results[folder] = {"status": "error"}

    elapsed = int(time.time() - start)
    done = [f for f, r in results.items() if r.get("status") == "done"]
    errs = [f for f, r in results.items() if r.get("status") == "error"]

    print(f"\n{'='*60}")
    print(f"✅ BUILD COMPLETE — {elapsed//60}m {elapsed%60}s")
    print(f"   Done: {len(done)} | Errors: {len(errs)}")
    print(f"\nYou can now run: python -m streamlit run app.py")
    print("="*60)

if __name__ == "__main__":
    main()
