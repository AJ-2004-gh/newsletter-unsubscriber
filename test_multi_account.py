"""
Test script for multi-account functionality
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gmail_auth import list_authenticated_accounts, get_gmail_service, get_authenticated_email

def test_multi_account():
    """Test multi-account functionality"""
    
    print("=" * 80)
    print("Testing Multi-Account Functionality")
    print("=" * 80)
    
    # Test 1: List authenticated accounts
    print("\n1. Listing authenticated accounts...")
    accounts = list_authenticated_accounts()
    
    if accounts:
        print(f"   Found {len(accounts)} authenticated account(s):")
        for i, email in enumerate(accounts, 1):
            print(f"   {i}. {email}")
    else:
        print("   No authenticated accounts found.")
        print("   Run 'python src/gmail_auth.py your@email.com' to add an account.")
        return
    
    # Test 2: Get service for first account
    print(f"\n2. Testing service for first account: {accounts[0]}")
    try:
        service = get_gmail_service(account_email=accounts[0])
        email = get_authenticated_email(service)
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"   ✓ Successfully authenticated as: {email}")
        print(f"   ✓ Total messages: {profile.get('messagesTotal')}")
        print(f"   ✓ Threads total: {profile.get('threadsTotal')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Test default account (no email specified)
    print("\n3. Testing default account (no email specified)...")
    try:
        service = get_gmail_service()
        email = get_authenticated_email(service)
        print(f"   ✓ Default account: {email}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Multi-account test complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_multi_account()
