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
from pydantic import BaseModel, ValidationError
from openai import BadRequestError

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

if PROVIDER == "groq":
    MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
elif PROVIDER == "openai":
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
else:
    raise ValueError(
        f"Unknown LLM_PROVIDER '{PROVIDER}'. Use 'groq' or 'openai'."
    )

_client = None
_client_provider = None


def get_client():
    global _client, _client_provider

    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if _client is not None and _client_provider == provider:
        return _client

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        base_url = "https://api.groq.com/openai/v1"
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = None
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    if not api_key:
        raise RuntimeError(
            f"Missing API key for provider '{provider}'. "
            "Configure the appropriate environment variable."
        )

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    _client = OpenAI(**kwargs)
    _client_provider = provider
    return _client


import json
from openai import BadRequestError


class LLMResponseError(Exception):
    """Raised when an LLM response is malformed or fails validation."""


def ask_json(
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
) -> BaseModel:
    """Request JSON, validate its schema, and retry invalid output."""

    import json
    client = get_client()
    max_attempts = 3
    current_prompt = user_prompt
    last_error = None

    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": current_prompt},
                ],
            )

            raw = response.choices[0].message.content

            if not raw or not raw.strip():
                raise LLMResponseError("LLM returned an empty response.")

            try:
                data = _parse_json(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                raise LLMResponseError(
                    "LLM returned malformed JSON."
                ) from exc

            try:
                return response_model.model_validate(data)
            except ValidationError as exc:
                details = exc.errors(include_input=False)
                raise LLMResponseError(
                    f"LLM output failed {response_model.__name__} "
                    f"validation: {details}"
                ) from exc

        except LLMResponseError as exc:
            last_error = exc

            if attempt == max_attempts - 1:
                break

            current_prompt = (
                f"{user_prompt}\n\n"
                f"Your previous response failed validation: {exc}\n"
                f"Return a corrected JSON object matching this schema: "
                f"{response_model.model_json_schema()}\n"
                "Include all required fields, use correct types, and "
                "do not include unexpected fields."
            )

        except BadRequestError as exc:
            # Groq can reject malformed JSON before returning a response.
            body = exc.body if isinstance(exc.body, dict) else {}
            details = body.get("error", body)
            error_code = (
                details.get("code")
                if isinstance(details, dict)
                else None
            )

            if error_code != "json_validate_failed":
                raise LLMResponseError(
                    f"LLM provider rejected the request: {exc}"
                ) from exc

            last_error = exc

            if attempt == max_attempts - 1:
                break

            failed_generation = (
                details.get("failed_generation", "")
                if isinstance(details, dict)
                else ""
            )

            current_prompt = (
                f"{user_prompt}\n\n"
                "The previous output was rejected as invalid JSON. "
                "Return one complete JSON object matching the requested "
                "schema. Ensure every array item is a complete object "
                "with correct braces, commas, fields, and types."
            )

            if failed_generation:
                current_prompt += (
                    "\nPrevious invalid output:\n" + failed_generation
                )

        except Exception as exc:
            # Network errors, authentication errors, and other unexpected
            # provider failures must not be misclassified as bad JSON.
            raise LLMResponseError(
                f"LLM request failed: {type(exc).__name__}: {exc}"
            ) from exc

    raise LLMResponseError(
        f"Could not obtain valid {response_model.__name__} output "
        f"after {max_attempts} attempts."
    ) from last_error



def ask_text(system_prompt: str, user_prompt: str) -> str:
    """Call the model and return plain text (used for generated code)."""

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content

    if not content or not content.strip():
        raise LLMResponseError("LLM returned an empty response.")

    return content.strip()

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
