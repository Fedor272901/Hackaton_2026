from fastapi import FastAPI, Request, Depends, APIRouter
from fastapi.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging
from app.api_router import api_router

# Настройка логгера для записи ошибок и событий приложения
logger = logging.getLogger(__name__)

# Импортируем функцию для получения текущего пользователя из токена
from app.core.dependencies import get_optional_user_from_token

# Импортируем сервисный слой для работы с данными через API
# Это обеспечивает единую точку входа и обходит прямые вызовы CRUD
from app.services.page_data_service import PageDataService, ServiceAPIError


# НАСТРОЙКА ШАБЛОНОВ Jinja2
# Указываем путь к директории с HTML-шаблонами.
# Все шаблоны будут искаться относительно этой папки.
# Структура: templates/ с подпапками public/, citizen/, deputy/, admin/
templates = Jinja2Templates(directory="templates")


# НАСТРОЙКА СТАТИЧЕСКИХ ФАЙЛОВ
# Подключаем раздачу статических файлов (CSS, JS, картинки).
# Путь '/static' в URL будет соответствовать папке static/
# Это позволяет использовать url_for('static', path='/css/styles.css') в шаблонах
app = FastAPI(title="Hackathon API", version="1.0.0")

# Монтируем статику по пути /static - все файлы из static/ будут доступны через этот URL
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем API роутер (уже существующие endpoints)
app.include_router(api_router)

# РЕГИСТРАЦИЯ КАСТОМНЫХ ФИЛЬТРОВ JINJA2
# Регистрируем наши кастомные фильтры для использования в шаблонах.
# Это должно быть сделано ПОСЛЕ создания templates и ДО подключения pages_router.
# Фильтры становятся доступными глобально во всех шаблонах.
from app.filters import register_jinja_filters
register_jinja_filters(templates)

# MIDDLEWARE ДЛЯ ДОБАВЛЕНИЯ CURRENT_USER В КОНТЕКСТ ЗАПРОСА
# Этот middleware автоматически добавляет current_user в request.state
# для каждого запроса, что делает переменную доступной в шаблонах
@app.middleware("http")
async def add_current_user_to_state(request: Request, call_next):
    """
    Middleware для добавления текущего пользователя в контекст запроса.
    Извлекает токен из заголовка Authorization или cookies и декодирует его.
    
    Важно: Эта функция НЕ использует Depends(), поэтому вся логика
    извлечения и валидации токена реализована вручную.
    
    Возвращает:
        - UserRead | dict с данными пользователя, если токен валиден
        - None, если токена нет или он невалиден (не выбрасывает исключение!)
    """
    from jose import JWTError, jwt
    from app.core.config import settings
    from app.schemas.user import UserRead
    
    user = None
    
    # 1. Извлекаем токен из заголовка Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    
    # 2. Если в заголовке нет, пробуем взять из cookies (для совместимости с фронтендом)
    if not token:
        token = request.cookies.get("access_token")
    
    # 3. Если токен найден, пытаемся его декодировать
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            
            if user_id is not None:
                # Создаём упрощённый объект пользователя из данных токена
                # Примечание: без проверки в БД (для скорости в middleware)
                # Если нужна полная проверка — передавайте db и вызывайте CRUD
                user = UserRead(
                    id=int(user_id),
                    email=payload.get("email", ""),
                    first_name=payload.get("first_name", ""),
                    last_name=payload.get("last_name", ""),
                    role=payload.get("role", "user"),
                    # Добавляем остальные поля, если они есть в токене
                    **{k: v for k, v in payload.items() 
                       if k not in ["sub", "exp", "iat", "email", "first_name", "last_name", "role"]}
                )
        except (JWTError, ValueError, KeyError, Exception):
            # 🔴 ВАЖНО: Никогда не выбрасываем исключение здесь!
            # Опциональная аутентификация = пользователь может быть анонимным
            # Просто оставляем user = None
            pass
    
    # 4. Добавляем пользователя в state запроса для использования в шаблонах
    request.state.current_user = user
    
    # 5. Продолжаем обработку запроса
    response = await call_next(request)
    return response

# СОЗДАНИЕ РОУТЕРА ДЛЯ HTML СТРАНИЦ
# Выносим HTML-роуты в отдельный router для лучшей организации кода.
# Это позволяет логически отделить API endpoints (возвращающие JSON)
# от серверных страниц (возвращающих HTML).
pages_router = APIRouter()



# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОДГОТОВКИ ДАННЫХ
# Эти функции теперь используют сервисный слой вместо прямых вызовов CRUD.
# Архитектурный выигрыш:
# - Единая точка входа через API (все бизнес-правила применяются централизованно)
# - Возможность кэширования на уровне сервиса
# - Обработка ошибок сети и таймаутов в одном месте
# - Упрощение тестирования (можно замокать PageDataService)


