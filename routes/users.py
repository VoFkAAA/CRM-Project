import bcrypt
import re
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from flask_cors import CORS

from models import db, User
from helpers.validation_helper import (validate_password, validate_name,
                               validate_email)


user_bp = Blueprint('users_bp', __name__)


@user_bp.route("/")
def index():
    return render_template("login.html")


@user_bp.route("/register_page")
def register_page():
    return render_template("register.html")


@user_bp.route("/profile_page")
def profile_page():
    return render_template("profile.html")


@user_bp.route("/clients_page")
def clients_page():
    return render_template("clients.html")


@user_bp.route("/create_client_page")
def create_client_page():
    return render_template("create_client.html")


@user_bp.route("/register", methods=["POST"])
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
        
        valid_email, msg = validate_email(email)
        if not valid_email:
            return jsonify({"success": False, "message": msg}), 400

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


@user_bp.route("/login", methods=["POST"])
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


@user_bp.route("/update_profile", methods=["GET", "PUT", "PATCH"])
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
        valid_email, msg = validate_email(data["email"])
        if not valid_email:
            return jsonify({"success": False, "message": msg}), 400
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


@user_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"success": True, "message": "Выход выполнен успешно"}), 200


@user_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Server is running"}), 200


@user_bp.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,PATCH,OPTIONS"
    )
    return response
