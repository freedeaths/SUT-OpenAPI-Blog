import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_session, SQLITE_TEST_DB

# 设置测试环境
os.environ["APP_ENV"] = "test"

# 测试数据库配置
test_engine = create_engine(SQLITE_TEST_DB, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=test_engine)

@pytest.fixture(autouse=True)
def clean_db():
    """清理并重建测试数据库"""
    with test_engine.connect() as conn:
        # 先删除所有表（按依赖关系顺序）
        conn.execute(text("DROP TABLE IF EXISTS post_tags"))
        conn.execute(text("DROP TABLE IF EXISTS tags"))
        conn.execute(text("DROP TABLE IF EXISTS reactions"))
        conn.execute(text("DROP TABLE IF EXISTS replies"))
        conn.execute(text("DROP TABLE IF EXISTS comments"))
        conn.execute(text("DROP TABLE IF EXISTS posts"))
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.commit()

    # 创建所有表
    Base.metadata.create_all(bind=test_engine)
    yield
    
    # 测试结束后清理
    with test_engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS post_tags"))
        conn.execute(text("DROP TABLE IF EXISTS tags"))
        conn.execute(text("DROP TABLE IF EXISTS reactions"))
        conn.execute(text("DROP TABLE IF EXISTS replies"))
        conn.execute(text("DROP TABLE IF EXISTS comments"))
        conn.execute(text("DROP TABLE IF EXISTS posts"))
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.commit()

@pytest.fixture
def client(clean_db):
    """创建测试客户端"""
    # 创建测试会话
    test_session = TestSessionLocal()
    
    # 覆盖依赖
    def override_get_session():
        try:
            yield test_session
        finally:
            test_session.close()
    
    app.dependency_overrides[get_session] = override_get_session
    
    # 返回测试客户端
    client = TestClient(app)
    yield client
    
    # 测试结束后清理
    test_session.close()
    app.dependency_overrides.clear()
