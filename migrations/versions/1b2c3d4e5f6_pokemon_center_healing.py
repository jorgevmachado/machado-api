"""add pokemon center healing tables

Revision ID: 1b2c3d4e5f6
Revises: 0a1b2c3d4e5f
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pokemon_center_healings",
        sa.Column("trainer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("healed_pokemon_quantity", sa.Integer(), nullable=False),
        sa.Column("restored_hp", sa.Integer(), nullable=False),
        sa.Column("restored_pp", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pokemon_center_healings_trainer_created_at",
        "pokemon_center_healings",
        ["trainer_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "healing_logs",
        sa.Column("trainer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pokemon_center_healing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("my_pokemon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["my_pokemon_id"], ["my_pokemons.id"]),
        sa.ForeignKeyConstraint(["pokemon_center_healing_id"], ["pokemon_center_healings.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_healing_logs_trainer_created_at",
        "healing_logs",
        ["trainer_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_healing_logs_healing_id",
        "healing_logs",
        ["pokemon_center_healing_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_healing_logs_healing_id", table_name="healing_logs")
    op.drop_index("ix_healing_logs_trainer_created_at", table_name="healing_logs")
    op.drop_table("healing_logs")
    op.drop_index(
        "ix_pokemon_center_healings_trainer_created_at",
        table_name="pokemon_center_healings",
    )
    op.drop_table("pokemon_center_healings")
