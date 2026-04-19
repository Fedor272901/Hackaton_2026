from fastapi import FastAPI, Request, Depends, APIRouter
from fastapi.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.api_router import api_router

# Импортируем зависимости для получения сессии базы данных
from app.db.database import get_db
from sqlalchemy.orm import Session

# Импортируем CRUD функции для работы с данными
# Эти функции инкапсулируют всю логику доступа к базе данных
from app.crud.request import get_requests, get_request_categories, get_request_statuses
from app.crud.district import get_districts
from app.crud.deputy import get_deputies

# Импортируем функцию регистрации кастомных фильтров Jinja2
# Фильтры нужны для форматирования дат, статусов и безопасного рендеринга HTML в шаблонах
from app.filters import register_jinja_filters

# Импортируем функцию для получения текущего пользователя из токена
from app.core.dependencies import get_optional_user_from_token


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
register_jinja_filters(templates)

# MIDDLEWARE ДЛЯ ДОБАВЛЕНИЯ CURRENT_USER В КОНТЕКСТ ЗАПРОСА
# Этот middleware автоматически добавляет current_user в request.state
# для каждого запроса, что делает переменную доступной в шаблонах
@app.middleware("http")
async def add_current_user_to_state(request: Request, call_next):
    """
    Middleware для добавления текущего пользователя в контекст запроса.

    Извлекает токен из cookies и получает данные пользователя.
    Добавляет current_user в request.state для использования в шаблонах.
    """
    request.state.current_user = await get_optional_user_from_token(request)
    response = await call_next(request)
    return response

# СОЗДАНИЕ РОУТЕРА ДЛЯ HTML СТРАНИЦ
# Выносим HTML-роуты в отдельный router для лучшей организации кода.
# Это позволяет логически отделить API endpoints (возвращающие JSON)
# от серверных страниц (возвращающих HTML).
pages_router = APIRouter()



# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОДГОТОВКИ ДАННЫХ

def prepare_citizen_context(db: Session):
    """
    Подготовить контекст данных для страницы гражданина

    Эта функция извлекает из БД все необходимые данные для отображения
    личного кабинета гражданина: список обращений пользователя, категории, статусы.

    Поток данных:
    1. Запрашиваем список всех категорий обращений (для формы создания)
    2. Запрашиваем список всех статусов (для фильтрации и отображения)
    3. Загружаем последние обращения (в будущем — с фильтрацией по user_id)

    Возвращает словарь, который будет передан в шаблон как context.
    """
    # Получаем справочники для формы создания обращения
    categories = get_request_categories(db)
    statuses = get_request_statuses(db)

    # Получаем список обращений (пока все, позже добавим фильтр по текущему пользователю)
    requests_data = get_requests(db, skip=0, limit=10)

    # Формируем контекст с понятными именами переменных для шаблона
    # Шаблон ожидает именно эти ключи: categories, statuses, requests, total
    return {
        "categories": categories,           # Список объектов RequestCategory
        "statuses": statuses,               # Список объектов RequestStatus
        "requests": requests_data["items"], # Список объектов Request (последние 10)
        "total": requests_data["total"],    # Общее количество обращений (для пагинации)
        # Статистика для карточек сводки
        "in_progress_count": sum(1 for r in requests_data["items"] if r.status and r.status.code in ["new", "considering", "in_progress"]),
        "completed_count": sum(1 for r in requests_data["items"] if r.status and r.status.code == "closed"),
    }


def prepare_deputy_context(db: Session, district_id: int = None):
    """
    Подготовить контекст данных для страницы депутата

    Депутату нужны:
    - Список обращений его округа (или всех, если district_id не указан)
    - Информация о округе
    - Статистика по статусам

    Параметры:
    - db: сессия базы данных
    - district_id: опциональный фильтр по округу (если депутат закреплен за конкретным округом)
    """
    # Получаем обращения, отфильтрованные по округу если указан
    requests_data = get_requests(db, skip=0, limit=20, district_id=district_id)

    # Получаем информацию об округе если указан ID
    district = None
    if district_id:
        from app.crud.district import get_district
        district = get_district(db, district_id)

    # Статистика по статусам для диаграмм
    status_stats = {}
    for req in requests_data["items"]:
        if req.status:
            status_name = req.status.name or "Неизвестно"
            status_stats[status_name] = status_stats.get(status_name, 0) + 1

    return {
        "requests": requests_data["items"],
        "total": requests_data["total"],
        "district": district,
        "status_stats": status_stats,  # Словарь {название статуса: количество}
        "in_progress_count": sum(1 for r in requests_data["items"] if r.status and r.status.code in ["new", "considering", "in_progress"]),
        "completed_count": sum(1 for r in requests_data["items"] if r.status and r.status.code == "closed"),
    }