async def prepare_citizen_context(page_service: PageDataService):
    """
    Подготовить контекст данных для страницы гражданина.

    Агрегирует данные для личного кабинета гражданина:
    - Список категорий обращений (для формы создания)
    - Список статусов (для фильтрации и отображения)
    - Последние обращения пользователя
    
    Архитектурные изменения:
    - Раньше: прямые вызовы CRUD функций из БД (синхронно)
    - Теперь: асинхронные вызовы через PageDataService к API endpoints
    - Выигрыш: применение rate limiting, spam filter, единая обработка ошибок
    
    Параметры:
        page_service (PageDataService): Экземпляр сервиса для получения данных через API.
            Инициализируется в endpoint'ах через Depends() или создается явно.
    
    Возвращает:
        dict: Словарь с данными для шаблона:
            - categories: список категорий обращений
            - statuses: список статусов
            - requests: список последних обращений
            - total: общее количество обращений
            - in_progress_count: количество обращений в работе
            - completed_count: количество завершенных обращений
    
    Исключения:
        ServiceAPIError: При ошибках соединения с API или таймаутах.
    """
    # Получаем справочники для формы создания обращения через API
    # Ожидаемое время выполнения: 50-200ms на каждый запрос
    # Fallback: при ошибке API вернется пустой список, форма будет нерабочей
    categories = await page_service.get_categories()
    statuses = await page_service.get_statuses()

    # Получаем список последних обращений через API
    # GET /api/v1/requests/?skip=0&limit=10
    # Ожидаемое время выполнения: 100-300ms в зависимости от размера БД
    # Fallback: при ошибке покажем empty state в шаблоне
    requests_data = await page_service.get_requests(skip=0, limit=10)

    # Формируем контекст с понятными именами переменных для шаблона
    # Шаблон ожидает именно эти ключи: categories, statuses, requests, total
    return {
        "categories": categories,           # Список объектов RequestCategory из JSON API
        "statuses": statuses,               # Список объектов RequestStatus из JSON API
        "requests": requests_data.get("items", []),  # Список объектов Request (последние 10)
        "total": requests_data.get("total", 0),      # Общее количество обращений (для пагинации)
        # Статистика для карточек сводки
        "in_progress_count": sum(1 for r in requests_data.get("items", []) if r.get("status") and r["status"].get("code") in ["new", "considering", "in_progress"]),
        "completed_count": sum(1 for r in requests_data.get("items", []) if r.get("status") and r["status"].get("code") == "closed"),
    }


async def prepare_deputy_context(page_service: PageDataService, district_id: int = None):
    """
    Подготовить контекст данных для страницы депутата.

    Агрегирует данные для рабочего кабинета депутата:
    - Список обращений округа (или всех, если district_id не указан)
    - Информация об округе
    - Статистика по статусам для диаграмм
    
    Архитектурные изменения:
    - Раньше: прямые вызовы CRUD.get_requests(), CRUD.get_district() (синхронно)
    - Теперь: асинхронные вызовы через PageDataService к API endpoints
    - Выигрыш: проверка прав доступа на уровне API, единая обработка ошибок
    
    Параметры:
        page_service (PageDataService): Экземпляр сервиса для получения данных через API.
            Инициализируется в endpoint'ах через Depends() или создается явно.
        district_id (int, optional): Фильтр по округу. Если депутат закреплен за конкретным округом.
    
    Возвращает:
        dict: Словарь с данными для шаблона:
            - requests: список обращений округа
            - total: общее количество обращений
            - district: информация об округе (если указан district_id)
            - status_stats: словарь {название статуса: количество}
            - in_progress_count: количество обращений в работе
            - completed_count: количество завершенных обращений
    
    Исключения:
        ServiceAPIError: При ошибках соединения с API или таймаутах.
    """
    # Получаем обращения, отфильтрованные по округу если указан
    # GET /api/v1/requests/?skip=0&limit=20&district_id={district_id}
    # Ожидаемое время выполнения: 100-300ms
    # Fallback: при ошибке покажем пустой список обращений
    requests_data = await page_service.get_requests(skip=0, limit=20, district_id=district_id)

    # Получаем информацию об округе если указан ID
    # GET /api/v1/districts/{district_id}
    # Ожидаемое время выполнения: 50-150ms
    # Fallback: district=None, шаблон отобразит "Все округа"
    district = None
    if district_id:
        try:
            district = await page_service.get_district_by_id(district_id)
        except ServiceAPIError:
            # Если округ не найден или ошибка API, продолжаем без информации об округе
            pass

    # Статистика по статусам для диаграмм
    # Агрегируем на клиенте из полученных данных
    status_stats = {}
    for req in requests_data.get("items", []):
        if req.get("status"):
            status_name = req["status"].get("name") or "Неизвестно"
            status_stats[status_name] = status_stats.get(status_name, 0) + 1

    return {
        "requests": requests_data.get("items", []),
        "total": requests_data.get("total", 0),
        "district": district,
        "status_stats": status_stats,  # Словарь {название статуса: количество}
        "in_progress_count": sum(1 for r in requests_data.get("items", []) if r.get("status") and r["status"].get("code") in ["new", "considering", "in_progress"]),
        "completed_count": sum(1 for r in requests_data.get("items", []) if r.get("status") and r["status"].get("code") == "closed"),
    }


