"""add_postgis_to_districts

Revision ID: b9b9811a7568
Revises: 
Create Date: 2026-04-20

"""
from typing import Sequence, Union


from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = 'b9b9811a7568'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Включаем PostGIS
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    # Удаляем старую колонку
    op.execute('ALTER TABLE districts DROP COLUMN IF EXISTS geometry')
    
    # Добавляем новую геометрическую колонку
    op.add_column('districts', 
        sa.Column('geom', Geometry('GEOMETRY', srid=4326), nullable=True))
    
    # Создаём пространственный индекс
    op.execute('CREATE INDEX IF NOT EXISTS idx_districts_geom ON districts USING GIST (geom)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_districts_geom')
    op.drop_column('districts', 'geom')
    op.add_column('districts', sa.Column('geometry', sa.Text(), nullable=True))