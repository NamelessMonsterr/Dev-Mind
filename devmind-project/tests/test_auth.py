"""
Tests for authentication system.

Covers registration, login, token management, RBAC, and security features.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from devmind.api.app import create_app
from devmind.core.database import Base, get_db
from devmind.auth.models import User, UserRole
from devmind.auth import security

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_auth.db"

# Test engine and session
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    """Create test client with test database."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create app
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    # Test client
    client = TestClient(app)
    
    yield client
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user_data():
    """Test user registration data."""
    return {
        "email": "test@devmind.com",
        "username": "testuser",
        "password": "StrongP@ssw0rd123!",
        "full_name": "Test User"
    }


class TestUserRegistration:
    """Test user registration."""
    
    def test_register_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["username"] == test_user_data["username"]
        assert data["user"]["role"] == "user"
    
    def test_register_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email."""
        # First registration
        client.post("/auth/register", json=test_user_data)
        
        # Second registration with same email
        test_user_data["username"] = "different_username"
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_duplicate_username(self, client, test_user_data):
        """Test registration with duplicate username."""
        # First registration
        client.post("/auth/register", json=test_user_data)
        
        # Second registration with same username
        test_user_data["email"] = "different@devmind.com"
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 409
        assert "already taken" in response.json()["detail"].lower()
    
    def test_register_weak_password(self, client, test_user_data):
        """Test registration with weak password."""
        test_user_data["password"] = "weak"
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self, client, test_user_data):
        """Test registration with invalid email."""
        test_user_data["email"] = "not-an-email"
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == 422


class TestUserLogin:
    """Test user login."""
    
    def test_login_success_with_email(self, client, test_user_data):
        """Test successful login with email."""
        # Register user
        client.post("/auth/register", json=test_user_data)
        
        # Login
        response = client.post("/auth/login", json={
            "username_or_email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_login_success_with_username(self, client, test_user_data):
        """Test successful login with username."""
        # Register user
        client.post("/auth/register", json=test_user_data)
        
        # Login
        response = client.post("/auth/login", json={
            "username_or_email": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password."""
        # Register user
        client.post("/auth/register", json=test_user_data)
        
        # Login with wrong password
        response = client.post("/auth/login", json={
            "username_or_email": test_user_data["email"],
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post("/auth/login", json={
            "username_or_email": "nobody@devmind.com",
            "password": "AnyPassword123!"
        })
        
        assert response.status_code == 401


class TestAccountLockout:
    """Test account lockout after failed login attempts."""
    
    def test_account_lockout_after_5_attempts(self, client, test_user_data):
        """Test account is locked after 5 failed attempts."""
        # Register user
        client.post("/auth/register", json=test_user_data)
        
        # Make 5 failed login attempts
        for _ in range(5):
            client.post("/auth/login", json={
                "username_or_email": test_user_data["email"],
                "password": "WrongPassword123!"
            })
        
        # 6th attempt should be locked
        response = client.post("/auth/login", json={
            "username_or_email": test_user_data["email"],
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 423  # Locked
        assert "locked" in response.json()["detail"].lower()


class TestTokenManagement:
    """Test JWT token management."""
    
    def test_access_protected_endpoint(self, client, test_user_data):
        """Test accessing protected endpoint with valid token."""
        # Register user
        reg_response = client.post("/auth/register", json=test_user_data)
        token = reg_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["email"] == test_user_data["email"]
    
    def test_access_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 403
    
    def test_access_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_refresh_token(self, client, test_user_data):
        """Test refreshing access token."""
        # Register user
        reg_response = client.post("/auth/register", json=test_user_data)
        refresh_token = reg_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token  # New refresh token
    
    def test_logout(self, client, test_user_data):
        """Test user logout."""
        # Register user
        reg_response = client.post("/auth/register", json=test_user_data)
        refresh_token = reg_response.json()["refresh_token"]
        
        # Logout
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {reg_response.json()['access_token']}"}
        )
        
        assert response.status_code == 204
        
        # Try to use refresh token after logout
        refresh_response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert refresh_response.status_code == 401


class TestPasswordManagement:
    """Test password change functionality."""
    
    def test_change_password(self, client, test_user_data):
        """Test changing password."""
        # Register user
        reg_response = client.post("/auth/register", json=test_user_data)
        token = reg_response.json()["access_token"]
        
        # Change password
        new_password = "NewStrongP@ssw0rd456!"
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": new_password
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204
        
        # Login with new password
        login_response = client.post("/auth/login", json={
            "username_or_email": test_user_data["email"],
            "password": new_password
        })
        
        assert login_response.status_code == 200
    
    def test_change_password_wrong_current(self, client, test_user_data):
        """Test changing password with wrong current password."""
        # Register user
        reg_response = client.post("/auth/register", json=test_user_data)
        token = reg_response.json()["access_token"]
        
        # Change password with wrong current
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewStrongP@ssw0rd456!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401


class TestPasswordSecurity:
    """Test password security features."""
    
    def test_password_hashing(self):
        """Test passwords are hashed with bcrypt."""
        password = "TestPassword123!"
        hashed = security.hash_password(password)
        
        # Should not be plain text
        assert hashed != password
        
        # Should verify correctly
        assert security.verify_password(password, hashed)
    
    def test_password_validation_length(self):
        """Test password minimum length requirement."""
        is_valid, msg = security.validate_password_strength("Short1!")
        assert not is_valid
        assert "12 characters" in msg
    
    def test_password_validation_complexity(self):
        """Test password complexity requirements."""
        # Missing uppercase
        is_valid, msg = security.validate_password_strength("password123!")
        assert not is_valid
        
        # Missing lowercase
        is_valid, msg = security.validate_password_strength("PASSWORD123!")
        assert not is_valid
        
        # Missing digit
        is_valid, msg = security.validate_password_strength("PasswordABC!")
        assert not is_valid
        
        # Missing special
        is_valid, msg = security.validate_password_strength("Password1234")
        assert not is_valid
        
        # Valid password
        is_valid, msg = security.validate_password_strength("ValidP@ssw0rd123")
        assert is_valid
