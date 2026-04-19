"""
Модуль кастомных фильтров для Jinja2

Этот модуль расширяет возможности шаблонизатора Jinja2 дополнительными фильтрами,
которые используются для форматирования данных перед отображением в HTML.

Зачем нужны кастомные фильтры:
1. Форматирование дат - приводим даты из БД к читаемому виду (DD.MM.YYYY HH:MM)
2. Маппинг статусов - переводим технические коды статусов (pending, approved)
   в человеко-понятные названия на русском языке
3. Обрезка текста - ограничиваем длину описаний для превью
4. Безопасный рендеринг - разрешаем определённые HTML-теги в пользовательском контенте

Все фильтры регистрируются в FastAPI приложении и становятся доступны
в любом шаблоне через синтаксис: {{ variable|filter_name }}
"""

from datetime import datetime
from typing import Optional, Any
import html


# ============================================================================
# МАППИНГ СТАТУСОВ И КАТЕГОРИЙ
# ============================================================================
# Словари для перевода технических кодов в понятные названия
# Эти данные могут быть вынесены в БД в будущем для гибкости

STATUS_MAP: dict[str, str] = {
    "new": "Новое",
    "pending": "На рассмотрении",
    "considering": "Рассматривается",
    "in_progress": "В работе",
    "resolved": "Решено",
    "closed": "Закрыто",
    "rejected": "Отклонено",
    "spam": "Спам",
    "archived": "Архивировано",
}

# Цветовые метки для статусов (для UI)
STATUS_COLOR_MAP: dict[str, str] = {
    "new": "blue",
    "pending": "yellow",
    "considering": "orange",
    "in_progress": "purple",
    "resolved": "green",
    "closed": "gray",
    "rejected": "red",
    "spam": "black",
    "archived": "silver",
}

# Маппинг ролей пользователей
ROLE_MAP: dict[str, str] = {
    "citizen": "Гражданин",
    "deputy": "Депутат",
    "admin": "Администратор",
    "moderator": "Модератор",
}


# ============================================================================
# ФИЛЬТРЫ ДЛЯ ДАТ
# ============================================================================

def format_datetime(value: Optional[datetime], format_string: str = "%d.%m.%Y %H:%M") -> str:
    """
    Фильтр для форматирования объектов datetime в строку.

    Использование в шаблоне:
        {{ appeal.created_at|format_datetime }}
        {{ appeal.updated_at|format_datetime("%d.%m.%Y") }}

    Параметры:
        value: Объект datetime из БД (может быть None)
        format_string: Формат вывода (по умолчанию DD.MM.YYYY HH:MM)

    Возвращает:
        Отформатированную строку или пустую строку если value is None

    Почему это важно:
        В БД даты хранятся в формате ISO 8601 (2024-01-15T10:30:00),
        что неудобно для чтения пользователем. Этот фильтр приводит
        даты к локализованному российскому формату.
    """
    if value is None:
        return ""

    if not isinstance(value, datetime):
        # Если передана строка или другой тип, пробуем распарсить
        try:
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                return str(value)
        except (ValueError, TypeError):
            return str(value)

    return value.strftime(format_string)


def format_date_relative(value: Optional[datetime]) -> str:
    """
    Фильтр для относительного форматирования дат ("5 минут назад", "2 дня назад").

    Использование в шаблоне:
        {{ message.created_at|format_date_relative }}

    Логика работы:
        - Менее минуты → "Только что"
        - Менее часа → "N минут назад"
        - Менее суток → "N часов назад"
        - Менее недели → "N дней назад"
        - Иначе → обычное форматирование даты

    Это улучшает UX, показывая свежесть контента интуитивно понятно.
    """
    if value is None:
        return ""

    if not isinstance(value, datetime):
        return str(value)

    now = datetime.now()
    diff = now - value

    seconds = diff.total_seconds()

    if seconds < 60:
        return "Только что"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} мин. назад"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} ч. назад"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} дн. назад"
    else:
        return value.strftime("%d.%m.%Y")


# ============================================================================
# ФИЛЬТРЫ ДЛЯ ТЕКСТА
# ============================================================================

