<<<<<<< HEAD
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
=======
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
import os
from dotenv import load_dotenv

# загружаем переменные из .env
load_dotenv()

<<<<<<< HEAD
# берём URL базы
DATABASE_URL = os.getenv("DATABASE_URL")

# создаём подключение к БД
engine = create_engine(DATABASE_URL)

# фабрика сессий (через неё будем работать с БД)
SessionLocal = sessionmaker(bind=engine)
=======
# берём URL базы (должен быть в формате postgresql+asyncpg://...)
DATABASE_URL = os.getenv("DATABASE_URL")

# создаём асинхронный движок к БД
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# фабрика асинхронных сессий (через неё будем работать с БД)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)

# базовый класс для моделей
Base = declarative_base()


<<<<<<< HEAD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
=======
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий базы данных.
    
    Используется как dependency в FastAPI endpoints.
    Автоматически закрывает сессию после использования.
    
    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Инициализация базы данных - создание всех таблиц.
    
    Вызывается при старте приложения.
    Использует async engine для создания таблиц.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Закрытие подключения к базе данных.
    
    Вызывается при остановке приложения.
    Освобождает ресурсы connection pool.
    """
    await engine.dispose()
>>>>>>> 9b6d3f7 (немного переписанна логика бекэнда)
