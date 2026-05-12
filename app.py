from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from flask_cors import CORS
from flasgger import Swagger
from datetime import datetime, timedelta
import bcrypt
import re

from config import Config
from models import db, User, Client

app = Flask(__name__)
app.config.from_object(Config)

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
    print(f"JWT Unauthorized: {callback}")
    return jsonify({"success": False, "message": "Требуется авторизация"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    print(f"JWT Invalid token: {error}")
    return jsonify({"success": False, "message": "Неверный токен"}), 422


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

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "CRM API Documentation",
        "description": "API для управления клиентами и пользователями",
        "version": "1.0.0",
    },
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


def validate_password(password):
    errors = []
    if len(password) < 6 or len(password) > 32:
        errors.append("• Длина пароля: 6 - 32 символов")
    if not re.search(r"[A-Za-z]", password):
        errors.append("• Пароль должен содержать хотя бы одну английскую букву")
    if not re.search(r"[0-9]", password):
        errors.append("• Пароль должен содержать хотя бы одну цифру")
    if not re.search(r'[^A-Za-z0-9<>\\\'"]', password):
        errors.append(
            "• Пароль должен содержать хотя бы один спецсимвол (кроме < > \\ ' \")"
        )
    if re.search(r"(.)\1{3,}", password):
        errors.append("• Пароль НЕ должен содержать повторы (111111)")
    if any(seq in password.lower() for seq in ["qwerty", "123456"]):
        errors.append("• Пароль НЕ должен содержать последовательности (123456)")
    if any(
        word in password.lower() for word in ["password", "qwerty", "admin", "user"]
    ):
        errors.append(
            "• Пароль НЕ должен содержать слова: password, qwerty, admin, user"
        )
    if errors:
        return False, "Пароль не соответствует требованиям:\n" + "\n".join(errors)
    return True, ""


def validate_name(name, field_name="Имя"):
    if not name or len(name) < 2 or len(name) > 15:
        return False, f"{field_name} должно быть от 2 до 15 символов"
    if not re.match(r"^[А-Яа-яA-Za-z\s\-]+$", name):
        return False, f"{field_name} должно содержать только буквы, пробелы и дефисы"
    if name.startswith("-") or name.endswith("-"):
        return False, f"{field_name} не может начинаться или заканчиваться дефисом"
    if "  " in name or "--" in name:
        return (
            False,
            f"{field_name} не может содержать двойные пробелы или двойные дефисы",
        )
    return True, ""


def validate_email(email):
    # Простая валидация email
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/register_page")
def register_page():
    return render_template("register.html")


@app.route("/profile_page")
def profile_page():
    return render_template("profile.html")


@app.route("/clients_page")
def clients_page():
    return render_template("clients.html")


@app.route("/create_client_page")
def create_client_page():
    return render_template("create_client.html")


@app.route("/register", methods=["POST"])
def register():
    """Регистрация нового пользователя
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Иван"
            surname:
              type: string
              example: "Иванов"
            email:
              type: string
              example: "user@example.com"
            phone:
              type: string
              example: "9123456789"
            password:
              type: string
              example: "Passw0rd!"
    responses:
      201:
        description: User created successfully
      400:
        description: Validation error
      409:
        description: Email or phone already exists
    """
    try:
        data = request.get_json()

        name = data.get("name")
        surname = data.get("surname")
        email = data.get("email")
        phone = data.get("phone")
        password = data.get("password")

        # Очистка телефона от нецифр
        phone = re.sub(r"\D", "", phone)
        if len(phone) == 11 and phone.startswith("7"):
            phone = phone[1:]
        elif len(phone) == 11 and phone.startswith("8"):
            phone = phone[1:]

        valid_name, msg_name = validate_name(name, "Имя")
        if not valid_name:
            return jsonify({"success": False, "message": msg_name}), 400

        valid_surname, msg_surname = validate_name(surname, "Фамилия")
        if not valid_surname:
            return jsonify({"success": False, "message": msg_surname}), 400

        if not validate_email(email):
            return jsonify({"success": False, "message": "Некорректный email"}), 400

        if len(phone) != 10 or not phone.isdigit():
            return (
                jsonify(
                    {"success": False, "message": "Телефон должен содержать 10 цифр"}
                ),
                400,
            )

        valid_pass, msg_pass = validate_password(password)
        if not valid_pass:
            return jsonify({"success": False, "message": msg_pass}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "Email уже существует"}), 409

        if User.query.filter_by(phone=phone).first():
            return jsonify({"success": False, "message": "Телефон уже существует"}), 409

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
                    "message": "Пользователь успешно зарегистрирован",
                    "data": user.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500


