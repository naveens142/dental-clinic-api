import os
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
import jwt
from jwt_utils import verify_token

def validate_environment():
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "DB_HOST",
        "DB_USER",
        "DB_NAME"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

def generate_room_name(clinic_id: str) -> str:
    unique_id = uuid.uuid4().hex[:8]
    return f"clinic_session_{unique_id}"

def generate_participant_identity() -> str:
    return f"participant_{uuid.uuid4().hex[:8]}"

def verify_jwt_token(credentials = Depends(HTTPBearer())) -> dict:
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def generate_livekit_token(
    room_name: str,
    participant_identity: str,
    session_id: str,
    livekit_url: str,
    livekit_api_key: str,
    livekit_api_secret: str,
    token_ttl: int = 86400
) -> str:
    payload = {
        "iss": livekit_api_key,
        "sub": participant_identity,
        "aud": room_name,
        "nbf": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=token_ttl),
        "video": {
            "room_join": True,
            "room": room_name,
            "can_publish": True,
            "can_subscribe": True,
            "can_publish_data": True,
        },
        "livekit_url": livekit_url,
        "session_id": session_id
    }
    return jwt.encode(payload, livekit_api_secret, algorithm="HS256")
