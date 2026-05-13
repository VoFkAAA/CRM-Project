from flask import Blueprint, request, Response, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)

from sqlalchemy.exc import IntegrityError

from models import db, Client
from helpers.validation_helper import (clean_phone_number, validate_phone_number,
                               validate_name, validate_email)


client_bp = Blueprint('client_bp', __name__)


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

    user_id = get_jwt_identity()

    process_client_validation_errors(client_name, email, phone)

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
    except IntegrityError  as err:
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


@client_bp.route("/clients/<int:client_id>/", methods=['GET'])
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


@client_bp.route("/clients/<int:client_id>/", methods=['DELETE'])
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


@client_bp.route("/clients/<int:client_id>/", methods=['PUT'])
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

    process_client_validation_errors(data.get("client_name"), data.get("email"), data.get("phone"))
    

    client = db.get_or_404(Client, client_id)

    try:
        client.client_name = data.get("client_name")
        client.email = data.get("email")
        client.phone = data.get("phone")
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


@client_bp.route("/clients/<int:client_id>/", methods=['PATCH'])
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
            process_client_validation_errors(data["client_name"])
            client.client_name = data["client_name"]
        if data.get("email"):
            process_client_validation_errors(data["email"])
            client.email = data["email"]
        if data.get("phone"):
            process_client_validation_errors(data["phone"])
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



def process_client_validation_errors(client_name: str = None, email: str = None, phone: str = None) -> Response:
    error_messages = []
    if client_name is not None:
        valid_name, msg = validate_name(client_name)
        if not valid_name:
            error_messages.append(msg)
    if email is not None:
        valid_email, msg = validate_email(email)
        if not valid_email:
            error_messages.append(msg)

    if phone is not None:
        valid_phone, msg = validate_phone_number(phone)
        if not valid_phone:
            error_messages.append(msg)

    return jsonify({"success": False, "message": error_messages}), 400
