import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.reply import ReplyStatus
from app.models.user import User

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }

@pytest.fixture
def test_post_data():
    return {
        "title": "Test Post",
        "content": "This is a test post content",
        "status": "ACTIVE"
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
    register_response = client.post("/api/users/register", json=test_user_data)
    print("Register response:", register_response.json())
    
    # 登录
    login_response = client.post("/api/users/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
    print("Login response:", login_response.json())
    token = login_response.json()["access_token"]
    
    # 创建一个新的客户端，设置认证头
    auth_client = TestClient(client.app)
    auth_client.headers = {"Authorization": f"Bearer {token}"}
    print("Setting auth headers:", auth_client.headers)
    
    # 验证认证是否成功
    me_response = auth_client.get("/api/users/me")
    print("Me response:", me_response.json())
    assert me_response.status_code == 200
    
    return auth_client

@pytest.fixture
def test_post(authenticated_client, test_post_data):
    """创建一个测试文章并返回"""
    # 创建文章
    response = authenticated_client.post("/api/posts", json=test_post_data)
    print("Create post response:", response.json())
    assert response.status_code == 201  # 确保文章创建成功
    post = response.json()
    
    # 激活文章
    activate_response = authenticated_client.post(
        f"/api/posts/{post['id']}:activatePost"
    )
    print("Activate post response:", activate_response.json())
    assert activate_response.status_code == 200  # 确保文章激活成功
    
    return activate_response.json()

@pytest.fixture
def test_comment(authenticated_client, test_post, test_comment_data):
    """创建一个测试评论并返回"""
    print("Creating comment with auth headers:", authenticated_client.headers)
    # 创建评论
    response = authenticated_client.post(
        f"/api/posts/{test_post['id']}/comments",
        json=test_comment_data
    )
    print("Create comment response:", response.json())
    assert response.status_code == 201  # 确保评论创建成功
    comment = response.json()
    
    # 激活评论
    activate_response = authenticated_client.post(
        f"/api/posts/{test_post['id']}/comments/{comment['id']}:activateComment"
    )
    print("Activate comment response:", activate_response.json())
    assert activate_response.status_code == 200  # 确保评论激活成功
    
    return activate_response.json()

class TestReplyCreation:
    def test_create_reply(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试在活动评论下创建回复"""
        print(f"test_post: {test_post}")  # 打印文章信息
        print(f"test_comment: {test_comment}")  # 打印评论信息
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == test_reply_data["content"]
        assert "id" in data
        assert "created_at" in data
        assert "author_id" in data
        assert data["comment_id"] == test_comment["id"]
        assert data["status"] == "ACTIVE"

    def test_create_reply_on_archived_comment(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试在归档评论下创建回复（应该失败）"""
        # 先归档评论
        authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}:archiveComment"
        )
        
        # 尝试创建回复
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        assert response.status_code == 403

    def test_create_empty_reply(self, authenticated_client, test_post, test_comment):
        """测试创建空内容回复（应该失败）"""
        response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json={"content": ""}
        )
        assert response.status_code == 422

    def test_create_reply_unauthorized(self, client, test_post, test_comment, test_reply_data):
        """测试未登录用户创建回复"""
        response = client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        assert response.status_code == 401

class TestReplyRetrieval:
    def test_list_replies(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试获取评论的回复列表"""
        # 创建回复
        authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        
        # 获取回复列表
        response = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == test_reply_data["content"]
        assert data[0]["status"] == "ACTIVE"

    def test_list_replies_with_archived(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试获取包含归档回复的列表（不应显示归档回复）"""
        # 创建两个回复
        for _ in range(2):
            authenticated_client.post(
                f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
                json=test_reply_data
            )
        
        # 获取回复列表，确认有两个回复
        response = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies"
        )
        assert len(response.json()) == 2
        
        # 归档第一个回复
        first_reply_id = response.json()[0]["id"]
        authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{first_reply_id}:archiveReply"
        )
        
        # 再次获取列表，应该只有一个回复
        response = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies"
        )
        assert len(response.json()) == 1

class TestReplyUpdate:
    def test_update_own_reply(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试更新自己的回复"""
        # 创建回复
        create_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        reply_id = create_response.json()["id"]
        
        # 更新回复
        new_content = {"content": "Updated reply content"}
        response = authenticated_client.put(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}",
            json=new_content
        )
        assert response.status_code == 200
        assert response.json()["content"] == new_content["content"]

    def test_update_others_reply(self, client, authenticated_client, test_post, test_comment, test_reply_data):
        """测试更新他人的回复（应该失败）"""
        # 创建回复
        create_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        reply_id = create_response.json()["id"]
        
        # 创建另一个用户
        other_user = {
            "username": "otheruser",
            "email": "other@example.com",
            "password": "password123"
        }
        client.post("/api/users/register", json=other_user)
        login_response = client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        
        # 尝试更新回复
        response = client.put(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Trying to update others reply"}
        )
        assert response.status_code == 403

class TestReplyDeletion:
    def test_delete_own_reply(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试删除自己的回复"""
        # 创建回复
        create_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        reply_id = create_response.json()["id"]
        
        # 删除回复
        response = authenticated_client.delete(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}"
        )
        assert response.status_code == 204
        
        # 确认回复已被归档
        response = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies"
        )
        replies = response.json()
        assert len(replies) == 0

    def test_delete_others_reply(self, client, authenticated_client, test_post, test_comment, test_reply_data):
        """测试删除他人的回复（应该失败）"""
        # 创建回复
        create_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        reply_id = create_response.json()["id"]
        
        # 创建另一个用户
        other_user = {
            "username": "otheruser2",
            "email": "other2@example.com",
            "password": "password123"
        }
        client.post("/api/users/register", json=other_user)
        login_response = client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        token = login_response.json()["access_token"]
        
        # 尝试删除回复
        response = client.delete(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

class TestReplyStatus:
    def test_archive_and_activate_reply(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试归档和激活回复"""
        # 创建回复
        create_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        reply_id = create_response.json()["id"]
        
        # 归档回复
        archive_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}:archiveReply"
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "ARCHIVED"
        
        # 确认回复不在列表中
        list_response = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies"
        )
        assert len(list_response.json()) == 0
        
        # 激活回复
        activate_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}:activateReply"
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["status"] == "ACTIVE"
        
        # 确认回复重新出现在列表中
        list_response = authenticated_client.get(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies"
        )
        assert len(list_response.json()) == 1

    def test_archive_others_reply(self, authenticated_client, test_post, test_comment, test_reply_data):
        """测试归档他人的回复（应该失败）"""
        # 创建回复
        create_response = authenticated_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
            json=test_reply_data
        )
        reply_id = create_response.json()["id"]
        
        # 创建另一个用户的客户端
        other_user = {
            "username": "otheruser3",
            "email": "other3@example.com",
            "password": "password123"
        }
        # 注册新用户
        register_response = authenticated_client.post("/api/users/register", json=other_user)
        assert register_response.status_code == 201
        
        # 登录新用户
        login_response = authenticated_client.post("/api/users/login", 
            json={
                "username": other_user["username"],
                "password": other_user["password"]
            })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 创建一个新的已认证客户端
        other_client = TestClient(authenticated_client.app)
        other_client.headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试归档回复
        response = other_client.post(
            f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies/{reply_id}:archiveReply"
        )
        assert response.status_code == 403
