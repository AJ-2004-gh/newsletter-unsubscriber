# API Reference - Newsletter Unsubscriber

Complete reference for all API endpoints with multi-account support.

## Account Management

### GET /accounts
List all authenticated Gmail accounts.

**Response:**
```json
{
  "success": true,
  "accounts": ["user1@gmail.com", "user2@gmail.com"],
  "count": 2
}
```

### POST /accounts/add
Add a new Gmail account by initiating OAuth flow.

**Request:**
```json
{
  "email": "newuser@gmail.com"
}
```

**Response:**
```json
{
  "success": true,
  "email": "newuser@gmail.com",
  "message": "Successfully authenticated newuser@gmail.com"
}
```

**Error Response (Account Mismatch):**
```json
{
  "success": false,
  "error": "Account mismatch...",
  "message": "Account mismatch. Please log in with the correct account."
}
```

### POST /accounts/remove
Remove authentication for a Gmail account.

**Request:**
```json
{
  "email": "user@gmail.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Removed authentication for user@gmail.com"
}
```

## Newsletter Scanning

### GET /scan
Scan Gmail inbox for newsletters with configurable limits.

**Query Parameters:**
- `account` (optional): Email address of account to scan. Default: first authenticated account
- `max_results` (optional): Number of emails to scan. Options: 50, 100, 250, 500, 1000, "all". Default: 100

**Example:**
```
GET /scan?account=user@gmail.com&max_results=250
```

**Response:**
```json
{
  "success": true,
  "account": "user@gmail.com",
  "newsletters": [
    {
      "id": "msg123",
      "sender_email": "newsletter@example.com",
      "sender_name": "Example Newsletter",
      "subject": "Weekly Update",
      "date": "2025-12-07T10:30:00",
      "unsubscribe_link": "https://example.com/unsubscribe",
      "unsubscribe_method": "header",
      "difficulty": "easy",
      "whitelisted": false
    }
  ],
  "count": 45,
  "total_found": 45,
  "total_scanned": 100,
  "scan_limit": 100,
  "inbox_stats": {
    "total_emails": 5234,
    "estimated_newsletters": 156,
    "recommended_limit": 250
  },
  "categories": {
    "easy": 30,
    "medium": 10,
    "hard": 5,
    "whitelisted": 0
  }
}
```

**Error Response (Not Authenticated):**
```json
{
  "success": false,
  "error": "Account not authenticated",
  "message": "Account not authenticated. Please add the account first."
}
```

## Unsubscribe Operations

### POST /unsubscribe
Unsubscribe from selected newsletters.

**Request:**
```json
{
  "account": "user@gmail.com",
  "newsletters": [
    {
      "id": "msg123",
      "sender_email": "newsletter@example.com",
      "sender_name": "Example Newsletter",
      "unsubscribe_link": "https://example.com/unsubscribe"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "account": "user@gmail.com",
  "total": 3,
  "auto_success": 2,
  "manual_required": 1,
  "failed": 0,
  "details": [
    {
      "id": "msg123",
      "sender_name": "Example Newsletter",
      "sender_email": "newsletter@example.com",
      "status": "auto_success",
      "method": "header",
      "message": "Successfully unsubscribed",
      "unsubscribe_url": null
    },
    {
      "id": "msg456",
      "sender_name": "Another Newsletter",
      "sender_email": "news@another.com",
      "status": "manual_required",
      "method": "login_required",
      "message": "Login required - please complete manually",
      "unsubscribe_url": "https://another.com/unsubscribe"
    }
  ]
}
```

## Whitelist Management

### POST /whitelist/add
Add sender to whitelist.

**Request:**
```json
{
  "sender_email": "important@example.com",
  "sender_name": "Important Newsletter",
  "account": "user@gmail.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Added important@example.com to whitelist"
}
```

### POST /whitelist/remove
Remove sender from whitelist.

**Request:**
```json
{
  "sender_email": "important@example.com",
  "account": "user@gmail.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Removed important@example.com from whitelist"
}
```

### GET /whitelist
Get all whitelisted senders.

**Query Parameters:**
- `account` (optional): Filter by account (for future account-specific whitelist)

**Example:**
```
GET /whitelist?account=user@gmail.com
```

**Response:**
```json
{
  "success": true,
  "account": "user@gmail.com",
  "whitelist": [
    {
      "id": 1,
      "sender_email": "important@example.com",
      "sender_name": "Important Newsletter",
      "added_date": "2025-12-07T10:00:00"
    }
  ],
  "count": 1
}
```

## Manual Unsubscribe

### GET /newsletter/<id>/manual-link
Get unsubscribe URL for manual action.

**Query Parameters:**
- `url`: The unsubscribe URL

**Example:**
```
GET /newsletter/msg123/manual-link?url=https://example.com/unsubscribe
```

**Response:**
```json
{
  "success": true,
  "newsletter_id": "msg123",
  "unsubscribe_url": "https://example.com/unsubscribe",
  "message": "Please complete unsubscribe manually in your browser"
}
```

## Health Check

### GET /health
Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-07T12:34:56.789Z"
}
```

## Error Responses

All endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "success": false,
  "error": "Missing required parameter",
  "message": "User-friendly error message"
}
```

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "Account not authenticated",
  "message": "Account not authenticated. Please add the account first."
}
```

**404 Not Found:**
```json
{
  "success": false,
  "error": "Not found",
  "message": "The requested resource was not found"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "error": "Exception message",
  "error_type": "ValueError",
  "message": "User-friendly error message",
  "details": "Stack trace (only in debug mode)"
}
```

## Session Management

The application stores session data:
- `selected_account`: Currently selected Gmail account
- `scan_max_results`: User's preferred scan limit

Sessions are managed automatically by Flask and stored server-side.

## Rate Limiting

The application implements rate limiting for unsubscribe operations:
- 2-second delay between unsubscribe requests
- Prevents overwhelming newsletter servers
- Reduces risk of being flagged as spam

## CORS

CORS is enabled for local development. In production, configure CORS to only allow your frontend domain.
