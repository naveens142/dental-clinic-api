"""
JWT Utilities for token generation and verification.
"""

import os
import jwt
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(".env")

logger = logging.getLogger(__name__)

# Secret key for JWT - MUST be set in environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
EXPIRE_MINUTES = 24 * 60  # 24 hours

# Validate JWT secret is set
if not SECRET_KEY:
    logger.error("CRITICAL: JWT_SECRET_KEY not set in environment variables!")
    raise EnvironmentError(
        "JWT_SECRET_KEY environment variable is required but not set. "
        "Generate one using: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

if len(SECRET_KEY) < 32:
    logger.warning(f"WARNING: JWT_SECRET_KEY is weak ({len(SECRET_KEY)} chars). Use 32+ characters.")


def create_access_token(data: dict) -> str:
    """
    Create JWT token.
    
    Args:
        data: Data to encode in token (e.g., {"email": "naveens142@gmail.com})
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token data
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
