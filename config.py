import os

ENV = os.getenv("ENV", "local")

if ENV == "server":
    from config_prod import Config
else:
    from config_dev import Config
