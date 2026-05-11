import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-key")

    # PostgreSQL (через Docker или локально)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgreuser01@localhost:5432/CRM-Project"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT настройки
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 часа

    # Swagger
    SWAGGER_URL = "/api/docs"
    API_URL = None
