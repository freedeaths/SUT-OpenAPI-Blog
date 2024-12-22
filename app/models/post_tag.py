from datetime import datetime, UTC
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import uuid

class PostTag(Base):
    """文章标签关联模型"""
    __tablename__ = "post_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id: Mapped[str] = mapped_column(String(36))  # 不使用外键，只存储文章ID
    tag_id: Mapped[str] = mapped_column(String(36))  # 不使用外键，只存储标签ID
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
