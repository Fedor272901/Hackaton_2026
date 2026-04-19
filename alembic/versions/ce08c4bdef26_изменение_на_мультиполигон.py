"""изменение на мультиполигон

Revision ID: ce08c4bdef26
Revises: b9b9811a7568
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = 'ce08c4bdef26'  # ← ИСПРАВИТЬ ЗДЕСЬ
down_revision: Union[str, None] = 'b9b9811a7568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE districts 
        ALTER COLUMN geom 
        TYPE geometry(MultiPolygon, 4326) 
        USING ST_Multi(geom)
    """)



def downgrade() -> None:
    op.execute("""
        ALTER TABLE districts 
        ALTER COLUMN geom 
        TYPE geometry(Geometry, 4326)
    """)