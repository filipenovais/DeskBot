"""Database operations for conversations and messages."""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Conversation, Message


async def create_conversation(session: AsyncSession, title: str = "New Conversation"):
    """Create a new conversation."""
    conv = Conversation(title=title)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def get_conversation(session: AsyncSession, conversation_id: str):
    """Get conversation by ID with messages loaded."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def list_conversations(session: AsyncSession):
    """List all conversations, newest first."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    # Convert to dicts while still in session context
    # Access messages to ensure they're loaded before returning
    return [
        {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "message_count": len(conv.messages),
        }
        for conv in conversations
    ]


async def update_conversation(session: AsyncSession, conversation_id: str, title: str):
    """Update conversation title."""
    conv = await get_conversation(session, conversation_id)
    if not conv:
        return None
    conv.title = title
    conv.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return conv


async def delete_conversation(session: AsyncSession, conversation_id: str):
    """Delete a conversation."""
    conv = await get_conversation(session, conversation_id)
    if not conv:
        return False
    await session.delete(conv)
    await session.commit()
    return True


async def add_message(session: AsyncSession, conversation_id: str, role: str, content: str):
    """Add a message to a conversation."""
    conv = await get_conversation(session, conversation_id)
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        position=len(conv.messages),
    )
    session.add(msg)
    conv.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return msg
