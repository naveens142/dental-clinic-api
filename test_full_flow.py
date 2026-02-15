import requests
import time
from datetime import datetime

# Configuration
FASTAPI_BASE_URL = "http://127.0.0.1:8000"
LOGIN_EMAIL = "westack@gmail.com"
LOGIN_PASSWORD = "westack.ai"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_complete_flow():
    """Test the complete user flow: Login → Create Session → Connect"""
    
    print_section("🔐 STEP 1: USER LOGIN")
    
    # Step 1: Login to get JWT token
    login_response = requests.post(
        f"{FASTAPI_BASE_URL}/api/v1/login",
        json={
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        },
        headers={"Content-Type": "application/json"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    login_data = login_response.json()
    jwt_token = login_data.get("token")
    user_info = login_data.get("user")
    
    print(f"✅ Login successful!")
    print(f"   User: {user_info.get('email')} (ID: {user_info.get('id')})")
    print(f"   JWT Token: {jwt_token[:50]}...")
    
    # Step 2: Create LiveKit session using JWT token
    print_section("🎫 STEP 2: CREATE LIVEKIT SESSION")
    print("⏳ Dispatching agent and creating session (this takes ~8-10 seconds)...")
    
    start_time = time.time()
    
    token_response = requests.post(
        f"{FASTAPI_BASE_URL}/api/v1/token",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "accept": "application/json"
        }
    )
    
    elapsed_time = time.time() - start_time
    
    if token_response.status_code != 200:
        print(f"❌ Token creation failed: {token_response.status_code}")
        print(token_response.text)
        return
    
    session_data = token_response.json()
    
    if not session_data.get("success"):
        print(f"❌ Session creation failed: {session_data.get('message')}")
        return
    
    data = session_data.get("data")
    
    print(f"✅ Session created successfully in {elapsed_time:.1f} seconds!")
    print(f"\n📊 Session Details:")
    print(f"   Session ID: {data.get('session_id')}")
    print(f"   Room Name: {data.get('room_name')}")
    print(f"   Participant ID: {data.get('participant_identity')}")
    print(f"   Agent Name: {data.get('agent_name')}")
    print(f"   Dispatch ID: {data.get('dispatch_id')}")
    
    # Step 3: Display connection information
    print_section("🎯 STEP 3: LIVEKIT CONNECTION INFO")
    print("\nUse these credentials in LiveKit Playground (Manual Mode):")
    print("-" * 70)
    print(f"WSS URL: {data.get('livekit_url')}")
    print(f"\nToken (copy this):")
    print(f"{data.get('access_token')}")
    print("-" * 70)
    
    # Step 4: Provide instructions
    print_section("📱 STEP 4: CONNECT TO AGENT")
    print("\n🔗 Option 1: LiveKit Playground (Manual Testing)")
    print("   1. Go to: https://agents-playground.livekit.io/")
    print("   2. Select 'Manual' mode")
    print("   3. Paste the WSS URL and Token from above")
    print("   4. Click 'Connect'")
    print("   5. Agent should greet you immediately!")
    
    print("\n💻 Option 2: Next.js Frontend Integration")
    print("   Use this data object in your React/Next.js component:")
    print(f"""
   const sessionData = {{
     livekitUrl: "{data.get('livekit_url')}",
     accessToken: "{data.get('access_token')[:50]}...",
     roomName: "{data.get('room_name')}",
     sessionId: "{data.get('session_id')}"
   }};
   
   // Then connect using LiveKit React SDK
   await room.connect(sessionData.livekitUrl, sessionData.accessToken);
   """)
    
    print_section("✨ TEST COMPLETE")
    print("\n🎉 All steps successful!")
    print(f"⏰ Total time: {elapsed_time:.1f} seconds")
    print("\n💡 The agent is now waiting in the room. Connect within the next few minutes.")
    
    return {
        "jwt_token": jwt_token,
        "livekit_url": data.get('livekit_url'),
        "access_token": data.get('access_token'),
        "room_name": data.get('room_name'),
        "session_id": data.get('session_id')
    }

if __name__ == "__main__":
    try:
        print("\n🚀 Starting Complete FastAPI + LiveKit Flow Test")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        result = test_complete_flow()
        
        if result:
            # Optional: Save credentials to file for easy access
            with open("livekit_credentials.txt", "w") as f:
                f.write(f"LiveKit Connection Credentials\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"\n{'='*70}\n")
                f.write(f"WSS URL: {result['livekit_url']}\n")
                f.write(f"Token: {result['access_token']}\n")
                f.write(f"Room: {result['room_name']}\n")
                f.write(f"Session ID: {result['session_id']}\n")
                f.write(f"{'='*70}\n")
            
            print("\n📄 Credentials also saved to: livekit_credentials.txt")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to FastAPI server")
        print(f"   Make sure your server is running at: {FASTAPI_BASE_URL}")
        print("   Run: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()