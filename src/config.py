
"""
Configuration settings for Kara to Medusa.js migration
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# API configuration
API_BASE_URL = "https://kara.com.ng/rest/V1"
API_USERNAME = os.getenv("KARA_API_USERNAME", "elevated")
API_PASSWORD = os.getenv("KARA_API_PASSWORD", "nynwEd-7bucpe-rysdim")

# Database configuration
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medusa")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Migration settings
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))  # Reduced batch size for reliability
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))  # Increased number of retries
TIMEOUT = int(os.getenv("TIMEOUT", "60"))  # Increased timeout in seconds

# Media handling
DOWNLOAD_IMAGES = os.getenv("DOWNLOAD_IMAGES", "True").lower() in ("true", "1", "t")
MEDIA_STORAGE_PATH = os.getenv("MEDIA_STORAGE_PATH", "/app/media")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/migration.log")