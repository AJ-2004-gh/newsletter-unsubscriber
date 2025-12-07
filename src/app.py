"""
Flask Web Application for Newsletter Unsubscriber

Provides a web interface for scanning, managing, and unsubscribing from newsletters.
Supports multiple Gmail accounts and configurable scan limits.
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from datetime import datetime
import os
import sys

# Import our modules
from gmail_auth import (
    get_gmail_service,
    get_authenticated_email,
    list_authenticated_accounts,
    remove_account
)
from scanner import scan_newsletters, get_inbox_stats
from unsubscriber import (
    unsubscribe_from_newsletter,
    batch_unsubscribe,
    categorize_unsubscribe_difficulty
)
from whitelist import (
    init_database,
    add_to_whitelist,
    remove_from_whitelist,
    is_whitelisted,
    get_all_whitelisted
)


# Get the parent directory (Newsletter Unsubscriber folder)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Initialize Flask app with correct template and static folders
app = Flask(__name__,
            template_folder=os.path.join(parent_dir, 'templates'),
            static_folder=os.path.join(parent_dir, 'static'))
app.secret_key = os.urandom(24)  # For session management
app.config['DEBUG'] = True

# Enable CORS for local development
CORS(app)

# Initialize database on startup
init_database()

# Global cache for Gmail services (keyed by account email)
gmail_services = {}


def get_service(account_email=None):
    """
    Get or create Gmail service instance for specified account.
    
    Args:
        account_email: Email address of the account. If None, uses first authenticated account.
        
    Returns:
        tuple: (service, email) - Gmail service object and authenticated email
        
    Raises:
        ValueError: If no accounts are authenticated or specified account not found
    """
    global gmail_services
    
    # If no account specified, use first authenticated account
    if not account_email:
        accounts = list_authenticated_accounts()
        if not accounts:
            raise ValueError("No authenticated accounts found. Please add an account first.")
        account_email = accounts[0]
        log_message(f"Using default account: {account_email}")
    
    # Check if service is cached
    if account_email in gmail_services:
        return gmail_services[account_email], account_email
    
    # Create new service
    try:
        service = get_gmail_service(account_email=account_email)
        # Verify the email
        verified_email = get_authenticated_email(service)
        gmail_services[verified_email] = service
        return service, verified_email
    except Exception as e:
        log_message(f"Error getting service for {account_email}: {e}")
        raise ValueError(f"Account {account_email} is not authenticated or authentication failed.")


def log_message(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def sanitize_newsletter_data(newsletter):
    """
    Ensure all newsletter data is JSON-serializable.
    Converts bytes to strings, handles dates, and ensures proper types.
    
    Args:
        newsletter: Dictionary containing newsletter data
        
    Returns:
        dict: Sanitized newsletter data safe for JSON serialization
    """
    sanitized = {}
    
    for key, value in newsletter.items():
        # Handle None values
        if value is None:
            sanitized[key] = None
        
        # Handle bytes objects - convert to string
        elif isinstance(value, bytes):
            try:
                sanitized[key] = value.decode('utf-8', errors='ignore')
            except Exception:
                sanitized[key] = str(value)
        
        # Handle datetime objects - convert to ISO format string
        elif isinstance(value, datetime):
            sanitized[key] = value.isoformat()
        
        # Handle other objects that might not be JSON-serializable
        elif not isinstance(value, (str, int, float, bool, list, dict)):
            sanitized[key] = str(value)
        
        # Already JSON-serializable
        else:
            sanitized[key] = value
    
    # Ensure required fields exist with proper types
    required_fields = {
        'id': '',
        'sender_email': '',
        'sender_name': '',
        'subject': '',
        'date': '',
        'unsubscribe_link': None,
        'unsubscribe_method': 'none'
    }
    
    for field, default in required_fields.items():
        if field not in sanitized:
            sanitized[field] = default
        elif sanitized[field] is not None and not isinstance(sanitized[field], str):
            sanitized[field] = str(sanitized[field])
    
    return sanitized


@app.route('/')
def index():
    """Render main dashboard."""
    try:
        return render_template('index.html')
    except Exception as e:
        log_message(f"Error rendering index: {e}")
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/accounts', methods=['GET'])
def get_accounts():
    """
    Get list of all authenticated Gmail accounts.
    """
    try:
        log_message("Fetching authenticated accounts...")
        
        accounts = list_authenticated_accounts()
        
        log_message(f"Found {len(accounts)} authenticated account(s)")
        
        return jsonify({
            'success': True,
            'accounts': accounts,
            'count': len(accounts)
        }), 200
        
    except Exception as e:
        log_message(f"Error fetching accounts: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch accounts'
        }), 500


@app.route('/accounts/add', methods=['POST'])
def add_account():
    """
    Add a new Gmail account by initiating OAuth flow.
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing email parameter'
            }), 400
        
        email = data['email']
        
        log_message(f"Initiating OAuth flow for {email}...")
        
        # Initiate OAuth flow for this specific email
        try:
            service = get_gmail_service(account_email=email)
            verified_email = get_authenticated_email(service)
            
            # Cache the service
            gmail_services[verified_email] = service
            
            log_message(f"Successfully authenticated {verified_email}")
            
            return jsonify({
                'success': True,
                'email': verified_email,
                'message': f'Successfully authenticated {verified_email}'
            }), 200
            
        except ValueError as e:
            # Account mismatch error
            log_message(f"Account mismatch: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Account mismatch. Please log in with the correct account.'
            }), 400
            
    except Exception as e:
        log_message(f"Error adding account: {e}")
        import traceback
        error_details = traceback.format_exc()
        log_message(f"Error details: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to add account',
            'details': error_details if app.config['DEBUG'] else None
        }), 500


