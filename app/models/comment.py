from datetime import datetime, timezone as tz
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import uuid
import enum

class CommentStatus(str, enum.Enum):
    """Comment status"""
    DRAFT = "DRAFT"  # Draft
    ACTIVE = "ACTIVE"  # Active, visible to everyone
    ARCHIVED = "ARCHIVED"  # Archived, only visible to author and post author

class Comment(Base):
    """Comment model"""
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id: Mapped[str] = mapped_column(String(36))  # Not using foreign key, only storing ID
    author_id: Mapped[str] = mapped_column(String(36))  # Not using foreign key, only storing ID
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[CommentStatus] = mapped_column(
        Enum(CommentStatus),
        default=CommentStatus.DRAFT,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(tz.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(tz.utc),
        onupdate=lambda: datetime.now(tz.utc)
    )
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    dislikes_count: Mapped[int] = mapped_column(Integer, default=0)
