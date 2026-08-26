from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
if TYPE_CHECKING:
    from app.models.customer import Customer



class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        index=True,
    )

    twilio_call_sid: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="initiated",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="calls",
    )