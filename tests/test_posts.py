import pytest
from fastapi.testclient import TestClient
from app.models.post import PostStatus

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
        "content": "Test comment"
    }

@pytest.fixture
def test_reply_data():
    return {
        "content": "Test reply"
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

class TestPostCreation:
    def test_create_post(self, authenticated_client, test_post_data):
        """测试创建文章"""
        response = authenticated_client.post("/api/posts", json=test_post_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == test_post_data["title"]
        assert data["content"] == test_post_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert "author_id" in data
        assert "status" in data
        assert data["status"] == PostStatus.DRAFT

    def test_create_post_unauthorized(self, client, test_post_data):
        """测试未认证用户创建文章"""
        response = client.post("/api/posts", json=test_post_data)
        assert response.status_code == 401

class TestPostRetrieval:
    def test_get_own_draft_post(self, authenticated_client, test_post_data):
        """测试获取自己的草稿文章"""
        # 创建一篇文章（默认为草稿状态）
        create_response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = create_response.json()["id"]
        
        # 获取文章
        response = authenticated_client.get(f"/api/posts/{post_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == test_post_data["title"]
        assert data["content"] == test_post_data["content"]
        assert data["status"] == PostStatus.DRAFT

    def test_get_others_draft_post(self, client, authenticated_client, test_post_data):
        """测试获取他人的草稿文章（应该失败）"""
        # 创建一篇文章（默认为草稿状态）
        create_response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = create_response.json()["id"]
        
        # 使用未认证的客户端尝试获取文章
        response = client.get(f"/api/posts/{post_id}")
        assert response.status_code == 401

        # 注册另一个用户
        other_user = {
            "username": "otheruser",
            "email": "other@example.com",
            "password": "otherpassword123",
            "bio": "Other user bio"
        }
        client.post("/api/users/register", json=other_user)
        
        # 登录另一个用户
        login_response = client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        client.headers = {"Authorization": f"Bearer {token}"}
        
        # 使用另一个用户尝试获取文章
        response = client.get(f"/api/posts/{post_id}")
        assert response.status_code == 403

    def test_list_posts(self, authenticated_client, test_post_data):
        """测试获取文章列表"""
        # 创建多篇文章
        post1 = authenticated_client.post("/api/posts", json=test_post_data).json()
        post2 = authenticated_client.post("/api/posts", json={
            "title": "Second Post",
            "content": "Content of second post"
        }).json()

        # 将第一篇文章设为 ACTIVE
        authenticated_client.post(f"/api/posts/{post1['id']}:activatePost")

        # 获取所有文章（作者可以看到自己的所有文章）
        response = authenticated_client.get("/api/posts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
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
        
        # 其他用户只能看到 ACTIVE 状态的文章
        response = other_client.get("/api/posts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == PostStatus.ACTIVE

class TestPostStatusTransition:
    def test_activate_post(self, authenticated_client, test_post_data):
        """测试激活文章"""
        # 创建文章
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        
        # 激活文章
        response = authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        assert response.status_code == 200
        assert response.json()["status"] == PostStatus.ACTIVE

    def test_modify_post(self, authenticated_client, test_post_data):
        """测试将文章改为修改中状态"""
        # 创建并激活文章
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        
        # 将文章改为修改中状态
        response = authenticated_client.post(f"/api/posts/{post_id}:modifyPost")
        assert response.status_code == 200
        assert response.json()["status"] == PostStatus.MODIFYING

    def test_archive_post(self, authenticated_client, test_post_data):
        """测试归档文章"""
        # 创建并激活文章
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        
        # 归档文章
        response = authenticated_client.post(f"/api/posts/{post_id}:archivePost")
        assert response.status_code == 200
        assert response.json()["status"] == PostStatus.ARCHIVED

    def test_activate_archived_post(self, authenticated_client, test_post_data):
        """测试激活已归档的文章（应该失败）"""
        # 创建并归档文章
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        authenticated_client.post(f"/api/posts/{post_id}:archivePost")
        
        # 尝试激活已归档的文章
        response = authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        assert response.status_code == 400
        assert "cannot activate an archived post" in response.json()["detail"].lower()

    def test_modify_archived_post(self, authenticated_client, test_post_data):
        """测试修改已归档的文章（应该失败）"""
        # 创建并归档文章
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        authenticated_client.post(f"/api/posts/{post_id}:archivePost")
        
        # 尝试将已归档的文章改为修改中状态
        response = authenticated_client.post(f"/api/posts/{post_id}:modifyPost")
        assert response.status_code == 400
        assert "cannot modify an archived post" in response.json()["detail"].lower()

class TestPostUpdate:
    def test_update_post_in_modifying_status(self, authenticated_client, test_post_data):
        """测试在修改中状态更新文章"""
        # 创建文章并改为修改中状态
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        authenticated_client.post(f"/api/posts/{post_id}:modifyPost")
        
        # 更新文章
        new_data = {
            "title": "Updated Title",
            "content": "Updated content"
        }
        response = authenticated_client.put(f"/api/posts/{post_id}", json=new_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_data["title"]
        assert data["content"] == new_data["content"]
        assert data["status"] == PostStatus.MODIFYING

    def test_update_post_in_active_status(self, authenticated_client, test_post_data):
        """测试在活跃状态更新文章（应该失败）"""
        # 创建并激活文章
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        
        # 尝试更新文章
        new_data = {
            "title": "Updated Title",
            "content": "Updated content"
        }
        response = authenticated_client.put(f"/api/posts/{post_id}", json=new_data)
        assert response.status_code == 400
        assert "can only update post in modifying status" in response.json()["detail"].lower()

    def test_update_others_post(self, client, authenticated_client, test_post_data):
        """测试更新他人的文章（应该失败）"""
        # 创建文章并改为修改中状态
        response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = response.json()["id"]
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        authenticated_client.post(f"/api/posts/{post_id}:modifyPost")
        
        # 注册另一个用户
        other_user = {
            "username": "otheruser",
            "email": "other@example.com",
            "password": "otherpassword123",
            "bio": "Other user bio"
        }
        client.post("/api/users/register", json=other_user)
        
        # 登录另一个用户
        login_response = client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        other_client = TestClient(client.app)
        other_client.headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试更新文章
        new_data = {
            "title": "Updated Title",
            "content": "Updated content"
        }
        response = other_client.put(f"/api/posts/{post_id}", json=new_data)
        assert response.status_code == 403

class TestPostDeletion:
    def test_delete_own_post(self, authenticated_client, test_post_data):
        """测试删除自己的文章"""
        # 创建文章
        create_response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = create_response.json()["id"]
        
        # 删除文章
        response = authenticated_client.delete(f"/api/posts/{post_id}")
        assert response.status_code == 204
        
        # 确认文章已被删除
        response = authenticated_client.get(f"/api/posts/{post_id}")
        assert response.status_code == 404

    def test_delete_others_post(self, client, authenticated_client, test_post_data):
        """测试删除他人的文章（应该失败）"""
        # 创建文章
        create_response = authenticated_client.post("/api/posts", json=test_post_data)
        post_id = create_response.json()["id"]
        
        # 注册另一个用户
        other_user = {
            "username": "otheruser",
            "email": "other@example.com",
            "password": "otherpassword123",
            "bio": "Other user bio"
        }
        client.post("/api/users/register", json=other_user)
        
        # 登录另一个用户
        login_response = client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        client.headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试删除文章
        response = client.delete(f"/api/posts/{post_id}")
        assert response.status_code == 403

    def test_cascade_delete(self, authenticated_client, test_post_data, test_comment_data, test_reply_data):
        """测试删除文章时级联删除评论和回复"""
        # 1. 创建文章
        post_response = authenticated_client.post("/api/posts", json=test_post_data)
        assert post_response.status_code == 201
        post_id = post_response.json()["id"]
        
        # 激活文章，以便可以添加评论
        authenticated_client.post(f"/api/posts/{post_id}:activatePost")
        
        # 2. 创建评论
        comment_response = authenticated_client.post(
            f"/api/posts/{post_id}/comments",
            json=test_comment_data
        )
        assert comment_response.status_code == 201
        comment_id = comment_response.json()["id"]
        
        # 3. 创建回复
        reply_response = authenticated_client.post(
            f"/api/posts/{post_id}/comments/{comment_id}/replies",
            json=test_reply_data
        )
        assert reply_response.status_code == 201
        reply_id = reply_response.json()["id"]
        
        # 4. 删除文章
        delete_response = authenticated_client.delete(f"/api/posts/{post_id}")
        assert delete_response.status_code == 204
        
        # 5. 验证文章、评论和回复都被删除
        post_get = authenticated_client.get(f"/api/posts/{post_id}")
        assert post_get.status_code == 404
        
        comment_get = authenticated_client.get(f"/api/posts/{post_id}/comments/{comment_id}")
        assert comment_get.status_code == 404
        
        reply_get = authenticated_client.get(f"/api/posts/{post_id}/comments/{comment_id}/replies/{reply_id}")
        assert reply_get.status_code == 404
