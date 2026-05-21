"""
BitHide Backend - Configuration Layer
Loads all environment variables and app-wide constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY: str = os.getenv("SECRET_KEY", "bithide-dev-secret-key-change-in-prod")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    TESTING: bool = False

    # File Upload
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024  # default 50 MB
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "/tmp/bithide_uploads")
    OUTPUT_FOLDER: str = os.getenv("OUTPUT_FOLDER", "/tmp/bithide_outputs")

    ALLOWED_MIME_TYPES: set = {
        "image/jpeg",
        "image/png",
        "audio/mpeg",
        "audio/wav",
        "application/pdf",
    }

    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".mp3", ".wav", ".pdf"}

    # Security
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "5000"))
    MIN_KEY_LENGTH: int = int(os.getenv("MIN_KEY_LENGTH", "8"))

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "30 per minute")
    RATE_LIMIT_ENCODE: str = os.getenv("RATE_LIMIT_ENCODE", "10 per minute")
    RATE_LIMIT_DECODE: str = os.getenv("RATE_LIMIT_DECODE", "10 per minute")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/bithide.log")

    @staticmethod
    def ensure_directories():
        """Ensure required directories exist at startup."""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        os.makedirs("logs", exist_ok=True)


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
