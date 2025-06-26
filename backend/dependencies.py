# backend/dependencies.py
from fastapi import Header, HTTPException, status
from services.auth_service import auth_service # Import the auth_service

async def get_current_user_id(x_user_id: str = Header(..., alias="X-User-ID")):
    """
    Dependency to get the current user ID from the 'X-User-ID' header.
    Validates if the user exists in the database using AuthService.
    """
    user = await auth_service.get_user_by_id(x_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or invalid credentials."
        )
    return x_user_id