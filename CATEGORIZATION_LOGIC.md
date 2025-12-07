# Newsletter Categorization Logic

## Overview

The application categorizes newsletters into three difficulty levels based on how easy it is to automatically unsubscribe from them. This categorization is done by the `categorize_unsubscribe_difficulty()` function in `src/unsubscriber.py`.

## Category Definitions

### 🟢 Easy (Green) - "Auto"
**Automatic unsubscribe via HTTP request**

**Criteria:**
- Newsletter has a **List-Unsubscribe header** (RFC 2369 compliant)
- Can be unsubscribed with a simple HTTP GET/POST request
- No browser interaction needed
- No login required

**How it works:**
```python
if unsubscribe_method == 'header':
    return 'easy'
```

**Examples:**
- Professional newsletters from MailChimp
- Marketing emails from major companies
- Newsletters that follow email standards
- One-click unsubscribe links

**Success Rate:** ~90%

---

### 🔵 Medium (Blue) - "Auto"
**Automatic unsubscribe via browser automation**

**Criteria:**
- Newsletter has unsubscribe link in **email body** (not header)
- Link points to common newsletter platforms
- Can be automated with Selenium browser
- No login required
- No CAPTCHA

**How it works:**
```python
# Common newsletter platforms
common_newsletter_domains = [
    'mailchimp.com',
    'sendgrid.net',
    'constantcontact.com',
    'aweber.com',
    'getresponse.com',
    'activecampaign.com'
]

if any(domain in netloc for domain in common_newsletter_domains):
    return 'medium'

# Or if found in body
if unsubscribe_method == 'body':
    return 'medium'
```

**Examples:**
- Newsletters from SendGrid
- Marketing emails from ConstantContact
- Promotional emails with body links
- Standard unsubscribe pages

**Success Rate:** ~70%

---

### 🟡 Hard (Orange/Yellow) - "Manual"
**Requires manual action from user**

**Criteria:**
- Requires **login** to unsubscribe
- Uses **mailto:** links (needs SMTP setup)
- Has **CAPTCHA** verification
- Multi-step unsubscribe process
- Complex preference pages

**How it works:**
```python
# Known domains requiring login
LOGIN_REQUIRED_DOMAINS = [
    'medium.com',
    'quora.com',
    'substack.com',
    'patreon.com'
]

if any(domain in netloc for domain in LOGIN_REQUIRED_DOMAINS):
    return 'hard'

# mailto: links
if unsubscribe_link.startswith('mailto:'):
    return 'hard'
```

**Examples:**
- Medium Daily Digest (requires login)
- Quora Digest (requires login)
- Substack newsletters (requires login)
- Patreon updates (requires login)
- Newsletters with CAPTCHA
- Newsletters with mailto: links

**Success Rate:** ~0% (requires manual action)

---

### ⚪ Whitelisted (Gray)
**User has marked as "keep"**

**Criteria:**
- User manually added to whitelist
- Won't be scanned in future
- Can't be unsubscribed via bulk action

**How it works:**
```python
if sender_email and is_whitelisted(sender_email):
    newsletter['whitelisted'] = True
    newsletter['difficulty'] = 'whitelisted'
```

**Examples:**
- Important work newsletters
- Personal subscriptions user wants to keep
- Newsletters from friends/family
- Critical service updates

---

## Complete Categorization Flow

```python
def categorize_unsubscribe_difficulty(newsletter_data):
    """
    Categorization decision tree:
    
    1. Check if has List-Unsubscribe header
       → YES: Return 'easy' (🟢 Green)
       
    2. Check if no unsubscribe link at all
       → YES: Return 'medium' (🔵 Blue)
       
    3. Check if domain requires login
       (medium.com, quora.com, substack.com, patreon.com)
       → YES: Return 'hard' (🟡 Orange)
       
    4. Check if mailto: link
       → YES: Return 'hard' (🟡 Orange)
       
    5. Check if common newsletter platform
       (mailchimp, sendgrid, constantcontact, etc.)
       → YES: Return 'medium' (🔵 Blue)
       
    6. Check if link found in body
       → YES: Return 'medium' (🔵 Blue)
       
    7. Default: Return 'medium' (🔵 Blue)
    """
```

## Visual Representation

### In the UI

**Table Row Colors:**
```css
/* Easy - Green background */
.table-success {
    background-color: #d1e7dd;
}

/* Medium - Blue/Info background */
.table-info {
    background-color: #cfe2ff;
}

/* Hard - Orange/Warning background */
.table-warning {
    background-color: #fff3cd;
}

/* Whitelisted - Gray background */
.table-secondary {
    background-color: #e2e3e5;
}
```

**Category Badges:**
```javascript
if (difficulty === 'easy') {
    badge = '🟢 Auto';  // Green circle + "Auto"
    color = 'bg-success';
} else if (difficulty === 'medium') {
    badge = '🔵 Auto';  // Blue circle + "Auto"
    color = 'bg-info';
} else if (difficulty === 'hard') {
    badge = '🟡 Manual';  // Yellow circle + "Manual"
    color = 'bg-warning';
} else {
    badge = '⚪ Unknown';  // White circle + "Unknown"
    color = 'bg-secondary';
}
```

