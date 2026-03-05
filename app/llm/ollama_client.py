import logging
import requests
from app.config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def generate(prompt: str) -> str:
    try:
        # Check what models are available first
        tags_resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if tags_resp.status_code != 200:
            logger.warning("Ollama not ready — skipping summary.")
            return "LLM unavailable."

        models = [m["name"] for m in tags_resp.json().get("models", [])]

        if not models:
            logger.warning(
                "Ollama has no models loaded. "
                "Run: docker exec -it <ollama-container> ollama pull llama3"
            )
            return "No LLM model loaded."

        # Use configured model, or fall back to first available
        model = OLLAMA_MODEL
        if model not in models:
            base = model.split(":")[0]
            match = next((m for m in models if m.startswith(base)), models[0])
            logger.info(f"Model '{model}' not found, using '{match}'. Available: {models}")
            model = match

        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not reachable — skipping LLM summary.")
        return "LLM unavailable."
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Summary unavailable."