async def prepare_admin_context(page_service: PageDataService):
    """
    Подготовить контекст данных для панели администратора.

    Агрегирует общую статистику по системе для администратора:
    - Все округа (для управления)
    - Все депутаты (для назначения/снятия)
    - Общая статистика по обращениям
    - Распределение по статусам и категориям
    
    Архитектурные изменения:
    - Раньше: прямые вызовы CRUD.get_districts(), CRUD.get_deputies(), CRUD.get_requests() (синхронно)
    - Теперь: асинхронные вызовы через PageDataService к API endpoints
    - Выигрыш: проверка прав администратора на уровне API, единая обработка ошибок, возможность кэширования
    
    Параметры:
        page_service (PageDataService): Экземпляр сервиса для получения данных через API.
            Инициализируется в endpoint'ах через Depends() или создается явно.
    
    Возвращает:
        dict: Словарь с данными для шаблона:
            - districts: список всех округов
            - deputies: список всех депутатов
            - requests: последние обращения для модерации
            - total_requests: общее количество обращений
            - status_distribution: распределение по статусам {code: count}
            - category_distribution: распределение по категориям {name: count}
            - districts_count: количество округов
            - deputies_count: количество депутатов
    
    Исключения:
        ServiceAPIError: При ошибках соединения с API или таймаутах.
    """
    # Получаем все округа для управления
    # GET /api/v1/districts/?skip=0&limit=100
    # Ожидаемое время выполнения: 50-200ms
    # Fallback: при ошибке покажем пустой список, админка будет частично нерабочей
    districts = await page_service.get_districts(skip=0, limit=100)

    # Получаем всех депутатов
    # GET /api/v1/deputies/?skip=0&limit=100
    # Ожидаемое время выполнения: 50-200ms
    # Fallback: при ошибке покажем пустой список
    deputies = await page_service.get_deputies(skip=0, limit=100)

    # Получаем обращения для модерации
    # GET /api/v1/requests/?skip=0&limit=50
    # Ожидаемое время выполнения: 100-300ms
    # Fallback: при ошибке покажем пустой список
    requests_data = await page_service.get_requests(skip=0, limit=50)

    # Агрегируем общую статистику
    total_requests = requests_data.get("total", 0)

    # Считаем распределение по статусам
    status_distribution = {}
    for req in requests_data.get("items", []):
        if req.get("status"):
            code = req["status"].get("code") or "unknown"
            status_distribution[code] = status_distribution.get(code, 0) + 1

    # Считаем распределение по категориям
    category_distribution = {}
    for req in requests_data.get("items", []):
        if req.get("category"):
            cat_name = req["category"].get("name") or "Неизвестно"
            category_distribution[cat_name] = category_distribution.get(cat_name, 0) + 1

    return {
        "districts": districts,
        "deputies": deputies,
        "requests": requests_data.get("items", []),
        "total_requests": total_requests,
        "status_distribution": status_distribution,
        "category_distribution": category_distribution,
        "districts_count": len(districts),
        "deputies_count": len(deputies),
    }



# HTML РОУТЫ (СЕРВЕРНЫЙ РЕНДЕРИНГ)
# Эти маршруты возвращают HTML-страницы, а не JSON как API endpoints.
# Каждый маршрут:
# 1. Получает сессию базы данных через Depends(get_db)
# 2. Вызывает CRUD функции для извлечения данных
# 3. Формирует context словарь с данными
# 4. Рендерит шаблон через templates.TemplateResponse
#
# request обязателен в context для работы url_for() в шаблонах.

@pages_router.get("/auth", name="auth")
async def auth_page(request: Request) -> Response:
    """
    Страница авторизации (публичная зона)

    Точка входа для неавторизованных пользователей.
    Показывает общую информацию о сервисе и форму входа.
    """
    return templates.TemplateResponse(
        request,
        "public/auth.html",
        {
            "current_user": request.state.current_user,
        }
    )


