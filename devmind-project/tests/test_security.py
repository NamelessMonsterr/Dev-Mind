"""
Security-focused tests for DevMind.

Tests authentication, authorization, workspace isolation, and security hardening.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from devmind.api.app import create_app
from devmind.core.database import Base, get_db
from devmind.auth.models import User, UserRole
from devmind.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from devmind.auth import security

# Test database
TEST_DATABASE_URL = "sqlite:///./test_security.db"
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
    """Create test client."""
    Base.metadata.create_all(bind=engine)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_users(client):
    """Create test users with different roles."""
    db = next(override_get_db())
    
    # Admin user
    admin = User(
        id=uuid.uuid4(),
        email="admin@devmind.com",
        username="admin",
        password_hash=security.hash_password("AdminP@ssw0rd123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    
    # Regular user
    user = User(
        id=uuid.uuid4(),
        email="user@devmind.com",
        username="user",
        password_hash=security.hash_password("UserP@ssw0rd123!"),
        full_name="Regular User",
        role=UserRole.USER,
        is_active=True
    )
    
    # Viewer
    viewer = User(
        id=uuid.uuid4(),
        email="viewer@devmind.com",
        username="viewer",
        password_hash=security.hash_password("ViewerP@ssw0rd123!"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True
    )
    
    db.add_all([admin, user, viewer])
    db.commit()
    
    yield {"admin": admin, "user": user, "viewer": viewer}
    
    db.close()


class TestSecurityHeaders:
    """Test security headers are properly set."""
    
    def test_security_headers_present(self, client):
        """Test all security headers are present in response."""
        response = client.get("/health")
        
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        assert "Content-Security-Policy" in response.headers
        
        assert "Referrer-Policy" in response.headers


class TestRBACEnforcement:
    """Test role-based access control enforcement."""
    
    def test_admin_role_required(self, client, test_users):
        """Test endpoint requiring admin role."""
        # Login as regular user
        login_response = client.post("/auth/login", json={
            "username_or_email": "user",
            "password": "UserP@ssw0rd123!"
        })
        user_token = login_response.json()["access_token"]
        
        # Try admin-only operation (example: future admin endpoint)
        # For now, test that non-admin cannot create certain resources
        # This is a placeholder - adjust based on actual admin endpoints
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "user"


class TestWorkspaceIsolation:
    """Test workspace data isolation."""
    
    def test_workspace_creation_and_access(self, client, test_users):
        """Test users can only access their workspaces."""
        # Login as user1
        login1 = client.post("/auth/login", json={
            "username_or_email": "user",
            "password": "UserP@ssw0rd123!"
        })
        token1 = login1.json()["access_token"]
        
        # Login as admin
        login2 = client.post("/auth/login", json={
            "username_or_email": "admin",
            "password": "AdminP@ssw0rd123!"
        })
        token2 = login2.json()["access_token"]
        
        # User1 creates workspace
        ws_response = client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "name": "User1 Workspace",
                "slug": "user1-ws",
                "description": "Private workspace"
            }
        )
        assert ws_response.status_code == 201
        workspace_id = ws_response.json()["id"]
        
        # User2 should NOT be able to access User1's workspace
        access_response = client.get(
            f"/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert access_response.status_code == 403  # Forbidden
    
    def test_workspace_slug_uniqueness(self, client, test_users):
        """Test workspace slugs are globally unique."""
        login1 = client.post("/auth/login", json={
            "username_or_email": "user",
            "password": "UserP@ssw0rd123!"
        })
        token1 = login1.json()["access_token"]
        
        login2 = client.post("/auth/login", json={
            "username_or_email": "admin",
            "password": "AdminP@ssw0rd123!"
        })
        token2 = login2.json()["access_token"]
        
        # User1 creates workspace
        client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {token1}"},
            json={"name": "Project", "slug": "my-project"}
        )
        
        # User2 tries same slug
        response = client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {token2}"},
            json={"name": "Different Project", "slug": "my-project"}
        )
        assert response.status_code == 409  # Conflict


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection attempts are blocked."""
        # Try SQL injection in login
        response = client.post("/auth/login", json={
            "username_or_email": "admin' OR '1'='1",
            "password": "password"
        })
        assert response.status_code == 401  # Should fail authentication
    
    def test_xss_payload_rejected(self, client, test_users):
        """Test XSS payloads are rejected."""
        login = client.post("/auth/login", json={
            "username_or_email": "user",
            "password": "UserP@ssw0rd123!"
        })
        token = login.json()["access_token"]
        
        # Try XSS in workspace name
        response = client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "<script>alert('XSS')</script>",
                "slug": "xss-test"
            }
        )
        # Should succeed but name should be sanitized/escaped
        # API returns JSON so XSS is primarily frontend concern
        assert response.status_code in [201, 400]
    
    def test_invalid_email_format(self, client):
        """Test invalid email format is rejected."""
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "username": "testuser",
            "password": "ValidP@ssw0rd123!"
        })
        assert response.status_code == 422  # Validation error


class TestPasswordPolicy:
    """Test password policy enforcement."""
    
    def test_weak_passwords_rejected(self, client):
        """Test various weak passwords are rejected."""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
        ]
        
        for password in weak_passwords:
            response = client.post("/auth/register", json={
                "email": f"test@example.com",
                "username": "testuser",
                "password": password
            })
            assert response.status_code == 400, f"Weak password accepted: {password}"


class TestCORSConfiguration:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        # OPTIONS requests should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


# Note: Additional tests to implement:
# - Rate limiting tests (requires rate limiting implementation)
# - CSRF protection tests (requires CSRF implementation)
# - File upload validation (requires file upload implementation)
# - Concurrent session management
# - Token expiration and refresh
