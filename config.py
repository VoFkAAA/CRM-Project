import os

# Определяем окружение по переменной ENV
ENV = os.getenv("ENV", "local")

if ENV == "server":
    from config_server import Config
else:
    from config_local import Config