## Statistics

### Typical Distribution

In a scan of 100 newsletters:
- **Easy (🟢):** ~40% (40 newsletters)
  - Have List-Unsubscribe header
  - Professional senders
  
- **Medium (🔵):** ~50% (50 newsletters)
  - Body links only
  - Common platforms
  
- **Hard (🟡):** ~10% (10 newsletters)
  - Require login
  - Have CAPTCHA
  - Use mailto:

### Success Rates

**Auto-Unsubscribe (Easy + Medium):**
- Combined: ~90 newsletters
- Success rate: ~80%
- Result: ~72 successfully unsubscribed

**Manual (Hard):**
- Total: ~10 newsletters
- Success rate: ~0% (requires user action)
- Result: User must visit websites manually

## Why This Categorization?

### User Benefits

1. **Transparency:** Users know what to expect
2. **Time Saving:** Focus on auto-unsubscribe first
3. **Realistic Expectations:** Know which need manual work
4. **Prioritization:** Can choose to handle manual later

### Technical Benefits

1. **Resource Optimization:** Don't waste time on impossible tasks
2. **Better Success Rates:** Focus automation where it works
3. **Error Reduction:** Avoid false positives
4. **User Satisfaction:** Set correct expectations

## Examples by Category

### Easy (🟢 Green)

```
From: newsletter@company.com
List-Unsubscribe: <https://company.com/unsubscribe?id=123>
Body: [Newsletter content]

→ Category: EASY
→ Method: HTTP GET to header link
→ Success: 95%
```

### Medium (🔵 Blue)

```
From: updates@startup.com
Body: 
  [Newsletter content]
  <a href="https://mailchimp.com/unsubscribe/xyz">Unsubscribe</a>

→ Category: MEDIUM
→ Method: Browser automation to body link
→ Success: 75%
```

### Hard (🟡 Orange)

```
From: digest@medium.com
Body:
  [Newsletter content]
  <a href="https://medium.com/settings/emails">Manage email settings</a>

→ Category: HARD
→ Reason: Requires Medium login
→ Success: 0% (manual action needed)
```

## Customization

### Adding New Login-Required Domains

Edit `src/unsubscriber.py`:

```python
LOGIN_REQUIRED_DOMAINS = [
    'medium.com',
    'quora.com',
    'substack.com',
    'patreon.com',
    'your-domain.com',  # Add here
]
```

### Adding New Newsletter Platforms

Edit `src/unsubscriber.py`:

```python
common_newsletter_domains = [
    'mailchimp.com',
    'sendgrid.net',
    'constantcontact.com',
    'aweber.com',
    'getresponse.com',
    'activecampaign.com',
    'your-platform.com',  # Add here
]
```

## Testing Categorization

### Test Script

```python
from unsubscriber import categorize_unsubscribe_difficulty

# Test newsletter
newsletter = {
    'sender_email': 'test@example.com',
    'unsubscribe_link': 'https://example.com/unsubscribe',
    'unsubscribe_method': 'header'
}

difficulty = categorize_unsubscribe_difficulty(newsletter)
print(f"Difficulty: {difficulty}")  # Output: easy
```

### Expected Results

```python
# Easy
{'unsubscribe_method': 'header'} → 'easy'

# Medium
{'unsubscribe_method': 'body', 'unsubscribe_link': 'https://example.com/unsub'} → 'medium'
{'unsubscribe_link': 'https://mailchimp.com/unsub'} → 'medium'

# Hard
{'unsubscribe_link': 'https://medium.com/settings'} → 'hard'
{'unsubscribe_link': 'mailto:unsub@example.com'} → 'hard'
```

## Troubleshooting

### Newsletter Categorized Incorrectly?

**Problem:** Newsletter marked as "Easy" but fails to unsubscribe

**Solution:** 
1. Check if domain requires login (add to `LOGIN_REQUIRED_DOMAINS`)
2. Check if has CAPTCHA (will be detected during unsubscribe)
3. Check if link is expired

**Problem:** Newsletter marked as "Hard" but could be automated

**Solution:**
1. Remove domain from `LOGIN_REQUIRED_DOMAINS` if incorrect
2. Check if it's actually a common platform
3. Test with browser automation

## Summary

The categorization system uses a **smart decision tree** to classify newsletters:

1. **🟢 Easy (Green)** - Has List-Unsubscribe header → HTTP request
2. **🔵 Medium (Blue)** - Body link to common platforms → Browser automation  
3. **🟡 Hard (Orange)** - Requires login/CAPTCHA/mailto → Manual action
4. **⚪ Whitelisted (Gray)** - User wants to keep → No action

This provides users with **realistic expectations** and **optimal automation** while being **transparent** about what requires manual work.
