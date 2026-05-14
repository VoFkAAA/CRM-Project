import re


def clean_phone_number(phone: str) -> str:
    """Очистка телефона"""
    return phone[1:]

        

def validate_phone_input(phone_input: str) -> tuple[bool, str]:
    valid = True
    msg = ""
    if len(phone_input) != 11 and not phone_input.startswith(("7", "8")):
        valid = False
        msg = "Введенный телефона должен начинаться с 7 или 8  и содержать 11 цифр"
    return valid, msg


def validate_phone_number(phone_input: str) -> tuple[bool, str]:
    valid = True
    msg = ""
    if len(phone_input) != 11 or not phone_input.isdigit():
        valid = False
        msg = "Телефон должен содержать 11 цифр"
    elif not phone_input.startswith(("7", "8")):
        valid = False
        msg = "Телефон должен начинаться с 7 или 8"
    return valid, msg


def validate_password(password: str) -> bool:
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
    valid = True
    msg = ""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        valid = False
        msg = "Некорректный email"
    return valid, msg