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
        "password": "testpassword123"
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
def test_tag_data():
    return {
        "name": "test-tag",
        "description": "This is a test tag"
    }

class TestTagCreation:
    def test_create_tag(self, authenticated_client, test_tag_data):
        """测试创建标签"""
        response = authenticated_client.post("/api/tags", json=test_tag_data)
        print(f"Response: {response.json()}")
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == test_tag_data["name"]
        assert data["description"] == test_tag_data["description"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["usage_count"] == 0

    def test_create_duplicate_tag(self, authenticated_client, test_tag_data):
        """测试创建重复标签名（应该失败）"""
        # 先创建一个标签
        authenticated_client.post("/api/tags", json=test_tag_data)
        # 尝试创建同名标签
        response = authenticated_client.post("/api/tags", json=test_tag_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

class TestTagUpdate:
    def test_update_tag_description(self, authenticated_client, test_tag_data):
        """测试更新标签描述"""
        # 先创建标签
        create_response = authenticated_client.post("/api/tags", json=test_tag_data)
        tag_id = create_response.json()["id"]
        
        # 更新描述
        update_data = {"description": "Updated description"}
        response = authenticated_client.put(f"/api/tags/{tag_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == update_data["description"]
        assert data["name"] == test_tag_data["name"]

    def test_update_tag_name(self, authenticated_client, test_tag_data):
        """测试更新标签名称"""
        # 先创建标签
        create_response = authenticated_client.post("/api/tags", json=test_tag_data)
        tag_id = create_response.json()["id"]
        
        # 更新名称
        update_data = {"name": "new-tag-name"}
        response = authenticated_client.put(f"/api/tags/{tag_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_update_tag_to_duplicate_name(self, authenticated_client, test_tag_data):
        """测试更新标签为已存在的名称（应该失败）"""
        # 创建第一个标签
        authenticated_client.post("/api/tags", json=test_tag_data)
        
        # 创建第二个标签
        second_tag_data = {
            "name": "second-tag",
            "description": "Second test tag"
        }
        second_tag_response = authenticated_client.post("/api/tags", json=second_tag_data)
        second_tag_id = second_tag_response.json()["id"]
        
        # 尝试将第二个标签更新为第一个标签的名称
        update_data = {"name": test_tag_data["name"]}
        response = authenticated_client.put(f"/api/tags/{second_tag_id}", json=update_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

class TestTagDeletion:
    def test_delete_unused_tag(self, authenticated_client, test_tag_data):
        """测试删除未使用的标签"""
        # 创建标签
        create_response = authenticated_client.post("/api/tags", json=test_tag_data)
        tag_id = create_response.json()["id"]
        
        # 删除标签
        response = authenticated_client.delete(f"/api/tags/{tag_id}")
        assert response.status_code == 204

class TestPostTagOperations:
    def test_add_tag_to_post(self, authenticated_client, test_tag_data):
        """测试给文章添加标签"""
        # 创建标签
        tag_response = authenticated_client.post("/api/tags", json=test_tag_data)
        tag_id = tag_response.json()["id"]
        
        # 创建文章
        post_data = {
            "title": "Test Post",
            "content": "Test content"
        }
        post_response = authenticated_client.post("/api/posts", json=post_data)
        post_id = post_response.json()["id"]
        
        # 添加标签
        response = authenticated_client.post(
            f"/api/tags/posts/{post_id}/tags/{tag_id}"
        )
        assert response.status_code == 204
        
        # 验证标签计数更新
        tag_info = authenticated_client.get(f"/api/tags/{tag_id}").json()
        assert tag_info["usage_count"] == 1

    def test_remove_tag_from_post(self, authenticated_client, test_tag_data):
        """测试从文章移除标签"""
        # 创建标签
        tag_response = authenticated_client.post("/api/tags", json=test_tag_data)
        tag_id = tag_response.json()["id"]
        
        # 创建文章
        post_data = {
            "title": "Test Post",
            "content": "Test content"
        }
        post_response = authenticated_client.post("/api/posts", json=post_data)
        post_id = post_response.json()["id"]
        
        # 添加标签
        authenticated_client.post(
            f"/api/tags/posts/{post_id}/tags/{tag_id}"
        )
        
        # 移除标签
        response = authenticated_client.delete(
            f"/api/tags/posts/{post_id}/tags/{tag_id}"
        )
        assert response.status_code == 204
        
        # 验证标签计数更新
        tag_info = authenticated_client.get(f"/api/tags/{tag_id}").json()
        assert tag_info["usage_count"] == 0

    def test_list_post_tags(self, authenticated_client, test_tag_data):
        """测试列出文章的标签"""
        # 创建标签
        tag_response = authenticated_client.post("/api/tags", json=test_tag_data)
        tag_id = tag_response.json()["id"]
        
        # 创建文章
        post_data = {
            "title": "Test Post",
            "content": "Test content"
        }
        post_response = authenticated_client.post("/api/posts", json=post_data)
        post_id = post_response.json()["id"]
        
        # 添加标签
        authenticated_client.post(
            f"/api/tags/posts/{post_id}/tags/{tag_id}"
        )
        
        # 获取文章的标签
        response = authenticated_client.get(f"/api/tags/posts/{post_id}/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == tag_id
        assert data[0]["name"] == test_tag_data["name"]
