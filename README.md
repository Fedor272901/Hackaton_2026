# Hackathon 2026

Система для работы с обращениями граждан.

Проект разработан в рамках хакатона. Я был капитаном команды и в основном занимался backend-частью, базой данных и инфраструктурой запуска.

## Стек

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- PostGIS
- JWT

### Frontend

- HTML
- CSS
- JavaScript

### Infrastructure

- Docker
- Docker Compose
- Nginx

## Что реализовано

- авторизация и JWT;
- роли пользователей;
- обращения граждан;
- категории и статусы обращений;
- районы;
- назначение ответственных;
- сообщения и история изменения статусов;
- загрузка фотографий;
- статистика;
- REST API;
- работа с геоданными через PostGIS.

## Архитектура

```text
Browser
   |
   v
Nginx :80
   |------------------|
   v                  v
Frontend           FastAPI :8000
                      |
                      v
              PostgreSQL + PostGIS
```

## Запуск

Требуется Docker и Docker Compose.

git clone [git@github.com](mailto:git@github.com):Fedor272901/Hackaton_2026.git
cd Hackaton_2026
docker compose up -d --build

После запуска:

* приложение: [http://localhost/](http://localhost/)
* Swagger: [http://localhost/docs](http://localhost/docs)

При старте backend автоматически:

1. применяет Alembic-миграции;
2. выполняет seed начальных данных;
3. запускает FastAPI.

### Тестовый пользователь

Email: [admin@example.com](mailto:admin@example.com)
Password: admin123

## Структура проекта

```text
app/                  Backend и REST API
alembic/              Миграции базы данных
templates/            HTML frontend
static/               CSS и статические файлы
docs/                 Документация
seed.py               Начальное заполнение БД
Dockerfile            Образ backend
docker-compose.yml    Запуск сервисов
nginx.conf            Конфигурация Nginx
```

## Моя роль

В проекте я был капитаном команды и в основном отвечал за backend и техническую часть проекта:

* разработка REST API и БД;
* работа с PostgreSQL и PostGIS;
* SQLAlchemy и Alembic;
* авторизация и роли;

## Статус

Учебный / хакатонный проект.

Основной фокус проекта — backend, база данных и инфраструктура.

## Документация

Дополнительные инструкции для разработчиков находятся в [docs/development.md](docs/development.md).