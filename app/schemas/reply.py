from pydantic import BaseModel, Field
from datetime import datetime
from app.models.reply import ReplyStatus

class ReplyBase(BaseModel):
    """回复基础模型"""
    content: str = Field(..., min_length=1, description="回复内容")

class ReplyCreate(ReplyBase):
    """创建回复请求模型"""
    pass

class ReplyUpdate(ReplyBase):
    """更新回复请求模型"""
    pass

class ReplyResponse(ReplyBase):
    """回复响应模型"""
    id: str = Field(..., description="回复ID")
    comment_id: str = Field(..., description="评论ID")
    author_id: str = Field(..., description="作者ID")
    status: ReplyStatus = Field(..., description="回复状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    likes_count: int = Field(default=0, description="点赞数")
    dislikes_count: int = Field(default=0, description="点踩数")

    class Config:
        from_attributes = True
