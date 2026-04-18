# Walkthrough: Dual Colab Backend Architecture

We have successfully split the application backend into two independent systems to avoid Ngrok authentication conflicts. The app now handles a Voice Server (Whisper) and an Agent Server (Embeddings) simultaneously.

## Step 1: Upgraded UI Sidebar
The Streamlit app (`app.py`) has been upgraded. If you look at the sidebar under the gear icon, you will now see **two** distinct control zones:
1. **🎙️ Voice Server:** Tracks the Whisper Colab URL.
2. **🧠 Agent Server:** Tracks the distinct Agent Colab URL.

## Step 2: Wrote Dedicated Agent Colab Code
A new file called [agent_colab_server.py](file:///c:/Users/nithi/OneDrive/Documents/New%20project/agent_colab_server.py) has been generated exclusively for your second notebook.
- It includes your specific new Google Sheet ID `14oa-bmjbl3...`
- It includes your specific Ngrok Authentication Token `3CSdXfML...`
- When you run Cell 5, it connects to ngrok and immediately updates your new Google Sheet!

## Step 3: Updated Backend RAG Routing
We modified `utils/rag_engine.py` and `utils/colab_config.py`. 
- The RAG Engine now strictly dials the `agent_backend_url` to perform matrix embedding operations, completely ignoring the Voice URL line. 

> [!TIP]
> You can now confidently run **both** notebooks side-by-side using your two separate Google accounts! The UI will fetch both URLs dynamically and assign them to the correct background operations.
