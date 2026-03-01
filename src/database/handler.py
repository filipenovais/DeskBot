"""Database handler - unified interface for database operations."""

from .client import (
    check_database,
    transcribe,
    save_messages,
    create_conversation,
    synthesize,
    list_conversations,
    get_conversation,
    delete_conversation,
    update_conversation_title,
)


class DatabaseHandler:
    """Handler for database and voice service operations."""

    def __init__(self):
        """Initialize database handler."""
        pass

    @staticmethod
    async def check() -> bool:
        """Check if database is running."""
        return await check_database()

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Convert audio to text."""
        return await transcribe(audio_bytes)

    async def save_messages(self, conversation_id: str, messages: list[dict]) -> str:
        """Save messages to database."""
        return await save_messages(conversation_id, messages)

    async def create_conversation(self, title: str = None) -> dict:
        """Create a new conversation."""
        return await create_conversation(title)

    async def synthesize(self, text: str) -> bytes:
        """Convert text to speech."""
        return await synthesize(text)

    async def list_conversations(self) -> list:
        """Get all saved conversations."""
        return await list_conversations()

    async def get_conversation(self, conversation_id: str) -> dict:
        """Get a conversation with all its messages."""
        return await get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        return await delete_conversation(conversation_id)

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update a conversation's title."""
        return await update_conversation_title(conversation_id, title)
