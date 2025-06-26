# ─── Pydantic Models for Request/Response Validation ──────────────────────────
from pydantic import BaseModel, Field, EmailStr
from typing import Any, Dict, List, Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class InitialTaxDetailsInput(BaseModel):
    user_details: Dict[str, Any]

class ChatMessageInput(BaseModel):
    message: str
    is_interruption_response: bool = Field(False, description="Set to true if this message is a response to a human-in-the-loop interruption.")

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_call_id: Optional[str] = None
class ChatSessionResponse(BaseModel):
    # Changed from Field(alias="_id") to just 'id'
    id: str 
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    chat_history: List[ChatMessage]
    initial_tax_details: Dict[str, Any]

class ChatSessionSummary(BaseModel):
    # Changed from Field(alias="_id") to just 'id'
    id: str 
    title: str
    created_at: datetime
    updated_at: datetime

# --- NEW Pydantic Models for API Responses ---
class StartSessionResponse(BaseModel):
    message: str
    session_id: str
    bot_response: str
    chat_history: List[ChatMessage]
    awaiting_human_input: bool

class SendMessageResponse(BaseModel):
    message: str
    bot_response: str
    updated_chat_history: List[ChatMessage]
    awaiting_human_input: bool
    session_id: Optional[str] = None 
# ---------------------------------------------