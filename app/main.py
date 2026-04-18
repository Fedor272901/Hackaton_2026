from fastapi import FastAPI
from app.api_router import api_router
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

app = FastAPI(title="Hackathon API", version="1.0.0")

app.include_router(api_router)

# Импортируем FastAPI - современный фреймворк для создания API на Python
from fastapi import FastAPI, Request

# Импортируем роутер для API endpoints (уже существующая часть проекта)
from app.api_router import api_router

# Импортируем Jinja2Templates для серверного рендеринга HTML-шаблонов
# Jinja2 - это мощный шаблонизатор, который позволяет создавать динамические HTML-страницы
# Мы используем его для отображения веб-интерфейса пользователям
from fastapi.templating import Jinja2Templates

# Импортируем StaticFiles для раздачи статических файлов (CSS, JS, изображения)
# Это нужно чтобы браузеры могли загружать стили и скрипты по правильным путям
from fastapi.staticfiles import StaticFiles

# ============================================================================
# НАСТРОЙКА ШАБЛОНОВ (Jinja2)
# ============================================================================
# Указываем путь к директории с HTML-шаблонами.
# Все шаблоны будут искаться относительно этой папки.
# Структура: app/templates/ с подпапками public/, citizen/, deputy/, admin/
templates = Jinja2Templates(directory="templates")

# ============================================================================
# НАСТРОЙКА СТАТИЧЕСКИХ ФАЙЛОВ
# ============================================================================
# Подключаем раздачу статических файлов (CSS, JS, картинки).
# Путь '/static' в URL будет соответствовать папке app/static/
# Например: /static/css/base.css -> app/static/css/base.css
# Это позволяет использовать url_for('static', path='/css/base.css') в шаблонах
app = FastAPI(title="Hackathon API", version="1.0.0")

# Монтируем статику по пути /static - все файлы из app/static/ будут доступны через этот URL
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем API роутер (уже существующие endpoints)
app.include_router(api_router)

# ============================================================================
# HTML РОУТЫ (СЕРВЕРНЫЙ РЕНДЕРИНГ)
# ============================================================================
# Эти маршруты возвращают HTML-страницы, а не JSON как API endpoints.
# Каждый маршрут использует templates.TemplateResponse для рендеринга шаблона.


@app.get("/")
async def home_page(request: Request):
    """
    Главная страница приложения (публичная зона).

    Возвращает HTML-страницу с общей информацией о приложении.
    Использует шаблон public/index.html, который наследуется от base.html.
    request обязателен для работы url_for() в шаблонах.
    """
    return templates.TemplateResponse(
        request,                    # ← первый аргумент: объект request
        "public/auth.html",         # ← второй: имя шаблона
        {}                          # ← третий: контекст (опционально)
    )


@app.get("/citizen")
async def citizen_page(request: Request):
    """
    Страница гражданина (личный кабинет пользователя).

    Здесь граждане могут просматривать и создавать заявки.
    Использует шаблон citizen/index.html.
    В будущем здесь будет проверка авторизации и роли пользователя.
    """
    return templates.TemplateResponse(
        request,                    # ← первый аргумент: объект request
        "citizen/dashboard.html",   # ← второй: имя шаблона
        {}                          # ← третий: контекст (опционально)
    )


@app.get("/deputy")
async def deputy_page(request: Request):
    """
    Страница депутата (рабочий кабинет).

    Депутаты могут управлять заявками от избирателей своего округа.
    Использует шаблон deputy/index.html.
    В будущем будет интеграция с базой данных для отображения реальных заявок.
    """
    return templates.TemplateResponse(
        request,                    # ← первый аргумент: объект request
        "deputy/dashboard.html",    # ← второй: имя шаблона
        {}                          # ← третий: контекст (опционально)
    )


@app.get("/admin")
async def admin_page(request: Request):
    """
    Панель администратора.

    Администраторы управляют пользователями, настройками системы и мониторингом.
    Использует шаблон admin/index.html.
    Требуется строгая проверка прав доступа (будет добавлена позже).
    """
    return templates.TemplateResponse(
        request,                    # ← первый аргумент: объект request
        "admin/dashboard.html",     # ← второй: имя шаблона
        {}                          # ← третий: контекст (опционально)
    )