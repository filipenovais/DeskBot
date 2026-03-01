"""HTTP client for talking to backend services."""

import httpx
from tkinter import messagebox

from src import config
from src.voice import VoiceHandler, STTDisabledError, TTSDisabledError

TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class DatabaseError(Exception):
    """Database service error."""
    pass


async def check_database() -> bool:
    """Check if database is running.

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{config.DATABASE_SERVICE_URL}/health")
            return r.status_code == 200
    except Exception:
        return False


async def transcribe(audio_bytes: bytes) -> str | None:
    """Convert audio to text using Groq Whisper.

    Returns:
        Transcribed text, or None if STT is disabled.
    """
    try:
        return VoiceHandler.speech_to_text(audio_data=audio_bytes)
    except STTDisabledError:
        return None


async def save_messages(conversation_id: str, messages: list[dict]) -> str:
    """Save messages to database.

    Args:
        conversation_id: The conversation ID (optional for new conversations)
        messages: List of message dicts with "role" and "content" keys

    Returns:
        The conversation ID
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            payload = {"conversation_id": conversation_id, "messages": messages}
            r = await client.post(f"{config.DATABASE_SERVICE_URL}/chat", json=payload)
            r.raise_for_status()
            return r.json()["conversation_id"]
    except httpx.TimeoutException:
        messagebox.showerror("Database Error", "Database request timed out")
        raise DatabaseError("Database request timed out")
    except httpx.HTTPStatusError as e:
        messagebox.showerror("Database Error", f"Failed to save messages: {e.response.status_code}")
        raise DatabaseError(f"Failed to save messages: {e}")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to save messages: {e}")
        raise DatabaseError(f"Failed to save messages: {e}")


async def create_conversation(title: str = None) -> dict:
    """Create a new conversation.

    Args:
        title: Optional conversation title

    Returns:
        Conversation dict with id, title, created_at, etc.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            payload = {"title": title or "New Conversation"}
            r = await client.post(f"{config.DATABASE_SERVICE_URL}/conversations", json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        messagebox.showerror("Database Error", "Database request timed out")
        raise DatabaseError("Database request timed out")
    except httpx.HTTPStatusError as e:
        messagebox.showerror("Database Error", f"Failed to create conversation: {e.response.status_code}")
        raise DatabaseError(f"Failed to create conversation: {e}")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to create conversation: {e}")
        raise DatabaseError(f"Failed to create conversation: {e}")


async def synthesize(text: str) -> bytes | None:
    """Convert text to speech using Groq Orpheus, returns WAV bytes.

    Returns:
        Audio bytes in WAV format, or None if TTS is disabled.
    """
    try:
        return VoiceHandler.text_to_speech(text)
    except TTSDisabledError:
        return None


async def list_conversations() -> list:
    """Get all saved conversations."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{config.DATABASE_SERVICE_URL}/conversations")
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        messagebox.showerror("Database Error", "Database request timed out")
        raise DatabaseError("Database request timed out")
    except httpx.HTTPStatusError as e:
        messagebox.showerror("Database Error", f"Failed to list conversations: {e.response.status_code}")
        raise DatabaseError(f"Failed to list conversations: {e}")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to list conversations: {e}")
        raise DatabaseError(f"Failed to list conversations: {e}")


async def get_conversation(conversation_id: str) -> dict:
    """Get a conversation with all its messages."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{config.DATABASE_SERVICE_URL}/conversations/{conversation_id}")
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        messagebox.showerror("Database Error", "Database request timed out")
        raise DatabaseError("Database request timed out")
    except httpx.HTTPStatusError as e:
        messagebox.showerror("Database Error", f"Failed to get conversation: {e.response.status_code}")
        raise DatabaseError(f"Failed to get conversation: {e}")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to get conversation: {e}")
        raise DatabaseError(f"Failed to get conversation: {e}")


async def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.delete(f"{config.DATABASE_SERVICE_URL}/conversations/{conversation_id}")
            return r.status_code == 200
    except httpx.TimeoutException:
        messagebox.showerror("Database Error", "Database request timed out")
        raise DatabaseError("Database request timed out")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to delete conversation: {e}")
        raise DatabaseError(f"Failed to delete conversation: {e}")


async def update_conversation_title(conversation_id: str, title: str) -> bool:
    """Update a conversation's title."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.put(
                f"{config.DATABASE_SERVICE_URL}/conversations/{conversation_id}",
                json={"title": title}
            )
            return r.status_code == 200
    except httpx.TimeoutException:
        messagebox.showerror("Database Error", "Database request timed out")
        raise DatabaseError("Database request timed out")
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to update conversation title: {e}")
        raise DatabaseError(f"Failed to update conversation title: {e}")
