"""
Первичное наполнение БД.

Запуск из корня проекта (после alembic upgrade head):
    python seed.py

Создаёт:
- 4 статуса обращений (NEW, IN_PROGRESS, DONE, REJECTED)
- 5 категорий из ТЗ (ЖКХ, Дороги, Благоустройство, Безопасность, Социальные вопросы)
- Тестового админа (для проверки роутов)

Скрипт идемпотентен — запускай сколько угодно раз, дубликатов не будет.
"""
import os
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(bind=engine)

# импортируем модели
from app.db import models  # noqa: E402


STATUSES = [
    ("NEW", "Новое"),
    ("IN_PROGRESS", "В работе"),
    ("DONE", "Выполнено"),
    ("REJECTED", "Отклонено"),
]

CATEGORIES = [
    ("ЖКХ", "Жилищно-коммунальное хозяйство"),
    ("Дороги", "Состояние дорог, разметка, знаки"),
    ("Благоустройство", "Парки, дворы, освещение, мусор"),
    ("Безопасность", "Общественная безопасность, правопорядок"),
    ("Социальные вопросы", "Социальная сфера, льготы, помощь"),
]


def seed_statuses(db):
    added = 0
    for code, name in STATUSES:
        exists = db.query(models.RequestStatus).filter(
            models.RequestStatus.code == code
        ).first()
        if not exists:
            db.add(models.RequestStatus(code=code, name=name))
            added += 1
    db.commit()
    print(f"✓ Статусы: добавлено {added} (уже было {len(STATUSES) - added})")


def seed_categories(db):
    added = 0
    for name, description in CATEGORIES:
        exists = db.query(models.RequestCategory).filter(
            models.RequestCategory.name == name
        ).first()
        if not exists:
            db.add(models.RequestCategory(name=name, description=description))
            added += 1
    db.commit()
    print(f"✓ Категории: добавлено {added} (уже было {len(CATEGORIES) - added})")


def seed_admin(db):
    email = "admin@test.local"
    exists = db.query(models.User).filter(
        models.User.email == email
    ).first()
    if not exists:
        admin = models.User(
            first_name="Тестовый",
            last_name="Админ",
            email=email,
            password_hash="admin123",  # блок 1 заменит на хеш
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✓ Тестовый админ создан: {email} | id={admin.id}")
    else:
        print(f"✓ Тестовый админ уже есть: {email} | id={exists.id}")


def main():
    db = SessionLocal()
    try:
        print("→ Наполняю БД начальными данными...\n")
        seed_statuses(db)
        seed_categories(db)
        seed_admin(db)
        print("\n✓ Готово. Запускай сервер: uvicorn app.main:app --reload")
    finally:
        db.close()


if __name__ == "__main__":
    main()
