# backend/controllers/chat_controller.py
import traceback
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse

from models.chat_message_model import (
    InitialTaxDetailsInput,
    ChatMessageInput,
    ChatSessionResponse,
    ChatSessionSummary,
    StartSessionResponse,
    SendMessageResponse
)
from services.chat_service import chat_service
from dependencies import get_current_user_id # Import the dependency

router = APIRouter()

@router.get("/chats", summary="Get all chat sessions for the logged-in user", response_model=List[ChatSessionSummary])
async def get_user_chats_route(user_id: str = Depends(get_current_user_id)):
    """Retrieves a list of all chat sessions associated with the authenticated user."""
    return await chat_service.get_user_chat_sessions(user_id)

@router.get("/chats/{session_id}", summary="Get a specific chat session by ID", response_model=ChatSessionResponse)
async def get_chat_session_by_id_route(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Retrieves a detailed view of a specific chat session."""
    return await chat_service.get_chat_session_by_id(session_id, user_id)

@router.post(
    "/chats/start_new_tax_session",
    summary="Start a new tax deduction chat session",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED
)
async def start_new_tax_session_route(
    input_data: InitialTaxDetailsInput,
    user_id: str = Depends(get_current_user_id)
):
    """
    Initiates a new tax chat session, performing an initial tax analysis using LangGraph
    and generating an opening message from the AI assistant.
    """
    try:
        return await chat_service.start_new_tax_session(input_data, user_id)
    except HTTPException:
        raise # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        print(f"An unexpected error occurred during new session creation: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post(
    "/chats/{session_id}/send_message",
    summary="Send a new message to an existing chat session",
    response_model=SendMessageResponse
)
async def send_message_to_chat_route(
    session_id: str,
    input_data: ChatMessageInput,
    user_id: str = Depends(get_current_user_id)
):
    """Sends a new user message to an ongoing chat session and receives an AI response."""
    try:
        return await chat_service.send_message_to_chat(session_id, input_data, user_id)
    except HTTPException:
        raise # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        print(f"An unexpected error occurred during message sending: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")