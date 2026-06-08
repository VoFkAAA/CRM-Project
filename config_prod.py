import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-key-please-change")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SWAGGER_URL = "/api/docs"
    API_URL = None
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # На сервере - DATABASE_URL из переменных окружения Render
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не задан на сервере")

    # Добавляем SSL для подключения Supabase к Amvera (если в URL нет sslmode)
    if "supabase" in DATABASE_URL and "sslmode" not in DATABASE_URL:
        separator = "?" if "?" not in DATABASE_URL else "&"
        DATABASE_URL += f"{separator}sslmode=require"

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"options": "-c client_encoding=utf8"}}