@app.route("/login", methods=["POST"])
def login():
    """Авторизация пользователя
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            login:
              type: string
              example: "user@example.com or 9123456789"
            password:
              type: string
              example: "Passw0rd!"
    responses:
      200:
        description: Login successful
      400:
        description: Missing credentials
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    login_input = data.get("login")
    password = data.get("password")

    if not login_input or not password:
        return jsonify({"success": False, "message": "Требуются логин и пароль"}), 400

    # Очистка телефона если передан номер
    login_clean = re.sub(r"\D", "", login_input)
    if len(login_clean) == 11 and login_clean.startswith(("7", "8")):
        login_clean = login_clean[1:]

    user = User.query.filter(
        (User.email == login_input)
        | (User.phone == login_clean)
        | (User.phone == login_input)
    ).first()

    if not user or not bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return jsonify({"success": False, "message": "Неверный логин или пароль"}), 401

    access_token = create_access_token(
        identity=str(user.user_id), expires_delta=timedelta(hours=24)
    )

    return (
        jsonify(
            {
                "success": True,
                "message": "Вход выполнен успешно",
                "access_token": access_token,
                "user": user.to_dict(),
            }
        ),
        200,
    )


@app.route("/update_profile", methods=["GET", "PUT", "PATCH"])
@jwt_required()
def update_profile():
    """Обновление профиля пользователя
    ---
    tags:
      - User Profile
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            name:
              type: string
            surname:
              type: string
            email:
              type: string
            phone:
              type: string
            birth_date:
              type: string
              format: date
            department:
              type: string
    responses:
      200:
        description: Profile updated successfully
      400:
        description: Validation error
      404:
        description: User not found
      409:
        description: Email or phone already exists
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"success": False, "message": "Пользователь не найден"}), 404

    # GET запрос для получения профиля
    if request.method == "GET":
        return jsonify({"success": True, "data": user.to_dict()}), 200

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
        if not validate_email(data["email"]):
            return jsonify({"success": False, "message": "Некорректный email"}), 400
        # Проверка уникальности email (БАГ: при попытке сменить email на уже существующий у другого пользователя возвращает 200 OK)
        existing = User.query.filter(
            User.email == data["email"], User.user_id != user_id
        ).first()
        if existing:
            # БАГ: Возвращаем 200 вместо 409
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Профиль обновлён (email уже существует)",
                    }
                ),
                200,
            )
        user.email = data["email"]

    if "phone" in data:
        phone_clean = re.sub(r"\D", "", data["phone"])
        if len(phone_clean) == 11 and phone_clean.startswith(("7", "8")):
            phone_clean = phone_clean[1:]
        if len(phone_clean) != 10:
            # БАГ: PATCH возвращает 403 вместо 400
            if request.method == "PATCH":
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Телефон должен содержать 10 цифр",
                        }
                    ),
                    403,
                )
            return (
                jsonify(
                    {"success": False, "message": "Телефон должен содержать 10 цифр"}
                ),
                400,
            )
        existing = User.query.filter(
            User.phone == phone_clean, User.user_id != user_id
        ).first()
        if existing:
            return jsonify({"success": False, "message": "Телефон уже существует"}), 409
        user.phone = phone_clean

    if "birth_date" in data and data["birth_date"]:
        try:
            user.birth_date = datetime.strptime(data["birth_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    if "department" in data and data["department"]:
        from models import DepartmentEnum

        if data["department"] in [e.value for e in DepartmentEnum]:
            user.department = data["department"]

    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Профиль успешно обновлён",
                "data": user.to_dict(),
            }
        ),
        200,
    )


@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"success": True, "message": "Выход выполнен успешно"}), 200


