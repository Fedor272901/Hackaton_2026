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
from app.core.security import hash_password


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
    email = "admin@example.com"
    exists = db.query(models.User).filter(
        models.User.email == email
    ).first()
    if not exists:
        admin = models.User(
            first_name="Тестовый",
            last_name="Админ",
            email=email,
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✓ Тестовый админ создан: {email} | id={admin.id}")
    else:
        print(f"✓ Тестовый админ уже есть: {email} | id={exists.id}")


# Тестовые округа Калуги: два прямоугольника, закрывающие центр города.
# Координаты GeoJSON: [долгота, широта], контур замкнут.
DISTRICTS = [
    (
        "Октябрьский округ",
        "Западная часть города (тестовый полигон)",
        {
            "type": "Polygon",
            "coordinates": [[
                [36.2000, 54.4700],
                [36.2700, 54.4700],
                [36.2700, 54.5600],
                [36.2000, 54.5600],
                [36.2000, 54.4700],
            ]],
        },
    ),
    (
        "Ленинский округ",
        "Восточная часть города (тестовый полигон)",
        {
            "type": "Polygon",
            "coordinates": [[
                [36.2700, 54.4700],
                [36.3400, 54.4700],
                [36.3400, 54.5600],
                [36.2700, 54.5600],
                [36.2700, 54.4700],
            ]],
        },
    ),
]


def seed_districts(db):
    added = 0
    for name, description, geometry in DISTRICTS:
        exists = db.query(models.District).filter(
            models.District.name == name
        ).first()
        if not exists:
            db.add(models.District(
                name=name,
                description=description,
                geom=models.District.from_geojson(geometry),
            ))
            added += 1
    db.commit()
    print(f"✓ Округа: добавлено {added} (уже было {len(DISTRICTS) - added})")


def main():
    db = SessionLocal()
    try:
        print("→ Наполняю БД начальными данными...\n")
        seed_statuses(db)
        seed_categories(db)
        seed_districts(db)
        seed_admin(db)
        print("\n✓ Готово. Запускай сервер: uvicorn app.main:app --reload")
    finally:
        db.close()


if __name__ == "__main__":
    main()
