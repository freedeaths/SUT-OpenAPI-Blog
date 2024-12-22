from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from app.models.tag import TagStatus

class TagBase(BaseModel):
    """标签基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")

class TagCreate(TagBase):
    """创建标签请求模型"""
    pass

class TagUpdate(BaseModel):
    """更新标签请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")

class TagResponse(TagBase):
    """标签响应模型"""
    id: str = Field(..., description="标签ID")
    creator_id: str = Field(..., description="创建者ID")
    status: TagStatus = Field(..., description="标签状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    usage_count: int = Field(..., description="使用次数")

    class Config:
        from_attributes = True
