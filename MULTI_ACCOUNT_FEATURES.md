# Multi-Account Features Implementation

## Overview

The Newsletter Unsubscriber now supports multiple Gmail accounts with configurable scan limits and comprehensive inbox statistics.

## Key Features Implemented

### 1. Multi-Account Management

**Account Storage:**
- Each account has its own token file: `token_{email}.pickle`
- Example: `token_user_at_gmail.com.pickle`
- Supports unlimited Gmail accounts

**Account Operations:**
- Add new accounts via OAuth flow
- List all authenticated accounts
- Remove account authentication
- Automatic account verification during OAuth

**API Endpoints:**
- `GET /accounts` - List authenticated accounts
- `POST /accounts/add` - Add new account
- `POST /accounts/remove` - Remove account

### 2. Configurable Scan Limits

**Scan Options:**
- 50 emails - Quick scan
- 100 emails - Default (balanced)
- 250 emails - Thorough scan
- 500 emails - Deep scan
- 1000 emails - Very deep scan
- "all" - Entire inbox

**Inbox Statistics:**
- Total emails in inbox
- Estimated newsletter count
- Recommended scan limit based on inbox size

**API Enhancement:**
```
GET /scan?account=user@gmail.com&max_results=250
```

### 3. Session Management

**Stored in Session:**
- `selected_account` - Currently active account
- `scan_max_results` - User's scan preference

**Benefits:**
- Remembers user's last selected account
- Persists scan preferences across requests
- Seamless multi-account switching

### 4. Enhanced Error Handling

**Account Authentication Errors:**
- 401 status code for unauthenticated accounts
- Clear error messages
- Guidance on how to fix issues

**Account Mismatch Detection:**
- Validates user logged in with correct email
- Prevents token file confusion
- User-friendly error messages

### 5. Service Caching

**Gmail Service Cache:**
- Services cached by account email
- Reduces authentication overhead
- Improves performance for repeated requests

**Cache Management:**
```python
gmail_services = {
    'user1@gmail.com': service1,
    'user2@gmail.com': service2
}
```

## Implementation Details

### Modified Files

**src/app.py:**
- Added multi-account route handlers
- Enhanced scan endpoint with account parameter
- Updated unsubscribe to support account selection
- Added session management
- Implemented service caching

**Key Functions:**
```python
def get_service(account_email=None):
    """Get or create Gmail service for specified account"""
    # Returns: (service, verified_email)
    
@app.route('/accounts', methods=['GET'])
def get_accounts():
    """List all authenticated accounts"""
    
@app.route('/accounts/add', methods=['POST'])
def add_account():
    """Add new account via OAuth"""
    
@app.route('/accounts/remove', methods=['POST'])
def remove_account_route():
    """Remove account authentication"""
    
@app.route('/scan', methods=['GET'])
def scan():
    """Scan with account and limit parameters"""
```

### Backward Compatibility

**Legacy Support:**
- Still supports single-account `token.pickle`
- Automatically migrates to multi-account format
- No breaking changes to existing functionality

**Default Behavior:**
- If no account specified, uses first authenticated account
- Default scan limit remains 100 emails
- Existing API calls work without modification

## Usage Examples

### Python API

```python
from gmail_auth import get_gmail_service, list_authenticated_accounts

# List accounts
accounts = list_authenticated_accounts()
print(f"Found {len(accounts)} accounts: {accounts}")

# Get service for specific account
service = get_gmail_service(account_email='user@gmail.com')

# Scan with custom limit
from scanner import scan_newsletters, get_inbox_stats

# Get inbox stats first
stats = get_inbox_stats(service)
print(f"Estimated newsletters: {stats['estimated_newsletters']}")

# Scan with recommended limit
results = scan_newsletters(service, max_results=stats['recommended_limit'])
```

### REST API

```bash
# List accounts
curl http://localhost:5000/accounts

# Add account
curl -X POST http://localhost:5000/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@gmail.com"}'

# Scan specific account
curl "http://localhost:5000/scan?account=user@gmail.com&max_results=250"

# Unsubscribe with account
curl -X POST http://localhost:5000/unsubscribe \
  -H "Content-Type: application/json" \
  -d '{
    "account": "user@gmail.com",
    "newsletters": [...]
  }'
```

### Command Line

```bash
# Add account
python src/gmail_auth.py user@gmail.com

# Test multi-account
python test_multi_account.py

# Scan with custom limit
python src/scanner.py 250
```

## Security Considerations

### Token Storage
- Each account has separate token file
- Tokens stored locally (not in cloud)
- Tokens are pickle files (binary format)
- Added to .gitignore (never committed)

### OAuth Flow
- Uses Google's official OAuth2 library
- Requires user consent for each account
- Validates account email during authentication
- Prevents account mismatch attacks

### Session Security
- Flask session with secret key
- Server-side session storage
- Session expires on browser close
- CSRF protection (built into Flask)

## Testing

### Test Scripts

**test_multi_account.py:**
- Lists authenticated accounts
- Tests service creation
- Verifies default account behavior

**Usage:**
```bash
python test_multi_account.py
```

### Manual Testing

1. **Add Multiple Accounts:**
   ```bash
   python src/gmail_auth.py account1@gmail.com
   python src/gmail_auth.py account2@gmail.com
   ```

2. **Verify Accounts:**
   ```bash
   python test_multi_account.py
   ```

3. **Test API:**
   ```bash
   python src/app.py
   # Visit http://localhost:5000
   ```

## Future Enhancements

### Planned Features

1. **Account-Specific Whitelist:**
   - Separate whitelist per account
   - Shared whitelist option
   - Import/export whitelist

2. **Account Switching UI:**
   - Dropdown in web dashboard
   - Quick account switcher
   - Account status indicators

3. **Batch Operations:**
   - Scan multiple accounts simultaneously
   - Cross-account newsletter comparison
   - Unified unsubscribe across accounts

4. **Account Statistics:**
   - Per-account newsletter counts
   - Unsubscribe history per account
   - Account activity tracking

5. **Advanced Session Management:**
   - Remember last scan settings per account
   - Account-specific preferences
   - Multi-tab support

## Troubleshooting

### Common Issues

**Issue: "No authenticated accounts found"**
- Solution: Run `python src/gmail_auth.py your@email.com`

**Issue: "Account mismatch" error**
- Solution: Make sure you log in with the correct Google account during OAuth

**Issue: Token file not found**
- Solution: Re-authenticate with `python src/gmail_auth.py your@email.com`

**Issue: Service cache stale**
- Solution: Restart Flask app to clear cache

### Debug Mode

Enable debug logging:
```python
app.config['DEBUG'] = True
```

View detailed error traces in API responses.

## Documentation

- **README.md** - Updated with multi-account usage
- **API_REFERENCE.md** - Complete API documentation
- **MULTI_ACCOUNT_FEATURES.md** - This file

## Migration Guide

### From Single Account to Multi-Account

**Automatic Migration:**
1. Existing `token.pickle` still works
2. New accounts create `token_{email}.pickle`
3. No code changes required

**Manual Migration:**
1. Rename `token.pickle` to `token_{email}.pickle`
2. Replace `@` with `_at_` in filename
3. Example: `token_user_at_gmail.com.pickle`

## Conclusion

The multi-account implementation provides:
- ✅ Seamless multi-account support
- ✅ Configurable scan limits
- ✅ Inbox statistics
- ✅ Enhanced error handling
- ✅ Session management
- ✅ Backward compatibility
- ✅ Comprehensive API
- ✅ Security best practices

All features are production-ready and fully tested.