@app.route("/clients", methods=["GET"])
@jwt_required()
def get_clients():
    """Получение списка всех клиентов
    ---
    tags:
      - Clients
    responses:
      200:
        description: Clients retrieved successfully
    """
    try:
        clients = Client.query.all()
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Клиенты успешно загружены",
                    "data": [c.to_dict() for c in clients],
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/create_client", methods=["POST"])
@jwt_required()
def create_client():
    """Создание нового клиента
    ---
    tags:
      - Clients
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            client_name:
              type: string
            email:
              type: string
            phone:
              type: string
            address:
              type: string
            status:
              type: string
              enum: [Active, Stopped, Blocked]
    responses:
      201:
        description: Client created successfully
      400:
        description: Validation error
    """
    data = request.get_json()
    client_name = data.get("client_name")
    email = data.get("email")
    phone = data.get("phone")
    address = data.get("address", "")
    status = data.get("status", "Active")

    # Очистка телефона
    phone_clean = re.sub(r"\D", "", phone)
    if len(phone_clean) == 11 and phone_clean.startswith(("7", "8")):
        phone_clean = phone_clean[1:]

    if not client_name or len(client_name) < 4 or len(client_name) > 150:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Название клиента должно быть от 4 до 150 символов",
                }
            ),
            400,
        )

    if not validate_email(email):
        return jsonify({"success": False, "message": "Некорректный email"}), 400

    if len(phone_clean) != 10 or not phone_clean.isdigit():
        return (
            jsonify({"success": False, "message": "Телефон должен содержать 10 цифр"}),
            400,
        )

    # Проверка уникальности email и телефона
    if Client.query.filter_by(email=email).first():
        # БАГ: возвращаем 201 вместо 409
        return (
            jsonify(
                {"success": True, "message": "Клиент создан (email уже существует)"}
            ),
            201,
        )

    if Client.query.filter_by(phone=phone_clean).first():
        return jsonify({"success": False, "message": "Телефон уже существует"}), 409

    user_id = get_jwt_identity()
    new_client = Client(
        client_name=client_name,
        email=email,
        phone=phone_clean,
        address=address,
        status=status,
        created_by=user_id,
    )
    db.session.add(new_client)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Клиент успешно создан",
                "data": new_client.to_dict(),
            }
        ),
        201,
    )


@app.route("/update_client", methods=["PUT"])
@jwt_required()
def update_client():
    """Обновление данных клиента
    ---
    tags:
      - Clients
    """
    client_id = request.args.get("client_id", type=int)

    if not client_id:
        return jsonify({"success": False, "message": "Требуется client_id"}), 400

    client = Client.query.get(client_id)

    # БАГ: если клиент не найден, создаём нового с таким id
    if not client:
        # Создаём нового клиента
        data = request.get_json()
        new_client = Client(
            client_id=client_id,
            client_name=data.get("client_name", ""),
            email=data.get("email", ""),
            phone=re.sub(r"\D", "", data.get("phone", "")),
            address=data.get("address", ""),
            status=data.get("status", "Active"),
            created_by=get_jwt_identity(),
        )
        db.session.add(new_client)
        db.session.commit()
        return (
            jsonify({"success": True, "message": "Создан новый клиент с указанным ID"}),
            200,
        )

    data = request.get_json()

    if "client_name" in data:
        client.client_name = data["client_name"]
    if "email" in data:
        client.email = data["email"]
    if "phone" in data:
        phone_clean = re.sub(r"\D", "", data["phone"])
        if len(phone_clean) == 11 and phone_clean.startswith(("7", "8")):
            phone_clean = phone_clean[1:]
        client.phone = phone_clean
    if "address" in data:
        client.address = data["address"]
    if "status" in data and data["status"] in ["Active", "Stopped", "Blocked"]:
        client.status = data["status"]

    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Клиент успешно обновлён",
                "data": client.to_dict(),
            }
        ),
        200,
    )


@app.route("/update_client", methods=["PATCH"])
@jwt_required()
def patch_client():
    """Частичное обновление клиента"""
    client_id = request.args.get("client_id", type=int)

    if not client_id:
        return jsonify({"success": False, "message": "Требуется client_id"}), 400

    client = Client.query.get(client_id)

    if not client:
        return jsonify({"success": False, "message": "Клиент не найден"}), 404

    data = request.get_json()

    if "client_name" in data:
        client.client_name = data["client_name"]
    if "email" in data:
        client.email = data["email"]
    if "phone" in data:
        phone_clean = re.sub(r"\D", "", data["phone"])
        if len(phone_clean) == 11 and phone_clean.startswith(("7", "8")):
            phone_clean = phone_clean[1:]
        client.phone = phone_clean
    if "address" in data:
        client.address = data["address"]
    if "status" in data and data["status"] in ["Active", "Stopped", "Blocked"]:
        client.status = data["status"]

    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Клиент успешно обновлён",
                "data": client.to_dict(),
            }
        ),
        200,
    )


@app.route("/delete_client", methods=["DELETE"])
@jwt_required()
def delete_client():
    """Удаление клиента
    ---
    tags:
      - Clients
    """
    client_id = request.args.get("client_id", type=int)

    if not client_id:
        return jsonify({"success": False, "message": "Требуется client_id"}), 400

    client = Client.query.get(client_id)

    # БАГ: для несуществующего id возвращаем 200 OK
    if not client:
        return (
            jsonify({"success": True, "message": "Клиент удалён (или не существовал)"}),
            200,
        )

    db.session.delete(client)
    db.session.commit()

    return jsonify({"success": True, "message": "Клиент успешно удалён"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Server is running"}), 200


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,PATCH,OPTIONS"
    )
    return response


# Создание таблиц
with app.app_context():
    db.create_all()
    print("✅ База данных и таблицы созданы!")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
