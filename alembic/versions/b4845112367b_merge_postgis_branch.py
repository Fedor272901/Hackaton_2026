"""merge_postgis_branch

Revision ID: b4845112367b
Revises: 6e412dc81dd8, ce08c4bdef26
Create Date: 2026-04-20 01:31:28.189375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4845112367b'
down_revision: Union[str, Sequence[str], None] = ('6e412dc81dd8', 'ce08c4bdef26')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
