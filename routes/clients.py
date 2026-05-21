from flask import Blueprint, request, Response, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)

from sqlalchemy.exc import IntegrityError

from models import db, Client
from helpers.validation_helper import (
    clean_phone_number,
    validate_phone_number,
    validate_client_name,
    validate_email,
)

client_bp = Blueprint("client_bp", __name__)


@client_bp.route("/clients", methods=["GET"])
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


@client_bp.route("/create_client", methods=["POST"])
@jwt_required()
def create():
    data = request.get_json()

    client_name = data.get("client_name")
    email = data.get("email")
    phone = data.get("phone")
    address = data.get("address", "")
    status = data.get("status")  # если не выбран — вернётся None или пустая строка

    if not status:  # пустая строка или None → None
        status = None

    user_id = get_jwt_identity()

    if error_messages := check_client_validation_errors(client_name, email, phone):
        return jsonify({"success": False, "message": "\n".join(error_messages)}), 400

    # Если статус не выбран, не передаём его в БД (будет NULL или значение по умолчанию в модели)
    if not status:
        status = None

    try:
        new_client = Client(
            client_name=client_name,
            email=email,
            phone=clean_phone_number(phone),
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

    except IntegrityError as err:
        db.session.rollback()
        # Проверяем тип ошибки уникальности
        error_str = str(err.orig)
        if "clients_email_key" in error_str:
            return jsonify({"success": False, "message": "Email уже существует"}), 409
        elif "clients_phone_key" in error_str:
            return jsonify({"success": False, "message": "Телефон уже существует"}), 409
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Клиент с такими данными уже существует",
                    }
                ),
                409,
            )


@client_bp.route("/clients/<int:client_id>/", methods=["GET"])
@jwt_required()
def get_client(client_id: int) -> Response:
    """Получение одного клиента
    ---
    parameters:
      - name: client_id
        in: path
        type: integer
    tags:
      - Clients
    responses:
      200:
        description: Client retrieved successfully
      404:
        description: Client not found
    """
    client = db.get_or_404(Client, client_id)
    return jsonify(client.to_dict()), 200


@client_bp.route("/clients/<int:client_id>/", methods=["DELETE"])
@jwt_required()
def delete_client(client_id: int) -> Response:
    """Удаление клиента
    ---
    parameters:
      - name: client_id
        in: path
        type: integer
    tags:
      - Clients
    responses:
      204:
        description: Client deleted successfully
      404:
        description: Client not found
    """
    client = db.get_or_404(Client, client_id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({"message": "Client deleted successfully"}), 204


@client_bp.route("/clients/<int:client_id>/", methods=["PUT"])
@jwt_required()
def update_client(client_id: int) -> Response:
    """Обновление клиента
    ---
    parameters:
      - name: client_id
        in: path
        type: integer
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
    tags:
      - Clients
    responses:
      200:
        description: Client updated successfully
      404:
        description: Client not found
    """
    data = request.get_json()

    ## Можно сохранить без указания телефона (с пустым полем Телефон)

    if error_messages := check_client_validation_errors(
        data.get("client_name"), data.get("email"), None
    ):
        return jsonify({"success": False, "message": "\n".join(error_messages)}), 400

    client = db.get_or_404(Client, client_id)

    try:
        client.client_name = data.get("client_name")
        client.email = data.get("email")
        client.phone = data.get("phone") if data.get("phone") else None
        client.address = data.get("address")
        client.status = data.get("status")

        db.session.commit()
        return jsonify(client.to_dict()), 200
    except IntegrityError as err:
        db.session.rollback()
        # Handle the duplicate, e.g., return an error message to the user
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Получена ошибка уникальности {err.orig}",
                }
            ),
            201,
        )


@client_bp.route("/clients/<int:client_id>/", methods=["PATCH"])
@jwt_required()
def patch_client(client_id: int) -> Response:
    """Патчинг клиента
    ---
    parameters:
      - name: client_id
        in: path
        type: integer
      - in: body
        name: body
        required: false
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
    tags:
      - Clients
    responses:
      200:
        description: Client updated successfully
      404:
        description: Client not found
    """
    data = request.get_json()

    client = db.get_or_404(Client, client_id)

    try:
        if data.get("client_name"):
            if error_messages := check_client_validation_errors(data["client_name"]):
                return (
                    jsonify({"success": False, "message": "\n".join(error_messages)}),
                    400,
                )
            client.client_name = data["client_name"]
        if data.get("email"):
            if error_messages := check_client_validation_errors(data["email"]):
                return (
                    jsonify({"success": False, "message": "\n".join(error_messages)}),
                    400,
                )
            client.email = data["email"]
        if data.get("phone"):
            if error_messages := check_client_validation_errors(data["phone"]):
                return (
                    jsonify({"success": False, "message": "\n".join(error_messages)}),
                    400,
                )
            client.phone = data["phone"]
        if data.get("address"):
            client.address = data["address"]
        if data.get("status"):
            client.status = data["status"]
        if data.get("client_name"):
            client.client_name = data["client_name"]
        db.session.commit()
        return jsonify(client.to_dict()), 200
    except IntegrityError as err:
        db.session.rollback()
        # Handle the duplicate, e.g., return an error message to the user
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Получена ошибка уникальности {err.orig}",
                }
            ),
            201,
        )


def check_client_validation_errors(
    client_name: str = None, email: str = None, phone: str = None
) -> str:
    error_messages = []
    if client_name is not None:
        valid_name, err_msg = validate_client_name(client_name)
        if not valid_name:
            error_messages.append(err_msg)
    if email is not None:
        valid_email, err_msg = validate_email(email)
        if not valid_email:
            error_messages.append(err_msg)

    if phone is not None:
        valid_phone, err_msg = validate_phone_number(phone)
        print(valid_phone)
        if not valid_phone:
            error_messages.append(err_msg)

    return error_messages
