# Quick Start Guide - Multi-Account Newsletter Unsubscriber

## 5-Minute Setup

### Step 1: Install Dependencies (1 min)
```bash
cd "Newsletter Unsubscriber"
pip install -r requirements.txt
```

### Step 2: Get Gmail API Credentials (2 min)
1. Visit: https://console.cloud.google.com/
2. Create project → Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download as `credentials.json` in project root

### Step 3: Add Your First Account (1 min)
```bash
python src/gmail_auth.py your@gmail.com
```
- Browser will open for authorization
- Grant permissions
- Token saved automatically

### Step 4: Start the Application (1 min)
```bash
python src/app.py
```
- Open: http://localhost:5000
- Click "Scan My Inbox"
- Review newsletters
- Unsubscribe!

## Adding More Accounts

### Method 1: Command Line
```bash
python src/gmail_auth.py second@gmail.com
python src/gmail_auth.py third@gmail.com
```

### Method 2: API Call
```bash
curl -X POST http://localhost:5000/accounts/add \
  -H "Content-Type: application/json" \
  -d '{"email": "second@gmail.com"}'
```

## Common Tasks

### List All Accounts
```bash
curl http://localhost:5000/accounts
```

### Scan Specific Account
```bash
curl "http://localhost:5000/scan?account=your@gmail.com&max_results=100"
```

### Remove Account
```bash
curl -X POST http://localhost:5000/accounts/remove \
  -H "Content-Type: application/json" \
  -d '{"email": "old@gmail.com"}'
```

## Scan Limits Explained

| Limit | Use Case | Time |
|-------|----------|------|
| 50 | Quick check for recent newsletters | ~10 sec |
| 100 | Default, balanced scan | ~20 sec |
| 250 | Thorough scan | ~45 sec |
| 500 | Deep scan | ~90 sec |
| 1000 | Very deep scan | ~3 min |
| all | Entire inbox | Varies |

## Troubleshooting

### "No authenticated accounts found"
```bash
python src/gmail_auth.py your@gmail.com
```

### "Account mismatch" error
- Make sure you log in with the correct Google account
- Close all Google sessions and try again

### "credentials.json not found"
- Download from Google Cloud Console
- Place in project root directory

### Port 5000 already in use
```bash
# Change port in src/app.py:
app.run(port=5001)
```

## Testing

### Test Multi-Account Setup
```bash
python test_multi_account.py
```

Expected output:
```
Found 2 authenticated account(s):
  1. user1@gmail.com
  2. user2@gmail.com
✓ Successfully authenticated as: user1@gmail.com
```

## What's Next?

1. **Scan your inbox** - Find all newsletters
2. **Review categories** - Easy/Medium/Hard to unsubscribe
3. **Whitelist keepers** - Mark newsletters you want
4. **Bulk unsubscribe** - Clean up your inbox
5. **Add more accounts** - Manage multiple Gmail accounts

## Need Help?

- **API Documentation**: See `API_REFERENCE.md`
- **Feature Details**: See `MULTI_ACCOUNT_FEATURES.md`
- **Full README**: See `README.md`

## Pro Tips

💡 **Use inbox stats** - Check estimated newsletter count before scanning
💡 **Start small** - Try 100 emails first, then increase if needed
💡 **Whitelist first** - Mark important newsletters before unsubscribing
💡 **Multiple accounts** - Scan all your Gmail accounts in one place
💡 **Session persistence** - Your last account selection is remembered

Happy unsubscribing! 🎉
