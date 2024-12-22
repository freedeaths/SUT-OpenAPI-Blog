from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.db.database import get_session
from app.models.tag import Tag, TagStatus
from app.models.post_tag import PostTag
from app.models.post import Post, PostStatus
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate, TagResponse
from app.core.security import get_current_user, get_optional_current_user
from datetime import datetime, UTC

router = APIRouter()

@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag: TagCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new tag"""
    # Check if tag name already exists
    existing_tag = session.query(Tag).filter(Tag.name == tag.name).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag name already exists"
        )
    
    # Create tag
    db_tag = Tag(
        name=tag.name,
        description=tag.description,
        creator_id=current_user.id,
        status=TagStatus.ACTIVE
    )
    session.add(db_tag)
    session.commit()
    session.refresh(db_tag)
    return db_tag

@router.get("/", response_model=List[TagResponse])
def list_tags(
    session: Session = Depends(get_session)
):
    """List all tags"""
    return session.query(Tag).filter(Tag.status == TagStatus.ACTIVE).all()

@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific tag"""
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    if tag.status != TagStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    return tag

@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: str,
    tag_update: TagUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a tag"""
    # Check if tag exists
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check permissions
    if tag.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if new name already exists
    if tag_update.name and tag_update.name != tag.name:
        existing_tag = session.query(Tag).filter(Tag.name == tag_update.name).first()
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag name already exists"
            )
        tag.name = tag_update.name
    
    # Update description
    if tag_update.description is not None:
        tag.description = tag_update.description
    
    tag.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(tag)
    return tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a tag"""
    # Check if tag exists
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check permissions
    if tag.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Delete all associated post_tags
    session.query(PostTag).filter(PostTag.tag_id == tag_id).delete()
    
    # Delete tag
    session.delete(tag)
    session.commit()

@router.post("/{tag_id}/archive", response_model=TagResponse)
def archive_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Archive a tag"""
    # Check if tag exists
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check permissions
    if tag.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Archive tag
    tag.status = TagStatus.ARCHIVED
    tag.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(tag)
    return tag

@router.post("/posts/{post_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_tag_to_post(
    post_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Add a tag to a post"""
    # Check if post exists and belongs to current user
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if tag exists and is active
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag or tag.status != TagStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check if tag is already added to post
    existing = session.query(PostTag).filter(
        and_(
            PostTag.post_id == post_id,
            PostTag.tag_id == tag_id
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag already added to this post"
        )
    
    # Add tag to post
    post_tag = PostTag(
        post_id=post_id,
        tag_id=tag_id
    )
    session.add(post_tag)
    
    # Update tag usage count
    tag.usage_count += 1
    
    session.commit()

@router.delete("/posts/{post_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag_from_post(
    post_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Remove a tag from a post"""
    # Check if post exists and belongs to current user
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if tag exists
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Remove tag from post
    result = session.query(PostTag).filter(
        and_(
            PostTag.post_id == post_id,
            PostTag.tag_id == tag_id
        )
    ).delete()
    
    if result > 0:
        # Update tag usage count
        tag.usage_count -= 1
        session.commit()

@router.get("/posts/{post_id}/tags", response_model=List[TagResponse])
def list_post_tags(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user)
):
    """List all tags of a post"""
    # Check if post exists and is active
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check permissions
    # 1. Draft posts must be logged in and only the author can access
    if post.status == PostStatus.DRAFT:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view draft posts"
            )
        if post.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this post"
            )
    # 2. Other status posts can be accessed by anyone
    elif post.status not in [PostStatus.ACTIVE, PostStatus.ARCHIVED]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Post is not accessible"
        )
    
    # Get all tags of the post
    post_tags = session.query(PostTag).filter(PostTag.post_id == post_id).all()
    tag_ids = [pt.tag_id for pt in post_tags]
    
    # Only return active tags
    return session.query(Tag).filter(
        and_(
            Tag.id.in_(tag_ids),
            Tag.status == TagStatus.ACTIVE
        )
    ).all()
