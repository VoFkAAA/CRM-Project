import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-key")

    # Эта строчка будет работать И на твоём компьютере, И на Render
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "crm_testing.db")}'

    # JWT настройки
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 часа

    # Swagger
    SWAGGER_URL = "/api/docs"
    API_URL = None
