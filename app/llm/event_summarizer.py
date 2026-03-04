from app.llm.ollama_client import generate

def summarize(duration):

    prompt = f"""
A surveillance system detected a person with eyes closed
for {duration:.1f} seconds.

Explain briefly if this may indicate fatigue.
"""

    return generate(prompt)