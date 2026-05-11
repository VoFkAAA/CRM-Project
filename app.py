from flask import Flask, render_template, request, jsonify, session
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from flask_cors import CORS
from flasgger import Swagger, swag_from
from datetime import datetime, timedelta
import bcrypt
import re

from config import Config
from models import db, User, Client, ClientStatusEnum, DepartmentEnum

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
jwt = JWTManager(app)
CORS(app)

# Swagger конфигурация
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
    "specs_route": "/api/docs",
}
Swagger(app, config=swagger_config)


def validate_password(password):
    """Проверка сложности пароля по требованиям"""
    errors = []

    # Сначала собираем все нарушения
    if len(password) < 6 or len(password) > 32:
        errors.append("• Длина пароля: 6 - 32 символов")

    if not re.search(r"[A-Za-z]", password):
        errors.append("• Пароль должен содержать хотя бы одну английскую букву")

    if not re.search(r"[0-9]", password):
        errors.append("• Пароль должен содержать хотя бы одну цифру")

    if not re.search(r'[^A-Za-z0-9<>\\\'"]', password):
        errors.append(
            """• Пароль должен содержать хотя бы один спецсимвол (кроме < > \ ' ")"""
        )

    if re.search(r"(.)\1{3,}", password):
        errors.append("• Пароль НЕ должен содержать повторы (111111)")

    # Проверки на последовательности и запрещённые слова
    forbidden_seq = ["qwerty", "123456"]
    if any(seq in password.lower() for seq in forbidden_seq):
        errors.append("• Пароль НЕ должен содержать последовательности (123456)")

    forbidden_words = ["password", "admin", "user"]
    if any(word in password.lower() for word in forbidden_words):
        errors.append(
            "• Пароль НЕ должен содержать слова: password, qwerty, admin, user"
        )

    # ВСЕГДА показываем полный список требований, если есть хоть одно нарушение
    if errors:
        message = "Пароль не соответствует требованиям:\n" + "\n".join(
            [
                "• Длина пароля: 6 - 32 символов",
                "• Пароль должен содержать хотя бы одну английскую букву",
                "• Пароль должен содержать хотя бы одну цифру",
                "• Пароль должен содержать хотя бы один спецсимвол (кроме < > \\ ' \")",
                "• Пароль НЕ должен содержать повторы (111111)",
                "• Пароль НЕ должен содержать последовательности (123456)",
                "• Пароль НЕ должен содержать слова: password, qwerty, admin, user",
            ]
        )
        return False, message

    return True, ""


def validate_name(name, field_name="Имя"):
    """Проверка имени/фамилии по требованиям"""
    if not name or len(name) < 2 or len(name) > 15:
        return False, f"{field_name} must be 2-15 characters"
    if not re.match(r"^[А-Яа-яA-Za-z\s\-]+$", name):
        return False, f"{field_name} must contain only letters, spaces and hyphens"
    if name.startswith("-") or name.endswith("-"):
        return False, f"{field_name} cannot start or end with hyphen"
    if "  " in name or "--" in name:
        return False, f"{field_name} cannot have double spaces or double hyphens"
    return True, ""


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/register_page")
def register_page():
    return render_template("register.html")


@app.route("/profile_page")
@jwt_required(optional=True)
def profile_page():
    return render_template("profile.html")


@app.route("/clients_page")
@jwt_required(optional=True)
def clients_page():
    return render_template("clients.html")


@app.route("/register", methods=["POST"])
@swag_from(
    {
        "tags": ["Auth"],
        "summary": "Регистрация нового пользователя",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "example": "Иван"},
                        "surname": {"type": "string", "example": "Иванов"},
                        "email": {"type": "string", "example": "ivan@example.com"},
                        "phone": {"type": "string", "example": "9001112233"},
                        "password": {
                            "type": "string",
                            "example": "R5#kL9$mQ2",
                            "description": "Только англ. буквы. Длина 6-32 символов. Должен содержать букву, цифру, спецсимвол (кроме < > \\ ' \"). Запрещены повторы, последовательности и слова (qwerty, password, admin, user)",
                        },
                    },
                    "required": ["name", "surname", "email", "phone", "password"],
                },
            }
        ],
        "responses": {
            201: {
                "description": "User account created successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "message": {
                            "type": "string",
                            "example": "User account created successfully",
                        },
                        "data": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "example": 1},
                                "name": {"type": "string", "example": "Иван"},
                                "surname": {"type": "string", "example": "Иванов"},
                                "email": {
                                    "type": "string",
                                    "example": "ivan@example.com",
                                },
                                "phone": {"type": "string", "example": "9001112233"},
                            },
                        },
                    },
                },
            },
            400: {
                "description": "Invalid input data",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "message": {
                            "type": "string",
                            "example": "Password must be 6-32 characters",
                        },
                    },
                },
            },
            409: {
                "description": "Email or phone already exists",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "message": {
                            "type": "string",
                            "example": "Email already exists",
                        },
                    },
                },
            },
        },
    }
)
def register():
    data = request.get_json()

    name = data.get("name")
    surname = data.get("surname")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    # Валидация
    valid_name, msg_name = validate_name(name, "Имя")
    if not valid_name:
        return jsonify({"success": False, "message": msg_name}), 400

    valid_surname, msg_surname = validate_name(surname, "Фамилия")
    if not valid_surname:
        return jsonify({"success": False, "message": msg_surname}), 400

    valid_pass, msg_pass = validate_password(password)
    if not valid_pass:
        return jsonify({"success": False, "message": msg_pass}), 400

    # Проверка уникальности
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already exists"}), 409

    if User.query.filter_by(phone=phone).first():
        return jsonify({"success": False, "message": "Phone already exists"}), 409

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user = User(
        name=name,
        surname=surname,
        email=email,
        phone=phone,
        password_hash=hashed.decode("utf-8"),
    )
    db.session.add(user)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "User account created successfully",
                "data": user.to_dict(),
            }
        ),
        201,
    )


