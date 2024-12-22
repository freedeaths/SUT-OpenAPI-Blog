import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "bio": "Test user bio"
    }

@pytest.fixture
def test_post_data():
    return {
        "title": "Test Post",
        "content": "This is a test post content"
    }

@pytest.fixture
def test_comment_data():
    return {
        "content": "This is a test comment"
    }

@pytest.fixture
def test_reply_data():
    return {
        "content": "This is a test reply"
    }

@pytest.fixture
def authenticated_client(client, test_user_data):
    """返回一个已认证的客户端"""
    # 注册用户
    client.post("/api/users/register", json=test_user_data)
    # 登录
    login_response = client.post("/api/users/login", 
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
    token = login_response.json()["access_token"]
    # 创建一个新的客户端，设置认证头
    auth_client = TestClient(client.app)
    auth_client.headers = {"Authorization": f"Bearer {token}"}
    return auth_client

@pytest.fixture
def test_post(authenticated_client, test_post_data):
    """创建一个测试文章并返回"""
    # 创建文章
    response = authenticated_client.post("/api/posts", json=test_post_data)
    post = response.json()
    # 激活文章
    authenticated_client.post(f"/api/posts/{post['id']}:activatePost")
    # 获取最新状态
    response = authenticated_client.get(f"/api/posts/{post['id']}")
    return response.json()

class TestCommentCreation:
    def test_create_comment(self, authenticated_client, test_post, test_comment_data):
        """测试在活动文章下创建评论"""
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == test_comment_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_comment_on_draft_post(self, authenticated_client, test_post, test_comment_data):
        """测试在草稿文章下创建评论（应该失败）"""
        # 将文章改为草稿状态
        authenticated_client.post(f"/api/posts/{test_post['id']}:modifyPost")
        
        # 尝试创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 403
        assert "only comment on active posts" in response.json()["detail"].lower()

    def test_create_comment_unauthorized(self, client, test_post, test_comment_data):
        """测试未认证用户创建评论"""
        response = client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 401

class TestCommentRetrieval:
    def test_get_post_comments(self, authenticated_client, test_post, test_comment_data):
        """测试获取文章的评论列表"""
        # 创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        
        # 获取评论列表
        response = authenticated_client.get(f"/api/posts/{test_post['id']}/comments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == test_comment_data["content"]

    def test_get_draft_post_comments(self, authenticated_client, test_post, test_comment_data):
        """测试获取草稿文章的评论（应该失败）"""
        # 创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        
        # 将文章改为草稿状态
        authenticated_client.post(f"/api/posts/{test_post['id']}:modifyPost")
        
        # 尝试获取评论
        response = authenticated_client.get(f"/api/posts/{test_post['id']}/comments")
        assert response.status_code == 403
        assert "only visible on active posts" in response.json()["detail"].lower()

class TestCommentUpdate:
    def test_update_own_comment(self, authenticated_client, test_post, test_comment_data):
        """测试更新自己的评论"""
        # 创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        comment_id = response.json()["id"]
        
        # 更新评论
        new_content = "Updated comment content"
        response = authenticated_client.put(
            f"/api/posts/{test_post['id']}/comments/{comment_id}",
            json={"content": new_content}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == new_content
        assert data["updated_at"] > data["created_at"]

    def test_update_others_comment(self, authenticated_client, test_post, test_comment_data):
        """测试更新他人的评论（应该失败）"""
        # 创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        comment_id = response.json()["id"]
        
        # 注册另一个用户
        other_user = {
            "username": "otheruser",
            "email": "other@example.com",
            "password": "otherpassword123",
            "bio": "Other user bio"
        }
        authenticated_client.post("/api/users/register", json=other_user)
        
        # 登录另一个用户
        login_response = authenticated_client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        other_client = TestClient(authenticated_client.app)
        other_client.headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试更新评论
        response = other_client.put(
            f"/api/posts/{test_post['id']}/comments/{comment_id}",
            json={"content": "Trying to update others comment"}
        )
        assert response.status_code == 403

class TestCommentDeletion:
    def test_delete_own_comment(self, authenticated_client, test_post, test_comment_data):
        """测试删除自己的评论"""
        # 创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        comment_id = response.json()["id"]
        
        # 删除评论
        response = authenticated_client.delete(
            f"/api/posts/{test_post['id']}/comments/{comment_id}"
        )
        assert response.status_code == 204

    def test_delete_others_comment(self, authenticated_client, test_post, test_comment_data):
        """测试删除他人的评论（应该失败）"""
        # 创建评论
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert response.status_code == 201
        comment_id = response.json()["id"]
        
        # 注册另一个用户
        other_user = {
            "username": "otheruser",
            "email": "other@example.com",
            "password": "otherpassword123",
            "bio": "Other user bio"
        }
        authenticated_client.post("/api/users/register", json=other_user)
        
        # 登录另一个用户
        login_response = authenticated_client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        other_client = TestClient(authenticated_client.app)
        other_client.headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试删除评论
        response = other_client.delete(
            f"/api/posts/{test_post['id']}/comments/{comment_id}"
        )
        assert response.status_code == 403

    def test_cascade_delete(self, authenticated_client, test_post, test_comment_data, test_reply_data):
        """测试删除评论时级联删除回复"""
        # 1. 创建评论
        comment_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments",
            json=test_comment_data
        )
        assert comment_response.status_code == 201
        comment_id = comment_response.json()["id"]
        
        # 2. 创建回复
        reply_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{comment_id}/replies",
            json=test_reply_data
        )
        assert reply_response.status_code == 201
        reply_id = reply_response.json()["id"]
        
        # 3. 删除评论
        delete_response = authenticated_client.delete(
            f"/api/posts/{test_post['id']}/comments/{comment_id}"
        )
        assert delete_response.status_code == 204
        
        # 4. 验证评论和回复都被删除
        comment_get = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{comment_id}"
        )
        assert comment_get.status_code == 404
        
        reply_get = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{comment_id}/replies/{reply_id}"
        )
        assert reply_get.status_code == 404
