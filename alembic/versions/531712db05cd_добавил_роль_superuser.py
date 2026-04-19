"""Добавил роль superuser

Revision ID: 531712db05cd
Revises: 10f2906e5a29
Create Date: 2026-04-18 15:46:36.281695
"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "531712db05cd"
down_revision: Union[str, Sequence[str], None] = "10f2906e5a29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ДОБАВЛЯЕМ значение в ENUM
    op.execute("ALTER TYPE user_roles ADD VALUE 'superuser'")


def downgrade() -> None:
    # PostgreSQL не умеет удалять значения ENUM
    pass
