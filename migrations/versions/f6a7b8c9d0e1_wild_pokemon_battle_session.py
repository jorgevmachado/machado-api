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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE battlesessionstatusenum AS ENUM ('ACTIVE', 'WILD_POKEMON_DEFEATED', 'TRAINER_DEFEATED', 'ESCAPED');
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

    if "battle_sessions" not in existing_tables:
        op.create_table(
            "battle_sessions",
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
                    "WILD_POKEMON_DEFEATED",
                    "TRAINER_DEFEATED",
                    "ESCAPED",
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

    battle_session_indexes = {index["name"] for index in inspector.get_indexes("battle_sessions")}
    if "ix_battle_sessions_active_unique" not in battle_session_indexes:
        op.create_index(
            "ix_battle_sessions_active_unique",
            "battle_sessions",
            ["trainer_id"],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
        )
    if "ix_battle_sessions_trainer_created" not in battle_session_indexes:
        op.create_index(
            "ix_battle_sessions_trainer_created",
            "battle_sessions",
            ["trainer_id", "created_at"],
        )

    if "battle_turns" not in existing_tables:
        op.create_table(
            "battle_turns",
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
            sa.ForeignKeyConstraint(["battle_session_id"], ["battle_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    battle_turn_indexes = {index["name"] for index in inspector.get_indexes("battle_turns")}
    if "ix_battle_turns_session_turn" not in battle_turn_indexes:
        op.create_index(
            "ix_battle_turns_session_turn",
            "battle_turns",
            ["battle_session_id", "turn_number", "created_at"],
        )

    if "battle_logs" not in existing_tables:
        op.create_table(
            "battle_logs",
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
                    "ESCAPED",
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
            sa.ForeignKeyConstraint(["battle_session_id"], ["battle_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    battle_log_indexes = {index["name"] for index in inspector.get_indexes("battle_logs")}
    if "ix_battle_logs_session_created" not in battle_log_indexes:
        op.create_index(
            "ix_battle_logs_session_created",
            "battle_logs",
            ["battle_session_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_battle_logs_session_created", table_name="battle_logs")
    op.drop_table("battle_logs")
    op.drop_index("ix_battle_turns_session_turn", table_name="battle_turns")
    op.drop_table("battle_turns")
    op.drop_index("ix_battle_sessions_trainer_created", table_name="battle_sessions")
    op.drop_index("ix_battle_sessions_active_unique", table_name="battle_sessions")
    op.drop_table("battle_sessions")
    sa.Enum(name="battlelogtypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battleactiontypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battleactorenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battlesessionstatusenum").drop(op.get_bind(), checkfirst=False)
