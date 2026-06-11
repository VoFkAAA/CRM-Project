Учебная CRM-система для тестирования на Python + Flask

Браузеры (актуальные версии):
* Microsoft Edge 
* Google Chrome 
* Mozilla Firefox

Разрешения экранов:

* 1920 x 1080
* 1600 x 900

API - Swagger 
Адрес Swagger: 
_________________________________
Эндпоинты:
/register, /login, /update_profile, /logout, /create_client, /update_client, /delete_client

Есть примеры запросов (с телом запроса/ответа, где это необходимо) со статус-кодами 200, 400, 401, 403, 409

БД (СУБД) - PostgreSQL
Адрес БД: 
________________________________

Структура БД: 

Таблица users
	user_id: auto_increment, unique (SERIAL)
	name: string
	surname: string
	email: unique, string
	phone: unique, string
	register_date: timestamp (Заполняется автоматически при создании пользователя)
	birth_date: date
	department: enum (Администрация, Бухгалтерия, АХО, Закупки, Продажи, Производство)
	password_hash: string
	
Таблица clients
	client_id: auto_increment, unique (SERIAL)
	client_name: string
	email: unique, string
	phone: unique, string
	address: string
	status: enum (Active, Stopped, Blocked)
	created_by: int (id юзера - присваивается автоматически в БД)
	created_at: timestamp 
	updated_at: timestamp 
	

Flask, SQLAlchemy, Flasgger.
	Структура: 
		app.py, models.py, requirements.txt, docker-compose.yml для БД. 
