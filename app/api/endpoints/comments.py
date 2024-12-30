from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_session
from app.models.comment import Comment, CommentStatus
from app.models.post import Post, PostStatus
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from app.core.security import get_current_user
from datetime import datetime, UTC
from typing import List

router = APIRouter()

@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, summary="Create a comment on a post")
def create_comment(
    post_id: str,
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a comment on a post"""
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
            detail="You can only comment on active posts"
        )
    
    # Create comment
    db_comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        content=comment.content,
        status=CommentStatus.ACTIVE  # Comments are active by default
    )
    session.add(db_comment)
    
    # Update post's comment count
    post.comments_count += 1
    
    session.commit()
    session.refresh(db_comment)
    return db_comment

@router.get("", response_model=List[CommentResponse], summary="List all comments on a post")
def list_comments(
    post_id: str,
    session: Session = Depends(get_session)
):
    """List all comments on a post"""
    # Check if post exists
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Can only view comments on active posts
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comments are only visible on active posts"
        )
    
    return session.query(Comment).filter(
            Comment.post_id == post_id,
            Comment.status == CommentStatus.ACTIVE
    ).all()

@router.get("/{comment_id}", response_model=CommentResponse, summary="Get a specific comment on a post")
def get_comment(
    post_id: str,
    comment_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific comment"""
    # Check if post exists
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Can only view comments on active posts
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comments are only visible on active posts"
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
            detail="Comment not found"
        )
    
    return comment

@router.put("/{comment_id}", response_model=CommentResponse, summary="Update a comment on a post")
def update_comment(
    post_id: str,
    comment_id: str,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a comment"""
    # Check if post exists
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Check if comment belongs to this post
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    # Check permissions
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this comment"
        )
    
    # Check post status: can only update comments on active posts
    post = session.query(Post).filter(Post.id == comment.post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update comments on active posts"
        )
    
    # Check comment status: can only update active comments
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update active comments"
        )
    
    comment.content = comment_update.content
    comment.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(comment)
    return comment

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a comment on a post")
def delete_comment(
    post_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a comment and all its replies."""
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Check if comment belongs to this post
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    # Check permissions: only the author can delete the comment
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this comment"
        )
    
    # Check post status: only active posts can have comments
    post = session.query(Post).filter(Post.id == comment.post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete comments on active posts"
        )
    
    # Check comment status: only active comments can be deleted
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete active comments"
        )
    
    # 1. Delete all replies to this comment
    from app.models.reply import Reply
    session.query(Reply).filter(Reply.comment_id == comment_id).delete(synchronize_session=False)
    
    # Then delete the comment
    session.delete(comment)
    
    # Update post's comment count
    post.comments_count -= 1
    session.commit()

@router.post("/{comment_id}:activateComment", response_model=CommentResponse, summary="Activate a comment on a post")
def activate_comment(
    post_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Activate a comment"""
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Check if comment belongs to this post
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    # Check permissions
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to activate this comment"
        )
    
    # Can only activate comments on active posts
    post = session.query(Post).filter(Post.id == comment.post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only activate comments on active posts"
        )
    
    comment.status = CommentStatus.ACTIVE
    session.commit()
    session.refresh(comment)
    return comment

@router.post("/{comment_id}:archiveComment", response_model=CommentResponse, summary="Archive a comment on a post")
def archive_comment(
    post_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Archive a comment"""
    comment = session.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Check if comment belongs to this post
    if comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found in this post"
        )
    
    # Check permissions
    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to archive this comment"
        )
    
    # Can only archive comments on active posts
    post = session.query(Post).filter(Post.id == comment.post_id).first()
    if post.status != PostStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only archive comments on active posts"
        )
    
    # Can only archive active comments
    if comment.status != CommentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only archive active comments"
        )
    
    comment.status = CommentStatus.ARCHIVED
    session.commit()
    session.refresh(comment)
    return comment
