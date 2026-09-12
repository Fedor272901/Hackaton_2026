from datetime import datetime

from pydantic import BaseModel


class RoleRequestCreate(BaseModel):
    """Что гражданин присылает при подаче заявки на роль депутата."""
    user_id: int           # пока без авторизации, передаём руками
    requested_role: str    # обычно "deputy"
    user_comment: str | None = None


class RoleRequestDecision(BaseModel):
    """Что админ присылает при одобрении/отклонении."""
    admin_id: int          # пока без авторизации, передаём руками
    status: str            # "approved" или "rejected"
    admin_comment: str | None = None


class RoleRequestRead(BaseModel):
    id: int
    user_id: int
    requested_role: str
    status: str
    user_comment: str | None = None
    admin_comment: str | None = None
    processed_by_admin_id: int | None = None
    created_at: datetime
    decided_at: datetime | None = None

    class Config:
        from_attributes = True
