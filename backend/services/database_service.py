# backend/services/database_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, PyMongoError
from fastapi import HTTPException, status

from config.settings import settings

class DatabaseService:
    _client: AsyncIOMotorClient = None
    _db = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """
        Initializes and returns an asynchronous MongoDB client.
        Ensures a single client instance is used throughout the application.
        """
        if cls._client is None:
            try:
                cls._client = AsyncIOMotorClient(settings.MONGODB_URI)
                cls._db = cls._client[settings.DB_NAME]
                print("MongoDB connection successful (via DatabaseService)!")
            except ConnectionFailure as e:
                print(f"MongoDB connection failed: {e}")
                raise HTTPException(status_code=500, detail="Could not connect to database.")
        return cls._client

    @classmethod
    def get_database(cls):
        """Returns the current MongoDB database instance."""
        if cls._db is None:
            cls.get_client() # Ensure client and db are initialized
        return cls._db

    @classmethod
    async def connect(cls):
        """Connects to MongoDB on application startup."""
        client = cls.get_client()
        try:
            await client.admin.command('ping')
            print("MongoDB client connected successfully on startup (via DatabaseService).")
        except Exception as e:
            print(f"MongoDB startup connection check failed: {e}")
            # Do not raise here, allow app to start, but future requests will fail
            pass

    @classmethod
    async def disconnect(cls):
        """Closes MongoDB connection on application shutdown."""
        if cls._client:
            cls._client.close()
            print("MongoDB connection closed (via DatabaseService).")

    @classmethod
    def get_user_collection(cls):
        """Returns the users collection."""
        return cls.get_database()["users"]

    @classmethod
    def get_session_collection(cls):
        """Returns the sessions collection."""
        return cls.get_database()["sessions"]

# Instantiate the service to be used as a singleton
db_service = DatabaseService()