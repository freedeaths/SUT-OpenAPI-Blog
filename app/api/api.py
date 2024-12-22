from fastapi import APIRouter
from app.api.endpoints import (
    users,
    posts,
    comments,
    replies,
    reactions,
    tags
)

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(comments.router, prefix="/posts/{post_id}/comments", tags=["comments"])
api_router.include_router(replies.router, prefix="/posts/{post_id}/comments/{comment_id}/replies", tags=["replies"])
api_router.include_router(reactions.router, prefix="/reactions", tags=["reactions"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
