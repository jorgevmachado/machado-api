"""add wild pokemon battle session

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE battlesessionstatusenum AS ENUM ('ACTIVE', 'WON', 'LOST', 'FLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE battleactorenum AS ENUM ('TRAINER', 'WILD');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE battleactiontypeenum AS ENUM ('USE_MOVE', 'SWITCH', 'FLEE', 'AUTO_RESPONSE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE battlelogtypeenum AS ENUM ('SESSION_STARTED', 'MOVE_USED', 'DAMAGE_DEALT', 'SWITCHED', 'FLED', 'SESSION_FINISHED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "wild_pokemon_battle_sessions",
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("exploration_event_id", sa.Uuid(), nullable=False),
        sa.Column("trainer_active_my_pokemon_id", sa.Uuid(), nullable=True),
        sa.Column("wild_pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("wild_pokemon_name", sa.String(), nullable=False),
        sa.Column("wild_pokemon_level", sa.Integer(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "WON",
                "LOST",
                "FLED",
                name="battlesessionstatusenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("trainer_party_snapshot", sa.JSON(), nullable=False),
        sa.Column("wild_pokemon_snapshot", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["exploration_event_id"], ["exploration_events.id"]),
        sa.ForeignKeyConstraint(["trainer_active_my_pokemon_id"], ["my_pokemons.id"]),
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.ForeignKeyConstraint(["wild_pokemon_id"], ["pokemons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wild_pokemon_battle_sessions_active_unique",
        "wild_pokemon_battle_sessions",
        ["trainer_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_wild_pokemon_battle_sessions_trainer_created",
        "wild_pokemon_battle_sessions",
        ["trainer_id", "created_at"],
    )

    op.create_table(
        "wild_pokemon_battle_turns",
        sa.Column("battle_session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column(
            "actor",
            postgresql.ENUM(
                "TRAINER",
                "WILD",
                name="battleactorenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "action_type",
            postgresql.ENUM(
                "USE_MOVE",
                "SWITCH",
                "FLEE",
                "AUTO_RESPONSE",
                name="battleactiontypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("move_name", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["battle_session_id"], ["wild_pokemon_battle_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wild_pokemon_battle_turns_session_turn",
        "wild_pokemon_battle_turns",
        ["battle_session_id", "turn_number", "created_at"],
    )

    op.create_table(
        "wild_pokemon_battle_logs",
        sa.Column("battle_session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column(
            "actor",
            postgresql.ENUM(
                "TRAINER",
                "WILD",
                name="battleactorenum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "log_type",
            postgresql.ENUM(
                "SESSION_STARTED",
                "MOVE_USED",
                "DAMAGE_DEALT",
                "SWITCHED",
                "FLED",
                "SESSION_FINISHED",
                name="battlelogtypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["battle_session_id"], ["wild_pokemon_battle_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wild_pokemon_battle_logs_session_created",
        "wild_pokemon_battle_logs",
        ["battle_session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_wild_pokemon_battle_logs_session_created", table_name="wild_pokemon_battle_logs")
    op.drop_table("wild_pokemon_battle_logs")
    op.drop_index("ix_wild_pokemon_battle_turns_session_turn", table_name="wild_pokemon_battle_turns")
    op.drop_table("wild_pokemon_battle_turns")
    op.drop_index("ix_wild_pokemon_battle_sessions_trainer_created", table_name="wild_pokemon_battle_sessions")
    op.drop_index("ix_wild_pokemon_battle_sessions_active_unique", table_name="wild_pokemon_battle_sessions")
    op.drop_table("wild_pokemon_battle_sessions")
    sa.Enum(name="battlelogtypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battleactiontypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battleactorenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battlesessionstatusenum").drop(op.get_bind(), checkfirst=False)
