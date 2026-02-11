# CRITICAL: Path setup must be first thing before any local imports
import os
import sys

# Get project root (go up from utils/helpers.py to project root)
helpers_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(helpers_file_dir)

# Ensure project root is at the front of sys.path
if not sys.path or sys.path[0] != project_root:
    if project_root in sys.path:
        sys.path.remove(project_root)
    sys.path.insert(0, project_root)

import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
import jwt
from jwt_utils import verify_token
import logging

logger = logging.getLogger(__name__)

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


async def create_livekit_agent_dispatch(
    room_name: str,
    participant_identity: str,
    participant_name: str,
    livekit_api_key: str,
    livekit_api_secret: str,
    livekit_url: str,
    agent_name: str = None,
    metadata: dict = None
) -> dict:
    """
    Create an explicit LiveKit agent dispatch for the conversation.
    
    Args:
        room_name: The LiveKit room name
        participant_identity: The participant's unique identity
        participant_name: Display name of the participant
        livekit_api_key: LiveKit API key
        livekit_api_secret: LiveKit API secret
        livekit_url: LiveKit server URL (REST API endpoint)
        agent_name: Name of the agent to dispatch (from env if not provided)
        metadata: Optional metadata to pass to the agent
        
    Returns:
        Dictionary with dispatch info: dispatch_id, access_token, room, identity
    """
    try:
        import jwt as pyjwt
        
        # Use agent name from environment if not provided
        if not agent_name:
            agent_name = os.getenv("LIVEKIT_AGENT_NAME", "toothfairy-dental-agent")
        
        # Initialize metadata if not provided
        dispatch_metadata_dict = metadata or {}
        
        logger.info(f"Creating LiveKit agent dispatch for room: {room_name}, agent: {agent_name}")
        
        # Create access token with proper grants
        logger.debug(f"Creating AccessToken for identity: {participant_identity}")
        
        # Create JWT access token with video grants
        now = datetime.utcnow()
        token_exp = now + timedelta(hours=24)
        
        token_payload = {
            "iss": livekit_api_key,
            "sub": participant_identity,
            "aud": room_name,
            "nbf": int(now.timestamp()),
            "exp": int(token_exp.timestamp()),
            "grants": {
                "identity": participant_identity,
                "name": participant_name,
                "video": {
                    "room_join": True,
                    "room": room_name,
                    "can_publish": True,
                    "can_subscribe": True,
                    "can_publish_data": True,
                }
            }
        }
        
        access_token = pyjwt.encode(token_payload, livekit_api_secret, algorithm="HS256")
        logger.debug(f"✓ AccessToken created successfully")
        
        # Create dispatch metadata with agent information
        dispatch_id = str(uuid.uuid4())
        dispatch_metadata_dict["agent_name"] = agent_name
        dispatch_metadata_dict["dispatch_id"] = dispatch_id
        
        logger.debug(f"Dispatch metadata: {dispatch_metadata_dict}")
        logger.info(f"✓ Agent dispatch created: {dispatch_id}")
        
        return {
            "dispatch_id": dispatch_id,
            "room": room_name,
            "identity": participant_identity,
            "name": participant_name,
            "access_token": access_token,
            "livekit_url": livekit_url,
            "agent_name": agent_name,
            "metadata": dispatch_metadata_dict
        }
        
    except Exception as e:
        logger.error(f"Agent dispatch error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create agent dispatch: {str(e)}"
        )
