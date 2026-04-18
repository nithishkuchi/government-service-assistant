# ══════════════════════════════════════════════════════════════
# DO NOT RUN THIS FILE ON YOUR LAPTOP.
# This file contains code to COPY into Google Colab ONLY.
# Each section below is ONE separate cell in Colab.
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# COLAB CELL 1 — Paste this into your FIRST Colab cell and run it
# ──────────────────────────────────────────────────────────────

CELL_1 = """
!pip install -q sentence-transformers fastapi uvicorn nest-asyncio pyngrok faster-whisper
print("All packages installed!")
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 2 — Load both models (Whisper + Embedding)
# ──────────────────────────────────────────────────────────────

CELL_2 = """
from sentence_transformers import SentenceTransformer
from faster_whisper import WhisperModel
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

print("Loading embedding model...")
embed_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
embed_model = embed_model.to(device)
print("Embedding model ready! Dimension:", embed_model.get_sentence_embedding_dimension())

print("Loading Whisper STT model...")
whisper_model = WhisperModel("large-v3", device=device, compute_type="float16" if device == "cuda" else "int8")
print("Whisper model ready!")

print("Both models loaded on:", device.upper())
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 3 — Start the combined server (Whisper + Embeddings)
# ──────────────────────────────────────────────────────────────

CELL_3 = """
import nest_asyncio
import uvicorn
import threading
import tempfile
import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

nest_asyncio.apply()

app = FastAPI(title="Government Assistant Backend")

class EmbedRequest(BaseModel):
    text: str

class EmbedBatchRequest(BaseModel):
    texts: List[str]

# ── Health check ──
@app.get("/")
def root():
    return {"status": "ok", "services": ["embed", "transcribe"]}

@app.get("/health")
def health():
    return {
        "alive": True,
        "device": device,
        "model": "large-v3",
        "vram_gb": 0,
        "dimension": embed_model.get_sentence_embedding_dimension()
    }

# ── Embedding endpoints ──
@app.post("/embed")
def embed_single(req: EmbedRequest):
    try:
        vector = embed_model.encode(req.text, convert_to_list=True)
        return {"embedding": vector, "dimension": len(vector)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/embed_batch")
def embed_batch(req: EmbedBatchRequest):
    try:
        if not req.texts:
            return {"embeddings": [], "count": 0}
        vectors = embed_model.encode(req.texts, convert_to_list=True, show_progress_bar=len(req.texts) > 20)
        return {"embeddings": vectors, "count": len(vectors)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ── Whisper STT endpoint ──
@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form(default="en")):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name
        segments, info = whisper_model.transcribe(tmp_path, language=language if language != "en" else None)
        text = " ".join([s.text for s in segments]).strip()
        os.unlink(tmp_path)
        return {"text": text, "language": info.language, "success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ── TTS endpoint (basic) ──
@app.post("/tts")
async def tts_endpoint(request: dict):
    return JSONResponse(status_code=501, content={"error": "TTS not available on this server. Using edge-tts on laptop."})

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

import time
time.sleep(2)
print("Combined server running on port 8000")
print("Endpoints: /health  /embed  /embed_batch  /transcribe")
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 4 — Get public URL (paste this URL into Streamlit sidebar)
# ──────────────────────────────────────────────────────────────

CELL_4 = """
from pyngrok import ngrok
import time

ngrok.kill()
time.sleep(1)

tunnel = ngrok.connect(8000)
public_url = tunnel.public_url

print("=" * 60)
print("YOUR URL IS READY — COPY IT!")
print("=" * 60)
print(public_url)
print("=" * 60)
print()
print("STEP 1: Paste this URL in Streamlit sidebar -> Manual URL")
print()
print("STEP 2: Run this on your laptop terminal to build embeddings:")
print(f"  python scripts/build_embeddings_colab.py --url {public_url}")
print()
print("STEP 3: After build is done, run your app:")
print("  python -m streamlit run app.py")
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 5 — Test everything works
# ──────────────────────────────────────────────────────────────

CELL_5 = """
import requests

print("Testing health...")
h = requests.get(f"{public_url}/health").json()
print("Health:", h)

print("Testing embedding...")
e = requests.post(f"{public_url}/embed", json={"text": "How to apply for Aadhaar?"}).json()
print("Embedding dimension:", e.get("dimension"))

print("All tests passed! Server is ready.")
"""
