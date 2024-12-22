from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.db.database import get_session
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, UserUpdate, UserLogin
from datetime import timezone

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    session: Annotated[Session, Depends(get_session)]
) -> User:
    """Create a new user"""
    # Check if username already exists
    result = session.execute(
        select(User).where(User.username == user_in.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )
    
    # Check if email already exists
    result = session.execute(
        select(User).where(User.email == user_in.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
        bio=user_in.bio
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(
    user_in: UserLogin,
    session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Login a user"""
    # Verify user
    result = session.execute(
        select(User).where(User.username == user_in.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    user.last_login = datetime.now(timezone.utc)
    session.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get the current user"""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)]
) -> User:
    """Update the current user"""
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    session.commit()
    session.refresh(current_user)
    return current_user
