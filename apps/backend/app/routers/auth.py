from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional
import os
import boto3
import jwt
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from ..db import get_db
from ..models.user import User, UserOut

router = APIRouter()

# AWS Cognito configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET", None)

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Cognito client
cognito_client = boto3.client('cognito-idp', region_name=REGION)

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    sub: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class UserSchema(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    id: str
    
    class Config:
        orm_mode = True

def authenticate_user(username: str, password: str):
    """
    Authenticate a user against AWS Cognito
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
            }
        )
        return response
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'NotAuthorizedException':
            return None
        raise e

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependency that returns the current user from a JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, sub=username)
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Find the user in the database
    user = db.query(User).filter(User.email == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Dependency that ensures the user is active
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint that authenticates with AWS Cognito and returns JWT token
    """
    auth_response = authenticate_user(form_data.username, form_data.password)
    if not auth_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract Cognito tokens
    auth_result = auth_response.get('AuthenticationResult', {})
    id_token = auth_result.get('IdToken')
    access_token = auth_result.get('AccessToken')
    refresh_token = auth_result.get('RefreshToken')
    expires_in = auth_result.get('ExpiresIn', ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    # Create our own JWT with the necessary claims
    token_data = {"sub": form_data.username}
    jwt_token = create_access_token(
        data=token_data, 
        expires_delta=timedelta(seconds=expires_in)
    )
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "id_token": id_token
    }

@router.get("/user", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Return the current authenticated user's information
    """
    return current_user

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh the access token using a refresh token
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token,
            }
        )
        
        auth_result = response.get('AuthenticationResult', {})
        id_token = auth_result.get('IdToken')
        access_token = auth_result.get('AccessToken')
        expires_in = auth_result.get('ExpiresIn', ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        # Decode the ID token to get the username/email
        decoded_id_token = jwt.decode(id_token, options={"verify_signature": False})
        username = decoded_id_token.get('email', decoded_id_token.get('cognito:username'))
        
        # Create our own JWT
        token_data = {"sub": username}
        jwt_token = create_access_token(
            data=token_data, 
            expires_delta=timedelta(seconds=expires_in)
        )
        
        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "id_token": id_token
        }
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) 