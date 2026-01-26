"""
Authentication Module for Admin Dashboard
Provides JWT-based authentication with hardcoded admin credentials (local system only).
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security configuration
SECRET_KEY = "pharmacy_admin_secret_key_2026_local_only"  # Change in production
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

# Hardcoded admin credentials (for local system only)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "pharmacy_admin_2026"

# Pre-hashed password for verification
ADMIN_PASSWORD_HASH = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt())

# Active tokens (simple in-memory store for demo)
active_tokens = set()

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)


def create_access_token(username: str, role: str = "ADMIN") -> str:
    """
    Generate JWT access token.
    
    Args:
        username: Admin username
        role: User role (default: ADMIN)
    
    Returns:
        JWT token string
    """
    expiry = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    
    payload = {
        "sub": username,
        "role": role,
        "exp": expiry,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    active_tokens.add(token)
    
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        # Check if token is active
        if token not in active_tokens:
            return None
        
        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check expiry
        if datetime.utcnow().timestamp() > payload.get("exp", 0):
            active_tokens.discard(token)
            return None
        
        return payload
    
    except jwt.ExpiredSignatureError:
        active_tokens.discard(token)
        return None
    except jwt.JWTError:
        return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with username and password.
    
    Args:
        username: Username
        password: Plain text password
    
    Returns:
        User info dict or None if authentication fails
    """
    if username != ADMIN_USERNAME:
        return None
    
    if not verify_password(password, ADMIN_PASSWORD_HASH):
        return None
    
    return {
        "username": username,
        "role": "ADMIN"
    }


def invalidate_token(token: str) -> bool:
    """
    Invalidate (logout) a token.
    
    Args:
        token: JWT token to invalidate
    
    Returns:
        True if token was active, False otherwise
    """
    if token in active_tokens:
        active_tokens.remove(token)
        return True
    return False


async def get_current_admin(credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated admin.
    
    Args:
        credentials: HTTP Bearer credentials from request
    
    Returns:
        User info dict
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if user has admin role
    if payload.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )
    
    return {
        "username": payload.get("sub"),
        "role": payload.get("role")
    }


def require_admin(func):
    """
    Decorator to protect routes requiring admin authentication.
    Use with FastAPI route handlers.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request from args/kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            raise HTTPException(status_code=500, detail="Request object not found")
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract token
        token = auth_header.split(" ")[1]
        
        # Validate token
        payload = decode_token(token)
        if not payload or payload.get("role") != "ADMIN":
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Add user info to kwargs
        kwargs['current_admin'] = {
            "username": payload.get("sub"),
            "role": payload.get("role")
        }
        
        return await func(*args, **kwargs)
    
    return wrapper


# Helper function to get token from request
def extract_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from request headers."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None


# Statistics
def get_auth_stats() -> Dict[str, Any]:
    """Get authentication statistics."""
    return {
        "active_sessions": len(active_tokens),
        "token_expiry_hours": TOKEN_EXPIRY_HOURS
    }
