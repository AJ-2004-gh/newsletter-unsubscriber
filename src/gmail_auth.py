"""
Gmail OAuth Authentication Module with Multi-Account Support

This module handles OAuth2 authentication with Gmail API.
It manages token storage, refresh, and the initial authorization flow.
Supports multiple Gmail accounts with account-specific token files.
"""

import os
import pickle
import glob
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Gmail API scopes - define what permissions we need
# readonly: Read email metadata and content
# modify: Mark emails as read, delete, modify labels
# send: Send emails (for mailto: unsubscribe links)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

# File paths for credentials and token storage
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE_PATTERN = 'token_{email}.pickle'  # Pattern for multi-account tokens
LEGACY_TOKEN_FILE = 'token.pickle'  # Legacy single-account token


def get_gmail_service(account_email=None):
    """
    Authenticate with Gmail API and return service object.
    Supports multiple Gmail accounts with account-specific token storage.
    
    OAuth2 Flow:
    1. Determine token file path based on account_email
    2. Check if we have stored credentials (token_{email}.pickle)
    3. If credentials exist, load them
    4. If credentials are expired, refresh them
    5. If no credentials exist, initiate OAuth2 flow:
       - Load client secrets from credentials.json
       - Open browser for user authorization
       - Validate user logged in with correct email (if specified)
       - Exchange authorization code for access token
       - Save token_{email}.pickle for future use
    6. Build and return Gmail API service object
    
    Args:
        account_email: Optional email address for multi-account support.
                      If None, uses legacy token.pickle or prompts for auth.
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Gmail API service
        
    Raises:
        FileNotFoundError: If credentials.json is missing
        ValueError: If user logs in with wrong email
        Exception: For authorization or network errors
    """
    creds = None
    
    # Determine token file path
    if account_email:
        # Multi-account: use account-specific token file
        token_file = TOKEN_FILE_PATTERN.format(email=account_email.replace('@', '_at_'))
    else:
        # Legacy: check for old token.pickle first, then any token_*.pickle
        if os.path.exists(LEGACY_TOKEN_FILE):
            token_file = LEGACY_TOKEN_FILE
        else:
            # Try to find any existing token file
            existing_tokens = glob.glob('token_*.pickle')
            if existing_tokens:
                token_file = existing_tokens[0]
                print(f"Using existing token: {token_file}")
            else:
                token_file = LEGACY_TOKEN_FILE
    
    # Step 1 & 2: Check if token file exists and load stored credentials
    if os.path.exists(token_file):
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
                print(f"Loaded existing credentials from {token_file}")
        except Exception as e:
            print(f"Error loading {token_file}: {e}")
            # If token is corrupted, we'll create a new one
            creds = None
    
    # Step 3: Check if credentials are valid or need refresh
    if creds and creds.expired and creds.refresh_token:
        try:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
            print("Credentials refreshed successfully")
        except Exception as e:
            print(f"Error refreshing credentials: {e}")
            # If refresh fails, we'll need to re-authenticate
            creds = None
    
    # Step 4: If no valid credentials, initiate OAuth2 flow
    if not creds or not creds.valid:
        # Check if credentials.json exists
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Missing {CREDENTIALS_FILE}. Please download it from Google Cloud Console:\n"
                "1. Go to https://console.cloud.google.com/\n"
                "2. Create a project and enable Gmail API\n"
                "3. Create OAuth 2.0 credentials (Desktop app)\n"
                "4. Download and save as credentials.json"
            )
        
        try:
            print("Starting OAuth2 authorization flow...")
            print("A browser window will open for you to authorize the application.")
            
            # Create OAuth2 flow from client secrets
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, 
                SCOPES
            )
            
            # Run local server to handle OAuth callback
            # This will open the browser automatically
            creds = flow.run_local_server(
                port=0,  # Use any available port
                prompt='consent',  # Force consent screen to show all scopes
                success_message='Authorization successful! You can close this window.'
            )
            
            print("Authorization successful!")
            
            # Validate account email if specified
            if account_email:
                try:
                    # Build temporary service to get user email
                    temp_service = build('gmail', 'v1', credentials=creds)
                    profile = temp_service.users().getProfile(userId='me').execute()
                    authenticated_email = profile.get('emailAddress')
                    
                    if authenticated_email.lower() != account_email.lower():
                        raise ValueError(
                            f"Account mismatch! You logged in with {authenticated_email} "
                            f"but requested {account_email}. Please try again with the correct account."
                        )
                    
                    print(f"Verified authentication for {authenticated_email}")
                    # Update token file name with verified email
                    token_file = TOKEN_FILE_PATTERN.format(email=authenticated_email.replace('@', '_at_'))
                    
                except HttpError as error:
                    print(f"Warning: Could not verify account email: {error}")
            
            # Save credentials for future use
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
                print(f"Credentials saved to {token_file}")
                
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Credentials file error: {e}")
        except Exception as e:
            raise Exception(f"Authorization failed: {e}")
    
    # Step 5: Build and return Gmail API service
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("Gmail API service created successfully")
        return service
    except HttpError as error:
        raise Exception(f"Failed to build Gmail service: {error}")
    except Exception as e:
        raise Exception(f"Network or connection error: {e}")


