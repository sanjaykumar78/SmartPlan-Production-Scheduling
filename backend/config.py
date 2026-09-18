import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))


class Config:
    """Application configuration loaded from environment variables."""

    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', '5000'))
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'replace-this-secret-key')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'database': os.getenv('DB_NAME', 'smartplan_db'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
    }

    JSON_SORT_KEYS = False
