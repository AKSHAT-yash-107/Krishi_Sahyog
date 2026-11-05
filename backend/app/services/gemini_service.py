
import os
import httpx


async def generate_text(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to backend/.env.")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        result = response.json()

    choices = result.get("choices", [])

    if not choices:
        raise RuntimeError("Groq returned an empty response.")

    content = choices[0].get("message", {}).get("content", "")

    if not content:
        raise RuntimeError("Groq returned empty content.")

    return content.strip()
