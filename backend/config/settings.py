# backend/config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Assuming .env is in the project root or backend directory
# For this structure, it should be in `backend/.env`
load_dotenv() 

class Settings:
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DB_NAME: str = os.getenv("DB_NAME", "tax_helper_db")
    print(DB_NAME)

    # Google API Key for LLM
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    print(GOOGLE_API_KEY)
    # LLM Model Configuration
    LLM_CHATBOT_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.5

    def __init__(self):
        if not self.MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable not set. Please check your .env file.")
        if not self.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable not set. Please check your .env file.")
        
        # Set the Google API key as an environment variable for LangChain
        os.environ["GOOGLE_API_KEY"] = self.GOOGLE_API_KEY

settings = Settings()