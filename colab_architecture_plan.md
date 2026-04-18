# Plan: Bifurcated Colab Architecture

This plan documents exactly how we will split the application backend into two separate Colab Notebooks — one dedicated purely to Whisper (Voice/Speech-to-Text) and the other dedicated entirely to the RAG Agent (Embeddings/Generation). 

## User Review Required

> [!WARNING]
> **Ngrok Accounts:** Colab uses the free version of Ngrok. Ngrok allows only ONE active tunnel per account. If you start Notebook A and Notebook B on the exact same Ngrok Key, Ngrok will instantly shut down the first notebook. 
> **You MUST create a second free ngrok account** (using a different email) to get a second ngrok auth token strictly for the Agent Colab notebook.

## Proposed Changes

We will modify multiple layers of the application to juggle two dynamic URLs simultaneously.

### UI Configuration (`app.py`)

#### [MODIFY] `app.py`
We will expand the Streamlit sidebar to accommodate both configurations cleanly.
- Add "Voice Server URL" text box and state mapper.
- Add "Agent Server URL" text box and state mapper.
- Implement dual status indicators handling timeouts and success correctly.

### State Syncing (`utils/colab_config.py`)

#### [MODIFY] `utils/colab_config.py`
- Expose a new function `get_agent_url_from_sheet()` tailored specifically to read from the newly provisioned sheet setup.
- Create a specific status dictionary handling the Agent's remote health endpoint (`/health`).

### Agent Engine (`utils/rag_engine.py`)

#### [MODIFY] `utils/rag_engine.py` (specifically `embed_query`)
- Update `colab_url = st.session_state.get("backend_url", "")` to specifically seek the new Agent URL property. This is the core routing change ensuring agent traffic ignores the voice tunnel.

### Embeddings Builder (`scripts/build_embeddings_colab.py`)

#### [MODIFY] `scripts/build_embeddings_colab.py`
- We will update the docs and CLI prompts so the user explicitly passes the Agent URL, not the Whisper URL.

### New Colab Code Generation (`agent_colab_server.py`)

#### [NEW] `agent_colab_server.py`
- Creates a pristine copy of the Embedding Server designed to be deployed cleanly onto the second notebook.
- **Includes the Google Sheets integration:** The notebook will automatically execute `gspread` to write the newly spun Ngrok URL dynamically into your selected Google Sheet.

## Open Questions

> [!IMPORTANT]
> **For the Google Sheet Implementation:** Since you want the Agent notebook to write its URL to a sheet automatically, do you want to:
> 1. Use the **exact same** Google Sheet file you currently use for Whisper, but create a new Tab named `AgentConfig`?
> 2. Create an **entirely new** Google Sheet file, necessitating adding a new `agent_sheet_id` property into `.streamlit/secrets.toml`?
> *(Option #1 is recommended for cleanliness)*

## Verification Plan
1. Test sidebar rendering ensures both inputs process correctly.
2. Verify `utils/rag_engine.py` successfully hooks requests into the `agent_backend_url` var.
3. Validate the `gspread` credentials mapping logic in the new Colab script operates equivalently to your Whisper methodology.