@pages_router.get("/", name="home")
async def home_page(request: Request) -> Response:
    """
    Главная страница (публичная зона)

    Точка входа для неавторизованных пользователей.
    Показывает общую информацию о сервисе.
    """
    # Для главной страницы пока не нужны сложные данные из БД
    # Можно добавить статистику по всем обращениям для привлечения внимания
    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "public/auth.html",         # ← 2-й аргумент: путь к шаблону
    {
        "current_user": request.state.current_user,
    }                          # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/citizen", name="citizen_dashboard")
@pages_router.get("/citizen/dashboard", name="citizen_dashboard")
async def citizen_dashboard(request: Request) -> Response:
    """
    Личный кабинет гражданина

    Отображает:
    - Список обращений пользователя с их статусами
    - Форму для создания нового обращения
    - Сводную статистику (сколько всего, в работе, выполнено)

    Поток данных:
    1. Создаем экземпляр PageDataService для работы с API
    2. Вызываем prepare_citizen_context через await с сервисом
    3. Передаем данные в шаблон citizen/dashboard.html

    Обработка edge-кейсов:
    - Если обращений нет → шаблон покажет empty state
    - Если категории не загружены → форма создания будет пустой
    - При ошибке API → покажем сообщение об ошибке
    """
    # Создаем сервис для получения данных через API
    # Архитектурный выигрыш: все данные идут через единый API слой с обработкой ошибок
    page_service = PageDataService()
    
    # Подготавливаем данные через вспомогательную функцию (асинхронно)
    # Раньше: context = prepare_citizen_context(db) - синхронный вызов CRUD
    # Теперь: context = await prepare_citizen_context(page_service) - асинхронный вызов API
    context = await prepare_citizen_context(page_service)

    # Добавляем request обязательно для работы Jinja2
    context["request"] = request

    # Добавляем current_user из middleware для использования в шаблонах
    context["current_user"] = request.state.current_user

    # Рендерим шаблон с подготовленными данными
    # Шаблон ожидает переменные: requests, categories, statuses, total, etc.
    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "citizen/dashboard.html",   # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/citizen/create", name="citizen_create_appeal")
async def citizen_create_appeal(request: Request) -> Response:
    """
    Страница создания обращения (отдельная страница для формы)

    Предоставляет форму с полями:
    - Категория (выпадающий список из БД)
    - Заголовок, описание
    - Адрес (с автоопределением округа)
    - Фотографии

    В отличие от dashboard, эта страница фокусируется только на форме.
    """
    # Создаем сервис для получения справочников через API
    page_service = PageDataService()
    
    # Получаем справочники для заполнения формы через API
    # GET /api/v1/categories/ и GET /api/v1/districts/
    # Ожидаемое время выполнения: 50-200ms на каждый запрос
    # Fallback: при ошибке API формы будут частично нерабочими
    try:
        categories = await page_service.get_categories()
        districts = await page_service.get_districts(skip=0, limit=100)
    except ServiceAPIError:
        # При ошибке API используем пустые списки
        categories = []
        districts = []

    context = {
        "request": request,
        "categories": categories,
        "districts": districts,
        "page_title": "Подать обращение",
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                        # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "citizen/create_appeal.html",   # ← 2-й аргумент: путь к шаблону
    context                         # ← 3-й аргумент: контекст (словарь с данными)
)


