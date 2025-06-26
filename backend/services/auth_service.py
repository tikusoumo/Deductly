from datetime import datetime
from fastapi import HTTPException, status
from bson import ObjectId

from models.chat_message_model import UserCreate, UserLogin
from services.database_service import db_service
from utils.password_utils import hash_password, verify_password  # bcrypt helpers

class AuthService:
    async def signup_user(self, user_data: UserCreate):
        """
        Registers a user with lowercase username and email, and hashed password.
        Validates if username or email already exist.
        """
        users_collection = db_service.get_user_collection()

        # Normalize fields to lowercase
        username = user_data.username.lower()
        email = user_data.email.lower()

        # Check for existing username or email
        existing_user = await users_collection.find_one({
            "$or": [{"email": email}, {"username": username}]
        })

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already registered."
            )

        user_doc = {
            "username": username,
            "email": email,
            "password": hash_password(user_data.password),  # 🔐 Secure
            "created_at": datetime.now()
        }

        inserted_user = await users_collection.insert_one(user_doc)

        return {
            "message": "User registered successfully",
            "user_id": str(inserted_user.inserted_id),
            "username": username,
            "email": email
        }

    async def login_user(self, user_data: UserLogin):
        """
        Logs in a user using lowercase username and verifies password.
        """
        users_collection = db_service.get_user_collection()

        username = user_data.username.lower()
        user = await users_collection.find_one({"username": username})

        if not user or not verify_password(user_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password."
            )

        return {
            "message": "Login successful",
            "user_id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"]
        }

    async def get_user_by_id(self, user_id: str):
        """
        Fetches a user from the database using ObjectId.
        """
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format."
            )

        users_collection = db_service.get_user_collection()
        return await users_collection.find_one({"_id": user_obj_id})

auth_service = AuthService()
