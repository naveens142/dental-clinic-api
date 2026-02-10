f"""
FastAPI Service for Dental Clinic Agent
Provides REST endpoints for session creation and LiveKit integration.
"""

# CRITICAL: Path setup must be first thing before any local imports
import os
import sys

# Get the directory where this script is located (project root)
project_root = os.path.dirname(os.path.abspath(__file__))

# Ensure project root is at the front of sys.path for absolute imports
if not sys.path or sys.path[0] != project_root:
    if project_root in sys.path:
        sys.path.remove(project_root)
    sys.path.insert(0, project_root)

import logging
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers.api import router as api_router

# Load environment variables
load_dotenv(".env")

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Dental Clinic Agent API",
    description="API for managing LiveKit sessions with the dental clinic agent",
    version="1.0.0"
)
# ============================================================================
# MIDDLEWARE - CORS, COMPRESSION, LOGGING
# ============================================================================

# CORS Middleware - Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    if path != "/health":
        logger.info(f"→ {method} {path}")
    
    try:
        response = await call_next(request)
        elapsed = time.time() - start_time
        
        if path != "/health":
            logger.info(f"← {method} {path} | Status: {response.status_code} | Time: {elapsed:.3f}s")
        
        return response
    except Exception as e:
        logger.error(f"✗ {method} {path} | Error: {str(e)}")
        raise

# Routers
app.include_router(api_router)


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("FastAPI service started successfully")



@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("FastAPI service shutting down")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": "Validation error",
            "data": None,
            "error": str(exc)
        }
    )
