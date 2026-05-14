"""add my pokemon

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6, b2c3d4e5f6a7
Create Date: 2026-05-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = ("b1c2d3e4f5a6", "b2c3d4e5f6a7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_trainers_user_id", "trainers", ["user_id"])

    op.create_table(
        "my_pokemons",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("nickname", sa.String(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("experience", sa.Integer(), nullable=False),
        sa.Column("hp", sa.Integer(), nullable=False),
        sa.Column("max_hp", sa.Integer(), nullable=False),
        sa.Column("attack", sa.Integer(), nullable=False),
        sa.Column("defense", sa.Integer(), nullable=False),
        sa.Column("special_attack", sa.Integer(), nullable=False),
        sa.Column("special_defense", sa.Integer(), nullable=False),
        sa.Column("speed", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trainer_id", "name", name="uq_my_pokemons_trainer_name"),
    )
    op.create_index(
        "ix_my_pokemons_trainer_deleted",
        "my_pokemons",
        ["trainer_id", "deleted_at"],
    )

    op.create_table(
        "my_pokemon_moves",
        sa.Column("my_pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("pokemon_move_id", sa.Uuid(), nullable=False),
        sa.Column("pp", sa.Integer(), nullable=False),
        sa.Column("max_pp", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["my_pokemon_id"], ["my_pokemons.id"]),
        sa.ForeignKeyConstraint(["pokemon_move_id"], ["pokemon_moves.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_my_pokemon_moves_my_pokemon_deleted",
        "my_pokemon_moves",
        ["my_pokemon_id", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_my_pokemon_moves_my_pokemon_deleted", table_name="my_pokemon_moves"
    )
    op.drop_table("my_pokemon_moves")
    op.drop_index("ix_my_pokemons_trainer_deleted", table_name="my_pokemons")
    op.drop_table("my_pokemons")
    op.drop_constraint("uq_trainers_user_id", "trainers", type_="unique")