def get_authenticated_email(service):
    """
    Get the email address of the currently authenticated account.
    
    Args:
        service: Authenticated Gmail API service object
        
    Returns:
        str: Email address of the authenticated account
        
    Raises:
        HttpError: If unable to fetch user profile
    """
    try:
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress')
    except HttpError as error:
        print(f"Error fetching user profile: {error}")
        raise


def list_authenticated_accounts():
    """
    List all authenticated Gmail accounts.
    Scans for all token_*.pickle files and extracts email addresses.
    
    Returns:
        list: List of authenticated email addresses
    """
    accounts = []
    
    # Find all token files
    token_files = glob.glob('token_*.pickle')
    
    for token_file in token_files:
        try:
            # Extract email from filename: token_user_at_gmail.com.pickle -> user@gmail.com
            email = token_file.replace('token_', '').replace('.pickle', '').replace('_at_', '@')
            accounts.append(email)
        except Exception as e:
            print(f"Error parsing token file {token_file}: {e}")
    
    # Also check legacy token file
    if os.path.exists(LEGACY_TOKEN_FILE) and not accounts:
        try:
            with open(LEGACY_TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
                if creds and creds.valid:
                    # Try to get email from credentials
                    service = build('gmail', 'v1', credentials=creds)
                    email = get_authenticated_email(service)
                    accounts.append(email)
        except Exception as e:
            print(f"Error reading legacy token: {e}")
    
    return accounts


def remove_account(account_email):
    """
    Remove authentication for a specific Gmail account.
    Deletes the token_{email}.pickle file.
    
    Args:
        account_email: Email address of the account to remove
        
    Returns:
        bool: True if successful, False if account not found
    """
    if not account_email:
        return False
    
    # Determine token file path
    token_file = TOKEN_FILE_PATTERN.format(email=account_email.replace('@', '_at_'))
    
    if os.path.exists(token_file):
        try:
            os.remove(token_file)
            print(f"Removed authentication for {account_email}")
            return True
        except Exception as e:
            print(f"Error removing token file: {e}")
            return False
    else:
        print(f"No authentication found for {account_email}")
        return False


def revoke_credentials(account_email=None):
    """
    Revoke stored credentials and delete token file.
    Useful for logging out or switching accounts.
    
    Args:
        account_email: Optional email address. If None, removes legacy token.
    """
    if account_email:
        remove_account(account_email)
    else:
        # Remove legacy token
        if os.path.exists(LEGACY_TOKEN_FILE):
            try:
                os.remove(LEGACY_TOKEN_FILE)
                print(f"Removed {LEGACY_TOKEN_FILE}. You'll need to re-authorize on next use.")
            except Exception as e:
                print(f"Error removing token file: {e}")
        else:
            print("No stored credentials found.")


if __name__ == "__main__":
    # Test the authentication with multi-account support
    import sys
    
    print("Gmail Authentication Module - Multi-Account Support")
    print("=" * 60)
    
    # List existing accounts
    print("\nListing authenticated accounts...")
    accounts = list_authenticated_accounts()
    if accounts:
        print(f"Found {len(accounts)} authenticated account(s):")
        for i, email in enumerate(accounts, 1):
            print(f"  {i}. {email}")
    else:
        print("No authenticated accounts found.")
    
    # Test authentication
    print("\n" + "=" * 60)
    print("Testing authentication...")
    
    # Check if email provided as command line argument
    account_email = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        if account_email:
            print(f"Authenticating with specific account: {account_email}")
        else:
            print("Authenticating with default account...")
        
        service = get_gmail_service(account_email=account_email)
        
        # Get authenticated email
        email = get_authenticated_email(service)
        
        # Test API call - get user profile
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"\n✓ Authentication successful!")
        print(f"  Email: {email}")
        print(f"  Total messages: {profile.get('messagesTotal')}")
        print(f"  Threads total: {profile.get('threadsTotal')}")
        
    except ValueError as e:
        print(f"\n✗ Account mismatch: {e}")
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
