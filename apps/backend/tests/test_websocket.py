import pytest
import json
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.peer_review import PeerReview
from app.routers.realtime import get_likes_count, broadcast_like_update

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_websocket.db"
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

# Create test users
@pytest.fixture
def test_users(override_get_db):
    users = []
    for i in range(3):
        user = User(
            id=f"user-{i}",
            email=f"user{i}@example.com",
            full_name=f"User {i}",
            is_active=True,
            role=UserRole.EMPLOYEE,
        )
        override_get_db.add(user)
        users.append(user)
    
    override_get_db.commit()
    return users

# Create test peer reviews with likes
@pytest.fixture
def test_likes(override_get_db, test_users):
    # User 0 likes User 1
    review1 = PeerReview(
        employee_id=test_users[1].id,
        reviewer_id=test_users[0].id,
        liked=True,
        is_anonymous=False,
        comments="Great work!"
    )
    
    # User 2 likes User 1
    review2 = PeerReview(
        employee_id=test_users[1].id,
        reviewer_id=test_users[2].id,
        liked=True,
        is_anonymous=True,
        comments="Excellent teammate"
    )
    
    # User 1 likes User 0
    review3 = PeerReview(
        employee_id=test_users[0].id,
        reviewer_id=test_users[1].id,
        liked=True,
        is_anonymous=False,
        comments="Good job"
    )
    
    override_get_db.add_all([review1, review2, review3])
    override_get_db.commit()
    
    return [review1, review2, review3]

class TestWebSocketEndpoint:
    def test_websocket_connection(self, client):
        with client.websocket_connect("/realtime/likes") as websocket:
            # We should receive the initial data message
            data = websocket.receive_json()
            assert data["type"] == "initial_data"
            assert "data" in data
            assert "timestamp" in data
    
    def test_websocket_ping_pong(self, client):
        with client.websocket_connect("/realtime/likes") as websocket:
            # Skip initial data
            websocket.receive_json()
            
            # Send ping and expect pong response
            websocket.send_text("ping")
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response
    
    def test_like_counts(self, client, test_users, test_likes):
        with client.websocket_connect("/realtime/likes") as websocket:
            data = websocket.receive_json()
            
            # Check if user counts are correct
            like_counts = data["data"]
            assert like_counts[test_users[0].id] == 1  # User 0 received 1 like
            assert like_counts[test_users[1].id] == 2  # User 1 received 2 likes
            assert test_users[2].id not in like_counts or like_counts[test_users[2].id] == 0  # User 2 got no likes

    @pytest.mark.asyncio
    async def test_broadcast_like_update(self, override_get_db, test_users):
        with patch('app.routers.realtime.manager.broadcast') as mock_broadcast:
            # Call the broadcast function
            await broadcast_like_update(test_users[0].id, True)
            
            # Check that broadcast was called with the right message
            mock_broadcast.assert_called_once()
            broadcast_msg = mock_broadcast.call_args[0][0]
            assert broadcast_msg["type"] == "like_update"
            assert broadcast_msg["data"]["employee_id"] == test_users[0].id
            assert broadcast_msg["data"]["liked"] is True
            assert "timestamp" in broadcast_msg["data"]

    def test_user_specific_connection(self, client, test_users):
        with client.websocket_connect(f"/realtime/likes?user_id={test_users[0].id}") as websocket:
            # We should receive the initial data message
            data = websocket.receive_json()
            assert data["type"] == "initial_data"
            
            # We don't have an easy way to test if the connection is stored with user_id
            # in a unit test, but we can ensure it doesn't crash 