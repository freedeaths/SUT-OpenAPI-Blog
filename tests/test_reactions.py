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
    auth_client = TestClient(app)
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

@pytest.fixture
def test_comment(authenticated_client, test_post, test_comment_data):
    """创建一个测试评论并返回"""
    response = authenticated_client.post(
        f"/api/posts/{test_post['id']}/comments",
        json=test_comment_data
    )
    return response.json()

@pytest.fixture
def test_reply(authenticated_client, test_post, test_comment, test_reply_data):
    """创建一个测试回复并返回"""
    response = authenticated_client.post(
        f"/api/posts/{test_post['id']}/comments/{test_comment['id']}/replies",
        json=test_reply_data
    )
    reply = response.json()
    # 添加 post_id 到返回数据中
    reply["post_id"] = test_post["id"]
    return reply

class TestPostReactions:
    def test_like_post(self, authenticated_client, test_post):
        """测试给文章点赞"""
        response = authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 200
        
        # 验证点赞计数更新
        post_info = authenticated_client.get(f"/api/posts/{test_post['id']}").json()
        assert post_info["likes_count"] == 1
        assert post_info["dislikes_count"] == 0

    def test_dislike_post(self, authenticated_client, test_post):
        """测试给文章点踩"""
        response = authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "DISLIKE"}
        )
        assert response.status_code == 200
        
        # 验证点踩计数更新
        post_info = authenticated_client.get(f"/api/posts/{test_post['id']}").json()
        assert post_info["likes_count"] == 0
        assert post_info["dislikes_count"] == 1

    def test_change_post_reaction(self, authenticated_client, test_post):
        """测试改变文章的反应（从赞变踩）"""
        # 先点赞
        authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "LIKE"}
        )
        
        # 改为点踩
        response = authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "DISLIKE"}
        )
        assert response.status_code == 200
        
        # 验证计数更新
        post_info = authenticated_client.get(f"/api/posts/{test_post['id']}").json()
        assert post_info["likes_count"] == 0
        assert post_info["dislikes_count"] == 1

class TestCommentReactions:
    def test_like_comment(self, authenticated_client, test_comment):
        """测试给评论点赞"""
        response = authenticated_client.post(
            f"/api/reactions/comment/{test_comment['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 200
        
        # 验证点赞计数更新
        comment_info = authenticated_client.get(
            f"/api/posts/{test_comment['post_id']}/comments/{test_comment['id']}"
        ).json()
        assert comment_info["likes_count"] == 1
        assert comment_info["dislikes_count"] == 0

    def test_dislike_comment(self, authenticated_client, test_comment):
        """测试给评论点踩"""
        response = authenticated_client.post(
            f"/api/reactions/comment/{test_comment['id']}",
            json={"type": "DISLIKE"}
        )
        assert response.status_code == 200
        
        # 验证点踩计数更新
        comment_info = authenticated_client.get(
            f"/api/posts/{test_comment['post_id']}/comments/{test_comment['id']}"
        ).json()
        assert comment_info["likes_count"] == 0
        assert comment_info["dislikes_count"] == 1

    def test_react_to_archived_comment(self, authenticated_client, test_comment):
        """测试对归档的评论做出反应（应该失败）"""
        # 先归档评论
        authenticated_client.post(
            f"/api/posts/{test_comment['post_id']}/comments/{test_comment['id']}:archiveComment"
        )
        
        # 尝试点赞
        response = authenticated_client.post(
            f"/api/reactions/comment/{test_comment['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 400

class TestReplyReactions:
    def test_like_reply(self, authenticated_client, test_reply):
        """测试给回复点赞"""
        response = authenticated_client.post(
            f"/api/reactions/reply/{test_reply['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 200
        
        # 验证点赞计数更新
        reply_info = authenticated_client.get(
            f"/api/posts/{test_reply['post_id']}/comments/{test_reply['comment_id']}/replies/{test_reply['id']}"
        ).json()
        assert reply_info["likes_count"] == 1
        assert reply_info["dislikes_count"] == 0

    def test_dislike_reply(self, authenticated_client, test_reply):
        """测试给回复点踩"""
        response = authenticated_client.post(
            f"/api/reactions/reply/{test_reply['id']}",
            json={"type": "DISLIKE"}
        )
        assert response.status_code == 200
        
        # 验证点踩计数更新
        reply_info = authenticated_client.get(
            f"/api/posts/{test_reply['post_id']}/comments/{test_reply['comment_id']}/replies/{test_reply['id']}"
        ).json()
        assert reply_info["likes_count"] == 0
        assert reply_info["dislikes_count"] == 1

    def test_react_to_archived_reply(self, authenticated_client, test_reply):
        """测试对归档的回复做出反应（应该失败）"""
        # 先归档回复
        authenticated_client.post(
            f"/api/posts/{test_reply['post_id']}/comments/{test_reply['comment_id']}/replies/{test_reply['id']}:archiveReply"
        )
        
        # 尝试点赞
        response = authenticated_client.post(
            f"/api/reactions/reply/{test_reply['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 400

class TestReactionValidation:
    def test_invalid_reaction_type(self, authenticated_client, test_post):
        """测试无效的反应类型"""
        response = authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "INVALID"}
        )
        assert response.status_code == 422

    def test_unauthorized_reaction(self, client, test_post):
        """测试未登录用户的反应"""
        response = client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 401

    def test_remove_reaction(self, authenticated_client, test_post):
        """测试取消反应"""
        # 先点赞
        authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "LIKE"}
        )
        
        # 再次点赞以取消
        response = authenticated_client.post(
            f"/api/reactions/post/{test_post['id']}",
            json={"type": "LIKE"}
        )
        assert response.status_code == 204
        
        # 验证计数更新
        post_info = authenticated_client.get(f"/api/posts/{test_post['id']}").json()
        assert post_info["likes_count"] == 0
        assert post_info["dislikes_count"] == 0