def truncate_text(value: str, length: int = 100, suffix: str = "...") -> str:
    """
    Фильтр для обрезки длинного текста до указанной длины.

    Использование в шаблоне:
        {{ appeal.description|truncate_text(50) }}
        {{ appeal.title|truncate_text(30, " →") }}

    Параметры:
        value: Исходная строка
        length: Максимальная длина (по умолчанию 100 символов)
        suffix: Суффикс, добавляемый после обрезки (по умолчанию "...")

    Важные особенности:
        - Обрезка происходит по границе слов (не разрывает слова)
        - Суффикс добавляется только если текст был обрезан
        - HTML-теги экранируются для безопасности

    Зачем это нужно:
        Для превью обращений в списках, где важно показать начало текста,
        но не перегружать интерфейс длинными описаниями.
    """
    if not value:
        return ""

    # Сначала экранируем HTML для безопасности
    value = html.escape(str(value))

    if len(value) <= length:
        return value

    # Обрезаем по границе слова
    truncated = value[:length].rsplit(' ', 1)[0]
    return truncated + suffix


def strip_html(value: str) -> str:
    """
    Фильтр для удаления всех HTML-тегов из строки.

    Использование в шаблоне:
        {{ message.content|strip_html }}

    Возвращает:
        Чистый текст без каких-либо HTML-тегов

    Применение:
        Когда нужно отобразить текстовую версию контента,
        например, в meta-описаниях или plain-text уведомлениях.
    """
    if not value:
        return ""

    # Простая реализация через регулярное выражение
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', str(value))


# ============================================================================
# ФИЛЬТРЫ ДЛЯ БЕЗОПАСНОГО РЕНДЕРИНГА
# ============================================================================

def safe_html(value: str) -> str:
    """
    Фильтр для безопасного рендеринга HTML с ограниченным набором тегов.

    Использование в шаблоне:
        {{ message.content|safe_html }}

    Разрешённые теги:
        - <b>, <strong> - жирный текст
        - <i>, <em> - курсив
        - <u> - подчёркивание
        - <br> - перенос строки
        - <p> - параграфы
        - <ul>, <ol>, <li> - списки
        - <a href="..."> - ссылки (безопасные)

    Почему не просто |safe:
        Стандартный |safe в Jinja2 разрешает весь HTML, что опасно
        для пользовательского контента. Этот фильтр удаляет потенциально
        опасные теги (<script>, <iframe>, <object>) и атрибуты (onclick и др.).

    Важно:
        Все события JavaScript (onclick, onerror, onload) удаляются.
        Ссылки проверяются на безопасные протоколы (http, https, mailto).
    """
    if not value:
        return ""

    from bs4 import BeautifulSoup, Tag

    try:
        soup = BeautifulSoup(str(value), 'html.parser')

        # Удаляем опасные теги полностью
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button']
        for tag_name in dangerous_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Обрабатываем оставшиеся теги
        allowed_tags = {'b', 'strong', 'i', 'em', 'u', 'br', 'p', 'ul', 'ol', 'li', 'a', 'span', 'div'}
        allowed_attributes = {'a': {'href', 'title'}, 'td': {'colspan', 'rowspan'}}

        for tag in soup.find_all(True):
            if tag.name not in allowed_tags:
                tag.unwrap()  # Заменяем тег на его содержимое

            # Проверяем атрибуты
            if tag.name in allowed_attributes:
                allowed = allowed_attributes[tag.name]
                for attr in list(tag.attrs.keys()):
                    if attr not in allowed:
                        del tag[attr]
                    elif attr == 'href':
                        # Проверяем безопасность ссылок
                        href_value = tag.get(attr, '')
                        if not href_value.startswith(('http://', 'https://', 'mailto:', '#', '/')):
                            del tag[attr]
            else:
                # Удаляем все атрибуты у тегов без разрешённых атрибутов
                # Особенно важно для удаления onclick, onerror и других событий
                for attr in list(tag.attrs.keys()):
                    if attr.startswith('on'):  # Все обработчики событий
                        del tag[attr]

        return str(soup)

    except ImportError:
        # Если BeautifulSoup не установлен, возвращаем экранированный HTML
        return html.escape(str(value))
    except Exception:
        # При любой ошибке возвращаем экранированную версию
        return html.escape(str(value))


# ============================================================================
# ФИЛЬТРЫ ДЛЯ ДАННЫХ
# ============================================================================

