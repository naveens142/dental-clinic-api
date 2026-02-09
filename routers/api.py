import os
import sys

# Add project root to Python path for reliable imports in cloud deployment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from models.schemas import LoginRequest, LoginResponse, SessionCreateResponse
from utils.helpers import (
    validate_environment,
    generate_room_name,
    generate_participant_identity,
    verify_jwt_token,
    generate_livekit_token
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
        db = get_db()
        user = db.login(request.email, request.password)
        if user:
            token = create_access_token({"email": user["email"], "id": user["id"]})
            logger.info(f"Successful login: {request.email}")
            return LoginResponse(success=True, message="Login successful", token=token, user={"id": user["id"], "email": user["email"]})
        else:
            logger.warning(f"Failed login: {request.email} (invalid credentials)")
            return LoginResponse(success=False, message="Invalid email or password")
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return LoginResponse(success=False, message="Authentication error. Please try again.")

@router.post("/api/v1/token", response_model=SessionCreateResponse)
async def create_session(token_payload: dict = Depends(verify_jwt_token)) -> SessionCreateResponse:
    db = None
    try:
        validate_environment()
        room_name = generate_room_name("toothfairy")
        participant_identity = generate_participant_identity()
        user_email = token_payload.get("email", "unknown")
        logger.info(f"Creating session for user: {user_email}, room: {room_name}")
        db = get_db()
        session_id = db.create_session(room_name)
        logger.info(f"Created database session: {session_id}")
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        jwt_token = generate_livekit_token(
            room_name=room_name,
            participant_identity=participant_identity,
            session_id=session_id,
            livekit_url=livekit_url,
            livekit_api_key=livekit_api_key,
            livekit_api_secret=livekit_api_secret
        )
        user_id = token_payload.get("id")
        user_email = token_payload.get("email")
        response_data = {
            "user_id": user_id,
            "user_email": user_email,
            "livekit_url": livekit_url,
            "jwt_token": jwt_token
        }
        logger.info(f"Session created successfully: {session_id}")
        return SessionCreateResponse(success=True, message="Session created successfully", data=response_data, error=None)
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