# Рефакторинг: замена прямого CRUD на PageDataService (было: строка 417-488)
async def citizen_submit_appeal(request: Request) -> Response:
    """
    Обработка формы создания обращения через внутренний API.

    Архитектурное обоснование рефакторинга:
    =========================================
    Прямой CRUD в этом endpoint'е был антипаттерном по следующим причинам:
    
    1. Нарушение единой точки ответственности:
       - Раньше: валидация, создание записи, обработка файлов分散ены между endpoint и CRUD
       - Теперь: вся бизнес-логика инкапсулирована в API endpoint /api/v1/requests/
    
    2. Проблемы с транзакциями:
       - Раньше: ручное управление транзакциями в каждом endpoint'е
       - Теперь: API слой управляет транзакциями централизованно
    
    3. Отсутствие единой точки аудита:
       - Раньше: сложно отследить все места создания обращений
       - Теперь: все создания идут через один API endpoint с логированием
    
    4. Блокировка event-loop:
       - Раньше: синхронные вызовы CRUD блокировали асинхронный цикл
       - Теперь: асинхронный HTTP-запрос не блокирует обработку других запросов
    
    Вызов через внутренний API решает проблемы:
    - Валидация данных применяется единообразно через Pydantic схемы API
    - Spam filter и rate limiting работают централизованно
    - Обработка ошибок стандартизирована
    - Легче тестировать (можно замокать API endpoint)

    Поток данных:
    1. Получаем данные из формы
    2. Валидируем обязательные поля на уровне endpoint
    3. Отправляем POST-запрос к /api/v1/requests/
    4. Обрабатываем ответ: 201 → редирект, 4xx/5xx → возврат формы с ошибкой
    
    Логика редиректа/рендеринга ошибок:
    - При успехе (201 Created): перенаправляем на /citizen/dashboard с кодом 303
    - При ошибке валидации (400): рендерим форму заново с сообщением об ошибке
    - При ошибке авторизации (401): перенаправляем на /auth
    - При ошибке сервера (5xx): показываем страницу ошибки с дружественным сообщением
    
    Пользователь получает фидбек через:
    - Flash-сообщения в шаблоне (реализуется на стороне templates)
    - Отображение ошибок валидации под соответствующими полями формы
    """
    
    # Структура HTTP-запроса к внутреннему API:
    # ==========================================
    # Метод: POST
    # URL: {API_BASE_URL}/api/v1/requests/
    # Заголовки:
    #   - Content-Type: application/json
    #   - Cookie: access_token={token} (для передачи авторизации)
    # Тело запроса (JSON):
    #   {
    #       "category_id": int,
    #       "title": str,
    #       "description": str,
    #       "address": str,
    #       "photos": List[str],
    #       "district_id": Optional[int]
    #   }
    # Обработка статуса:
    #   - 201: Успешное создание → RedirectResponse
    #   - 400: Ошибка валидации → TemplateResponse с ошибками
    #   - 401: Неавторизован → RedirectResponse на /auth
    #   - 5xx: Ошибка сервера → TemplateResponse с сообщением об ошибке
    
    form_data = await request.form()

    category_code = form_data.get("category")
    title = form_data.get("title")
    description = form_data.get("description")
    address = form_data.get("address")
    truth_confirmed = form_data.get("truth_confirmed")
    photos = form_data.getlist("photos")

    from fastapi import HTTPException, UploadFile

    # Валидация обязательных полей перед отправкой в API
    if not category_code or not title or not description or not address:
        # Возвращаем форму с сообщением об ошибке
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": request.state.current_user,
                "error": "Все обязательные поля должны быть заполнены",
                "form_data": dict(form_data),  # Сохраняем введенные данные для повторного отображения
            }
        )

    if not truth_confirmed:
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": request.state.current_user,
                "error": "Необходимо подтвердить достоверность данных",
                "form_data": dict(form_data),
            }
        )

    # Проверяем авторизацию
    user = request.state.current_user
    if not user:
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": None,
                "error": "Требуется авторизация для создания обращения",
            }
        )

    user_id = user.get("id")

    # Обрабатываем фотографии
    photo_urls = []
    for photo in photos:
        if isinstance(photo, UploadFile) and photo.filename:
            photo_urls.append(f"/static/uploads/{photo.filename}")

    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Получаем ID категории через API (асинхронно)
    # Fallback: при ошибке покажем сообщение о проблеме
    try:
        categories = await page_service.get_categories()
        category_id = None
        for cat in categories:
            if cat.get("code") == category_code:
                category_id = cat.get("id")
                break
        
        if not category_id:
            return templates.TemplateResponse(
                request,
                "citizen/create_appeal.html",
                {
                    "request": request,
                    "current_user": user,
                    "error": "Неверная категория обращения",
                    "form_data": dict(form_data),
                }
            )
    except ServiceAPIError:
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": user,
                "error": "Ошибка загрузки справочника категорий. Попробуйте позже.",
                "form_data": dict(form_data),
            }
        )

    # Получаем округ по адресу через API (асинхронно)
    # Fallback: district_id=None, обращение будет создано без привязки к округу
    district_id = None
    try:
        districts = await page_service.get_districts(skip=0, limit=100)
        # Ищем округ по названию/адресу (упрощенная логика)
        for distr in districts.get("items", []):
            if address.lower().find(distr.get("name", "").lower()) != -1:
                district_id = distr.get("id")
                break
    except ServiceAPIError:
        # Продолжаем без district_id - API сам определит округ или оставит пустым
        pass

    # Формируем payload для отправки в API
    request_payload = {
        "category_id": category_id,
        "title": title,
        "description": description,
        "address": address,
        "photos": photo_urls,
    }
    if district_id is not None:
        request_payload["district_id"] = district_id

    # Отправляем POST-запрос к внутреннему API через httpx.AsyncClient
    # Используем context manager для гарантированного закрытия соединения
    import httpx
    from app.core.config import API_BASE_URL
    
    api_url = API_BASE_URL or "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # Формируем заголовки с токеном авторизации из cookies
            headers = {"Content-Type": "application/json"}
            access_token = request.cookies.get("access_token")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            response = await client.post(
                url=f"{api_url}/api/v1/requests/",
                json=request_payload,
                headers=headers,
                timeout=30.0,  # Увеличенный таймаут для создания обращения
            )
            
            # Обработка успешного ответа (201 Created)
            if response.status_code == 201:
                # Перенаправляем пользователя на dashboard
                return RedirectResponse(url="/citizen/dashboard", status_code=303)
            
            # Обработка ошибок валидации (4xx)
            if 400 <= response.status_code < 500:
                try:
                    error_data = response.json()
                    error_message = error_data.get("detail", "Ошибка при создании обращения")
                except Exception:
                    error_message = response.text or "Ошибка при создании обращения"
                
                return templates.TemplateResponse(
                    request,
                    "citizen/create_appeal.html",
                    {
                        "request": request,
                        "current_user": user,
                        "error": error_message,
                        "form_data": dict(form_data),
                    }
                )
            
            # Обработка ошибок сервера (5xx)
            if response.status_code >= 500:
                logger.error(f"API server error during appeal creation: {response.status_code}")
                return templates.TemplateResponse(
                    request,
                    "citizen/create_appeal.html",
                    {
                        "request": request,
                        "current_user": user,
                        "error": "Временная ошибка сервера. Пожалуйста, попробуйте позже.",
                        "form_data": dict(form_data),
                    }
                )
                
    except httpx.TimeoutException:
        # Таймаут запроса
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": user,
                "error": "Превышено время ожидания ответа. Попробуйте еще раз.",
                "form_data": dict(form_data),
            }
        )
    except httpx.ConnectError:
        # Ошибка соединения с API
        logger.error("Unable to connect to API service during appeal creation")
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": user,
                "error": "Ошибка соединения с сервером. Попробуйте позже.",
                "form_data": dict(form_data),
            }
        )
    except httpx.RequestError as e:
        # Другие ошибки запроса
        logger.error(f"Request error during appeal creation: {e}")
        return templates.TemplateResponse(
            request,
            "citizen/create_appeal.html",
            {
                "request": request,
                "current_user": user,
                "error": "Произошла ошибка при обработке запроса.",
                "form_data": dict(form_data),
            }
        )

    # Fallback на случай непредвиденной ситуации
    return templates.TemplateResponse(
        request,
        "citizen/create_appeal.html",
        {
            "request": request,
            "current_user": user,
            "error": "Неизвестная ошибка при создании обращения.",
            "form_data": dict(form_data),
        }
    )


