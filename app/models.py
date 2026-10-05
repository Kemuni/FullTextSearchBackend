import enum
from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, DateTime, Enum, Index, Integer, String, UnicodeText
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class Post(Base):
    """Пост в социальной сети"""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    rubrics: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, index=True
    )
    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )


class OutboxStatus(enum.StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class OutboxAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class PostOutbox(Base):
    """Модель для реализации паттерна Outbox. Позволяет синхронизовать данные между Postgres и ElasticSearch."""

    __tablename__ = "post_outboxes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(
            OutboxStatus,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=OutboxStatus.PENDING,
        index=True,
    )
    action: Mapped[OutboxAction] = mapped_column(
        Enum(
            OutboxAction,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_outbox_status_next_attempt", "status", "next_attempt_at"),
    )
