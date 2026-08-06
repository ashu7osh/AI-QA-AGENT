"""
Thin wrapper around an OpenAI-compatible chat completions API so every agent
calls the model the same way, and provider switching / JSON parsing only
lives in one place.

Supports two providers, switched via LLM_PROVIDER in .env:
  - "groq"   (default, FREE, no card required: https://console.groq.com/keys)
  - "openai" (paid)

Both use the same `openai` Python SDK — Groq just runs on a different
base_url, since its API is OpenAI-compatible. This is why switching
providers only needs a couple of env vars, not a code rewrite.

Swap-out point: if you later move to Gemini or LangGraph, this is the only
file that needs to change — every agent just calls `ask_json()` or `ask_text()`.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

if PROVIDER == "groq":
    _client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
elif PROVIDER == "openai":
    _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
else:
    raise ValueError(f"Unknown LLM_PROVIDER '{PROVIDER}'. Use 'groq' or 'openai'.")


def ask_json(system_prompt: str, user_prompt: str) -> dict:
    """Call the model and force a JSON object back. Raises if parsing fails."""
    response = _client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content
    return _parse_json(raw)


def ask_text(system_prompt: str, user_prompt: str) -> str:
    """Call the model and return plain text (used for generated code)."""
    response = _client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def _parse_json(raw: str) -> dict:
    import json
    import re

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Some models (esp. via Groq) occasionally wrap JSON in markdown
        # fences even in "json_object" mode. Strip and retry once.
        cleaned = re.sub(r"^```(json)?", "", raw.strip())
        cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model did not return valid JSON:\n{raw}") from e
