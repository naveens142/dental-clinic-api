# CRITICAL: Path setup must be first thing before any local imports
import os
import sys

# Compute API and project root directories
api_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(api_file_dir)

# Ensure project root is at the front of sys.path so absolute imports like
# `import models` resolve correctly in deployment environments.
if not sys.path or sys.path[0] != project_root:
    if project_root in sys.path:
        sys.path.remove(project_root)
    sys.path.insert(0, project_root)

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

# Import local application modules (project_root is on sys.path)
from models.schemas import LoginRequest, LoginResponse, SessionCreateResponse
from utils.helpers import (
    validate_environment,
    generate_room_name,
    generate_participant_identity,
    verify_jwt_token,
    generate_livekit_token,
    create_livekit_agent_dispatch,
)
from database_service import get_db
from jwt_utils import create_access_token
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Dental Clinic Agent API",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/api/v1/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    db = None
    try:
        if not request.email or not request.password:
            logger.warning("Login attempt with missing credentials")
            return LoginResponse(success=False, message="Email and password are required")
        
        logger.info(f"Attempting login for user: {request.email}")
        db = get_db()
        user = db.login(request.email, request.password)
        
        if user:
            try:
                token = create_access_token({"email": user["email"], "id": user["id"]})
                logger.info(f"Successful login: {request.email}")
                return LoginResponse(success=True, message="Login successful", token=token, user={"id": user["id"], "email": user["email"]})
            except Exception as token_error:
                logger.error(f"Token creation error for {request.email}: {str(token_error)}", exc_info=True)
                return LoginResponse(success=False, message="Token generation failed. Please try again.")
        else:
            logger.warning(f"Failed login: {request.email} (invalid credentials)")
            return LoginResponse(success=False, message="Invalid email or password")
    except Exception as e:
        logger.error(f"Login error for {request.email}: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.debug(f"Full login exception details", exc_info=True)
        return LoginResponse(success=False, message="Authentication error. Please try again.")

@router.post("/api/v1/token", response_model=SessionCreateResponse)
async def create_session(token_payload: dict = Depends(verify_jwt_token)) -> SessionCreateResponse:
    db = None
    try:
        validate_environment()
        room_name = generate_room_name("toothfairy")
        participant_identity = generate_participant_identity()
        user_email = token_payload.get("email", "unknown")
        user_id = token_payload.get("id")
        
        logger.info(f"Creating session for user: {user_email} (ID: {user_id}), room: {room_name}")
        
        # Create database session record
        db = get_db()
        session_id = db.create_session(room_name)
        logger.info(f"Created database session: {session_id}")
        
        # Get LiveKit configuration
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        # Create agent dispatch with explicit VideoGrants
        logger.info(f"Creating LiveKit agent dispatch for session: {session_id}")
        dispatch_metadata = {
            "session_id": session_id,
            "user_id": user_id,
            "user_email": user_email,
            "created_at": datetime.now().isoformat()
        }
        
        dispatch_result = await create_livekit_agent_dispatch(
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=user_email,
            livekit_api_key=livekit_api_key,
            livekit_api_secret=livekit_api_secret,
            livekit_url=livekit_url,
            agent_name=os.getenv("LIVEKIT_AGENT_NAME", "toothfairy-dental-agent"),
            metadata=dispatch_metadata
        )
        
        logger.info(f"✓ Agent dispatch created: {dispatch_result.get('dispatch_id')}")
        
        # Response data for client connection
        # IMPORTANT: Only send access_token to client (not API keys - security risk)
        # Client uses access_token to authenticate with LiveKit server
        response_data = {
            "user_id": user_id,
            "user_email": user_email,
            "session_id": session_id,
            "livekit_url": livekit_url,
            "room_name": room_name,
            "participant_identity": participant_identity,
            "participant_name": user_email,
            "agent_name": os.getenv("LIVEKIT_AGENT_NAME", "toothfairy-dental-agent"),
            "dispatch_id": dispatch_result.get("dispatch_id"),
            "access_token": dispatch_result.get("access_token"),
        }
        
        logger.info(f"✓ Session created successfully: {session_id}")
        logger.debug(f"Token details - ID: {participant_identity}, Room: {room_name}")
        return SessionCreateResponse(
            success=True, 
            message="Session created successfully with agent dispatch", 
            data=response_data, 
            error=None
        )
        
    except EnvironmentError as e:
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to create session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if db:
            try:
                db.close() if hasattr(db, 'close') else None
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")

@router.get("/")
async def root():
    return JSONResponse(
        status_code=200,
        content={
            "message": "Welcome to the Dental Clinic Agent API. See /docs for usage.",
            "status": "ok"
        }
    )
