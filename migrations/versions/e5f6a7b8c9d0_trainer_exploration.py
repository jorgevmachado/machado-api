"""add trainer exploration

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
                   DO $$ BEGIN
                       CREATE TYPE explorationeventtypeenum AS ENUM ('WILD_POKEMON', 'POKEBALLS', 'BLANK');
                   EXCEPTION
                       WHEN duplicate_object THEN null;
                   END $$;
               """)
    op.create_table(
        "trainer_encounters",
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("pokemon_encounter_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pokemon_encounter_id"], ["pokemon_encounters.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trainer_id",
            "pokemon_encounter_id",
            name="uq_trainer_encounters_trainer_encounter",
        ),
    )
    op.create_index(
        "ix_trainer_encounters_trainer_deleted",
        "trainer_encounters",
        ["trainer_id", "deleted_at"],
    )
    op.create_index(
        "ix_trainer_encounters_active_unique",
        "trainer_encounters",
        ["trainer_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND deleted_at IS NULL"),
    )

    op.create_table(
        "trainer_party",
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("my_pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["my_pokemon_id"], ["my_pokemons.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trainer_party_trainer_deleted",
        "trainer_party",
        ["trainer_id", "deleted_at"],
    )
    op.create_index(
        "ix_trainer_party_slot_unique",
        "trainer_party",
        ["trainer_id", "slot"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_trainer_party_my_pokemon_unique",
        "trainer_party",
        ["trainer_id", "my_pokemon_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "exploration_events",
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "WILD_POKEMON",
                "POKEBALLS",
                "BLANK",
                name="explorationeventtypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exploration_events_trainer_created",
        "exploration_events",
        ["trainer_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_exploration_events_trainer_created", table_name="exploration_events")
    op.drop_table("exploration_events")
    op.drop_index("ix_trainer_party_my_pokemon_unique", table_name="trainer_party")
    op.drop_index("ix_trainer_party_slot_unique", table_name="trainer_party")
    op.drop_index("ix_trainer_party_trainer_deleted", table_name="trainer_party")
    op.drop_table("trainer_party")
    op.drop_index("ix_trainer_encounters_active_unique", table_name="trainer_encounters")
    op.drop_index("ix_trainer_encounters_trainer_deleted", table_name="trainer_encounters")
    op.drop_table("trainer_encounters")
    sa.Enum(name="explorationeventtypeenum").drop(op.get_bind(), checkfirst=False)
