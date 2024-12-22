from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from typing import Optional
from functools import lru_cache

# 数据库配置
SQLITE_DEV_DB = "sqlite:///./dev.db"
SQLITE_TEST_DB = "sqlite:///./test.db"
SQLITE_PROD_DB = "sqlite:///./prod.db"

Base = declarative_base()

@lru_cache()
def get_engine():
    """获取数据库引擎"""
    env = os.getenv("APP_ENV", "development")
    if env == "test":
        DATABASE_URL = SQLITE_TEST_DB
    elif env == "production":
        DATABASE_URL = os.getenv("DATABASE_URL", SQLITE_PROD_DB)
    else:  # development
        DATABASE_URL = SQLITE_DEV_DB
    
    return create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

def get_session_maker():
    """获取会话工厂"""
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

def get_session():
    """获取数据库会话"""
    SessionLocal = get_session_maker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def create_tables(db_engine: Optional[object] = None):
    """创建所有表
    
    Args:
        db_engine: 可选的数据库引擎，如果不提供则使用默认引擎
    """
    engine = db_engine or get_engine()
    Base.metadata.create_all(bind=engine)
