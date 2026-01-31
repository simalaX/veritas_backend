import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Get the directory where config.py is located
BASE_DIR = Path(__file__).resolve().parent

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    # Use absolute path
    FIREBASE_JSON_PATH = os.getenv("FIREBASE_JSON_PATH", str(BASE_DIR / "serviceAccountKey.json"))
    SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")

settings = Settings()