def get_status_label(status_code: Optional[str]) -> str:
    """
    Фильтр для получения человеко-понятного названия статуса.

    Использование в шаблоне:
        {{ appeal.status.code|get_status_label }}

    Примеры:
        "new" → "Новое"
        "in_progress" → "В работе"
        "unknown_status" → "Неизвестно"

    Если статус не найден в маппинге, возвращается код статуса
    с заглавной буквы или "Неизвестно" если код пустой.
    """
    if not status_code:
        return "Неизвестно"

    return STATUS_MAP.get(status_code, status_code.capitalize())


def get_status_color(status_code: Optional[str]) -> str:
    """
    Фильтр для получения цвета статуса (для CSS-классов или inline-стилей).

    Использование в шаблоне:
        <span class="status status--{{ appeal.status.code|get_status_color }}">

    Возвращает название цвета на английском для использования в CSS классах.
    """
    if not status_code:
        return "gray"

    return STATUS_COLOR_MAP.get(status_code, "gray")


def get_role_label(role_code: Optional[str]) -> str:
    """
    Фильтр для получения названия роли пользователя.

    Использование в шаблоне:
        {{ user.role|get_role_label }}

    Примеры:
        "citizen" → "Гражданин"
        "deputy" → "Депутат"
    """
    if not role_code:
        return "Пользователь"

    return ROLE_MAP.get(role_code, role_code.capitalize())


def default_if_empty(value: Any, default: str = "—") -> Any:
    """
    Фильтр для замены пустых значений на дефолтные.

    Использование в шаблоне:
        {{ appeal.description|default_if_empty("Описание отсутствует") }}
        {{ user.phone|default_if_empty }}

    Заменяет на default если value:
        - None
        - Пустая строка ""
        - Пустой список []
        - Пустой словарь {}

    Полезно для отображения "—" вместо пустых полей в таблицах.
    """
    if value is None or value == "" or value == [] or value == {}:
        return default
    return value


def to_json(value: Any) -> str:
    """
    Фильтр для сериализации объекта в JSON строку.

    Использование в шаблоне:
        <div data-config="{{ config|to_json }}"></div>

    Применяется для передачи сложных объектов из сервера в JavaScript.
    Например, конфигурация графика или начальные данные для Vue/React компонента.
    """
    import json
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return "{}"


# ============================================================================
# РЕГИСТРАЦИЯ ФИЛЬТРОВ В ПРИЛОЖЕНИИ FASTAPI
# ============================================================================

def register_jinja_filters(templates):
    """
    Регистрация всех кастомных фильтров в приложении FastAPI.

    Эта функция вызывается один раз при старте приложения в main.py.
    После регистрации фильтры становятся доступны во всех шаблонах.

    Использование:
        from app.filters import register_jinja_filters
        register_jinja_filters(app)

    Механизм работы:
        FastAPI использует Jinja2Templates для рендеринга.
        У templates есть атрибут env.filters - словарь всех доступных фильтров.
        Мы добавляем наши функции в этот словарь под ключами-именами.

    После регистрации в шаблоне можно писать:
        {{ date|format_datetime }}
        {{ status|get_status_label }}
    """
    # Проверяем, что у приложения есть templates
    if templates is None or not hasattr(templates, 'env'):
        print("⚠️ Warning: Templates object is invalid. Filters not registered.")
        return

    # Получаем доступ к окружению Jinja2
    jinja_env = templates.env

    # Регистрируем каждый фильтр под своим именем
    # Ключ словаря - имя фильтра как оно будет использоваться в шаблоне
    # Значение - ссылка на функцию

    jinja_env.filters['format_datetime'] = format_datetime
    jinja_env.filters['format_date_relative'] = format_date_relative
    jinja_env.filters['truncate_text'] = truncate_text
    jinja_env.filters['strip_html'] = strip_html
    jinja_env.filters['safe_html'] = safe_html
    jinja_env.filters['get_status_label'] = get_status_label
    jinja_env.filters['get_status_color'] = get_status_color
    jinja_env.filters['get_role_label'] = get_role_label
    jinja_env.filters['default_if_empty'] = default_if_empty
    jinja_env.filters['to_json'] = to_json

    print("✅ Custom Jinja2 filters registered successfully")
    print("   Available filters:")
    print("   - format_datetime, format_date_relative")
    print("   - truncate_text, strip_html, safe_html")
    print("   - get_status_label, get_status_color, get_role_label")
    print("   - default_if_empty, to_json")