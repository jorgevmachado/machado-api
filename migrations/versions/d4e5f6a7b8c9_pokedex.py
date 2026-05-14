"""add pokedex

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pokedex",
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("hp", sa.Integer(), nullable=False),
        sa.Column("max_hp", sa.Integer(), nullable=False),
        sa.Column("attack", sa.Integer(), nullable=False),
        sa.Column("defense", sa.Integer(), nullable=False),
        sa.Column("special_attack", sa.Integer(), nullable=False),
        sa.Column("special_defense", sa.Integer(), nullable=False),
        sa.Column("speed", sa.Integer(), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("experience", sa.Integer(), nullable=False),
        sa.Column("discovered", sa.Boolean(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trainer_id", "pokemon_id", name="uq_pokedex_trainer_pokemon"
        ),
    )
    op.create_index(
        "ix_pokedex_trainer_deleted",
        "pokedex",
        ["trainer_id", "deleted_at"],
    )
    op.create_index(
        "ix_pokedex_pokemon_deleted",
        "pokedex",
        ["pokemon_id", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pokedex_pokemon_deleted", table_name="pokedex")
    op.drop_index("ix_pokedex_trainer_deleted", table_name="pokedex")
    op.drop_table("pokedex")
