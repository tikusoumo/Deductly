# backend/controllers/auth_controller.py
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from models.chat_message_model import UserCreate, UserLogin
from services.auth_service import auth_service

router = APIRouter()

@router.post("/signup", summary="Register a new user (Simplified for external auth)", status_code=status.HTTP_201_CREATED)
async def signup_user_route(user_data: UserCreate):
    """
    This endpoint now assumes that user registration is primarily handled by an external system.
    This FastAPI backend will simply record the username and generate an ID for internal use if needed.
    Password hashing/verification is omitted.
    """
    response_data = await auth_service.signup_user(user_data)
    return JSONResponse(content=response_data, status_code=status.HTTP_201_CREATED)

@router.post("/login", summary="Login user (Simplified for external auth)", status_code=status.HTTP_200_OK)
async def login_user_route(user_data: UserLogin):
    """
    This endpoint now assumes that actual login validation (username/password check)
    is handled by an external system. This FastAPI backend will simply confirm
    if a user with the given username exists in its own DB and return its internal ID.
    """
    response_data = await auth_service.login_user(user_data)
    return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)