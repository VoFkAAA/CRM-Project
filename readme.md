clone git@github.com:VoFkAAA/CRM-Project.git
python -m venv crm_env
source crm_env/bin/activate
cd CRM-Project
pip install -r requirements.txt

# Для прода добавить переменнюу окружения
export ENV=server

# Запустить приложение в debug-режиме
flask run --debug






