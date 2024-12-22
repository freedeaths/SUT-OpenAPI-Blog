from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_session
from app.models.post import Post, PostStatus
from app.models.user import User
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.core.security import get_current_user, get_optional_current_user
from datetime import datetime, UTC
from typing import List, Optional

router = APIRouter()

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post: PostCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new post"""
    db_post = Post(
        author_id=current_user.id,
        title=post.title,
        content=post.content
    )
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return db_post

@router.get("", response_model=List[PostResponse])
def list_posts(
    status: PostStatus = None,
    author_id: str = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all posts"""
    query = session.query(Post)
    
    # If viewing posts by a specific author
    if author_id:
        query = query.filter(Post.author_id == author_id)
        # If viewing own posts, show all statuses
        if author_id == current_user.id:
            if status:
                query = query.filter(Post.status == status)
        # If viewing another user's posts, only show active and archived posts
        else:
            query = query.filter(Post.status.in_([PostStatus.ACTIVE, PostStatus.ARCHIVED]))
            if status and status in [PostStatus.ACTIVE, PostStatus.ARCHIVED]:
                query = query.filter(Post.status == status)
    # If not viewing posts by a specific author, show own posts and public posts by others
    else:
        # Show own posts and public posts by others
        query = query.filter(
            (Post.author_id == current_user.id) |
            (Post.status.in_([PostStatus.ACTIVE, PostStatus.ARCHIVED]))
        )
        # If a status is specified, filter by that status
        if status:
            query = query.filter(Post.status == status)
    
    return query.all()

@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user)
):
    """Get a specific post"""
    print(f"current_user: {current_user}")  # Debug information
    
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    print(f"post.status: {post.status}")  # Debug information
    
    # Check permissions:
    # 1. Draft posts must be logged in and can only be accessed by the author
    if post.status == PostStatus.DRAFT:
        print(f"checking draft post access")  # Debug information
        if not current_user:
            print(f"raising 401")  # Debug information
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view draft posts"
            )
        if post.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this post"
            )
    # 2. Other statuses can be accessed by anyone
    
    # Increase view count
    post.views_count += 1
    session.commit()
    
    return post

@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: str,
    post_update: PostUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a post"""
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permissions
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this post"
        )
    
    # Check status
    if post.status != PostStatus.MODIFYING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update post in MODIFYING status"
        )
    
    # Update fields
    for field, value in post_update.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    post.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(post)
    return post

@router.post("/{post_id}:activatePost", response_model=PostResponse)
def activate_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Activate a post"""
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permissions
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to activate this post"
        )
    
    # Check current status
    if post.status == PostStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate an archived post"
        )
    
    post.status = PostStatus.ACTIVE
    post.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(post)
    return post

@router.post("/{post_id}:modifyPost", response_model=PostResponse)
def modify_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Put a post in modifying status"""
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permissions
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this post"
        )
    
    # Check current status
    if post.status == PostStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an archived post"
        )
    
    post.status = PostStatus.MODIFYING
    post.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(post)
    return post

@router.post("/{post_id}:archivePost", response_model=PostResponse)
def archive_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Archive a post"""
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permissions
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to archive this post"
        )
    
    post.status = PostStatus.ARCHIVED
    post.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(post)
    return post

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a post and all its comments and replies"""
    # Check if post exists
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permissions
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this post"
        )
    
    # 1. Delete all replies to comments
    from app.models.reply import Reply
    from app.models.comment import Comment
    
    # Get all comment IDs for this post
    comment_ids = [comment.id for comment in session.query(Comment).filter(Comment.post_id == post_id).all()]
    
    # Delete all replies to these comments
    if comment_ids:
        session.query(Reply).filter(Reply.comment_id.in_(comment_ids)).delete(synchronize_session=False)
    
    # 2. Delete all comments
    session.query(Comment).filter(Comment.post_id == post_id).delete(synchronize_session=False)
    
    # 3. Delete post
    session.delete(post)
    session.commit()
    return None
