import logging

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flasgger import Swagger

from config import Config
from models import db, User
from routes.clients import client_bp
from routes.users import user_bp

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.config.from_object(Config)
app.register_blueprint(client_bp)
app.register_blueprint(user_bp)

db.init_app(app)
jwt = JWTManager(app)
CORS(app)


@jwt.user_identity_loader
def user_identity_lookup(user_id):
    return str(user_id)


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)


# Отладка JWT (временно)
@jwt.unauthorized_loader
def unauthorized_response(callback):
    app.logger.info(f"JWT Unauthorized: {callback}")
    return jsonify({"success": False, "message": "Требуется авторизация"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    app.logger.info(f"JWT Invalid token: {error}")
    return jsonify({"success": False, "message": "Неверный токен"}), 422


swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger",   # вместо "/api/docs",
    "swagger_ui_config": {
        "apisSorter": "alpha",  # сортировка по алфавиту
        "operationsSorter": "method",  # сортировка операций внутри тега
        "docExpansion": "list",  # раскрыть все теги
    },
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "CRM API Documentation",
        "description": "API для управления клиентами и пользователями",
        "version": "1.0.0",
    },
    "tags": [
        {"name": "Authentication", "description": "Аутентификация"},
        {"name": "User Profile", "description": "Профиль пользователя"},
        {"name": "Clients", "description": "Управление клиентами"},
    ],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"',
        }
    },
    "security": [{"Bearer": []}],
}

Swagger(app, config=swagger_config, template=SWAGGER_TEMPLATE)

# Создание таблиц
with app.app_context():
    db.create_all()
    print("✅ База данных и таблицы созданы!")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
