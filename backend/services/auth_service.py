# backend/services/auth_service.py
from datetime import datetime
from fastapi import HTTPException, status
from bson import ObjectId

from models.chat_message_model import UserCreate, UserLogin
from services.database_service import db_service

class AuthService:
    async def signup_user(self, user_data: UserCreate):
        """
        Handles user registration. Assumes external auth for password validation.
        Creates a user entry in the internal database.
        """
        users_collection = db_service.get_user_collection()

        existing_user = await users_collection.find_one({"username": user_data.username})
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists. If registered externally, just log in.")

        user_doc = {
            "username": user_data.username,
            "created_at": datetime.now()
        }
        inserted_user = await users_collection.insert_one(user_doc)
        user_id_internal = str(inserted_user.inserted_id)

        return {
            "message": "User registered internally (via external auth system)",
            "user_id": user_id_internal,
            "username": user_data.username
        }

    async def login_user(self, user_data: UserLogin):
        """
        Handles user login. Assumes external auth for password validation.
        Confirms if a user with the given username exists and returns its internal ID.
        """
        users_collection = db_service.get_user_collection()

        user = await users_collection.find_one({"username": user_data.username})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

        return {
            "message": "Login successful (via external auth system)",
            "user_id": str(user["_id"]),
            "username": user["username"]
        }
    
    async def get_user_by_id(self, user_id: str):
        """Fetches a user by their ObjectId."""
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format. Must be a valid MongoDB ObjectId."
            )
        
        users_collection = db_service.get_user_collection()
        user = await users_collection.find_one({"_id": user_obj_id})
        return user

auth_service = AuthService()