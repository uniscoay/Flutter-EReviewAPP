import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.review import EmployerReview
from app.models.peer_review import PeerReview

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_reviews.db"
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

# Create test users with different roles
@pytest.fixture
def test_manager(override_get_db):
    user = User(
        id="manager-id",
        email="manager@example.com",
        full_name="Manager User",
        is_active=True,
        role=UserRole.MANAGER,
    )
    override_get_db.add(user)
    override_get_db.commit()
    return user

@pytest.fixture
def test_employee(override_get_db):
    user = User(
        id="employee-id",
        email="employee@example.com",
        full_name="Employee User",
        is_active=True,
        role=UserRole.EMPLOYEE,
    )
    override_get_db.add(user)
    override_get_db.commit()
    return user

@pytest.fixture
def test_employee2(override_get_db):
    user = User(
        id="employee2-id",
        email="employee2@example.com",
        full_name="Second Employee",
        is_active=True,
        role=UserRole.EMPLOYEE,
    )
    override_get_db.add(user)
    override_get_db.commit()
    return user

# Authentication helper
def get_auth_headers(user_email):
    import jwt
    from datetime import datetime, timedelta
    from app.routers.auth import SECRET_KEY, ALGORITHM
    
    expires_delta = timedelta(minutes=30)
    to_encode = {"sub": user_email}
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"Authorization": f"Bearer {encoded_jwt}"}

# Test employer review endpoints
class TestEmployerReviews:
    def test_create_employer_review(self, client, test_manager, test_employee):
        review_data = {
            "employee_id": test_employee.id,
            "performance_score": 4.5,
            "communication_score": 4.0,
            "teamwork_score": 4.2,
            "innovation_score": 3.8,
            "leadership_score": 3.5,
            "technical_score": 4.7,
            "reliability_score": 4.3,
            "comments": "Good performance overall",
            "review_period": "2023 Q2"
        }
        
        response = client.post(
            "/reviews/employer",
            json=review_data,
            headers=get_auth_headers(test_manager.email)
        )
        
        assert response.status_code == 200
        assert response.json()["employee_id"] == test_employee.id
        assert response.json()["reviewer_id"] == test_manager.id
        assert response.json()["performance_score"] == 4.5
    
    def test_get_employee_reviews_as_manager(self, client, test_manager, test_employee, override_get_db):
        # Create a test review in the database
        review = EmployerReview(
            employee_id=test_employee.id,
            reviewer_id=test_manager.id,
            performance_score=4.0,
            communication_score=4.0,
            teamwork_score=4.0,
            innovation_score=4.0,
            leadership_score=4.0,
            technical_score=4.0,
            reliability_score=4.0,
            comments="Test review",
            review_period="2023 Q2"
        )
        override_get_db.add(review)
        override_get_db.commit()
        
        response = client.get(
            f"/reviews/employer/{test_employee.id}",
            headers=get_auth_headers(test_manager.email)
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["employee_id"] == test_employee.id
    
    def test_get_own_reviews_as_employee(self, client, test_manager, test_employee, override_get_db):
        # Create a test review in the database
        review = EmployerReview(
            employee_id=test_employee.id,
            reviewer_id=test_manager.id,
            performance_score=4.0,
            communication_score=4.0,
            teamwork_score=4.0,
            innovation_score=4.0,
            leadership_score=4.0,
            technical_score=4.0,
            reliability_score=4.0,
            comments="Test review",
            review_period="2023 Q2"
        )
        override_get_db.add(review)
        override_get_db.commit()
        
        response = client.get(
            f"/reviews/employer/{test_employee.id}",
            headers=get_auth_headers(test_employee.email)
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["employee_id"] == test_employee.id

# Test peer review endpoints
class TestPeerReviews:
    def test_create_peer_review(self, client, test_employee, test_employee2):
        review_data = {
            "employee_id": test_employee2.id,
            "liked": True,
            "is_anonymous": True,
            "comments": "Great teammate!"
        }
        
        response = client.post(
            "/reviews/peer",
            json=review_data,
            headers=get_auth_headers(test_employee.email)
        )
        
        assert response.status_code == 200
        assert response.json()["employee_id"] == test_employee2.id
        assert response.json()["reviewer_id"] == test_employee.id
        assert response.json()["liked"] == True
    
    def test_get_my_peer_reviews(self, client, test_employee, test_employee2, override_get_db):
        # Create a test peer review
        review = PeerReview(
            employee_id=test_employee.id,
            reviewer_id=test_employee2.id,
            liked=True,
            is_anonymous=True,
            comments="Test peer review"
        )
        override_get_db.add(review)
        override_get_db.commit()
        
        response = client.get(
            "/reviews/peer/me",
            headers=get_auth_headers(test_employee.email)
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["employee_id"] == test_employee.id
        # If anonymous, reviewer_id should be None for non-admin users
        assert response.json()[0]["reviewer_id"] is None
    
    def test_cannot_review_self(self, client, test_employee):
        review_data = {
            "employee_id": test_employee.id,  # Same as reviewer
            "liked": True,
            "is_anonymous": False,
            "comments": "Self review should fail"
        }
        
        response = client.post(
            "/reviews/peer",
            json=review_data,
            headers=get_auth_headers(test_employee.email)
        )
        
        assert response.status_code == 400
        assert "Cannot review yourself" in response.json()["detail"]
    
    def test_cannot_review_twice(self, client, test_employee, test_employee2, override_get_db):
        # Create existing review
        review = PeerReview(
            employee_id=test_employee2.id,
            reviewer_id=test_employee.id,
            liked=True,
            is_anonymous=True,
            comments="Existing review"
        )
        override_get_db.add(review)
        override_get_db.commit()
        
        # Try to review again
        review_data = {
            "employee_id": test_employee2.id,
            "liked": False,
            "is_anonymous": True,
            "comments": "Should fail"
        }
        
        response = client.post(
            "/reviews/peer",
            json=review_data,
            headers=get_auth_headers(test_employee.email)
        )
        
        assert response.status_code == 400
        assert "already reviewed" in response.json()["detail"] 