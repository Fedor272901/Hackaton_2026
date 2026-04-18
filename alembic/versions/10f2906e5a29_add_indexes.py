"""add indexes

Revision ID: 10f2906e5a29
Revises: 15623115ed13
Create Date: 2026-04-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "10f2906e5a29"
down_revision: Union[str, Sequence[str], None] = "15623115ed13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Создаем ENUM
    user_roles_enum = sa.Enum("citizen", "deputy", "admin", name="user_roles")
    user_roles_enum.create(op.get_bind(), checkfirst=True)

    # 2. Чиним возможные старые значения (ВАЖНО)
    op.execute(
        """
        UPDATE users
        SET role = LOWER(role)
    """
    )

    # 3. Меняем тип колонки role на ENUM
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN role TYPE user_roles
        USING role::user_roles
    """
    )

    # === ДАЛЬШЕ АВТОГЕНЕРЕННЫЙ КОД ===

    op.alter_column("deputies", "user_id", existing_type=sa.INTEGER(), nullable=False)

    # НЕ ТРОГАЕМ constraint — он уже есть
    # op.drop_constraint(...) УДАЛЕНО

    op.create_index(
        "ix_deputies_district_id", "deputies", ["district_id"], unique=False
    )
    op.create_index("ix_deputies_user_id", "deputies", ["user_id"], unique=True)

    op.alter_column("messages", "user_id", existing_type=sa.INTEGER(), nullable=False)

    op.create_index("ix_messages_created_at", "messages", ["created_at"], unique=False)
    op.create_index("ix_messages_request_id", "messages", ["request_id"], unique=False)
    op.create_index("ix_messages_user_id", "messages", ["user_id"], unique=False)

    op.create_index(
        "ix_request_photos_request_id", "request_photos", ["request_id"], unique=False
    )

    op.alter_column("requests", "user_id", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column(
        "requests", "district_id", existing_type=sa.INTEGER(), nullable=False
    )
    op.alter_column(
        "requests", "category_id", existing_type=sa.INTEGER(), nullable=False
    )
    op.alter_column("requests", "status_id", existing_type=sa.INTEGER(), nullable=False)

    op.create_index(
        "ix_requests_assigned_deputy_id",
        "requests",
        ["assigned_deputy_id"],
        unique=False,
    )
    op.create_index(
        "ix_requests_category_id", "requests", ["category_id"], unique=False
    )
    op.create_index("ix_requests_created_at", "requests", ["created_at"], unique=False)
    op.create_index(
        "ix_requests_district_id", "requests", ["district_id"], unique=False
    )
    op.create_index("ix_requests_status_id", "requests", ["status_id"], unique=False)
    op.create_index("ix_requests_user_id", "requests", ["user_id"], unique=False)

    op.create_index(
        "ix_role_requests_processed_by_admin_id",
        "role_requests",
        ["processed_by_admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_role_requests_status", "role_requests", ["status"], unique=False
    )
    op.create_index(
        "ix_role_requests_user_id", "role_requests", ["user_id"], unique=False
    )

    op.create_index(
        "ix_status_history_created_at", "status_history", ["created_at"], unique=False
    )
    op.create_index(
        "ix_status_history_request_id", "status_history", ["request_id"], unique=False
    )

    op.create_index("ix_users_role", "users", ["role"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_users_role", table_name="users")

    # Возвращаем обратно VARCHAR
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN role TYPE VARCHAR
        USING role::text
    """
    )

    op.drop_index("ix_status_history_request_id", table_name="status_history")
    op.drop_index("ix_status_history_created_at", table_name="status_history")

    op.drop_index("ix_role_requests_user_id", table_name="role_requests")
    op.drop_index("ix_role_requests_status", table_name="role_requests")
    op.drop_index("ix_role_requests_processed_by_admin_id", table_name="role_requests")

    op.drop_index("ix_requests_user_id", table_name="requests")
    op.drop_index("ix_requests_status_id", table_name="requests")
    op.drop_index("ix_requests_district_id", table_name="requests")
    op.drop_index("ix_requests_created_at", table_name="requests")
    op.drop_index("ix_requests_category_id", table_name="requests")
    op.drop_index("ix_requests_assigned_deputy_id", table_name="requests")

    op.alter_column("requests", "status_id", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "requests", "category_id", existing_type=sa.INTEGER(), nullable=True
    )
    op.alter_column(
        "requests", "district_id", existing_type=sa.INTEGER(), nullable=True
    )
    op.alter_column("requests", "user_id", existing_type=sa.INTEGER(), nullable=True)

    op.drop_index("ix_request_photos_request_id", table_name="request_photos")

    op.drop_index("ix_messages_user_id", table_name="messages")
    op.drop_index("ix_messages_request_id", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")

    op.alter_column("messages", "user_id", existing_type=sa.INTEGER(), nullable=True)

    op.drop_index("ix_deputies_user_id", table_name="deputies")
    op.drop_index("ix_deputies_district_id", table_name="deputies")

    op.alter_column("deputies", "user_id", existing_type=sa.INTEGER(), nullable=True)

    # Удаляем ENUM
    user_roles_enum = sa.Enum("citizen", "deputy", "admin", name="user_roles")
    user_roles_enum.drop(op.get_bind(), checkfirst=True)
