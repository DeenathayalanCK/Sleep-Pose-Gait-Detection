import requests
from app.config import OLLAMA_HOST, OLLAMA_MODEL

def generate(prompt):

    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]