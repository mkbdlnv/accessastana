"""drop poi_matches (OSM-vs-registry completeness removed from scope)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_poi_matches_city_slug"), table_name="poi_matches")
    op.drop_table("poi_matches")


def downgrade() -> None:
    op.create_table(
        "poi_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_slug", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("osm_poi_id", sa.Integer(), nullable=True),
        sa.Column("registry_poi_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("name_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_slug"], ["cities.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["osm_poi_id"], ["pois.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registry_poi_id"], ["pois.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_poi_matches_city_slug"), "poi_matches", ["city_slug"], unique=False)
