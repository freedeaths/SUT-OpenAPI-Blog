from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.db.database import get_session
from app.models.tag import Tag, TagStatus
from app.models.post_tag import PostTag
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate, TagResponse
from app.core.security import get_current_user, get_optional_current_user
from datetime import datetime, UTC

router = APIRouter()

@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED, summary="Create a new tag")
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

@router.get("", response_model=List[TagResponse], summary="List all tags")
def list_tags(
    session: Session = Depends(get_session)
):
    """List all tags"""
    return session.query(Tag).filter(Tag.status == TagStatus.ACTIVE).all()

@router.get("/{tag_id}", response_model=TagResponse, summary="Get a specific tag")
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

@router.put("/{tag_id}", response_model=TagResponse, summary="Update a tag")
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

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a tag")
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
    
    # Only creator can delete tag
    if tag.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # First delete all post-tag relationships
    session.query(PostTag).filter(PostTag.tag_id == tag_id).delete()
    
    # Then delete the tag
    session.delete(tag)
    session.commit()
    return {"message": "Tag deleted"}

@router.post("/{tag_id}:archiveTag", response_model=TagResponse, summary="Archive a tag")
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
