import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG = True
    PORT = 5001
    DATA_STORE_PATH = "data_store.json"
    REPORTS_PATH = "reports/"
    
    @classmethod
    def validate(cls):
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")
        return True
