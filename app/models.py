import enum
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Enum, String, UnicodeText
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    rubrics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )


class OutboxStatus(enum.StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class OutboxAction(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class PostOutbox(Base):
    __tablename__ = "post_outboxes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(
            OutboxStatus,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    action: Mapped[OutboxAction] = mapped_column(
        Enum(
            OutboxAction,
            native_enum=False,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        )
    )
    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
