import pytest
import jwt
import sys
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

# 确保这个文件也能找到项目根目录
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.routers.auth import SECRET_KEY, ALGORITHM

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
@pytest.fixture
def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(override_get_db):
    def _get_db_override():
        try:
            db = override_get_db
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = _get_db_override
    yield TestClient(app)
    app.dependency_overrides = {}

# Create a test user
@pytest.fixture
def test_user(override_get_db):
    user = User(
        id="test-user-id",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        role=UserRole.EMPLOYEE,
        hashed_password="hashed_password"  # Not used with Cognito
    )
    override_get_db.add(user)
    override_get_db.commit()
    return user

# Create a test token
@pytest.fixture
def test_token(test_user):
    expires_delta = timedelta(minutes=30)
    to_encode = {"sub": test_user.email}
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Test authentication functions and endpoints
class TestAuth:
    @patch("app.routers.auth.cognito_client")
    def test_login(self, mock_cognito, client):
        # Mock the Cognito response
        mock_auth_response = {
            "AuthenticationResult": {
                "IdToken": "mock_id_token",
                "AccessToken": "mock_access_token",
                "RefreshToken": "mock_refresh_token",
                "ExpiresIn": 3600
            }
        }
        mock_cognito.initiate_auth.return_value = mock_auth_response
        
        login_data = {
            "username": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/auth/login", data=login_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "token_type" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    def test_get_current_user(self, client, test_token, test_user):
        response = client.get(
            "/auth/user",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email
    
    @patch("app.routers.auth.cognito_client")
    def test_refresh_token(self, mock_cognito, client):
        # Mock the Cognito refresh response
        mock_refresh_response = {
            "AuthenticationResult": {
                "IdToken": "mock_new_id_token",
                "AccessToken": "mock_new_access_token",
                "ExpiresIn": 3600
            }
        }
        # Mock JWT decode to return email
        mock_decoded = {"email": "test@example.com"}
        
        with patch("app.routers.auth.jwt.decode", return_value=mock_decoded):
            mock_cognito.initiate_auth.return_value = mock_refresh_response
            
            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "mock_refresh_token"}
            )
            
            assert response.status_code == 200
            assert "access_token" in response.json()
            assert "id_token" in response.json() 