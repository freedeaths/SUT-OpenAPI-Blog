from datetime import datetime, UTC
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import uuid
import enum

class TagStatus(str, enum.Enum):
    """Tag status"""
    ACTIVE = "ACTIVE"  # Active
    ARCHIVED = "ARCHIVED"  # Archived

class Tag(Base):
    """Tag model"""
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), unique=True)  # tag name must be unique
    description: Mapped[str] = mapped_column(Text, nullable=True)  # tag description, optional
    creator_id: Mapped[str] = mapped_column(String(36))  # not using foreign key, only store creator ID
    status: Mapped[TagStatus] = mapped_column(
        Enum(TagStatus),
        default=TagStatus.ACTIVE,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0)  # tag usage count
