# Government Service Assistant (Multilingual RAG)

This is a voice-enabled, multilingual AI assistant designed to provide step-by-step guidance for Indian government services like Aadhaar, Passport, PAN, and more.

## 🚀 Quick Start (Private Setup)

> [!IMPORTANT]
> **This repository is intended to be kept PRIVATE.** 
> It contains hardcoded configuration for your specific database and API endpoints. 

### 1. Prerequisites
- Python 3.9+
- A Google Colab account (for GPU tasks)
- A Groq or Gemini API key

### 2. Local Installation
1. Clone the repository to your laptop.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python -m streamlit run app.py
   ```

## 🧠 Backend Architecture (Dual Colab)

This project uses two independent Google Colab notebooks to handle GPU-heavy tasks:
1. **Voice Notebook**: Handles Whisper (STT) and Audio Pipeline.
2. **Agent Notebook**: Handles Multilingual Embeddings (Sentence-Transformers).

The code for these servers is located in:
- `agent_colab_server.py`
- `colab_embedding_server.py`

## 🔐 Git Workflow

### How to push new changes:
Since you are not changing the hardcoded keys, updating GitHub is easy. Whenever you make a change to the UI or your knowledge base:

1. **Check Status**: `git status`
2. **Stage Changes**: `git add .`
3. **Commit**: `git commit -m "Describe your update here (e.g., added Passport guide)"`
4. **Push**: `git push origin main`

### Keeping it Safe
- **Always** keep the repository set to **Private** on GitHub.
- If you ever decide to make it public, you **must** move your keys to `.streamlit/secrets.toml` before changing it to public.

---

*This project was built as part of a final semester university presentation.*