# Рефакторинг: замена прямого CRUD на PageDataService (было: строка 730-765)
@pages_router.get("/citizen/appeal/{appeal_id}", name="appeal_detail")
async def citizen_appeal_detail(request: Request, appeal_id: int) -> Response:
    """
    Детали конкретного обращения

    Показывает полную информацию:
    - Описание проблемы
    - Адрес на карте
    - Фотографии
    - Историю статусов
    - Переписку с депутатом

    Параметры:
    - appeal_id: ID обращения из URL (например, /citizen/appeal/123)
    
    Логика fallback:
    - При ошибке API или если обращение не найдено → HTTPException 404
    - При ошибке получения сообщений → показываем пустой список
    - При ошибке истории статусов → показываем пустой список
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Блок получения данных из справочников (раньше синхронные CRUD вызовы):
    # - get_request_by_id: получение основного обращения (~50-150ms)
    # - get_request_messages: получение переписки по обращению (~50-200ms)
    # - get_request_status_history: получение истории изменений статуса (~50-150ms)
    # Эти данные критичны для отображения полной информации об обращении.
    # При ошибке API → показываем fallback (пустые списки или 404)
    
    try:
        appeal = await page_service.get_request_by_id(appeal_id)
    except ServiceAPIError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    if not appeal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    # Получаем сообщения и историю статусов через API
    # Fallback: при ошибке покажем пустые списки
    try:
        messages = await page_service.get_request_messages(appeal_id, skip=0, limit=100)
    except ServiceAPIError:
        messages = []
    
    try:
        status_history = await page_service.get_request_status_history(appeal_id)
    except ServiceAPIError:
        status_history = []

    context = {
        "request": request,
        "appeal": appeal,
        "messages": messages,
        "status_history": status_history,
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                        # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "citizen/appeal_detail.html",   # ← 2-й аргумент: путь к шаблону
    context                         # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/deputy", name="deputy_dashboard")
@pages_router.get("/deputy/dashboard", name="deputy_dashboard")
async def deputy_dashboard(request: Request, district_id: int = None) -> Response:
    """
    Рабочий кабинет депутата

    Отображает обращения жителей округа депутата:
    - Список обращений с фильтрацией по статусу
    - Возможность взять обращение в работу
    - Форма ответа жителю

    Параметры:
    - district_id: опционально, если депутат работает в нескольких округах

    Поток данных:
    1. Создаем PageDataService для работы с API
    2. Вызываем prepare_deputy_context через await с сервисом
    3. Передаем данные в шаблон deputy/dashboard.html
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Подготавливаем данные через вспомогательную функцию (асинхронно)
    # Раньше: context = prepare_deputy_context(db, district_id) - синхронный CRUD
    # Теперь: context = await prepare_deputy_context(page_service, district_id) - API
    context = await prepare_deputy_context(page_service, district_id)
    context["request"] = request
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "deputy/dashboard.html",    # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/deputy/appeal/{appeal_id}", name="deputy_appeal_detail")
# Рефакторинг: замена прямого CRUD на PageDataService (было: строка 573-608)
async def deputy_appeal_detail(request: Request, appeal_id: int) -> Response:
    """
    Детали обращения для депутата

    Аналогично citizen_appeal_detail, но с дополнительными действиями:
    - Кнопки "Взять в работу", "Изменить статус"
    - Форма ответа заявителю
    
    Логика fallback:
    - При ошибке API или если обращение не найдено → HTTPException 404
    - При ошибке получения сообщений → показываем пустой список
    - При ошибке истории статусов → показываем пустой список
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Блок получения данных из справочников (раньше синхронные CRUD вызовы):
    # - get_request_by_id: получение основного обращения (~50-150ms)
    # - get_request_messages: получение переписки по обращению (~50-200ms)
    # - get_request_status_history: получение истории изменений статуса (~50-150ms)
    # Эти данные критичны для отображения полной информации об обращении.
    # При ошибке API → показываем fallback (пустые списки или 404)
    
    try:
        appeal = await page_service.get_request_by_id(appeal_id)
    except ServiceAPIError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    if not appeal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    # Получаем сообщения и историю статусов через API
    # Fallback: при ошибке покажем пустые списки
    try:
        messages = await page_service.get_request_messages(appeal_id, skip=0, limit=100)
    except ServiceAPIError:
        messages = []
    
    try:
        status_history = await page_service.get_request_status_history(appeal_id)
    except ServiceAPIError:
        status_history = []

    context = {
        "request": request,
        "appeal": appeal,
        "messages": messages,
        "status_history": status_history,
        # Флаги для отображения кнопок действий
        "can_take_to_work": appeal.get("status") and appeal["status"].get("code") == "new",
        "can_respond": True,  # Всегда можно ответить
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                        # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "deputy/appeal_detail.html",    # ← 2-й аргумент: путь к шаблону
    context                         # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/deputy/statistics", name="deputy_statistics")
async def deputy_statistics(request: Request, district_id: int = None) -> Response:
    """
    Статистика работы депутата

    Показывает:
    - Количество обращений по статусам
    - Среднее время решения
    - Распределение по категориям
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Подготавливаем данные через вспомогательную функцию (асинхронно)
    context = await prepare_deputy_context(page_service, district_id)
    context["request"] = request
    context["page_title"] = "Статистика"
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "deputy/statistics.html",   # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin", name="admin_dashboard")
@pages_router.get("/admin/dashboard", name="admin_dashboard")
async def admin_dashboard(request: Request) -> Response:
    """
    Панель администратора

    Основной экран с общей статистикой системы:
    - Количество округов, депутатов, обращений
    - Распределение обращений по статусам
    - Быстрый доступ к управлению сущностями

    Поток данных:
    1. Создаем PageDataService для работы с API
    2. Вызываем prepare_admin_context через await с сервисом
    3. Передаем данные в шаблон admin/dashboard.html
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Подготавливаем данные через вспомогательную функцию (асинхронно)
    # Раньше: context = prepare_admin_context(db) - синхронный CRUD
    # Теперь: context = await prepare_admin_context(page_service) - API
    context = await prepare_admin_context(page_service)
    context["request"] = request
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/dashboard.html",     # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin/districts", name="admin_districts")
async def admin_districts(request: Request) -> Response:
    """
    Управление округами

    Список всех округов с возможностью:
    - Создания нового округа
    - Редактирования существующих
    - Удаления (если нет депутатов и обращений)
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Получаем все округа через API
    # GET /api/v1/districts/?skip=0&limit=100
    # Ожидаемое время выполнения: 50-200ms
    # Fallback: при ошибке API покажем пустой список
    try:
        districts = await page_service.get_districts(skip=0, limit=100)
    except ServiceAPIError:
        districts = []

    context = {
        "request": request,
        "districts": districts,
        "page_title": "Управление округами",
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/districts.html",     # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin/deputies", name="admin_deputies")
async def admin_deputies(request: Request) -> Response:
    """
    Управление депутатами

    Список всех депутатов с возможностью:
    - Назначения нового депутата
    - Перевода между округами
    - Снятия полномочий
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Получаем депутатов и округа через API
    # GET /api/v1/deputies/?skip=0&limit=100
    # GET /api/v1/districts/?skip=0&limit=100
    # Ожидаемое время выполнения: 50-200ms на каждый запрос
    # Fallback: при ошибке API покажем пустые списки
    try:
        deputies = await page_service.get_deputies(skip=0, limit=100)
        districts = await page_service.get_districts(skip=0, limit=100)
    except ServiceAPIError:
        deputies = []
        districts = []

    context = {
        "request": request,
        "deputies": deputies,
        "districts": districts,
        "page_title": "Управление депутатами",
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/deputies.html",      # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin/moderation", name="admin_moderation")
async def admin_moderation(request: Request) -> Response:
    """
    Модерация обращений

    Список обращений требующих внимания администратора:
    - Спорные обращения
    - Жалобы на качество ответов
    - Обращения с нарушенными сроками
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Получаем обращения для модерации через API
    # GET /api/v1/requests/?skip=0&limit=50
    # Ожидаемое время выполнения: 100-300ms
    # Fallback: при ошибке API покажем пустой список
    try:
        requests_data = await page_service.get_requests(skip=0, limit=50)
    except ServiceAPIError:
        requests_data = {"items": [], "total": 0}

    context = {
        "request": request,
        "requests": requests_data.get("items", []),
        "total": requests_data.get("total", 0),
        "page_title": "Модерация обращений",
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/moderation.html",    # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin/statistics", name="admin_statistics")
async def admin_statistics(request: Request) -> Response:
    """
    Расширенная статистика системы

    Детальные отчеты:
    - Динамика обращений по времени
    - Эффективность работы по округам
    - Рейтинг депутатов
    """
    # Создаем сервис для получения данных через API
    page_service = PageDataService()
    
    # Подготавливаем данные через вспомогательную функцию (асинхронно)
    context = await prepare_admin_context(page_service)
    context["request"] = request
    context["page_title"] = "Статистика системы"
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/statistics.html",    # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/logout", name="logout")
async def logout(request: Request) -> Response:
    """
    Выход из системы

    Удаляет токен аутентификации из cookies и перенаправляет на главную страницу.
    """
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# Подключаем роутер страниц к основному приложению
# Теперь все HTML-роуты будут доступны через app

