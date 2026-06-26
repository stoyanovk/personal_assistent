from sqlalchemy import ForeignKey, Enum, DateTime, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True
    )
    timezone: Mapped[str] = mapped_column(nullable=False, default="UTC")

    calendar_items: Mapped[list["CalendarItem"]] = relationship(
        back_populates="user"
    )

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user"
    )


class EventType(enum.Enum):
    event = "event"
    reminder = "reminder"


class CalendarItem(Base):
    __tablename__ = "calendar_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[EventType] = mapped_column(Enum(EventType))
    title: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(nullable=True)
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_all_day: Mapped[bool] = mapped_column(default=False)
    recurrence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="calendar_items")


class StatusType(enum.Enum):
    pending = "pending"
    queued = "queued"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_status_send_at", "status", "send_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[StatusType] = mapped_column(
        Enum(StatusType), nullable=False, default=StatusType.pending
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    send_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    calendar_item_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_items.id"), index=True
    )
    calendar_item: Mapped["CalendarItem"] = relationship()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="notifications")