@app.route('/accounts/remove', methods=['POST'])
def remove_account_route():
    """
    Remove authentication for a Gmail account.
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing email parameter'
            }), 400
        
        email = data['email']
        
        log_message(f"Removing account: {email}")
        
        success = remove_account(email)
        
        # Remove from cache
        if email in gmail_services:
            del gmail_services[email]
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Removed authentication for {email}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'Account {email} not found'
            }), 404
        
    except Exception as e:
        log_message(f"Error removing account: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to remove account'
        }), 500


@app.route('/scan', methods=['GET'])
def scan():
    """
    Scan Gmail inbox for newsletters with multi-account support.
    Pre-analyzes difficulty and includes inbox statistics.
    """
    try:
        log_message("Starting newsletter scan...")
        
        # Get parameters
        account_email = request.args.get('account', None)
        max_results = request.args.get('max_results', 100, type=int)
        
        # Validate max_results
        if max_results not in [50, 100, 250, 500, 1000] and max_results != 'all':
            max_results = 100
        
        # Get Gmail service for specified account
        try:
            service, verified_email = get_service(account_email)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Account not authenticated. Please add the account first.'
            }), 401
        
        # Store selected account in session
        session['selected_account'] = verified_email
        session['scan_max_results'] = max_results
        
        log_message(f"Scanning account: {verified_email} (max_results: {max_results})")
        
        # Get inbox statistics first
        inbox_stats = get_inbox_stats(service)
        log_message(f"Inbox stats - Total: {inbox_stats.get('total_emails', 0)}, "
                   f"Estimated newsletters: {inbox_stats.get('estimated_newsletters', 0)}")
        
        # Scan for newsletters
        scan_results = scan_newsletters(service, max_results=max_results)
        
        # Handle both old list format and new dict format for backward compatibility
        if isinstance(scan_results, dict):
            newsletters = scan_results.get('newsletters', [])
            total_scanned = scan_results.get('total_scanned', 0)
            total_found = scan_results.get('total_found', len(newsletters))
            scan_limit = scan_results.get('scan_limit', max_results)
            log_message(f"Scanned {total_scanned} emails, found {total_found} newsletters")
        else:
            # Legacy format (list)
            newsletters = scan_results
            total_scanned = len(newsletters)
            total_found = len(newsletters)
            scan_limit = max_results
            log_message(f"Found {len(newsletters)} newsletters")
        
        # Categorize all newsletters (including whitelisted)
        all_newsletters = []
        categories = {'easy': 0, 'medium': 0, 'hard': 0, 'whitelisted': 0}
        
        for newsletter in newsletters:
            sender_email = newsletter.get('sender_email')
            
            # Check if whitelisted
            if sender_email and is_whitelisted(sender_email):
                newsletter['whitelisted'] = True
                newsletter['difficulty'] = 'whitelisted'
                categories['whitelisted'] += 1
                log_message(f"Found whitelisted sender: {sender_email}")
            else:
                newsletter['whitelisted'] = False
                # Categorize difficulty
                difficulty = categorize_unsubscribe_difficulty(newsletter)
                newsletter['difficulty'] = difficulty
                categories[difficulty] += 1
            
            # Ensure all fields are JSON-serializable
            sanitized_newsletter = sanitize_newsletter_data(newsletter)
            all_newsletters.append(sanitized_newsletter)
        
        log_message(f"Total newsletters: {len(all_newsletters)}")
        log_message(f"Categories - Easy: {categories['easy']}, Medium: {categories['medium']}, "
                   f"Hard: {categories['hard']}, Whitelisted: {categories['whitelisted']}")
        
        return jsonify({
            'success': True,
            'account': verified_email,
            'newsletters': all_newsletters,
            'count': len(all_newsletters),
            'total_found': total_found,
            'total_scanned': total_scanned,
            'scan_limit': scan_limit,
            'inbox_stats': {
                'total_emails': inbox_stats.get('total_emails', 0),
                'estimated_newsletters': inbox_stats.get('estimated_newsletters', 0),
                'recommended_limit': inbox_stats.get('recommended_limit', 100)
            },
            'categories': categories
        }), 200
        
    except ValueError as e:
        # Account authentication error
        log_message(f"Authentication error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Account not authenticated'
        }), 401
        
    except Exception as e:
        log_message(f"Error during scan: {e}")
        import traceback
        error_details = traceback.format_exc()
        log_message(f"Error details: {error_details}")
        
        # Check if it's an authentication error
        error_message = str(e)
        if 'credentials' in error_message.lower() or 'auth' in error_message.lower():
            error_message = 'Gmail authentication failed. Please check your credentials.json file.'
        else:
            error_message = f'Failed to scan newsletters: {str(e)}'
        
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': error_message,
            'details': error_details if app.config['DEBUG'] else None
        }), 500


@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """
    Unsubscribe from selected newsletters with multi-account support.
    Returns categorized results.
    """
    try:
        data = request.get_json()
        
        if not data or 'newsletters' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing newsletters data'
            }), 400
        
        newsletters = data['newsletters']
        account_email = data.get('account', None)
        
        if not isinstance(newsletters, list) or len(newsletters) == 0:
            return jsonify({
                'success': False,
                'error': 'Invalid newsletters data'
            }), 400
        
        # Get Gmail service for specified account
        try:
            service, verified_email = get_service(account_email)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Account not authenticated'
            }), 401
        
        log_message(f"Starting batch unsubscribe for {len(newsletters)} newsletters (account: {verified_email})...")
        
        # Progress tracking
        progress_data = {'current': 0, 'total': len(newsletters)}
        
        def progress_callback(current, total, result):
            progress_data['current'] = current
            log_message(f"Progress: {current}/{total} - {result['sender_name']}: {result.get('category', 'unknown')}")
        
        # Perform batch unsubscribe
        summary = batch_unsubscribe(newsletters, progress_callback=progress_callback)
        
        # Format detailed results for frontend
        details = []
        for result in summary['results']:
            # Sanitize each result to ensure JSON-serializable
            detail = {
                'id': str(result.get('id', '')),
                'sender_name': str(result.get('sender_name', '')),
                'sender_email': str(result.get('sender_email', '')),
                'status': str(result.get('category', 'failed')),
                'method': str(result.get('method', '')),
                'message': str(result.get('message', '')),
                'unsubscribe_url': str(result.get('unsubscribe_url', '')) if result.get('unsubscribe_url') else None
            }
            details.append(detail)
        
        log_message(f"Batch unsubscribe complete: {summary['auto_success_count']} success, "
                   f"{summary['manual_required_count']} manual, {summary['failed_count']} failed")
        
        return jsonify({
            'success': True,
            'account': verified_email,
            'total': summary['total'],
            'auto_success': summary['auto_success_count'],
            'manual_required': summary['manual_required_count'],
            'failed': summary['failed_count'],
            'details': details
        }), 200
        
    except ValueError as e:
        # Account authentication error
        log_message(f"Authentication error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Account not authenticated'
        }), 401
        
    except Exception as e:
        log_message(f"Error during unsubscribe: {e}")
        import traceback
        error_details = traceback.format_exc()
        log_message(f"Error details: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': 'Failed to unsubscribe from newsletters',
            'details': error_details if app.config['DEBUG'] else None
        }), 500


@app.route('/whitelist/add', methods=['POST'])
def whitelist_add():
    """Add sender to whitelist (optionally account-specific)."""
    try:
        data = request.get_json()
        
        if not data or 'sender_email' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing sender_email'
            }), 400
        
        sender_email = data['sender_email']
        sender_name = data.get('sender_name', None)
        account = data.get('account', None)  # Optional: for future account-specific whitelist
        
        log_message(f"Adding to whitelist: {sender_email}" + (f" (account: {account})" if account else ""))
        
        success = add_to_whitelist(sender_email, sender_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Added {sender_email} to whitelist'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'{sender_email} is already in whitelist'
            }), 200
        
    except Exception as e:
        log_message(f"Error adding to whitelist: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to add to whitelist'
        }), 500


@app.route('/whitelist/remove', methods=['POST'])
def whitelist_remove():
    """Remove sender from whitelist (optionally account-specific)."""
    try:
        data = request.get_json()
        
        if not data or 'sender_email' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing sender_email'
            }), 400
        
        sender_email = data['sender_email']
        account = data.get('account', None)  # Optional: for future account-specific whitelist
        
        log_message(f"Removing from whitelist: {sender_email}" + (f" (account: {account})" if account else ""))
        
        success = remove_from_whitelist(sender_email)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Removed {sender_email} from whitelist'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'{sender_email} not found in whitelist'
            }), 200
        
    except Exception as e:
        log_message(f"Error removing from whitelist: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to remove from whitelist'
        }), 500


@app.route('/whitelist', methods=['GET'])
def whitelist_get():
    """Get all whitelisted senders (optionally filtered by account)."""
    try:
        account = request.args.get('account', None)  # Optional: for future account-specific whitelist
        
        log_message(f"Fetching whitelist" + (f" for account: {account}" if account else "..."))
        
        whitelist = get_all_whitelisted()
        
        # Future: filter by account if needed
        # if account:
        #     whitelist = [w for w in whitelist if w.get('account') == account]
        
        return jsonify({
            'success': True,
            'whitelist': whitelist,
            'count': len(whitelist),
            'account': account
        }), 200
        
    except Exception as e:
        log_message(f"Error fetching whitelist: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch whitelist'
        }), 500


@app.route('/newsletter/<newsletter_id>/manual-link', methods=['GET'])
def get_manual_link(newsletter_id):
    """
    Get unsubscribe URL for manual action.
    Used when automatic unsubscribe fails.
    """
    try:
        # In a real implementation, you'd store newsletter data
        # For now, we'll expect the URL to be passed as a query parameter
        unsubscribe_url = request.args.get('url')
        
        if not unsubscribe_url:
            return jsonify({
                'success': False,
                'error': 'Missing unsubscribe URL'
            }), 400
        
        log_message(f"Manual link requested for newsletter {newsletter_id}")
        
        # Optional: Track that user clicked (analytics)
        # You could store this in a database or log file
        
        return jsonify({
            'success': True,
            'newsletter_id': newsletter_id,
            'unsubscribe_url': unsubscribe_url,
            'message': 'Please complete unsubscribe manually in your browser'
        }), 200
        
    except Exception as e:
        log_message(f"Error getting manual link: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get manual link'
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    log_message(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


if __name__ == '__main__':
    log_message("Starting Newsletter Unsubscriber web application...")
    log_message("Access the dashboard at: http://localhost:5000")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
