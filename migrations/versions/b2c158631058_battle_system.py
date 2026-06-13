"""Battle System

Revision ID: b2c158631058
Revises: b88c467fcfd6
Create Date: 2026-06-12 11:11:18.513645

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c158631058"
down_revision: Union[str, Sequence[str], None] = "b88c467fcfd6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
            DO $$ BEGIN
                CREATE TYPE battleactorenum AS ENUM ('WILD', 'TRAINER');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE battlesessionstatusenum AS ENUM ('ACTIVE', 'ESCAPED', 'CAPTURED', 'TRAINER_DEFEATED', 'WILD_POKEMON_DEFEATED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
            DO $$ BEGIN
                CREATE TYPE battleactiontypeenum AS ENUM ('FLEE', 'SWITCH', 'CAPTURE', 'USE_MOVE', 'AUTO_RESPONSE');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
    op.execute("""
            DO $$ BEGIN
                CREATE TYPE battlelogtypeenum AS ENUM ('ESCAPED', 'SWITCHED', 'MOVE_USED', 'DAMAGE_DEALT', 'CAPTURE_FAILED', 'SESSION_STARTED', 'CAPTURE_ATTEMPT', 'CAPTURE_SUCCESS', 'SESSION_FINISHED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
    op.execute("""
            DO $$ BEGIN
                CREATE TYPE explorationeventtypeenum AS ENUM ('POKEBALLS', 'WILD_POKEMON');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
    op.create_table(
        "exploration_events",
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "POKEBALLS",
                "WILD_POKEMON",
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
    op.create_table(
        "battle_sessions",
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("exploration_event_id", sa.Uuid(), nullable=False),
        sa.Column("wild_pokemon_id", sa.Uuid(), nullable=False),
        sa.Column("trainer_active_owned_pokemon_id", sa.Uuid(), nullable=True),
        sa.Column("wild_pokemon_name", sa.String(), nullable=False),
        sa.Column("wild_pokemon_level", sa.Integer(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "ESCAPED",
                "CAPTURED",
                "TRAINER_DEFEATED",
                "WILD_POKEMON_DEFEATED",
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
        sa.ForeignKeyConstraint(["trainer_id"], ["trainers.id"]),
        sa.ForeignKeyConstraint(["exploration_event_id"], ["exploration_events.id"]),
        sa.ForeignKeyConstraint(["wild_pokemon_id"], ["pokedex_entries.id"]),
        sa.ForeignKeyConstraint(
            ["trainer_active_owned_pokemon_id"], ["owned_pokemons.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_battle_sessions_trainer_status_created",
        "battle_sessions",
        ["trainer_id", "status", "created_at"],
    )
    op.create_index(
        "ix_battle_sessions_exploration_event_id",
        "battle_sessions",
        ["exploration_event_id"],
    )
    op.create_index(
        "ix_battle_sessions_wild_pokemon_id",
        "battle_sessions",
        ["wild_pokemon_id"],
    )
    op.create_index(
        "ix_battle_sessions_trainer_active_owned_pokemon_id",
        "battle_sessions",
        ["trainer_active_owned_pokemon_id"],
    )
    op.create_table(
        "battle_turns",
        sa.Column("battle_session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column(
            "actor",
            postgresql.ENUM(
                "WILD",
                "TRAINER",
                name="battleactorenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "action_type",
            postgresql.ENUM(
                "FLEE",
                "SWITCH",
                "CAPTURE",
                "USE_MOVE",
                "AUTO_RESPONSE",
                name="battleactiontypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("move_name", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["battle_session_id"], ["battle_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_battle_turns_session_turn",
        "battle_turns",
        ["battle_session_id", "turn_number"],
    )
    op.create_index(
        "ix_battle_turns_session_created",
        "battle_turns",
        ["battle_session_id", "created_at"],
    )
    op.create_table(
        "battle_logs",
        sa.Column("battle_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "log_type",
            postgresql.ENUM(
                "ESCAPED",
                "SWITCHED",
                "MOVE_USED",
                "DAMAGE_DEALT",
                "CAPTURE_FAILED",
                "SESSION_STARTED",
                "CAPTURE_ATTEMPT",
                "CAPTURE_SUCCESS",
                "SESSION_FINISHED",
                name="battlelogtypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column(
            "actor",
            postgresql.ENUM(
                "WILD",
                "TRAINER",
                name="battleactorenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["battle_session_id"], ["battle_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_battle_logs_session_created",
        "battle_logs",
        ["battle_session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("battle_logs")
    op.drop_table("battle_turns")
    op.drop_table("battle_sessions")
    op.drop_table("exploration_events")
    sa.Enum(name="explorationeventtypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battlelogtypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battleactiontypeenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battlesessionstatusenum").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="battleactorenum").drop(op.get_bind(), checkfirst=False)
