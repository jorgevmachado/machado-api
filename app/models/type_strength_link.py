from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import table_registry


@table_registry.mapped_as_dataclass
class TypeStrengthLink:
    __tablename__ = "type_strength_link"
    type_id: Mapped[str] = mapped_column(
        ForeignKey("types.id", ondelete="CASCADE"), primary_key=True
    )
    type_strength_id: Mapped[str] = mapped_column(
        ForeignKey("types.id", ondelete="CASCADE"), primary_key=True
    )
