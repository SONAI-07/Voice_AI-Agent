from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CallInsight(Base):
    __tablename__ = "call_insights"

    id: Mapped[int] = mapped_column(primary_key=True)

    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id"),
        unique=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        index=True,
    )

    classification: Mapped[str] = mapped_column(
        String(50),
    )

    purchase_probability: Mapped[float] = mapped_column(
        Float,
    )

    interest_score: Mapped[float] = mapped_column(
        Float,
    )

    summary: Mapped[str] = mapped_column(
        String(5000),
    )

    important_details: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )