"""
Authentication service.

Business logic for user management and authentication.
"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid
import logging

from devmind.auth.models import User, RefreshToken, UserRole
from devmind.auth.schemas import UserRegisterRequest, UserLoginRequest
from devmind.auth import security

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """Base exception for authentication errors."""
    pass


class UserAlreadyExistsError(AuthServiceError):
    """User with email/username already exists."""
    pass


class InvalidCredentialsError(AuthServiceError):
    """Invalid username/password."""
    pass


class AccountLockedError(AuthServiceError):
    """Account is temporarily locked."""
    pass


class WeakPasswordError(AuthServiceError):
    """Password doesn't meet security requirements."""
    pass


class AuthService:
    """
    Authentication service for user management.
    
    Handles registration, login, token management, and account security.
    """
    
    def __init__(self, db: Session):
        """
        Initialize auth service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def register_user(self, request: UserRegisterRequest) -> tuple[User, str, str]:
        """
        Register a new user.
        
        Args:
            request: User registration request
            
        Returns:
            Tuple of (user, access_token, refresh_token)
            
        Raises:
            UserAlreadyExistsError: If email/username already exists
            WeakPasswordError: If password doesn't meet requirements
        """
        # Validate password strength
        is_valid, error_msg = security.validate_password_strength(request.password)
        if not is_valid:
            raise WeakPasswordError(error_msg)
        
        # Hash password
        password_hash = security.hash_password(request.password)
        
        # Create user
        user = User(
            id=uuid.uuid4(),
            email=request.email.lower(),
            username=request.username,
            password_hash=password_hash,
            full_name=request.full_name,
            role=UserRole.USER,  # Default role
            is_active=True,
            is_email_verified=False
        )
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"User registered: {user.username} ({user.email})")
            
            # Generate tokens for immediate login
            access_token = security.create_access_token(
                data={"sub": str(user.id), "role": user.role.value}
            )
            
            refresh_token_str, expires_at = security.create_refresh_token(str(user.id))
            
            # Store refresh token
            refresh_token = RefreshToken(
                user_id=user.id,
                token=refresh_token_str,
                expires_at=expires_at
            )
            self.db.add(refresh_token)
            self.db.commit()
            
            return user, access_token, refresh_token_str
        except IntegrityError as e:
            self.db.rollback()
            if "email" in str(e):
                raise UserAlreadyExistsError(f"Email {request.email} already registered")
            elif "username" in str(e):
                raise UserAlreadyExistsError(f"Username {request.username} already taken")
            else:
                raise UserAlreadyExistsError("User already exists")
    
    def authenticate_user(self, request: UserLoginRequest) -> tuple[User, str, str]:
        """
        Authenticate user and generate tokens.
        
        Args:
            request: Login request
            
        Returns:
            Tuple of (user, access_token, refresh_token)
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
        """
        # Find user by email or username
        identifier = request.username_or_email.lower()
        user = self.db.query(User).filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()
        
        if not user:
            raise InvalidCredentialsError("Invalid username/email or password")
        
        # Check if account is locked
        if user.is_locked:
            remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
            raise AccountLockedError(
                f"Account locked due to multiple failed login attempts. "
                f"Try again in {int(remaining)} minutes."
            )
        
        # Verify password
        if not security.verify_password(request.password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            user.locked_until = security.get_lockout_until(user.failed_login_attempts)
            self.db.commit()
            
            raise InvalidCredentialsError("Invalid username/email or password")
        
        # Check if user is active
        if not user.is_active:
            raise InvalidCredentialsError("Account is inactive")
        
        # Successful login - reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Generate tokens
        access_token = security.create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )
        
        refresh_token_str, expires_at = security.create_refresh_token(str(user.id))
        
        # Store refresh token in database
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at
        )
        self.db.add(refresh_token)
        self.db.commit()
        
        logger.info(f"User logged in: {user.username}")
        return user, access_token, refresh_token_str
    
    def refresh_access_token(self, refresh_token_str: str) -> tuple[User, str, str]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token_str: Refresh token
            
        Returns:
            Tuple of (user, new_access_token, new_refresh_token)
            
        Raises:
            InvalidCredentialsError: If refresh token is invalid/expired
        """
        # Find refresh token in database
        refresh_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str
        ).first()
        
        if not refresh_token:
            raise InvalidCredentialsError("Invalid refresh token")
        
        # Check expiration
        if refresh_token.is_expired:
            self.db.delete(refresh_token)
            self.db.commit()
            raise InvalidCredentialsError("Refresh token expired")
        
        # Validate token
        payload = security.decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise InvalidCredentialsError("Invalid refresh token")
        
        # Get user
        user = self.db.query(User).filter(User.id == refresh_token.user_id).first()
        if not user or not user.is_active:
            raise InvalidCredentialsError("User not found or inactive")
        
        # Generate new tokens
        new_access_token = security.create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )
        
        new_refresh_token_str, new_expires_at = security.create_refresh_token(str(user.id))
        
        # Delete old refresh token and create new one
        self.db.delete(refresh_token)
        new_refresh_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token_str,
            expires_at=new_expires_at
        )
        self.db.add(new_refresh_token)
        self.db.commit()
        
        return user, new_access_token, new_refresh_token_str
    
    def logout_user(self, refresh_token_str: str) -> None:
        """
        Logout user by invalidating refresh token.
        
        Args:
            refresh_token_str: Refresh token to invalidate
        """
        refresh_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str
        ).first()
        
        if refresh_token:
            self.db.delete(refresh_token)
            self.db.commit()
            logger.info(f"User logged out: {refresh_token.user_id}")
    
    def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Raises:
            InvalidCredentialsError: If current password is wrong
            WeakPasswordError: If new password doesn't meet requirements
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise InvalidCredentialsError("User not found")
        
        # Verify current password
        if not security.verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
       # Validate new password
        is_valid, error_msg = security.validate_password_strength(new_password)
        if not is_valid:
            raise WeakPasswordError(error_msg)
        
        # Update password
        user.password_hash = security.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Invalidate all refresh tokens (force re-login on all devices)
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        
        self.db.commit()
        logger.info(f"Password changed for user: {user.username}")
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User or None
        """
        return self.db.query(User).filter(User.id == user_id).first()
