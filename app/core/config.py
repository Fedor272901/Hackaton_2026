<<<<<<< HEAD
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
=======
"""
Модуль конфигурации приложения.

Все критичные параметры вынесены в переменные окружения для:
- Безопасности (SECRET_KEY не хранится в коде)
- Гибкости развертывания (разные настройки для dev/prod)
- Централизации настроек (единый источник истины)

Использует pydantic-settings для валидации и типизации настроек.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки приложения из переменных окружения.
    
    Все поля без default значений являются обязательными.
    При отсутствии переменной окружения будет выброшена ValidationError.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================
    # БЕЗОПАСНОСТЬ (ОБЯЗАТЕЛЬНЫЕ)
    # ========================
    
    SECRET_KEY: str = Field(
        ...,
        env="SECRET_KEY",
        description="Секретный ключ для JWT токенов. Критично для безопасности!"
        # Если не задан: приложение не запустится (ValidationError)
        # Генерация: openssl rand -hex 32
    )
    
    ALGORITHM: str = Field(
        default="HS256",
        env="ALGORITHM",
        description="Алгоритм шифрования JWT"
    )
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        env="ACCESS_TOKEN_EXPIRE_MINUTES",
        ge=1,
        description="Время жизни access токена в минутах"
    )
    
    # ========================
    # API НАСТРОЙКИ
    # ========================
    
    API_BASE_URL: str = Field(
        default="http://localhost:8000",
        env="API_BASE_URL",
        description="Базовый URL API для внешних вызовов"
    )
    
    # ========================
    # ПАГИНАЦИЯ (Magic numbers extracted to config)
    # ========================
    
    DEFAULT_LIMIT: int = Field(
        default=20,
        env="DEFAULT_LIMIT",
        ge=1,
        le=200,
        description="Количество записей по умолчанию при пагинации"
        # Magic number extracted to config for environment flexibility
    )
    
    MAX_LIMIT: int = Field(
        default=100,
        env="MAX_LIMIT",
        ge=1,
        le=500,
        description="Максимальное количество записей на страницу"
        # Magic number extracted to config for environment flexibility
    )
    
    MAX_LIMIT_DEPUTIES: int = Field(
        default=200,
        env="MAX_LIMIT_DEPUTIES",
        ge=1,
        le=1000,
        description="Максимальное количество записей для списка депутатов"
        # Magic number extracted to config for environment flexibility
    )
    
    # ========================
    # RATE LIMITING
    # ========================
    
    MAX_REQUESTS: int = Field(
        default=5,
        env="MAX_REQUESTS",
        ge=1,
        description="Максимум обращений в сутки на пользователя"
        # Magic number extracted to config for environment flexibility
    )
    
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=86400,
        env="RATE_LIMIT_WINDOW_SECONDS",
        ge=60,
        description="Период rate limiting в секундах (по умолчанию 24 часа)"
        # Magic number extracted to config for environment flexibility
    )
    
    # ========================
    # ТАЙМАУТЫ
    # ========================
    
    API_TIMEOUT: float = Field(
        default=30.0,
        env="API_TIMEOUT",
        ge=1.0,
        description="Таймаут для внешних API запросов в секундах"
        # Magic number extracted to config for environment flexibility
    )
    
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        env="DB_POOL_TIMEOUT",
        ge=5,
        description="Таймаут ожидания соединения с БД"
    )


# Глобальный экземпляр настроек для импорта в других модулях
settings = Settings()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
