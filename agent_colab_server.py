# ══════════════════════════════════════════════════════════════
# DO NOT RUN THIS FILE ON YOUR LAPTOP.
# This file contains code to COPY into your AGENT Google Colab.
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# COLAB CELL 1 — Install dependencies
# ──────────────────────────────────────────────────────────────
CELL_1 = """
!pip install -q sentence-transformers fastapi uvicorn nest-asyncio pyngrok gspread
print("All packages installed!")
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 2 — Google account authentication (for writing sheet)
# ──────────────────────────────────────────────────────────────
CELL_2 = """
import gspread
from google.colab import auth
from google.auth import default

print("Authenticating with Google... (A popup will appear, click allow)")
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)
print("Google Sheets authentication complete!")
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 3 — Load the Embedding Model
# ──────────────────────────────────────────────────────────────
CELL_3 = """
from sentence_transformers import SentenceTransformer
import torch

print("Loading model... please wait about 1 minute...")
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

print("Model ready on:", device.upper())
print("Dimension:", model.get_sentence_embedding_dimension())
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 4 — Create the FastAPI Server
# ──────────────────────────────────────────────────────────────
CELL_4 = """
import nest_asyncio
import uvicorn
import threading
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

nest_asyncio.apply()

app = FastAPI()

class EmbedRequest(BaseModel):
    text: str

class EmbedBatchRequest(BaseModel):
    texts: List[str]

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {
        "alive": True,
        "device": device,
        "model": "paraphrase-multilingual-MiniLM-L12-v2",
        "dimension": model.get_sentence_embedding_dimension()
    }

@app.post("/embed")
def embed_single(req: EmbedRequest):
    try:
        vector = model.encode(req.text).tolist()
        return {"embedding": vector, "dimension": len(vector)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/embed_batch")
def embed_batch(req: EmbedBatchRequest):
    try:
        if not req.texts:
            return {"embeddings": [], "count": 0}
        vectors = model.encode(req.texts).tolist()
        return {"embeddings": vectors, "count": len(vectors)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

import time
time.sleep(2)
print("Server running on port 8000 internally.")
"""

# ──────────────────────────────────────────────────────────────
# COLAB CELL 5 — Connect Ngrok & Write to Google Sheet Automatically
# ──────────────────────────────────────────────────────────────
CELL_5 = """
from pyngrok import ngrok
import time

# Use the exact token provided by user:
ngrok.set_auth_token("3CSdXfMLxgLNklo9Ifx4ANChIcs_64WbXa27b2L8B3YciU2JA")

ngrok.kill()
time.sleep(1)

tunnel = ngrok.connect(8000)
public_url = tunnel.public_url

print("=" * 50)
print(f"AGENT NGROK URL: {public_url}")
print("=" * 50)
print("Writing this to Google Sheet: 14oa-bmjbl3FTOFf-Bt5NE70_HcJ0veTOztfmpIQrJkQ ...")

# Open the new sheet by ID
try:
    worksheet = gc.open_by_key("14oa-bmjbl3FTOFf-Bt5NE70_HcJ0veTOztfmpIQrJkQ").sheet1
    
    # We write headers and data cleanly
    data_to_write = [
        ["agent_backend_url", public_url],
        ["status", "online"]
    ]
    
    # Write to A1:B2
    worksheet.update('A1:B2', data_to_write)
    print("✅ SUCCESS: Agent URL has been synced to Google Sheet!")
except Exception as e:
    print(f"❌ ERROR writing to sheet: {str(e)}")
    print("Please make sure the Google Account you authenticated in Cell 2 has EDIT access to this Sheet id!")
"""
