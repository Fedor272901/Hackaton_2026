from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# загружаем переменные из .env
load_dotenv()

# берём URL базы
DATABASE_URL = os.getenv("DATABASE_URL")

# создаём подключение к БД
engine = create_engine(DATABASE_URL)

# фабрика сессий (через неё будем работать с БД)
SessionLocal = sessionmaker(bind=engine)

# базовый класс для моделей
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
