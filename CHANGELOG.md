# Changelog

All notable changes to the Newsletter Unsubscriber project.

## [2.0.0] - 2025-12-07

### Added - Multi-Account Support

#### Account Management
- **Multi-account authentication** - Support for unlimited Gmail accounts
- **Account-specific tokens** - Each account has its own `token_{email}.pickle` file
- **Account verification** - Validates user logged in with correct email during OAuth
- **Service caching** - Caches Gmail services by account for improved performance
- **Account listing** - `GET /accounts` endpoint to list all authenticated accounts
- **Account addition** - `POST /accounts/add` endpoint to add new accounts via OAuth
- **Account removal** - `POST /accounts/remove` endpoint to remove account authentication

#### Enhanced Scanning
- **Account selection** - Scan specific accounts via `?account=email` parameter
- **Configurable scan limits** - Choose from 50, 100, 250, 500, 1000, or "all" emails
- **Inbox statistics** - Get total emails, estimated newsletters, and recommended limit before scanning
- **Smart defaults** - Uses first authenticated account if none specified
- **Scan limit validation** - Validates and defaults to 100 if invalid limit provided

#### Session Management
- **Account persistence** - Remembers last selected account in session
- **Preference storage** - Stores scan limit preference in session
- **Automatic session handling** - Flask manages sessions automatically

#### Enhanced API Responses
- **Account information** - All responses include account email
- **Inbox statistics** - Scan responses include inbox stats
- **Scan metadata** - Responses include total_scanned, total_found, scan_limit
- **Comprehensive error messages** - Clear guidance on how to fix issues

#### Error Handling
- **401 Unauthorized** - Proper status code for unauthenticated accounts
- **Account mismatch detection** - Prevents wrong account authentication
- **Detailed error responses** - Includes error type, message, and debug details
- **User-friendly messages** - Clear instructions for resolving issues

### Changed

#### API Endpoints
- **GET /scan** - Now accepts `account` and `max_results` parameters
- **POST /unsubscribe** - Now accepts `account` parameter in request body
- **POST /whitelist/add** - Now accepts optional `account` parameter
- **POST /whitelist/remove** - Now accepts optional `account` parameter
- **GET /whitelist** - Now accepts optional `account` query parameter

#### Internal Functions
- **get_service()** - Now accepts `account_email` parameter and returns tuple `(service, email)`
- **Service caching** - Changed from single global service to dictionary of services
- **Default behavior** - Uses first authenticated account instead of requiring authentication

### Documentation

#### New Documentation Files
- **API_REFERENCE.md** - Complete API documentation with examples
- **MULTI_ACCOUNT_FEATURES.md** - Detailed feature documentation
- **IMPLEMENTATION_SUMMARY.md** - Implementation details and status
- **QUICKSTART.md** - 5-minute setup guide
- **CHANGELOG.md** - This file

#### Updated Documentation
- **README.md** - Added multi-account usage instructions and examples

#### Test Files
- **test_multi_account.py** - Test script for multi-account functionality

### Backward Compatibility

#### Maintained
- ✅ Legacy `token.pickle` still supported
- ✅ Single-account usage works without changes
- ✅ All existing API endpoints work without modification
- ✅ Default behavior unchanged (uses first account)
- ✅ No breaking changes to existing functionality

#### Migration Path
- Existing single-account setups continue to work
- Can gradually add more accounts
- Automatic migration from legacy token format

### Security

#### Enhanced
- Account-specific token storage
- OAuth2 account verification
- Session security with secret key
- Account mismatch prevention

#### Maintained
- Tokens in .gitignore
- CORS for development
- Secure OAuth2 flow
- No credentials in code

## [1.0.0] - 2025-12-06

### Initial Release

#### Core Features
- Gmail OAuth authentication
- Newsletter scanning with List-Unsubscribe header detection
- Body link extraction for unsubscribe URLs
- Smart categorization (easy/medium/hard)
- Bulk unsubscribe functionality
- Whitelist management
- Web-based dashboard
- Responsive UI with Bootstrap 5

#### Modules
- `gmail_auth.py` - Gmail authentication
- `scanner.py` - Email scanning and link extraction
- `unsubscriber.py` - Unsubscribe automation
- `whitelist.py` - SQLite-based whitelist management
- `app.py` - Flask web application

#### API Endpoints
- `GET /` - Dashboard
- `GET /scan` - Scan newsletters
- `POST /unsubscribe` - Batch unsubscribe
- `POST /whitelist/add` - Add to whitelist
- `POST /whitelist/remove` - Remove from whitelist
- `GET /whitelist` - Get whitelist
- `GET /newsletter/<id>/manual-link` - Get manual unsubscribe link
- `GET /health` - Health check

#### UI Features
- Stats cards (total, auto, manual)
- Filter tabs (all/auto/manual/whitelisted)
- Bulk selection controls
- Confirmation modals
- Results display
- Toast notifications
- Responsive design

---

## Version History

- **2.0.0** (2025-12-07) - Multi-account support and configurable scan limits
- **1.0.0** (2025-12-06) - Initial release with single-account support

## Upgrade Guide

### From 1.0.0 to 2.0.0

**No action required!** The upgrade is fully backward compatible.

**Optional: Add more accounts**
```bash
python src/gmail_auth.py second@gmail.com
```

**Optional: Use new features**
```bash
# Scan with custom limit
curl "http://localhost:5000/scan?max_results=250"

# Scan specific account
curl "http://localhost:5000/scan?account=user@gmail.com"
```

## Future Roadmap

### Planned for 3.0.0
- [ ] Account-specific whitelist
- [ ] Account switcher UI in dashboard
- [ ] Batch operations across multiple accounts
- [ ] Account statistics and analytics
- [ ] Import/export whitelist
- [ ] Scheduled scans
- [ ] Email notifications
- [ ] Advanced filtering options

### Under Consideration
- [ ] Browser extension
- [ ] Mobile app
- [ ] Cloud deployment option
- [ ] Team/organization features
- [ ] API rate limiting
- [ ] Webhook support
- [ ] Integration with other email providers

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## License

See LICENSE file for details.
