# utils/embeddings_store.py
# Saves and loads pre-built embeddings for each service folder
# embeddings.json format:
# {
#   "service": "learner_license",
#   "built_at": "2025-01-01 12:00:00",
#   "chunk_count": 87,
#   "chunks": [
#     {
#       "id": 0,
#       "source": "faq",
#       "section": "FAQ",
#       "text": "Question: ...\nAnswer: ...",
#       "embedding": [0.123, 0.456, ...]   ← 768 floats
#     },
#     ...
#   ]
# }

import json
import os
import math
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


# ─────────────────────────────────────────────────────
# SAVE EMBEDDINGS
# ─────────────────────────────────────────────────────

def save_embeddings(
    service_folder: str,
    chunks: List[Dict],
    embeddings: List[List[float]],
    knowledge_base_root: str = "knowledge_base"
) -> bool:
    """
    Saves chunks + their embeddings to embeddings.json
    inside the service folder.

    chunks: list of dicts from chunker.py (text, source, section, etc.)
    embeddings: parallel list of embedding vectors (one per chunk)
    """
    if len(chunks) != len(embeddings):
        print(f"ERROR: chunk count {len(chunks)} != embedding count {len(embeddings)}")
        return False

    service_path = Path(knowledge_base_root) / service_folder

    if not service_path.exists():
        print(f"ERROR: Service folder not found: {service_path}")
        return False

    output_path = service_path / "embeddings.json"

    data = {
        "service": service_folder,
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chunk_count": len(chunks),
        "chunks": []
    }

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        entry = {
            "id": i,
            "source": chunk.get("source", "unknown"),
            "section": chunk.get("section", ""),
            "text": chunk.get("text", ""),
            "word_count": chunk.get("word_count", 0),
            "embedding": embedding
        }
        # Preserve display_points if present (for voice UI)
        if "display_points" in chunk:
            entry["display_points"] = chunk["display_points"]

        data["chunks"].append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(chunks)} chunks to {output_path}")
    return True


# ─────────────────────────────────────────────────────
# LOAD EMBEDDINGS
# ─────────────────────────────────────────────────────

def load_embeddings(
    service_folder: str,
    knowledge_base_root: str = "knowledge_base"
) -> Optional[Dict]:
    """
    Loads embeddings.json for a service.
    Returns None if file doesn't exist (need to run build_embeddings.py first).
    """
    path = Path(knowledge_base_root) / service_folder / "embeddings.json"

    if not path.exists():
        print(f"WARNING: No embeddings found for {service_folder}")
        print(f"Run: python scripts/build_embeddings.py")
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


# ─────────────────────────────────────────────────────
# COSINE SIMILARITY
# ─────────────────────────────────────────────────────

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes cosine similarity between two vectors.
    Returns value between -1.0 and 1.0 (higher = more similar).
    Pure Python — no numpy needed.
    """
    if not vec_a or not vec_b:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


# ─────────────────────────────────────────────────────
# FIND TOP K CHUNKS
# ─────────────────────────────────────────────────────

def find_top_chunks(
    query_embedding: List[float],
    service_data: Dict,
    top_k: int = 3,
    min_similarity: float = 0.3
) -> List[Dict]:
    """
    Finds top_k most semantically similar chunks to the query.

    query_embedding: embedding vector of user's question
    service_data: loaded embeddings.json dict
    top_k: number of chunks to return
    min_similarity: minimum score to include (filters noise)

    Returns list of chunks sorted by similarity (highest first).
    Each chunk has an added 'similarity_score' field.
    """
    scored = []

    for chunk in service_data.get("chunks", []):
        chunk_embedding = chunk.get("embedding", [])
        if not chunk_embedding:
            continue

        score = cosine_similarity(query_embedding, chunk_embedding)

        # FAQ chunks get a small boost since they directly match questions
        if chunk.get("source") == "faq":
            score = min(score * 1.1, 1.0)

        scored.append({
            **chunk,
            "similarity_score": round(score, 4)
        })

    # Sort by similarity descending
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)

    # Filter by minimum similarity and return top_k
    results = [c for c in scored if c["similarity_score"] >= min_similarity]
    return results[:top_k]


# ─────────────────────────────────────────────────────
# CHECK IF EMBEDDINGS ARE BUILT
# ─────────────────────────────────────────────────────

def embeddings_exist(
    service_folder: str,
    knowledge_base_root: str = "knowledge_base"
) -> bool:
    """Quick check if embeddings.json exists for a service."""
    path = Path(knowledge_base_root) / service_folder / "embeddings.json"
    return path.exists()


def get_embedding_stats(
    service_folder: str,
    knowledge_base_root: str = "knowledge_base"
) -> Dict:
    """Returns basic stats about a service's embeddings."""
    data = load_embeddings(service_folder, knowledge_base_root)
    if not data:
        return {"exists": False}

    source_counts = {}
    for chunk in data.get("chunks", []):
        src = chunk.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    return {
        "exists": True,
        "service": data.get("service"),
        "built_at": data.get("built_at"),
        "total_chunks": data.get("chunk_count", 0),
        "by_source": source_counts
    }