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
import asyncio
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
    """
    Generate LiveKit access token using the official SDK.
    
    Args:
        room_name: Room to join
        participant_identity: Unique participant identifier
        session_id: Session ID for tracking
        livekit_url: LiveKit server URL
        livekit_api_key: API key for token signing
        livekit_api_secret: API secret for token signing
        token_ttl: Token time-to-live in seconds (default 24 hours)
    
    Returns:
        JWT token string with room_join=True permission
    """
    from livekit.api import AccessToken, VideoGrants
    
    token = AccessToken(livekit_api_key, livekit_api_secret) \
        .with_identity(participant_identity) \
        .with_grants(
            VideoGrants(
                room_join=True,  # CRITICAL: Required for agent to join room
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    
    return token.to_jwt()


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
    Wakes up the agent from sleeping state and assigns it to the room.
    
    Args:
        room_name: The LiveKit room name
        participant_identity: The participant's unique identity
        participant_name: Display name of the participant
        livekit_api_key: LiveKit API key
        livekit_api_secret: LiveKit API secret
        livekit_url: LiveKit server URL (WebSocket endpoint)
        agent_name: Name of the agent to dispatch (from env if not provided)
        metadata: Optional metadata to pass to the agent
        
    Returns:
        Dictionary with dispatch info: dispatch_id, access_token, room, identity
    """
    try:
        from livekit.api import AccessToken, VideoGrants
        from livekit import api as lk_api
        
        # Use agent name from environment if not provided
        if not agent_name:
            agent_name = os.getenv("LIVEKIT_AGENT_NAME", "toothfairy-dental-agent-prod")
        
        # Initialize metadata if not provided
        dispatch_metadata_dict = metadata or {}
        
        logger.info(f"Creating LiveKit agent dispatch for room: {room_name}, agent: {agent_name}")
        
        lkapi = None
        dispatch_id = str(uuid.uuid4())
        
        try:
            lkapi = lk_api.LiveKitAPI(livekit_url, livekit_api_key, livekit_api_secret)
            
            # STEP 1: Check and delete existing room if it exists
            logger.debug(f"Checking if room '{room_name}' already exists...")
            try:
                rooms = await lkapi.room.list_rooms()
                existing_room = next((r for r in rooms if r.name == room_name), None)
                if existing_room:
                    logger.info(f"Room '{room_name}' already exists. Deleting it...")
                    await lkapi.room.delete_room(lk_api.RoomDeleteRequest(room=room_name))
                    logger.info(f"✓ Old room '{room_name}' deleted")
                    await asyncio.sleep(2)  # Wait for cleanup
            except Exception as room_check_error:
                logger.debug(f"Room check/delete note: {room_check_error}")
            
            # STEP 2: Dispatch agent to the room
            logger.info(f"Dispatching agent '{agent_name}' to room '{room_name}'...")
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                lk_api.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room_name,
                    metadata=str(dispatch_metadata_dict)
                )
            )
            
            logger.info(f"✓ Agent dispatched successfully to room: {room_name}")
            
            # Extract dispatch ID from response if available
            if dispatch and hasattr(dispatch, 'agent_job') and dispatch.agent_job:
                dispatch_id = dispatch.agent_job.id
            elif dispatch and hasattr(dispatch, 'agent_dispatch_id'):
                dispatch_id = dispatch.agent_dispatch_id
            
            # STEP 3: CRITICAL - Wait for agent to initialize (8-10 seconds)
            logger.info("⏳ Waiting 8 seconds for agent to initialize...")
            await asyncio.sleep(8)
            
            # STEP 4: Verify agent joined the room (optional but recommended)
            try:
                participants = await lkapi.room.list_participants(
                    lk_api.ListParticipantsRequest(room=room_name)
                )
                agent_in_room = any(p.identity.startswith('agent-') or p.kind == 'agent' for p in participants)
                if agent_in_room:
                    logger.info(f"✓ Agent confirmed in room (participants: {len(participants)})")
                else:
                    logger.warning(f"⚠️ Agent not yet visible in room (participants: {len(participants)})")
            except Exception as check_error:
                logger.debug(f"Could not verify agent in room: {check_error}")
            
        except Exception as dispatch_error:
            logger.error(f"Agent dispatch failed: {type(dispatch_error).__name__}: {str(dispatch_error)}")
            raise  # Re-raise to handle in outer try-catch
        finally:
            # Properly close the LiveKit API connection
            if lkapi:
                await lkapi.aclose()
        
        # STEP 5: Create access token for participant (after agent is ready)
        logger.debug(f"Creating AccessToken for identity: {participant_identity}")
        
        token = AccessToken(livekit_api_key, livekit_api_secret) \
            .with_identity(participant_identity) \
            .with_name(participant_name) \
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
        
        access_token = token.to_jwt()
        logger.debug(f"✓ AccessToken created successfully")
        
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
