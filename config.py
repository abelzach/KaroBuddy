import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATABASE_PATH = os.getenv("DATABASE_PATH", "karobuddy.db")

# Bot Settings
MAX_CONVERSATION_HISTORY = 10
RESPONSE_TIMEOUT = 30

def validate_config():
    """Validate that all required configuration is present."""
    missing = []
    
    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please copy .env.example to .env and fill in your credentials."
        )
    
    return True