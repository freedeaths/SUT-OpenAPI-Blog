from sqlalchemy import Column, String, Integer, Enum as SQLEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, UTC
import uuid
import enum
from app.db.database import Base

class PostStatus(str, enum.Enum):
    """Post status"""
    DRAFT = "DRAFT"         # Draft, only visible to the author
    ACTIVE = "ACTIVE"       # Published, visible to everyone and can be commented
    ARCHIVED = "ARCHIVED"   # Archived, visible to everyone but cannot be commented
    MODIFYING = "MODIFYING" # Modifying, no new comments are allowed, existing comments are visible

class Post(Base):
    """Post model"""
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    author_id = Column(String, nullable=False)  
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    status = Column(SQLEnum(PostStatus), nullable=False, default=PostStatus.DRAFT)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    likes_count = Column(Integer, nullable=False, default=0)
    dislikes_count = Column(Integer, nullable=False, default=0)
    views_count = Column(Integer, nullable=False, default=0)
    comments_count = Column(Integer, nullable=False, default=0)
