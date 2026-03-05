import logging
import requests
from app.config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def generate(prompt: str) -> str:
    # BUG FIX: original had no timeout and no error handling — a missing/slow
    # Ollama container would block the thread indefinitely and then raise an
    # unhandled exception that killed the monitor loop.
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not reachable — skipping LLM summary.")
        return "LLM unavailable."
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Summary unavailable."
