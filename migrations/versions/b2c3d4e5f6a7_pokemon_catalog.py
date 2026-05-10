"""add pokemon catalog

Revision ID: b2c3d4e5f6a7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps(include_deleted: bool = True):
    columns = [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]
    if include_deleted:
        columns.append(
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    return columns


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE pokemonstatusenum AS ENUM ('COMPLETE', 'INCOMPLETE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "pokemon_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "COMPLETE",
                "INCOMPLETE",
                name="pokemonstatusenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("text_color", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("background_color", sa.String(), nullable=False),
        sa.Column("badge_url", sa.String(), nullable=False),
        sa.Column("badge_icon_url", sa.String(), nullable=False),
        sa.Column("badge_shield_url", sa.String(), nullable=False),
        sa.Column("badge_legends_url", sa.String(), nullable=False),
        sa.Column("badge_legend_icon_url", sa.String(), nullable=False),
        sa.Column("badge_shield_icon_url", sa.String(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemon_type_weaknesses",
        sa.Column("pokemon_type_id", sa.UUID(), nullable=False),
        sa.Column("pokemon_type_weakness_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pokemon_type_id"], ["pokemon_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pokemon_type_weakness_id"], ["pokemon_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("pokemon_type_id", "pokemon_type_weakness_id"),
    )
    op.create_table(
        "pokemon_type_strengths",
        sa.Column("pokemon_type_id", sa.UUID(), nullable=False),
        sa.Column("pokemon_type_strength_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pokemon_type_id"], ["pokemon_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pokemon_type_strength_id"], ["pokemon_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("pokemon_type_id", "pokemon_type_strength_id"),
    )
    op.create_table(
        "pokemon_moves",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pp", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("power", sa.Integer(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("effect", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("short_effect", sa.Text(), nullable=False),
        sa.Column("flavor_text", sa.Text(), nullable=False),
        sa.Column("damage_class", sa.String(), nullable=False),
        sa.Column("effect_chance", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemon_abilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("effect", sa.Text(), nullable=False),
        sa.Column("short_effect", sa.Text(), nullable=False),
        sa.Column("flavor_text", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemon_growth_rates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemon_habitats",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemon_shapes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemon_images",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("images", sa.Text(), nullable=False),
        sa.Column("back_source", sa.String(), nullable=False),
        sa.Column("back_image", sa.String(), nullable=False),
        sa.Column("front_image", sa.String(), nullable=False),
        sa.Column("front_source", sa.String(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
    )

    op.create_table(
        "pokemon_encounters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("chance", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("min_level", sa.Integer(), nullable=False),
        sa.Column("max_level", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(), nullable=False),
        sa.Column("max_chance", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "pokemons",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("external_image", sa.String(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "COMPLETE",
                "INCOMPLETE",
                name="pokemonstatusenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("hp", sa.Integer(), nullable=True),
        sa.Column("speed", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("attack", sa.Integer(), nullable=True),
        sa.Column("defense", sa.Integer(), nullable=True),
        sa.Column("special_attack", sa.Integer(), nullable=True),
        sa.Column("special_defense", sa.Integer(), nullable=True),
        sa.Column("base_experience", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capture_rate", sa.Integer(), nullable=True),
        sa.Column("is_baby", sa.Boolean(), nullable=True),
        sa.Column("is_mythical", sa.Boolean(), nullable=True),
        sa.Column("is_legendary", sa.Boolean(), nullable=True),
        sa.Column("gender_rate", sa.Integer(), nullable=True),
        sa.Column("hatch_counter", sa.Integer(), nullable=True),
        sa.Column("base_happiness", sa.Integer(), nullable=True),
        sa.Column("evolution_chain", sa.String(), nullable=True),
        sa.Column("evolves_from_species", sa.String(), nullable=True),
        sa.Column("has_gender_differences", sa.Boolean(), nullable=True),
        sa.Column("growth_rate_id", sa.UUID(), nullable=True),
        sa.Column("images_id", sa.UUID(), nullable=True),
        sa.Column("habitat_id", sa.UUID(), nullable=True),
        sa.Column("shape_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["growth_rate_id"], ["pokemon_growth_rates.id"]),
        sa.ForeignKeyConstraint(["images_id"], ["pokemon_images.id"]),
        sa.ForeignKeyConstraint(["habitat_id"], ["pokemon_habitats.id"]),
        sa.ForeignKeyConstraint(["shape_id"], ["pokemon_shapes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("order"),
    )
    op.create_table(
        "pokemon_type_links",
        sa.Column("pokemon_id", sa.UUID(), nullable=False),
        sa.Column("type_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["type_id"], ["pokemon_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pokemon_id", "type_id"),
    )
    op.create_table(
        "pokemon_move_links",
        sa.Column("pokemon_id", sa.UUID(), nullable=False),
        sa.Column("move_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["move_id"], ["pokemon_moves.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pokemon_id", "move_id"),
    )
    op.create_table(
        "pokemon_ability_links",
        sa.Column("pokemon_id", sa.UUID(), nullable=False),
        sa.Column("ability_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ability_id"], ["pokemon_abilities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("pokemon_id", "ability_id"),
    )
    op.create_table(
        "pokemon_encounter_links",
        sa.Column("pokemon_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["pokemon_encounters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("pokemon_id", "encounter_id"),
    )
    op.create_table(
        "pokemon_evolution_links",
        sa.Column("pokemon_id", sa.UUID(), nullable=False),
        sa.Column("evolution_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["pokemon_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evolution_id"], ["pokemons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pokemon_id", "evolution_id"),
    )


def downgrade() -> None:
    for table, column in reversed(
        (
            ("pokemons", "growth_rate_id"),
            ("pokemons", "habitat_id"),
            ("pokemons", "shape_id"),
            ("pokemon_images", "pokemon_id"),
        )
    ):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    op.drop_table("pokemon_images")
    op.drop_table("pokemon_evolution_links")
    op.drop_table("pokemon_ability_links")
    op.drop_table("pokemon_move_links")
    op.drop_table("pokemon_type_links")
    op.drop_table("pokemon_encounter_links")
    op.drop_table("pokemons")
    op.drop_table("pokemon_shapes")
    op.drop_table("pokemon_habitats")
    op.drop_table("pokemon_growth_rates")
    op.drop_table("pokemon_abilities")
    op.drop_table("pokemon_moves")
    op.drop_table("pokemon_types")
    op.drop_table("pokemon_encounters")
    op.execute("DROP TYPE IF EXISTS pokemonstatusenum")
