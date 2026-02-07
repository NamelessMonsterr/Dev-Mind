"""
Authentication API routes.

Endpoints for user registration, login, logout, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from devmind.auth import schemas
from devmind.auth.service import (
    AuthService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    AccountLockedError,
    WeakPasswordError
)
from devmind.auth.dependencies import get_current_user
from devmind.auth.models import User
from devmind.core.database import get_db
from devmind.middleware.rate_limit import rate_limit_login, rate_limit_register, rate_limit_refresh
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_register)])
async def register(
    request: schemas.UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Creates a user account and returns authentication tokens.
    """
    auth_service = AuthService(db)
    
    try:
        user, access_token, refresh_token = auth_service.register_user(request)
        
        return schemas.TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,  # 30 minutes
            user=schemas.UserResponse.from_orm(user)
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=schemas.TokenResponse, dependencies=[Depends(rate_limit_login)])
async def login(
    request: schemas.UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user.
    
    Authenticates user and returns JWT tokens.
    """
    auth_service = AuthService(db)
    
    try:
        user, access_token, refresh_token = auth_service.authenticate_user(request)
        
        return schemas.TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,  # 30 minutes
            user=schemas.UserResponse.from_orm(user)
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(e)
        )


@router.post("/refresh", response_model=schemas.TokenResponse, dependencies=[Depends(rate_limit_refresh)])
async def refresh_token(
    request: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token.
    
    Generates a new access token using a valid refresh token.
    """
    auth_service = AuthService(db)
    
    try:
        user, access_token, new_refresh_token = auth_service.refresh_access_token(request.refresh_token)
        
        return schemas.TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=30 * 60,  # 30 minutes
            user=schemas.UserResponse.from_orm(user)
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: schemas.RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user.
    
    Invalidates the refresh token.
    """
    auth_service = AuthService(db)
    auth_service.logout_user(request.refresh_token)
    return None


@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    
    Returns the authenticated user's profile.
    """
    return schemas.UserResponse.from_orm(current_user)


@router.put("/me", response_model=schemas.UserResponse)
async def update_current_user(
    full_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile.
    """
    current_user.full_name = full_name
    db.commit()
    db.refresh(current_user)
    
    return schemas.UserResponse.from_orm(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    
    Requires current password for verification.
    """
    auth_service = AuthService(db)
    
    try:
        auth_service.change_password(
            current_user.id,
            request.current_password,
            request.new_password
        )
        return None
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
