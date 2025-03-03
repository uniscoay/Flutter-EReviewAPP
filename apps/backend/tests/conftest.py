import pytest
import jwt
import sys
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 解决导入问题 - 添加项目根目录到 Python 路径
# 获取当前文件所在目录的上一级目录(即 backend 目录)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 现在可以正常导入 app 模块
from app.db import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.routers.auth import SECRET_KEY, ALGORITHM

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = {}

@pytest.fixture
def create_user(db):
    def _create_user(email="test@example.com", full_name="Test User", role=UserRole.EMPLOYEE):
        user = User(
            id=f"user-{email.split('@')[0]}",
            email=email,
            full_name=full_name,
            is_active=True,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _create_user

@pytest.fixture
def auth_headers():
    def _auth_headers(email):
        expires_delta = timedelta(minutes=30)
        to_encode = {"sub": email}
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return {"Authorization": f"Bearer {encoded_jwt}"}
    return _auth_headers 