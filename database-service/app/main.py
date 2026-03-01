"""Database Service - Conversation and message persistence."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    update_conversation,
)
from app.database import get_session, init_db
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    UpdateConversationRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Database Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "database-service"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_session)):
    """Save messages to a conversation. Creates conversation if needed.

    Args:
        request: ChatRequest with conversation_id (optional) and messages list

    Returns:
        ChatResponse with conversation_id
    """
    # Get or create conversation
    if request.conversation_id:
        conv = await get_conversation(session, request.conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")

        # Update title if it's still "New Conversation" and we have messages
        if len(conv.messages) == 0 and conv.title.startswith("New Conversation") and request.messages:
            first_message = next(
                (m for m in request.messages if m.role == "human"),
                request.messages[0] if request.messages else None
            )
            if first_message:
                new_title = first_message.content[:50] + ("..." if len(first_message.content) > 50 else "")
                await update_conversation(session, conv.id, new_title)
                conv.title = new_title  # Update local object too
    else:
        # Create new conversation with title from first user message
        first_message = next(
            (m for m in request.messages if m.role == "human"),
            request.messages[0] if request.messages else None
        )
        if first_message:
            title = first_message.content[:50] + ("..." if len(first_message.content) > 50 else "")
        else:
            title = "New Conversation"
        conv = await create_conversation(session, title=title)

    # Save all messages to database
    for msg in request.messages:
        await add_message(session, conv.id, msg.role, msg.content)

    return ChatResponse(conversation_id=conv.id)


@app.post("/conversations", response_model=ConversationResponse)
async def create_conv(
    request: CreateConversationRequest,
    session: AsyncSession = Depends(get_session)
):
    conv = await create_conversation(session, title=request.title)
    # Build dict manually to avoid accessing messages relationship
    result = {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "message_count": 0,  # New conversation has no messages
    }
    print(f"Created conversation: {conv.id}")
    return result


@app.get("/conversations", response_model=list[ConversationResponse])
async def list_convs(session: AsyncSession = Depends(get_session)):
    # list_conversations now returns dicts directly
    return await list_conversations(session)


@app.get("/conversations/{conv_id}", response_model=ConversationDetailResponse)
async def get_conv(conv_id: str, session: AsyncSession = Depends(get_session)):
    print(f"Getting conversation: {conv_id}")
    conv = await get_conversation(session, conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    # Build dict with messages while in session context
    result = {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "message_count": len(conv.messages),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "position": m.position,
                "created_at": m.created_at.isoformat(),
            }
            for m in conv.messages
        ]
    }
    return result


@app.put("/conversations/{conv_id}", response_model=ConversationResponse)
async def update_conv(
    conv_id: str,
    request: UpdateConversationRequest,
    session: AsyncSession = Depends(get_session)
):
    print(f"Updating conversation: {conv_id}")
    conv = await update_conversation(session, conv_id, request.title)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    # Build dict manually to avoid accessing messages relationship
    result = {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "message_count": len(conv.messages),
    }
    return result


@app.delete("/conversations/{conv_id}")
async def delete_conv(conv_id: str, session: AsyncSession = Depends(get_session)):
    if not await delete_conversation(session, conv_id):
        raise HTTPException(404, "Conversation not found")
    return {"detail": "Deleted"}
