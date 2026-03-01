"""LLM Handler - Direct HTTP requests to language model APIs."""

import logging
import httpx
from tkinter import messagebox

from src import config

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(120.0, connect=10.0)
CHECK_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


class LLMError(Exception):
    """Language model processing error."""
    pass


def chat_completion(
    messages: list[dict],
    system_prompt: str,
    model: str,
    provider: str,
    api_key: str,
    api_base_url: str,
) -> str:
    """
    Send chat completion request to LLM API.

    Args:
        messages: List of message dicts with "role" and "content" keys
                 Roles should be "user" or "assistant"
        system_prompt: Optional system prompt
        model: Model to use (defaults to config.LLM_MODEL)
        provider: Provider name (defaults to config.LLM_PROVIDER)
        api_key: API key (defaults to config.LLM_API_KEY)
        api_base_url: Base URL (defaults to config.LLM_API_BASE_URL)

    Returns:
        Assistant response text

    Raises:
        LLMError: If request fails
    """

    if not api_key and provider != "ollama":
        raise LLMError(f"API key not configured for provider '{provider}'")

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            if provider == "anthropic":
                return _anthropic_completion(client, messages, system_prompt, model, api_key)
            else:
                # OpenAI-compatible format (groq, openai, ollama)
                return _openai_completion(client, messages, system_prompt, model, api_key, api_base_url)

    except LLMError:
        raise
    except httpx.TimeoutException as e:
        logger.error(f"LLM timeout: {e}")
        messagebox.showerror("LLM API Error", "Chat completion request timed out")
        raise LLMError("Chat completion request timed out") from e
    except Exception as e:
        logger.error(f"LLM error: {e}")
        messagebox.showerror("LLM API Error", f"Failed to get chat completion: {e}")
        raise LLMError(f"Failed to get chat completion: {e}") from e


def _openai_completion(
    client: httpx.Client,
    messages: list[dict],
    system_prompt: str,
    model: str,
    api_key: str,
    api_base_url: str,
) -> str:
    """OpenAI-compatible chat completion (Groq, OpenAI, Ollama)."""
    # Build messages list with system prompt
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})

    # Convert message roles to OpenAI format
    for msg in messages:
        role = msg.get("role", "user")
        # Map internal roles to OpenAI roles
        if role in ("human", "user"):
            role = "user"
        elif role in ("ai", "assistant"):
            role = "assistant"
        api_messages.append({"role": role, "content": msg["content"]})

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = client.post(
        f"{api_base_url}/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": api_messages,
        },
    )

    if response.status_code != 200:
        error_msg = response.text
        try:
            error_msg = response.json().get("error", {}).get("message", response.text)
        except Exception:
            pass
        messagebox.showerror("LLM API Error", f"API error ({response.status_code}): {error_msg}")
        raise LLMError(f"API error ({response.status_code}): {error_msg}")

    return response.json()["choices"][0]["message"]["content"]


def _anthropic_completion(
    client: httpx.Client,
    messages: list[dict],
    system_prompt: str,
    model: str,
    api_key: str,
) -> str:
    """Anthropic Claude chat completion."""
    # Convert message roles to Anthropic format
    api_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        # Map internal roles to Anthropic roles
        if role in ("human", "user"):
            role = "user"
        elif role in ("ai", "assistant"):
            role = "assistant"
        api_messages.append({"role": role, "content": msg["content"]})

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": api_messages,
    }
    if system_prompt:
        payload["system"] = system_prompt

    response = client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json=payload,
    )

    if response.status_code != 200:
        error_msg = response.text
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except Exception:
            pass
        messagebox.showerror("LLM API Error", f"Anthropic API error ({response.status_code}): {error_msg}")
        raise LLMError(f"Anthropic API error ({response.status_code}): {error_msg}")

    return response.json()["content"][0]["text"]


async def check_llm() -> bool:
    """Check if LLM service is configured and reachable.

    Returns:
        True if LLM service is available, False otherwise
    """
    # Check basic config
    if not config.LLM_PROVIDER:
        return False
    if not config.LLM_MODEL:
        return False

    provider = config.LLM_PROVIDER.lower()

    # Ollama doesn't require API key
    if not config.LLM_API_KEY and provider != "ollama":
        return False

    try:
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT) as client:
            if provider == "anthropic":
                # Anthropic: check models endpoint
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": config.LLM_API_KEY,
                        "anthropic-version": "2023-06-01",
                    },
                )
                return response.status_code == 200
            else:
                # OpenAI-compatible (groq, openai, ollama): check models endpoint
                if not config.LLM_API_BASE_URL:
                    return False
                headers = {}
                if config.LLM_API_KEY:
                    headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
                response = await client.get(
                    f"{config.LLM_API_BASE_URL}/models",
                    headers=headers,
                )
                return response.status_code == 200
    except Exception:
        return False
