import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = "dev-secret-key-change-in-production"
    JWT_SECRET_KEY = "jwt-dev-secret-key-please-change"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SWAGGER_URL = "/api/docs"
    API_URL = None
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Локально - PostgreSQL через DATABASE_URL из .env
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL не задан в .env файле")
