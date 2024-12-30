from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_session
from app.models.reply import Reply, ReplyStatus
from app.models.comment import Comment, CommentStatus
from app.models.post import Post, PostStatus
from app.models.user import User
from app.schemas.reply import ReplyCreate, ReplyUpdate, ReplyResponse
from app.core.security import get_current_user
from datetime import datetime, UTC
from typing import List

router = APIRouter()

@router.post("", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED, summary="Create a reply to a comment")
def create_reply(
    post_id: str,
    comment_id: str,
    reply: ReplyCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a reply to a comment"""
    # Check if post exists and is active
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reply to comments on active posts"
        )
    
    # Check if comment exists and belongs to this post
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reply to active comments"
        )
    
    # Create reply
    db_reply = Reply(
        comment_id=comment_id,
        author_id=current_user.id,
        content=reply.content,
        status=ReplyStatus.ACTIVE  # Replies are active by default
    )
    session.add(db_reply)
    session.commit()
    session.refresh(db_reply)
    return db_reply

@router.get("", response_model=List[ReplyResponse], summary="List all replies to a comment")
def list_replies(
    post_id: str,
    comment_id: str,
    session: Session = Depends(get_session)
):
    """List all replies to a comment"""
    # Check if post exists and is active
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Replies are only visible on active posts"
        )
    
    # Check if comment exists and belongs to this post
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Replies are only visible on active comments"
        )
    
    return session.query(Reply).filter(
        Reply.comment_id == comment_id,
        Reply.status == ReplyStatus.ACTIVE
    ).all()

@router.get("/{reply_id}", response_model=ReplyResponse, summary="Get a specific reply to a comment")
def get_reply(
    post_id: str,
    comment_id: str,
    reply_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific reply"""
    # Check if post exists and is active
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Replies are only visible on active posts"
        )
    
    # Check if comment exists and belongs to this post
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Replies are only visible on active comments"
        )
    
    # Check if reply exists and belongs to this comment
    reply = session.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    if reply.comment_id != comment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found in this comment"
        )
    if reply.status != ReplyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reply not found"
        )
    
    return reply

@router.put("/{reply_id}", response_model=ReplyResponse, summary="Update a reply to a comment")
def update_reply(
    post_id: str,
    comment_id: str,
    reply_id: str,
    reply_update: ReplyUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a reply"""
    # Check if post exists
    reply = session.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    
    # Check if reply belongs to this comment
    if reply.comment_id != comment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found in this comment"
        )
    
    # Check if comment exists and belongs to this post
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    # Check permissions: only the author can update the reply
    if reply.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this reply"
        )
    
    # Check if post exists and is active
    post = session.query(Post).filter(Post.id == post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update replies on active posts"
        )
    
    # Check comment status: only active comments can have replies
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update replies on active comments"
        )
    
    # Check reply status: only active replies can be updated
    if reply.status != ReplyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update active replies"
        )
    
    reply.content = reply_update.content
    reply.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(reply)
    return reply

@router.delete("/{reply_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a reply")
def delete_reply(
    post_id: str,
    comment_id: str,
    reply_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a reply"""
    # Check if post exists
    reply = session.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    
    # Check if reply belongs to this comment
    if reply.comment_id != comment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found in this comment"
        )
    
    # Check if comment exists and belongs to this post
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    # Check permissions: only the author can delete the reply
    if reply.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this reply"
        )
    
    # Check post status: only active posts can have replies
    post = session.query(Post).filter(Post.id == post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete replies on active posts"
        )
    
    # Check comment status: only active comments can have replies
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete replies on active comments"
        )
    
    # Check reply status: only active replies can be deleted
    if reply.status != ReplyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete active replies"
        )
    
    # Set the reply status to ARCHIVED
    reply.status = ReplyStatus.ARCHIVED
    session.commit()

@router.post("/{reply_id}:activateReply", response_model=ReplyResponse, summary="Activate a reply")
def activate_reply(
    post_id: str,
    comment_id: str,
    reply_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Activate a reply"""
    # Check if reply exists
    reply = session.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    if reply.comment_id != comment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found in this comment"
        )
    

    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    

    if reply.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to activate this reply"
        )
    

    post = session.query(Post).filter(Post.id == post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only activate replies on active posts"
        )
    

    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only activate replies on active comments"
        )
    
    reply.status = ReplyStatus.ACTIVE
    session.commit()
    session.refresh(reply)
    return reply

@router.post("/{reply_id}:archiveReply", response_model=ReplyResponse, summary="Archive a reply")
def archive_reply(
    post_id: str,
    comment_id: str,
    reply_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Archive a reply"""

    reply = session.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    if reply.comment_id != comment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found in this comment"
        )
    
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    if reply.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to archive this reply"
        )
    
    post = session.query(Post).filter(Post.id == post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only archive replies on active posts"
        )
    
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only archive replies on active comments"
        )
    
    if reply.status != ReplyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only archive active replies"
        )
    
    reply.status = ReplyStatus.ARCHIVED
    session.commit()
    session.refresh(reply)
    return reply
