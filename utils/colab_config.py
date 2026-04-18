# utils/colab_config.py
# Fixed: Better CSV parsing for Google Sheet
# Fixed: Handles sheet not having VoicePipelineConfig tab yet

import streamlit as st
import requests


def get_backend_url_from_sheet() -> dict:
    """
    Read Colab URL from Google Sheet.
    Sheet must be public viewer access.
    """

    try:
        sheet_id = st.secrets.get("google_sheet", {}).get("sheet_id", "")

        if not sheet_id:
            return {
                "url": None,
                "status": "no_sheet_configured",
                "message": "Google Sheet ID not set in secrets.toml"
            }

        # Try VoicePipelineConfig tab first
        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            f"/gviz/tq?tqx=out:csv&sheet=VoicePipelineConfig"
        )

        response = requests.get(csv_url, timeout=8)

        if response.status_code != 200:
            return {
                "url": None,
                "status": "sheet_error",
                "message": (
                    "Cannot read Google Sheet. "
                    "Check Sheet ID and make sure sharing is set to Anyone with link = Viewer. "
                    f"HTTP status: {response.status_code}"
                )
            }

        # Parse CSV response
        lines = response.text.strip().split("\n")
        data = {}

        for line in lines:
            # Handle quoted CSV values properly
            line = line.strip()
            if not line:
                continue

            # Remove surrounding quotes from each field
            parts = line.replace('"', '').split(",", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key:
                    data[key] = value

        backend_url = data.get("backend_url", "").strip()

        if not backend_url or backend_url == "":
            return {
                "url": None,
                "status": "offline",
                "message": (
                    "Colab has not written its URL yet. "
                    "Start the Colab notebook and run all cells."
                )
            }

        # Validate URL format
        if not backend_url.startswith("http"):
            return {
                "url": None,
                "status": "invalid_url",
                "message": f"Invalid URL in sheet: {backend_url}"
            }

        return {
            "url": backend_url,
            "status": data.get("status", "unknown"),
            "last_updated": data.get("last_updated", "unknown"),
            "model": data.get("model", "large-v3"),
            "device": data.get("device", "cuda"),
            "vram_gb": data.get("vram_gb", "unknown"),
            "message": "Connected successfully"
        }

    except requests.exceptions.Timeout:
        return {
            "url": None,
            "status": "timeout",
            "message": "Google Sheet read timed out. Check internet connection."
        }
    except Exception as e:
        return {
            "url": None,
            "status": "error",
            "message": str(e)
        }

def get_agent_url_from_sheet() -> dict:
    """
    Read Agent Colab URL from Google Sheet.
    Sheet must be public viewer access.
    """
    try:
        sheet_id = st.secrets.get("google_sheet", {}).get("agent_sheet_id", "")
        sheet_name = st.secrets.get("google_sheet", {}).get("agent_sheet_name", "Sheet1")

        if not sheet_id:
            return {
                "url": None,
                "status": "no_sheet_configured",
                "message": "Agent Google Sheet ID not set in secrets.toml"
            }

        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            f"/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        )

        response = requests.get(csv_url, timeout=8)

        if response.status_code != 200:
            return {
                "url": None,
                "status": "sheet_error",
                "message": (
                    "Cannot read Agent Google Sheet. "
                    "Make sure sharing is set to Anyone with link = Viewer. "
                    f"HTTP status: {response.status_code}"
                )
            }

        lines = response.text.strip().split("\n")
        data = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.replace('"', '').split(",", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key:
                    data[key] = value

        agent_url = data.get("agent_backend_url", "").strip()

        if not agent_url or agent_url == "":
            return {
                "url": None,
                "status": "offline",
                "message": "Colab has not written its URL yet."
            }

        if not agent_url.startswith("http"):
            return {
                "url": None,
                "status": "invalid_url",
                "message": f"Invalid URL in sheet: {agent_url}"
            }

        return {
            "url": agent_url,
            "status": data.get("status", "unknown"),
            "message": "Connected successfully"
        }

    except Exception as e:
        return {
            "url": None,
            "status": "error",
            "message": str(e)
        }


def check_backend_health(url: str) -> dict:
    """
    Ping the Colab backend to verify it is alive.
    """
    if not url:
        return {"alive": False, "message": "No URL provided"}

    try:
        headers = {"ngrok-skip-browser-warning": "true"}
        response = requests.get(
            f"{url.rstrip('/')}/health",
            headers=headers,
            timeout=8
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "alive": True,
                "model": data.get("model", "large-v3"),
                "device": data.get("device", "cuda"),
                "vram_gb": data.get("vram_gb", 0),
                "gpu_available": data.get("gpu_available", False),
                "languages": data.get("languages_supported", 99),
            }
        return {
            "alive": False,
            "message": f"Backend returned HTTP {response.status_code}"
        }

    except requests.exceptions.ConnectionError:
        return {
            "alive": False,
            "message": "Connection refused. Colab may have stopped."
        }
    except requests.exceptions.Timeout:
        return {
            "alive": False,
            "message": "Health check timed out."
        }
    except Exception as e:
        return {
            "alive": False,
            "message": str(e)
        }