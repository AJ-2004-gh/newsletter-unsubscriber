from src.gmail_auth import get_gmail_service

print("Testing Gmail authentication...")

try:
    service = get_gmail_service()
    print("✅ Authentication successful!")
    
    # Test by getting user profile
    profile = service.users().getProfile(userId='me').execute()
    print(f"✅ Connected to: {profile['emailAddress']}")
    print(f"✅ Total messages in account: {profile['messagesTotal']}")
    
except FileNotFoundError:
    print("❌ credentials.json not found!")
    print("Download it from Google Cloud Console")
    
except Exception as e:
    print(f"❌ Error: {e}")