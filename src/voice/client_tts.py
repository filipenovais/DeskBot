"""Text-to-speech using direct HTTP requests."""

import logging
import httpx
from tkinter import messagebox

from src import config

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(120.0, connect=10.0)
CHECK_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


class TTSError(Exception):
    """Text-to-speech processing error."""
    pass


class TTSDisabledError(Exception):
    """TTS service is disabled (empty API key or base URL)."""
    pass


def text_to_speech(text: str, output_path: str = None, voice: str = None, model: str = None) -> bytes:
    """
    Convert text to speech using OpenAI-compatible API.

    Args:
        text: The text to convert to speech
        output_path: Optional path to save the audio file
        voice: Voice to use (default: from config TTS_VOICE)
        model: Model to use (default: from config TTS_MODEL)

    Returns:
        Audio bytes in WAV format

    Raises:
        TTSError: If synthesis fails
        TTSDisabledError: If TTS service is disabled (empty config)
        ValueError: If text is empty
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    # Check if TTS is disabled (empty config) - raise silently without messagebox
    if not config.TTS_API_BASE_URL:
        raise TTSDisabledError("TTS service is disabled")

    voice = voice or config.TTS_VOICE
    model = model or config.TTS_MODEL

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{config.TTS_API_BASE_URL}/audio/speech",
                headers={
                    "Authorization": f"Bearer {config.TTS_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "voice": voice,
                    "input": text,
                    "response_format": "wav",
                },
            )

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_msg = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    pass
                messagebox.showerror("TTS API Error", f"API error ({response.status_code}): {error_msg}")
                raise TTSError(f"API error ({response.status_code}): {error_msg}")

            audio_bytes = response.content

            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)

            return audio_bytes

    except TTSError:
        raise
    except httpx.TimeoutException as e:
        logger.error(f"TTS timeout: {e}")
        messagebox.showerror("TTS API Error", "Text-to-speech request timed out")
        raise TTSError("Text-to-speech request timed out") from e
    except Exception as e:
        logger.error(f"TTS error: {e}")
        messagebox.showerror("TTS API Error", f"Failed to synthesize speech: {e}")
        raise TTSError(f"Failed to synthesize speech: {e}") from e


async def check_tts() -> bool:
    """Check if TTS service is configured and reachable.

    Returns:
        True if TTS service is available, False otherwise
    """
    if not config.TTS_API_BASE_URL:
        return False

    try:
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT) as client:
            headers = {}
            if config.TTS_API_KEY:
                headers["Authorization"] = f"Bearer {config.TTS_API_KEY}"
            response = await client.get(
                f"{config.TTS_API_BASE_URL}/models",
                headers=headers,
            )
            return response.status_code == 200
    except Exception:
        return False
