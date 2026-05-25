"""add pokemon capture system support

Revision ID: 0a1b2c3d4e5f
Revises: f6a7b8c9d0e1
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_enum_value_if_missing(enum_name: str, value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}'
                  AND e.enumlabel = '{value}'
            ) THEN
                ALTER TYPE {enum_name} ADD VALUE '{value}';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    trainer_columns = {column["name"] for column in inspector.get_columns("trainers")}

    _add_enum_value_if_missing("battlesessionstatusenum", "CAPTURED")
    _add_enum_value_if_missing("battleactiontypeenum", "CAPTURE")
    _add_enum_value_if_missing("battlelogtypeenum", "CAPTURE_ATTEMPT")
    _add_enum_value_if_missing("battlelogtypeenum", "CAPTURE_SUCCESS")
    _add_enum_value_if_missing("battlelogtypeenum", "CAPTURE_FAILED")

    if "base_capture_rate" not in trainer_columns:
        op.add_column(
            "trainers",
            sa.Column("base_capture_rate", sa.Integer(), nullable=True),
        )
        op.execute("UPDATE trainers SET base_capture_rate = capture_rate WHERE base_capture_rate IS NULL")
        op.alter_column("trainers", "base_capture_rate", nullable=False)

    if "capture_progress_points" not in trainer_columns:
        op.add_column(
            "trainers",
            sa.Column("capture_progress_points", sa.Integer(), nullable=True),
        )
        op.execute("UPDATE trainers SET capture_progress_points = 0 WHERE capture_progress_points IS NULL")
        op.alter_column("trainers", "capture_progress_points", nullable=False)


def downgrade() -> None:
    op.drop_column("trainers", "capture_progress_points")
    op.drop_column("trainers", "base_capture_rate")