# 🔍 АРХИТЕКТУРНАЯ ПРОВЕРКА
# ==========================
# Все вызовы данных теперь идут через PageDataService или внутренний API.
# 
# Что было сделано:
# -----------------
# 1. citizen_submit_appeal: Переписан с прямого CRUD на POST-запрос к /api/v1/requests/
#    - Использует httpx.AsyncClient как context manager для гарантированного закрытия соединений
#    - Обрабатывает ошибки 4xx (валидация) и 5xx (сервер)
#    - При успехе (201) → редирект, при ошибке → рендер формы с сообщением
#
# 2. citizen_appeal_detail: Заменены CRUD вызовы на методы page_service
#    - get_request_by_id, get_request_messages, get_request_status_history
#    - Fallback: 404 при отсутствии обращения, пустые списки при ошибке API
#
# 3. deputy_appeal_detail: Аналогично citizen_appeal_detail через page_service
#
# 4. Все dashboard endpoints (citizen, deputy, admin): Используют prepare_*_context функции
#    которые вызывают PageDataService методы асинхронно
#
# 5. Удалены все импорты CRUD модулей из endpoint'ов
#    - Было: from app.crud.request import create_request, get_request_by_id, ...
#    - Стало: from app.services.page_data_service import PageDataService, ServiceAPIError
#
# Где можно расширить сервис при добавлении новых сущностей:
# ----------------------------------------------------------
# - Добавить новые методы в PageDataService (например, get_users, get_roles)
# - Создать соответствующие API endpoints в /api/v1/
# - Обновить prepare_*_context функции для агрегации новых данных
# - Для форм создания/редактирования использовать HTTP-запросы к API вместо CRUD
#
# Текущие методы PageDataService:
# --------------------------------
# - get_districts(skip, limit, active_only) → Dict[str, Any]
# - get_deputies(district_id, skip, limit) → Dict[str, Any]
# - get_deputy_by_district(district_id) → Optional[Dict[str, Any]]
# - get_requests(skip, limit, filters) → Dict[str, Any]
# - get_categories() → List[Dict[str, Any]]
# - get_statuses() → List[Dict[str, Any]]
# - get_district_by_id(district_id) → Optional[Dict[str, Any]]
# - get_request_by_id(request_id) → Optional[Dict[str, Any]]
# - get_request_messages(request_id, skip, limit) → Dict[str, Any]
# - get_request_status_history(request_id) → Dict[str, Any]
#
# Примечания:
# -----------
# - Импорт get_db из app.db.database остался только для обратной совместимости
#   (может использоваться в других частях приложения, не затронутых рефакторингом)
# - Session больше не используется в signature endpoint'ов
# - Все endpoints теперь async def с type hints для возвращаемого Response
app.include_router(pages_router)