@app.route("/login", methods=["POST"])
@swag_from(
    {
        "tags": ["Auth"],
        "summary": "Авторизация пользователя",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "login": {"type": "string", "example": "ivan@example.com"},
                        "password": {"type": "string", "example": "R5#kL9$mQ2"},
                    },
                    "required": ["login", "password"],
                },
            }
        ],
        "responses": {
            200: {
                "description": "Login successful",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "message": {"type": "string", "example": "Login successful"},
                        "access_token": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIs...",
                        },
                        "user": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer"},
                                "name": {"type": "string"},
                                "surname": {"type": "string"},
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                            },
                        },
                    },
                },
            },
            400: {
                "description": "Invalid data",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "message": {
                            "type": "string",
                            "example": "Login and password are required",
                        },
                    },
                },
            },
            401: {
                "description": "Invalid credentials",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "message": {"type": "string", "example": "Invalid credentials"},
                    },
                },
            },
        },
    }
)
def login():
    data = request.get_json()
    login_input = data.get("login")
    password = data.get("password")

    if not login_input or not password:
        return (
            jsonify({"success": False, "message": "Login and password required"}),
            400,
        )

    user = User.query.filter(
        (User.email == login_input) | (User.phone == login_input)
    ).first()

    if not user or not bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=user.user_id, expires_delta=timedelta(hours=24)
    )

    return (
        jsonify(
            {
                "success": True,
                "message": "Login successful",
                "access_token": access_token,
                "user": user.to_dict(),
            }
        ),
        200,
    )


@app.route("/update_profile", methods=["PUT", "PATCH"])
@swag_from(
    {
        "tags": ["Profile"],
        "summary": "Обновление профиля пользователя",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Bearer <access_token>",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "example": "Иван",
                            "description": "Имя (2-15 символов)",
                        },
                        "surname": {
                            "type": "string",
                            "example": "Иванов",
                            "description": "Фамилия (1-40 символов)",
                        },
                        "email": {"type": "string", "example": "ivan@example.com"},
                        "phone": {"type": "string", "example": "9001112233"},
                        "birth_date": {
                            "type": "string",
                            "format": "date",
                            "example": "1990-01-01",
                        },
                        "department": {
                            "type": "string",
                            "enum": [
                                "Администрация",
                                "Бухгалтерия",
                                "АХО",
                                "Закупки",
                                "Продажи",
                                "Производство",
                            ],
                        },
                    },
                },
            },
        ],
        "responses": {
            200: {
                "description": "Profile updated successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "message": {
                            "type": "string",
                            "example": "Profile updated successfully",
                        },
                        "data": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer"},
                                "name": {"type": "string"},
                                "surname": {"type": "string"},
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "birth_date": {"type": "string", "format": "date"},
                                "department": {"type": "string"},
                            },
                        },
                    },
                },
            },
            400: {"description": "Invalid input data"},
            401: {"description": "Missing or invalid token"},
            403: {"description": "Forbidden"},
            404: {"description": "User not found"},
            409: {"description": "Email or phone already exists"},
        },
    }
)
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    data = request.get_json()

    if "name" in data:
        valid, msg = validate_name(data["name"], "Имя")
        if not valid:
            return jsonify({"success": False, "message": msg}), 400
        user.name = data["name"]
    if "surname" in data:
        valid, msg = validate_name(data["surname"], "Фамилия")
        if not valid:
            return jsonify({"success": False, "message": msg}), 400
        user.surname = data["surname"]
    if "email" in data:
        # БАГ: нет проверки уникальности email
        user.email = data["email"]
    if "phone" in data:
        # БАГ: нет проверки уникальности телефона
        user.phone = data["phone"]
    if "birth_date" in data and data["birth_date"]:
        user.birth_date = datetime.strptime(data["birth_date"], "%Y-%m-%d").date()
    if "department" in data:
        if data["department"] in [e.value for e in DepartmentEnum]:
            user.department = data["department"]

    db.session.commit()
    return (
        jsonify(
            {
                "success": True,
                "message": "Profile updated successfully",
                "data": user.to_dict(),
            }
        ),
        200,
    )


