from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import default_lazy, table_registry
from app.models.common import utcnow
from app.models.enums import BattleSessionStatusEnum

if TYPE_CHECKING:
    from app.models.exploration_event import ExplorationEvent
    from app.models.my_pokemon import MyPokemon
    from app.models.pokemon import Pokemon
    from app.models.trainer import Trainer
    from app.models.battle_log import BattleLog
    from app.models.battle_turn import BattleTurn


@table_registry.mapped_as_dataclass
class BattleSession:
    __tablename__ = "battle_sessions"

    trainer_id: Mapped[UUID] = mapped_column(ForeignKey("trainers.id"), nullable=False)
    exploration_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("exploration_events.id"),
        nullable=False,
    )
    wild_pokemon_id: Mapped[UUID] = mapped_column(
        ForeignKey("pokemons.id"),
        nullable=False,
    )
    wild_pokemon_name: Mapped[str] = mapped_column(String, nullable=False)
    wild_pokemon_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trainer_active_my_pokemon_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("my_pokemons.id"),
        nullable=True,
        default=None,
    )
    status: Mapped[BattleSessionStatusEnum] = mapped_column(
        SAEnum(BattleSessionStatusEnum, name="battlesessionstatusenum"),
        nullable=False,
        default=BattleSessionStatusEnum.ACTIVE,
    )
    trainer_party_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default_factory=list,
    )
    wild_pokemon_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default_factory=dict,
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default_factory=uuid4,
        init=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default_factory=utcnow,
        init=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        init=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        init=False,
    )

    trainer: Mapped["Trainer"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="battle_sessions",
    )
    exploration_event: Mapped["ExplorationEvent"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="battle_sessions",
    )
    trainer_active_my_pokemon: Mapped["MyPokemon | None"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="active_battle_sessions",
    )
    wild_pokemon: Mapped["Pokemon"] = relationship(
        lazy=default_lazy,
        init=False,
        back_populates="battle_sessions",
    )
    turns: Mapped[list["BattleTurn"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="battle_session",
    )
    logs: Mapped[list["BattleLog"]] = relationship(
        lazy=default_lazy,
        default_factory=list,
        init=False,
        repr=False,
        back_populates="battle_session",
    )