def prepare_admin_context(db: Session):
    """
    Подготовить контекст данных для панели администратора

    Администратор видит общую статистику по системе:
    - Все округа
    - Все депутаты
    - Общая статистика по обращениям
    - Данные для модерации

    Возвращает расширенный контекст с данными для всех вкладок админки.
    """
    # Получаем все округа для управления
    districts = get_districts(db, skip=0, limit=100)

    # Получаем всех депутатов
    deputies = get_deputies(db, skip=0, limit=100)

    # Получаем обращения для модерации
    requests_data = get_requests(db, skip=0, limit=50)

    # Агрегируем общую статистику
    total_requests = requests_data["total"]

    # Считаем распределение по статусам
    status_distribution = {}
    for req in requests_data["items"]:
        if req.status:
            code = req.status.code or "unknown"
            status_distribution[code] = status_distribution.get(code, 0) + 1

    # Считаем распределение по категориям
    category_distribution = {}
    for req in requests_data["items"]:
        if req.category:
            cat_name = req.category.name or "Неизвестно"
            category_distribution[cat_name] = category_distribution.get(cat_name, 0) + 1

    return {
        "districts": districts,
        "deputies": deputies,
        "requests": requests_data["items"],
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
async def auth_page(request: Request, db: Session = Depends(get_db)):
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
async def home_page(request: Request, db: Session = Depends(get_db)):
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
async def citizen_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Личный кабинет гражданина

    Отображает:
    - Список обращений пользователя с их статусами
    - Форму для создания нового обращения
    - Сводную статистику (сколько всего, в работе, выполнено)

    Поток данных:
    1. Извлекаем категории и статусы из справочников
    2. Загружаем обращения (в будущем фильтруем по текущему пользователю)
    3. Передаем данные в шаблон citizen/dashboard.html

    Обработка edge-кейсов:
    - Если обращений нет → шаблон покажет empty state
    - Если категории не загружены → форма создания будет пустой
    """
    # Подготавливаем данные через вспомогательную функцию
    context = prepare_citizen_context(db)

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
async def citizen_create_appeal(request: Request, db: Session = Depends(get_db)):
    """
    Страница создания обращения (отдельная страница для формы)

    Предоставляет форму с полями:
    - Категория (выпадающий список из БД)
    - Заголовок, описание
    - Адрес (с автоопределением округа)
    - Фотографии

    В отличие от dashboard, эта страница фокусируется только на форме.
    """
    # Получаем справочники для заполнения формы
    categories = get_request_categories(db)
    statuses = get_request_statuses(db)
    districts = get_districts(db, skip=0, limit=100)

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


@pages_router.post("/citizen/create")
async def citizen_submit_appeal(request: Request, db: Session = Depends(get_db)):
    """
    Обработка формы создания обращения

    Принимает данные из формы:
    - category: категория обращения
    - title: заголовок
    - description: описание
    - address: адрес
    - photos: файлы изображений
    - truth_confirmed: подтверждение достоверности

    После успешного создания перенаправляет на dashboard.
    """
    form_data = await request.form()

    category_code = form_data.get("category")
    title = form_data.get("title")
    description = form_data.get("description")
    address = form_data.get("address")
    truth_confirmed = form_data.get("truth_confirmed")
    photos = form_data.getlist("photos")

    from fastapi import HTTPException, UploadFile
    from app.crud.request import create_request
    from app.schemas.requests import RequestCreate
    from app.crud.district import get_district_by_address

    if not category_code or not title or not description or not address:
        raise HTTPException(status_code=400, detail="Все обязательные поля должны быть заполнены")

    if not truth_confirmed:
        raise HTTPException(status_code=400, detail="Необходимо подтвердить достоверность данных")

    photo_urls = []
    for photo in photos:
        if isinstance(photo, UploadFile) and photo.filename:
            photo_urls.append(f"/static/uploads/{photo.filename}")

    user_id = request.state.current_user.get("id") if request.state.current_user else None

    if not user_id:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    district = get_district_by_address(db, address)
    district_id = district.id if district else None

    from app.crud.category import get_category_by_code
    category = get_category_by_code(db, category_code)
    category_id = category.id if category else None

    if not category_id:
        raise HTTPException(status_code=400, detail="Неверная категория обращения")

    request_data = RequestCreate(
        district_id=district_id,
        category_id=category_id,
        title=title,
        description=description,
        address=address,
        photos=photo_urls
    )

    new_appeal = create_request(
        db=db,
        request_data=request_data,
        user_id=user_id
    )

    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/citizen/dashboard", status_code=303)


@pages_router.get("/citizen/appeal/{appeal_id}", name="appeal_detail")
async def citizen_appeal_detail(request: Request, appeal_id: int, db: Session = Depends(get_db)):
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
    """
    from app.crud.request import get_request_by_id, get_request_messages, get_request_status_history

    # Загружаем обращение со всеми связанными данными
    appeal = get_request_by_id(db, appeal_id)

    # Edge-case: если обращение не найдено → возвращаем 404
    if not appeal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    # Загружаем сообщения (переписка)
    messages_data = get_request_messages(db, appeal_id, skip=0, limit=100)

    # Загружаем историю изменений статуса
    status_history = get_request_status_history(db, appeal_id)

    context = {
        "request": request,
        "appeal": appeal,
        "messages": messages_data["items"],
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
async def deputy_dashboard(request: Request, db: Session = Depends(get_db), district_id: int = None):
    """
    Рабочий кабинет депутата

    Отображает обращения жителей округа депутата:
    - Список обращений с фильтрацией по статусу
    - Возможность взять обращение в работу
    - Форма ответа жителю

    Параметры:
    - district_id: опционально, если депутат работает в нескольких округах

    Поток данных:
    1. Определяем округ депутата (в будущем из сессии пользователя)
    2. Загружаем обращения этого округа
    3. Формируем статистику по статусам
    """
    context = prepare_deputy_context(db, district_id)
    context["request"] = request
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "deputy/dashboard.html",    # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/deputy/appeal/{appeal_id}", name="deputy_appeal_detail")
async def deputy_appeal_detail(request: Request, appeal_id: int, db: Session = Depends(get_db)):
    """
    Детали обращения для депутата

    Аналогично citizen_appeal_detail, но с дополнительными действиями:
    - Кнопки "Взять в работу", "Изменить статус"
    - Форма ответа заявителю
    """
    from app.crud.request import get_request_by_id, get_request_messages, get_request_status_history

    appeal = get_request_by_id(db, appeal_id)

    if not appeal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    messages_data = get_request_messages(db, appeal_id, skip=0, limit=100)
    status_history = get_request_status_history(db, appeal_id)

    context = {
        "request": request,
        "appeal": appeal,
        "messages": messages_data["items"],
        "status_history": status_history,
        # Флаги для отображения кнопок действий
        "can_take_to_work": appeal.status and appeal.status.code == "new",
        "can_respond": True,  # Всегда можно ответить
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                        # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "deputy/appeal_detail.html",    # ← 2-й аргумент: путь к шаблону
    context                         # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/deputy/statistics", name="deputy_statistics")
async def deputy_statistics(request: Request, db: Session = Depends(get_db), district_id: int = None):
    """
    Статистика работы депутата

    Показывает:
    - Количество обращений по статусам
    - Среднее время решения
    - Распределение по категориям
    """
    context = prepare_deputy_context(db, district_id)
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
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Панель администратора

    Основной экран с общей статистикой системы:
    - Количество округов, депутатов, обращений
    - Распределение обращений по статусам
    - Быстрый доступ к управлению сущностями

    Поток данных:
    1. Загружаем все округа
    2. Загружаем всех депутатов
    3. Загружаем последние обращения
    4. Агрегируем статистику
    """
    context = prepare_admin_context(db)
    context["request"] = request
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/dashboard.html",     # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin/districts", name="admin_districts")
async def admin_districts(request: Request, db: Session = Depends(get_db)):
    """
    Управление округами

    Список всех округов с возможностью:
    - Создания нового округа
    - Редактирования существующих
    - Удаления (если нет депутатов и обращений)
    """
    districts = get_districts(db, skip=0, limit=100)

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
async def admin_deputies(request: Request, db: Session = Depends(get_db)):
    """
    Управление депутатами

    Список всех депутатов с возможностью:
    - Назначения нового депутата
    - Перевода между округами
    - Снятия полномочий
    """
    deputies = get_deputies(db, skip=0, limit=100)
    districts = get_districts(db, skip=0, limit=100)

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
async def admin_moderation(request: Request, db: Session = Depends(get_db)):
    """
    Модерация обращений

    Список обращений требующих внимания администратора:
    - Спорные обращения
    - Жалобы на качество ответов
    - Обращения с нарушенными сроками
    """
    # Пока загружаем все обращения, позже добавим фильтр по флагу "требует модерации"
    requests_data = get_requests(db, skip=0, limit=50)

    context = {
        "request": request,
        "requests": requests_data["items"],
        "total": requests_data["total"],
        "page_title": "Модерация обращений",
        "current_user": request.state.current_user,
    }

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/moderation.html",    # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/admin/statistics", name="admin_statistics")
async def admin_statistics(request: Request, db: Session = Depends(get_db)):
    """
    Расширенная статистика системы

    Детальные отчеты:
    - Динамика обращений по времени
    - Эффективность работы по округам
    - Рейтинг депутатов
    """
    context = prepare_admin_context(db)
    context["request"] = request
    context["page_title"] = "Статистика системы"
    context["current_user"] = request.state.current_user

    return templates.TemplateResponse(
    request,                    # ← 1-й аргумент: объект запроса (ОБЯЗАТЕЛЬНО)
    "admin/statistics.html",    # ← 2-й аргумент: путь к шаблону
    context                     # ← 3-й аргумент: контекст (словарь с данными)
)


@pages_router.get("/logout", name="logout")
async def logout(request: Request):
    """
    Выход из системы

    Удаляет токен аутентификации из cookies и перенаправляет на главную страницу.
    """
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# Подключаем роутер страниц к основному приложению
# Теперь все HTML-роуты будут доступны через app
app.include_router(pages_router)