@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


# Заглушки для клиентских эндпоинтов (будут в следующих файлах)
@app.route("/create_client", methods=["POST"])
@swag_from(
    {
        "tags": ["Clients"],
        "summary": "Создание нового клиента",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Bearer <access_token>",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "example": "ООО Ромашка",
                            "description": "Название компании (4-150 символов)",
                        },
                        "email": {"type": "string", "example": "romashka@example.com"},
                        "phone": {"type": "string", "example": "9001112233"},
                        "address": {
                            "type": "string",
                            "example": "Москва, ул. Ленина, д. 1",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["Active", "Stopped", "Blocked"],
                            "default": "Active",
                        },
                    },
                    "required": ["client_name", "email", "phone"],
                },
            },
        ],
        "responses": {
            201: {
                "description": "Client created successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                        "data": {"type": "object"},
                    },
                },
            },
            400: {"description": "Invalid input data"},
            401: {"description": "Missing or invalid token"},
            409: {"description": "Email or phone already exists"},
        },
    }
)
@jwt_required()
def create_client():
    return jsonify({"message": "Will be implemented"}), 501


@app.route("/update_client", methods=["PUT"])
@swag_from(
    {
        "tags": ["Clients"],
        "summary": "Полное обновление клиента",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Bearer <access_token>",
            },
            {
                "name": "client_id",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "ID клиента для обновления",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "example": "ООО Ромашка"},
                        "email": {"type": "string", "example": "romashka@example.com"},
                        "phone": {"type": "string", "example": "9001112233"},
                        "address": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["Active", "Stopped", "Blocked"],
                        },
                    },
                    "required": ["client_name", "email", "phone"],
                },
            },
        ],
        "responses": {
            200: {
                "description": "Client updated successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                        "data": {"type": "object"},
                    },
                },
            },
            400: {"description": "Invalid input data"},
            401: {"description": "Missing or invalid token"},
            404: {"description": "Client not found"},
        },
    }
)
@jwt_required()
def update_client():
    return jsonify({"message": "Will be implemented"}), 501


@app.route("/update_client", methods=["PATCH"])
@swag_from(
    {
        "tags": ["Clients"],
        "summary": "Частичное обновление клиента",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Bearer <access_token>",
            },
            {
                "name": "client_id",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "ID клиента для обновления",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "example": "ООО Ромашка"},
                        "email": {"type": "string", "example": "romashka@example.com"},
                        "phone": {"type": "string", "example": "9001112233"},
                        "address": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["Active", "Stopped", "Blocked"],
                        },
                    },
                },
            },
        ],
        "responses": {
            200: {
                "description": "Client updated successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                        "data": {"type": "object"},
                    },
                },
            },
            400: {"description": "Invalid input data"},
            401: {"description": "Missing or invalid token"},
            404: {"description": "Client not found"},
        },
    }
)
@jwt_required()
def patch_client():
    """Частичное обновление клиента (только переданные поля)"""
    from models import Client, ClientStatusEnum

    user_id = get_jwt_identity()
    client_id = request.args.get("client_id", type=int)

    if not client_id:
        return jsonify({"success": False, "message": "client_id is required"}), 400

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"success": False, "message": "Client not found"}), 404

    data = request.get_json()

    # Обновляем только те поля, которые переданы
    if "client_name" in data:
        # TODO: добавить валидацию client_name (4-150 символов)
        client.client_name = data["client_name"]

    if "email" in data:
        # БАГ: нет проверки уникальности email (по списку багов)
        client.email = data["email"]

    if "phone" in data:
        # БАГ: нет проверки уникальности телефона
        client.phone = data["phone"]

    if "address" in data:
        client.address = data["address"]

    if "status" in data:
        if data["status"] in ["Active", "Stopped", "Blocked"]:
            client.status = data["status"]

    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Client updated successfully",
                "data": client.to_dict(),
            }
        ),
        200,
    )


@app.route("/delete_client", methods=["DELETE"])
@swag_from(
    {
        "tags": ["Clients"],
        "summary": "Удаление клиента",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Bearer <access_token>",
            },
            {
                "name": "client_id",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "ID клиента для удаления",
            },
        ],
        "responses": {
            200: {
                "description": "Client deleted successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {
                            "type": "string",
                            "example": "Client deleted successfully",
                        },
                    },
                },
            },
            401: {"description": "Missing or invalid token"},
            404: {"description": "Client not found"},
        },
    }
)
@jwt_required()
def delete_client():
    return jsonify({"message": "Will be implemented"}), 501


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ База данных инициализирована")
    app.run(debug=True, host="0.0.0.0", port=5000)
