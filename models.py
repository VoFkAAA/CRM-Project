from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

db = SQLAlchemy()


class DepartmentEnum(str, Enum):
    ADMINISTRATION = "Администрация"
    ACCOUNTING = "Бухгалтерия"
    AHO = "АХО"
    PROCUREMENT = "Закупки"
    SALES = "Продажи"
    PRODUCTION = "Производство"


class ClientStatusEnum(str, Enum):
    ACTIVE = "Active"
    STOPPED = "Stopped"
    BLOCKED = "Blocked"


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    register_date = db.Column(db.DateTime, default=datetime.utcnow)
    birth_date = db.Column(db.Date, nullable=True)
    department = db.Column(
        db.String(50), nullable=True
    )  # Изменено на String для совместимости

    clients = db.relationship(
        "Client", backref="owner", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        # БАГ: в register_date отображается неправильная дата (год 1970)
        # Симулируем баг - возвращаем фиксированную дату
        bug_date = datetime(1970, 1, 1) if self.register_date else None

        return {
            "user_id": self.user_id,
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "phone": self.phone,
            "register_date": (
                bug_date.isoformat() if bug_date else "1970-01-01T00:00:00"
            ),
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "department": self.department,
        }


class Client(db.Model):
    __tablename__ = "clients"

    client_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    # Убрать default, чтобы поле могло быть пустым
    status = db.Column(db.String(20), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
