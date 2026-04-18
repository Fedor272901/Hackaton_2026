from enum import Enum


class Role(str, Enum):
    CITIZEN = "citizen"
    DEPUTY = "deputy"
    ADMIN = "admin"
    SUPERUSER = "superuser"  # ТОЛЬКО ДЛЯ РАЗРАБОТКИ
