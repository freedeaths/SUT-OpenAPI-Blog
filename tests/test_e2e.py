import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def user1_data():
    return {
        "username": "user1",
        "email": "user1@example.com",
        "password": "password123",
        "bio": "User 1 bio"
    }

@pytest.fixture
def user2_data():
    return {
        "username": "user2",
        "email": "user2@example.com",
        "password": "password123",
        "bio": "User 2 bio"
    }

@pytest.fixture
def post_data():
    return {
        "title": "Test Post",
        "content": "This is a test post content"
    }

@pytest.fixture
def comment_data():
    return {
        "content": "Test comment"
    }

@pytest.fixture
def reply_data():
    return {
        "content": "Test reply"
    }

@pytest.fixture
def tag_data():
    return {
        "name": "test-tag",
        "description": "Test tag description"
    }

class TestEndToEnd:
    def test_complete_flow(self, client, user1_data, user2_data, post_data, comment_data, reply_data, tag_data):
        """
        测试完整的端到端流程，包括：
        1. 用户注册和认证
        2. 文章的创建和状态转换
        3. 评论和回复的创建
        4. 标签的创建和管理
        5. 权限控制和错误处理
        
        测试步骤：
        1. 用户注册和登录
           - 注册两个用户：user1 和 user2
           - 分别获取他们的认证令牌
        
        2. 文章管理（user1）
           - 创建一篇文章（草稿状态）
           - user2 尝试查看文章（应该失败，因为是草稿）
           - user2 尝试激活文章（应该失败，因为不是作者）
           - user1 激活文章
           - user2 现在可以查看文章了
        
        3. 评论管理
           - user2 创建评论
           - user1 尝试删除 user2 的评论（应该失败）
           - user2 创建回复
           - user1 尝试删除 user2 的回复（应该失败）
        
        4. 标签管理
           - user1 创建标签
           - user1 将标签添加到文章
           - user2 尝试从文章移除标签（应该失败）
           - user1 从文章移除标签
        
        5. 清理
           - user1 删除文章（级联删除评论和回复）
           - 验证文章、评论、回复都已被删除
        """
        # 1. 用户注册和登录
        # 注册 user1
        response = client.post("/api/users/register", json=user1_data)
        assert response.status_code == 201
        
        # 登录 user1
        response = client.post("/api/users/login", 
            json={
                "username": user1_data["username"],
                "password": user1_data["password"]
            })
        assert response.status_code == 200
        user1_token = response.json()["access_token"]
        
        # 注册 user2
        response = client.post("/api/users/register", json=user2_data)
        assert response.status_code == 201
        
        # 登录 user2
        response = client.post("/api/users/login", 
            json={
                "username": user2_data["username"],
                "password": user2_data["password"]
            })
        assert response.status_code == 200
        user2_token = response.json()["access_token"]
        
        # 2. 文章管理
        # user1 创建文章
        headers_user1 = {"Authorization": f"Bearer {user1_token}"}
        response = client.post("/api/posts", json=post_data, headers=headers_user1)
        assert response.status_code == 201
        post_id = response.json()["id"]
        
        # user2 尝试查看草稿文章（应该失败）
        headers_user2 = {"Authorization": f"Bearer {user2_token}"}
        response = client.get(f"/api/posts/{post_id}", headers=headers_user2)
        assert response.status_code == 403
        
        # user2 尝试激活文章（应该失败）
        response = client.post(f"/api/posts/{post_id}:activatePost", headers=headers_user2)
        assert response.status_code == 403
        
        # user1 激活文章
        response = client.post(f"/api/posts/{post_id}:activatePost", headers=headers_user1)
        assert response.status_code == 200
        
        # user2 现在可以查看文章了
        response = client.get(f"/api/posts/{post_id}", headers=headers_user2)
        assert response.status_code == 200
        
        # 3. 评论管理
        # user2 创建评论
        response = client.post(
            f"/api/posts/{post_id}/comments",
            json=comment_data,
            headers=headers_user2
        )
        assert response.status_code == 201
        comment_id = response.json()["id"]
        
        # user1 尝试删除 user2 的评论（应该失败）
        response = client.delete(
            f"/api/posts/{post_id}/comments/{comment_id}",
            headers=headers_user1
        )
        assert response.status_code == 403
        
        # user2 创建回复
        response = client.post(
            f"/api/posts/{post_id}/comments/{comment_id}/replies",
            json=reply_data,
            headers=headers_user2
        )
        assert response.status_code == 201
        reply_id = response.json()["id"]
        
        # user1 尝试删除 user2 的回复（应该失败）
        response = client.delete(
            f"/api/posts/{post_id}/comments/{comment_id}/replies/{reply_id}",
            headers=headers_user1
        )
        assert response.status_code == 403
        
        # 4. 标签管理
        # user1 创建标签
        response = client.post("/api/tags/", json=tag_data, headers=headers_user1)
        assert response.status_code == 201
        tag_id = response.json()["id"]
        
        # user1 将标签添加到文章
        response = client.post(
            f"/api/tags/posts/{post_id}/tags/{tag_id}",
            headers=headers_user1
        )
        assert response.status_code == 204
        
        # user2 尝试从文章移除标签（应该失败）
        response = client.delete(
            f"/api/tags/posts/{post_id}/tags/{tag_id}",
            headers=headers_user2
        )
        assert response.status_code == 403
        
        # user1 从文章移除标签
        response = client.delete(
            f"/api/tags/posts/{post_id}/tags/{tag_id}",
            headers=headers_user1
        )
        assert response.status_code == 204
        
        # 5. 清理
        # user1 删除文章（级联删除评论和回复）
        response = client.delete(f"/api/posts/{post_id}", headers=headers_user1)
        assert response.status_code == 204
        
        # 验证文章被删除
        response = client.get(f"/api/posts/{post_id}", headers=headers_user1)
        assert response.status_code == 404
        
        # 验证评论被删除
        response = client.get(f"/api/posts/{post_id}/comments/{comment_id}", headers=headers_user1)
        assert response.status_code == 404
        
        # 验证回复被删除
        response = client.get(
            f"/api/posts/{post_id}/comments/{comment_id}/replies/{reply_id}",
            headers=headers_user1
        )
        assert response.status_code == 404
