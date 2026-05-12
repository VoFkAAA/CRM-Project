import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-key-please-change")

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "crm_testing.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SWAGGER_URL = "/api/docs"
    API_URL = None

    # Только ЭТИ настройки JWT
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
