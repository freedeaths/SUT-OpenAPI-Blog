import pytest
from fastapi import status
from app.core.security import verify_password
from datetime import datetime
import uuid
from app.models.user import User

@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "bio": "Test user bio"
    }

class TestUserRegistration:
    def test_successful_registration(self, client, test_user_data):
        """测试成功注册用户"""
        response = client.post("/api/users/register", json=test_user_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "id" in data
        assert "password_hash" not in data

    def test_duplicate_username(self, client, test_user_data):
        """测试重复用户名注册"""
        # 第一次注册
        client.post("/api/users/register", json=test_user_data)
        # 第二次注册相同用户名
        response = client.post("/api/users/register", json=test_user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_email(self, client, test_user_data):
        """测试无效的邮箱格式"""
        test_user_data["email"] = "invalid-email"
        response = client.post("/api/users/register", json=test_user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_password_too_short(self, client, test_user_data):
        """测试密码太短"""
        test_user_data["password"] = "short"
        response = client.post("/api/users/register", json=test_user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

class TestUserLogin:
    def test_successful_login(self, client, test_user_data):
        """测试成功登录"""
        # 先注册用户
        client.post("/api/users/register", json=test_user_data)
        # 登录
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/users/login", json=login_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_invalid_credentials(self, client, test_user_data):
        """测试无效的登录凭证"""
        # 先注册用户
        client.post("/api/users/register", json=test_user_data)
        # 使用错误的密码登录
        login_data = {
            "username": test_user_data["username"],
            "password": "wrongpassword"
        }
        response = client.post("/api/users/login", json=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

class TestUserProfile:
    def test_get_own_profile(self, client, test_user_data):
        """测试获取自己的资料"""
        # 注册并登录
        client.post("/api/users/register", json=test_user_data)
        login_response = client.post("/api/users/login", 
            json={"username": test_user_data["username"], "password": test_user_data["password"]}
        )
        token = login_response.json()["access_token"]
        
        # 获取个人资料
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]

    def test_update_profile(self, client, test_user_data):
        """测试更新用户资料"""
        # 注册并登录用户
        client.post("/api/users/register", json=test_user_data)
        login_response = client.post("/api/users/login", 
            json={"username": test_user_data["username"], "password": test_user_data["password"]}
        )
        token = login_response.json()["access_token"]
        
        # 更新个人资料
        new_bio = "Updated bio"
        response = client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"bio": new_bio}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bio"] == new_bio

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
