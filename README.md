# Hackathon 2026

Система для работы с обращениями граждан.

Проект был разработан в рамках хакатона. Я был капитаном команды и в основном занимался backend, базой данных и запуском проекта.

## Стек

### Backend

* Python
* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL
* PostGIS
* JWT

### Frontend

* HTML
* CSS
* JavaScript

### Infrastructure

* Docker
* Docker Compose
* Nginx

## Что реализовано

* авторизация и JWT;
* роли пользователей;
* обращения граждан;
* категории и статусы обращений;
* районы;
* назначение ответственных;
* сообщения и история изменения статусов;
* загрузка фотографий;
* статистика;
* REST API;
* работа с геоданными через PostGIS.

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

Для запуска нужны Docker и Docker Compose.

```bash
git clone git@github.com:Fedor272901/Hackaton_2026.git
cd Hackaton_2026
docker compose up -d --build
```

После запуска:

* приложение: http://localhost/
* Swagger: http://localhost/docs

При запуске backend автоматически:

1. применяет Alembic-миграции;
2. добавляет начальные данные;
3. запускает FastAPI.

### Тестовый пользователь

Email: `admin@example.com`

Password: `admin123`


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

В проекте я был капитаном команды и в основном отвечал за backend и техническую часть:

* разработка REST API и базы данных;
* работа с PostgreSQL и PostGIS;
* SQLAlchemy и Alembic;
* авторизация и роли;
* настройка запуска проекта через Docker.

## Статус

Учебный и хакатонный проект.

Проект сейчас не развивается и сохранён как пример моей работы с backend, базой данных и Docker.

Frontend в проекте реализован не полностью, поэтому основной фокус проекта — backend и техническая часть.

## Документация

Дополнительные инструкции для разработчиков находятся в [docs/development.md](docs/development.md).
