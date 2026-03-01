"""API request/response schemas."""

from pydantic import BaseModel


class MessageInput(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[MessageInput]


class ChatResponse(BaseModel):
    conversation_id: str


class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"


class UpdateConversationRequest(BaseModel):
    title: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    position: int
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
