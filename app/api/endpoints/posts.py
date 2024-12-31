from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_session
from app.models.post import Post, PostStatus
from app.models.user import User
from app.models.tag import Tag, TagStatus
from app.models.post_tag import PostTag
from app.models.comment import Comment, CommentStatus
from app.models.reaction import Reaction, ReactionType, TargetType
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.core.security import get_current_user, get_optional_current_user
from datetime import datetime, UTC
from typing import List, Optional

router = APIRouter()

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED, summary="Create a new post")
def create_post(
    post: PostCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new post"""
    # Create post
    new_post = Post(
        title=post.title,
        content=post.content,
        author_id=current_user.id,
        status=PostStatus.DRAFT
    )
    session.add(new_post)
    session.flush()  # Flush to get the post ID

    # Add tags if provided
    if post.tag_ids:
        # Check if all tags exist and are active
        tags = session.query(Tag).filter(
            Tag.id.in_(post.tag_ids),
            Tag.status == TagStatus.ACTIVE
        ).all()
        if len(tags) != len(post.tag_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some tags not found or not active"
            )
        
        # Add tags to post
        for tag_id in post.tag_ids:
            post_tag = PostTag(post_id=new_post.id, tag_id=tag_id)
            session.add(post_tag)
            # Update tag usage count
            tag = next(tag for tag in tags if tag.id == tag_id)
            tag.usage_count += 1

    session.commit()
    
    # Return post with tags
    return {
        "id": new_post.id,
        "title": new_post.title,
        "content": new_post.content,
        "author_id": new_post.author_id,
        "status": new_post.status,
        "created_at": new_post.created_at,
        "updated_at": new_post.updated_at,
        "likes_count": new_post.likes_count,
        "dislikes_count": 0,
        "views_count": 0,
        "comments_count": 0,
        "tag_ids": post.tag_ids or []
    }

@router.get("", response_model=List[PostResponse], summary="List all posts")
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
    
    posts = query.all()
    
    # Get post tags
    post_tags = {}
    for post in posts:
        tags = session.query(Tag).join(
            PostTag, PostTag.tag_id == Tag.id
        ).filter(
            PostTag.post_id == post.id,
            Tag.status == TagStatus.ACTIVE
        ).all()
        post_tags[post.id] = [tag.id for tag in tags]
    
    # Get comments count
    post_comments_count = {}
    for post in posts:
        comments_count = session.query(Comment).filter(
            Comment.post_id == post.id,
            Comment.status == CommentStatus.ACTIVE
        ).count()
        post_comments_count[post.id] = comments_count
    
    # Get dislikes count
    post_dislikes_count = {}
    for post in posts:
        dislikes_count = session.query(Reaction).filter(
            Reaction.target_id == post.id,
            Reaction.target_type == TargetType.POST,
            Reaction.type == ReactionType.DISLIKE
        ).count()
        post_dislikes_count[post.id] = dislikes_count
    
    # Get likes count
    post_likes_count = {}
    for post in posts:
        likes_count = session.query(Reaction).filter(
            Reaction.target_id == post.id,
            Reaction.target_type == TargetType.POST,
            Reaction.type == ReactionType.LIKE
        ).count()
        post_likes_count[post.id] = likes_count
    
    # Return posts with tags
    return [{
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "status": post.status,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "likes_count": post_likes_count.get(post.id, 0),
        "dislikes_count": post_dislikes_count.get(post.id, 0),
        "views_count": post.views_count,
        "comments_count": post_comments_count.get(post.id, 0),
        "tag_ids": post_tags.get(post.id, [])
    } for post in posts]

@router.get("/{post_id}", response_model=PostResponse, summary="Get a specific post")
def get_post(
    post_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user)
):
    """Get a specific post"""
    # Get post with tag information
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check if user has permission to view draft post
    if post.status == PostStatus.DRAFT:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        if current_user.id != post.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    # Get post tags
    tags = session.query(Tag).join(
        PostTag, PostTag.tag_id == Tag.id
    ).filter(
        PostTag.post_id == post_id,
        Tag.status == TagStatus.ACTIVE
    ).all()
    
    # Get comments count
    comments_count = session.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.status == CommentStatus.ACTIVE
    ).count()
    
    # Get dislikes count
    dislikes_count = session.query(Reaction).filter(
        Reaction.target_id == post_id,
        Reaction.target_type == TargetType.POST,
        Reaction.type == ReactionType.DISLIKE
    ).count()
    
    # Get likes count
    likes_count = session.query(Reaction).filter(
        Reaction.target_id == post_id,
        Reaction.target_type == TargetType.POST,
        Reaction.type == ReactionType.LIKE
    ).count()
    
    # Update post counts
    post.likes_count = likes_count
    post.dislikes_count = dislikes_count
    post.comments_count = comments_count

    session.commit()

    # Return post with tags
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "status": post.status,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "likes_count": likes_count,
        "dislikes_count": dislikes_count,
        "views_count": post.views_count,
        "comments_count": comments_count,
        "tag_ids": [tag.id for tag in tags]
    }

@router.put("/{post_id}", response_model=PostResponse, summary="Update a post, including title, content and tags of a post")
def update_post(
    post_id: str,
    post_update: PostUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a post"""
    # Check if post exists
    post = session.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if user has permission
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check post status
    if post.status not in [PostStatus.MODIFYING, PostStatus.DRAFT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update post in MODIFYING or DRAFT status"
        )
    
    # Update post fields if provided
    if post_update.title is not None:
        post.title = post_update.title
    if post_update.content is not None:
        post.content = post_update.content
    if post_update.status is not None:
        post.status = post_update.status
    
    # Update tags if provided
    if post_update.tag_ids is not None:
        # Check if all new tags exist and are active
        new_tags = session.query(Tag).filter(
            Tag.id.in_(post_update.tag_ids),
            Tag.status == TagStatus.ACTIVE
        ).all()
        if len(new_tags) != len(post_update.tag_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some tags not found or not active"
            )

        # Get current tags
        current_tags = session.query(Tag).join(
            PostTag, PostTag.tag_id == Tag.id
        ).filter(
            PostTag.post_id == post_id
        ).all()

        # Remove old tags
        session.query(PostTag).filter(PostTag.post_id == post_id).delete()

        # Update usage count for removed tags
        for tag in current_tags:
            if tag.id not in post_update.tag_ids and tag.usage_count > 0:
                tag.usage_count -= 1

        # Add new tags
        for tag_id in post_update.tag_ids:
            post_tag = PostTag(post_id=post_id, tag_id=tag_id)
            session.add(post_tag)
            # Update tag usage count
            tag = next(tag for tag in new_tags if tag.id == tag_id)
            if tag.id not in [t.id for t in current_tags]:
                tag.usage_count += 1

    post.updated_at = datetime.now(UTC)
    session.commit()
    
    # Get comments count
    comments_count = session.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.status == CommentStatus.ACTIVE
    ).count()
    
    # Get dislikes count
    dislikes_count = session.query(Reaction).filter(
        Reaction.target_id == post_id,
        Reaction.target_type == TargetType.POST,
        Reaction.type == ReactionType.DISLIKE
    ).count()
    
    # Get likes count
    likes_count = session.query(Reaction).filter(
        Reaction.target_id == post_id,
        Reaction.target_type == TargetType.POST,
        Reaction.type == ReactionType.LIKE
    ).count()
    
    # Update post counts
    post.likes_count = likes_count
    post.dislikes_count = dislikes_count
    post.comments_count = comments_count

    session.commit()

    # Get updated post with tags
    tags = session.query(Tag).join(
        PostTag, PostTag.tag_id == Tag.id
    ).filter(
        PostTag.post_id == post_id,
        Tag.status == TagStatus.ACTIVE
    ).all()
    
    # Return post with tags
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "status": post.status,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "likes_count": likes_count,
        "dislikes_count": dislikes_count,
        "views_count": post.views_count,
        "comments_count": comments_count,
        "tag_ids": [tag.id for tag in tags]
    }

@router.post("/{post_id}:activatePost", response_model=PostResponse, summary="Activate a post")
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
    
    # # Check current status
    # if post.status == PostStatus.ARCHIVED:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Cannot activate an archived post"
    #     )
    
    post.status = PostStatus.ACTIVE
    post.updated_at = datetime.now(UTC)
    
    session.commit()
    session.refresh(post)
    return post

@router.post("/{post_id}:modifyPost", response_model=PostResponse, summary="Put a post in modifying status")
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

@router.post("/{post_id}:archivePost", response_model=PostResponse, summary="Archive a post")
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

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a post and all its comments and replies")
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
    
    # 3. Delete post tags
    session.query(PostTag).filter(PostTag.post_id == post_id).delete(synchronize_session=False)
    
    # 4. Delete post
    session.delete(post)
    session.commit()
    return None
