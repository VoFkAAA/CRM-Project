from flask import Flask, render_template, request, jsonify
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
from models import db, User, Client

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
jwt = JWTManager(app)
CORS(app)

swagger_config = {
    "headers": [],
    "specs": [{"endpoint": "apispec", "route": "/apispec.json"}],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
}
Swagger(app, config=swagger_config)


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
            """• Пароль должен содержать хотя бы один спецсимвол (кроме < > \ ' ")"""
        )
    if re.search(r"(.)\1{3,}", password):
        errors.append("• Пароль НЕ должен содержать повторы (111111)")
    if any(seq in password.lower() for seq in ["qwerty", "123456"]):
        errors.append("• Пароль НЕ должен содержать последовательности (123456)")
    if any(word in password.lower() for word in ["password", "admin", "user"]):
        errors.append(
            "• Пароль НЕ должен содержать слова: password, qwerty, admin, user"
        )
    if errors:
        return False, "Пароль не соответствует требованиям:\n" + "\n".join(errors)
    return True, ""


def validate_name(name, field_name="Имя"):
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


@app.route("/create_client_page")
@jwt_required(optional=True)
def create_client_page():
    return render_template("create_client.html")


@app.route("/register", methods=["POST"])
def register():
    try:
        print("=== REGISTER REQUEST START ===")
        data = request.get_json()
        print(f"Received data: {data}")

        name = data.get("name")
        surname = data.get("surname")
        email = data.get("email")
        phone = data.get("phone")
        password = data.get("password")

        print(f"Validating name: {name}")
        valid_name, msg_name = validate_name(name, "Имя")
        if not valid_name:
            return jsonify({"success": False, "message": msg_name}), 400

        print(f"Validating surname: {surname}")
        valid_surname, msg_surname = validate_name(surname, "Фамилия")
        if not valid_surname:
            return jsonify({"success": False, "message": msg_surname}), 400

        print(f"Validating password")
        valid_pass, msg_pass = validate_password(password)
        if not valid_pass:
            return jsonify({"success": False, "message": msg_pass}), 400

        print(f"Checking if email exists: {email}")
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "Email already exists"}), 409

        print(f"Checking if phone exists: {phone}")
        if User.query.filter_by(phone=phone).first():
            return jsonify({"success": False, "message": "Phone already exists"}), 409

        print(f"Hashing password")
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        print(f"Creating user object")
        user = User(
            name=name,
            surname=surname,
            email=email,
            phone=phone,
            password_hash=hashed.decode("utf-8"),
        )

        print(f"Adding to database")
        db.session.add(user)
        db.session.commit()
        print("=== USER CREATED SUCCESSFULLY ===")

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
    except Exception as e:
        print(f"!!!!!!!!! CRITICAL ERROR IN REGISTER: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/login", methods=["POST"])
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
        user.email = data["email"]
    if "phone" in data:
        user.phone = data["phone"]
    if "birth_date" in data and data["birth_date"]:
        user.birth_date = datetime.strptime(data["birth_date"], "%Y-%m-%d").date()
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


@app.route("/clients", methods=["GET"])
@jwt_required()
def get_clients():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    clients = Client.query.all()
    return (
        jsonify(
            {
                "success": True,
                "message": "Clients retrieved successfully",
                "data": [c.to_dict() for c in clients],
            }
        ),
        200,
    )


@app.route("/create_client", methods=["POST"])
@jwt_required()
def create_client():
    data = request.get_json()
    client_name = data.get("client_name")
    email = data.get("email")
    phone = data.get("phone")
    address = data.get("address", "")
    status = data.get("status", "Active")

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
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Некорректный email"}), 400
    if not phone or len(phone) != 10 or not phone.isdigit():
        return (
            jsonify({"success": False, "message": "Телефон должен содержать 10 цифр"}),
            400,
        )

    user_id = get_jwt_identity()
    new_client = Client(
        client_name=client_name,
        email=email,
        phone=phone,
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
                "message": "Client created successfully",
                "data": new_client.to_dict(),
            }
        ),
        201,
    )


@app.route("/update_client", methods=["PUT"])
@jwt_required()
def update_client():
    client_id = request.args.get("client_id", type=int)
    if not client_id:
        return jsonify({"success": False, "message": "client_id is required"}), 400
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"success": False, "message": "Client not found"}), 404

    data = request.get_json()
    client_name = data.get("client_name")
    email = data.get("email")
    phone = data.get("phone")
    address = data.get("address", "")
    status = data.get("status", "Active")

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
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Некорректный email"}), 400
    if not phone or len(phone) != 10 or not phone.isdigit():
        return (
            jsonify({"success": False, "message": "Телефон должен содержать 10 цифр"}),
            400,
        )

    client.client_name = client_name
    client.email = email
    client.phone = phone
    client.address = address
    client.status = status
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


@app.route("/update_client", methods=["PATCH"])
@jwt_required()
def patch_client():
    client_id = request.args.get("client_id", type=int)
    if not client_id:
        return jsonify({"success": False, "message": "client_id is required"}), 400
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"success": False, "message": "Client not found"}), 404

    data = request.get_json()
    if "client_name" in data:
        client.client_name = data["client_name"]
    if "email" in data:
        client.email = data["email"]
    if "phone" in data:
        client.phone = data["phone"]
    if "address" in data:
        client.address = data["address"]
    if "status" in data and data["status"] in ["Active", "Stopped", "Blocked"]:
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
@jwt_required()
def delete_client():
    client_id = request.args.get("client_id", type=int)
    if not client_id:
        return jsonify({"success": False, "message": "client_id is required"}), 400
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"success": False, "message": "Client not found"}), 404
    db.session.delete(client)
    db.session.commit()
    return jsonify({"success": True, "message": "Client deleted successfully"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Server is running"}), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ База данных инициализирована")
    app.run(debug=True, host="0.0.0.0", port=5000)
