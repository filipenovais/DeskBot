"""Speech-to-text using direct HTTP requests."""

import logging
import httpx
from tkinter import messagebox

from src import config

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(120.0, connect=10.0)
CHECK_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


class STTError(Exception):
    """Speech-to-text processing error."""
    pass


class STTDisabledError(Exception):
    """STT service is disabled (empty API key or base URL)."""
    pass


def speech_to_text(audio_data: bytes = None, audio_path: str = None) -> str:
    """
    Convert speech to text using OpenAI-compatible API.

    Args:
        audio_data: Audio bytes (WAV format)
        audio_path: Path to audio file (alternative to audio_data)

    Returns:
        Transcribed text

    Raises:
        STTError: If transcription fails
        STTDisabledError: If STT service is disabled (empty config)
        ValueError: If neither audio_data nor audio_path provided
    """
    if not audio_data and not audio_path:
        raise ValueError("Either audio_data or audio_path must be provided")

    # Check if STT is disabled (empty config) - raise silently without messagebox
    if not config.STT_API_BASE_URL:
        raise STTDisabledError("STT service is disabled")

    try:
        # Read file if path provided
        if audio_path:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{config.STT_API_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {config.STT_API_KEY}"},
                files={"file": ("audio.wav", audio_data, "audio/wav")},
                data={
                    "model": config.STT_MODEL,
                    "response_format": "verbose_json",
                    "language": "en",  # Help prevent hallucinations
                },
            )

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_msg = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    pass
                messagebox.showerror("STT API Error", f"API error ({response.status_code}): {error_msg}")
                raise STTError(f"API error ({response.status_code}): {error_msg}")

            result = response.json()
            logger.info(f"STT response: {result}")
            return result["text"]

    except STTError:
        raise
    except httpx.TimeoutException as e:
        logger.error(f"STT timeout: {e}")
        messagebox.showerror("STT API Error", "Speech-to-text request timed out")
        raise STTError("Speech-to-text request timed out") from e
    except Exception as e:
        logger.error(f"STT error: {e}")
        messagebox.showerror("STT API Error", f"Failed to transcribe audio: {e}")
        raise STTError(f"Failed to transcribe audio: {e}") from e


async def check_stt() -> bool:
    """Check if STT service is configured and reachable.

    Returns:
        True if STT service is available, False otherwise
    """
    if not config.STT_API_BASE_URL:
        return False

    try:
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT) as client:
            headers = {}
            if config.STT_API_KEY:
                headers["Authorization"] = f"Bearer {config.STT_API_KEY}"
            response = await client.get(
                f"{config.STT_API_BASE_URL}/models",
                headers=headers,
            )
            return response.status_code == 200
    except Exception:
        return False
