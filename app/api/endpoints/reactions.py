from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.database import get_session
from app.models.user import User
from app.models.post import Post, PostStatus
from app.models.comment import Comment, CommentStatus
from app.models.reply import Reply, ReplyStatus
from app.models.reaction import Reaction, ReactionType, TargetType
from app.schemas.reaction import ReactionCreate, ReactionResponse

router = APIRouter()

def get_target_object(session: Session, target_type: TargetType, target_id: str):
    """Get target object"""
    model_map = {
        TargetType.POST: (Post, PostStatus.ACTIVE),
        TargetType.COMMENT: (Comment, CommentStatus.ACTIVE),
        TargetType.REPLY: (Reply, ReplyStatus.ACTIVE)
    }
    
    model, active_status = model_map[target_type]
    target = session.query(model).filter(model.id == target_id).first()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{target_type.value.capitalize()} not found"
        )
    
    if target.status != active_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot react to {target.status.lower()} {target_type.value}"
        )
    
    return target

@router.post("/{target_type}/{target_id}", response_model=ReactionResponse, status_code=status.HTTP_200_OK, summary="Create a reaction on a target object: post, comment, or reply")
def create_reaction(
    target_type: TargetType,
    target_id: str,
    reaction_in: ReactionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Create a reaction"""
    # Check if target object exists and is active
    target = get_target_object(session, target_type, target_id)
    
    # Check if user has already reacted
    existing_reaction = session.query(Reaction).filter(
        and_(
            Reaction.target_type == target_type,
            Reaction.target_id == target_id,
            Reaction.user_id == current_user.id
        )
    ).first()
    
    if existing_reaction:
        if existing_reaction.type == reaction_in.type:
            # If it's the same type of reaction, cancel the reaction
            session.delete(existing_reaction)
            session.commit()
            
            # Update target object's count
            if reaction_in.type == ReactionType.LIKE:
                target.likes_count -= 1
            else:
                target.dislikes_count -= 1
            session.commit()
            
            raise HTTPException(
                status_code=status.HTTP_204_NO_CONTENT,
                detail="Reaction removed"
            )
        else:
            # If it's a different type of reaction, update the reaction type
            existing_reaction.type = reaction_in.type
            session.commit()
            
            # Update target object's count
            if reaction_in.type == ReactionType.LIKE:
                target.likes_count += 1
                target.dislikes_count -= 1
            else:
                target.likes_count -= 1
                target.dislikes_count += 1
            session.commit()
            
            return existing_reaction
    
    # Create a new reaction
    reaction = Reaction(
        user_id=current_user.id,
        target_id=target_id,
        target_type=target_type,
        type=reaction_in.type
    )
    session.add(reaction)
    session.commit()
    
    # Update target object's count
    if reaction.type == ReactionType.LIKE:
        target.likes_count += 1
    else:
        target.dislikes_count += 1
    session.commit()
    
    return reaction
