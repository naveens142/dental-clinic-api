#!/usr/bin/env python3
"""
Test LiveKit agent dispatch functionality.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

# Setup path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)




async def test_agent_dispatch():
    """Test creating an agent dispatch."""
    print("\n" + "="*60)
    print("TEST: LiveKit Agent Dispatch")
    print("="*60)
    
    try:
        from utils.helpers import create_livekit_agent_dispatch
        
        # Test parameters
        room_name = "test_room_clinic_001"
        participant_identity = "doctor_user_123"
        participant_name = "Dr. Smith"
        agent_name = "dental_clinic_agent"
        
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        livekit_url = os.getenv("LIVEKIT_URL")
        
        print(f"\nDispatch Configuration:")
        print(f"  Room: {room_name}")
        print(f"  Participant: {participant_name} ({participant_identity})")
        print(f"  Agent: {agent_name}")
        print(f"  API Key: {livekit_api_key[:20]}...")
        print(f"  URL: {livekit_url}")
        
        # Metadata
        metadata = {
            "session_id": "sess_test001",
            "user_id": 1,
            "user_email": "test@example.com",
            "test": True
        }
        
        print(f"\nCreating agent dispatch...")
        result = await create_livekit_agent_dispatch(
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=participant_name,
            livekit_api_key=livekit_api_key,
            livekit_api_secret=livekit_api_secret,
            livekit_url=livekit_url,
            agent_name=agent_name,
            metadata=metadata
        )
        
        print(f"\n✓ Dispatch created successfully!")
        print(f"\nResponse:")
        for key, value in result.items():
            if key == "access_token":
                print(f"  {key}: {value[:50]}...")
            else:
                print(f"  {key}: {value}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print(f"\nInstall required packages:")
        print(f"  pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Dispatch failed: {type(e).__name__}: {str(e)}")
        logger.exception("Full error:")
        return False


async def main():
    print("\n" + "="*60)
    print("LIVEKIT AGENT DISPATCH TEST")
    print("="*60)
    
    print(f"\nConfiguration:")
    print(f"  LIVEKIT_URL: {os.getenv('LIVEKIT_URL')}")
    print(f"  LIVEKIT_API_KEY: {os.getenv('LIVEKIT_API_KEY', 'NOT SET')}")
    print(f"  LIVEKIT_API_SECRET: {'SET' if os.getenv('LIVEKIT_API_SECRET') else 'NOT SET'}")
    
    if await test_agent_dispatch():
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
