from datetime import datetime, UTC
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import uuid
import enum

class ReplyStatus(str, enum.Enum):
    """Reply status"""
    DRAFT = "DRAFT"  # Draft
    ACTIVE = "ACTIVE"  # Active, visible to everyone
    ARCHIVED = "ARCHIVED"  # Archived, only visible to author and comment author

class Reply(Base):
    """Reply model"""
    __tablename__ = "replies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comment_id: Mapped[str] = mapped_column(String(36))  # Not using foreign key, only storing comment ID
    author_id: Mapped[str] = mapped_column(String(36))  # Not using foreign key, only storing author ID
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[ReplyStatus] = mapped_column(
        Enum(ReplyStatus),
        default=ReplyStatus.DRAFT,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0)
