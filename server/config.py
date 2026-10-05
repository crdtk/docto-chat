"""Application configuration from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Model
MODEL_NAME = os.getenv("MODEL_NAME", "prav-974/medical-qa-tinyllama")
DEVICE = os.getenv("DEVICE", "cpu")

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # "json" or "text"

# Caching
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "100"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Async
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
