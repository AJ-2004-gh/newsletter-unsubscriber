"""
Email Scanner Module with Configurable Scan Limits

Scans Gmail inbox for newsletter emails and extracts unsubscribe information.
Supports both RFC 2369 List-Unsubscribe headers and body link extraction.
Includes progress tracking and flexible scan limits.
"""

import base64
import re
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError


def scan_newsletters(service, max_results=100, query_filter=None, progress_callback=None):
    """
    Scan Gmail inbox for newsletter emails containing unsubscribe links.
    
    Args:
        service: Authenticated Gmail API service object
        max_results: Maximum number of emails to scan. Can be:
                    - Integer: 50, 100, 250, 500, 1000
                    - String "all": Scan entire inbox
                    - Default: 100
        query_filter: Optional custom Gmail search query
                     Default: 'is:inbox "unsubscribe"'
        progress_callback: Optional callback function(current, total, message)
                          Called periodically with progress updates
        
    Returns:
        dict: Dictionary containing scan results:
            {
                'newsletters': [list of newsletter dicts],
                'total_scanned': N,  # Total emails scanned
                'total_found': M,    # Newsletters with unsubscribe links found
                'scan_limit': max_results value used
            }
        
        Each newsletter dict structure:
            {
                'id': message_id,
                'sender_email': email,
                'sender_name': name,
                'subject': subject,
                'date': date,
                'unsubscribe_link': url or None,
                'unsubscribe_method': 'header' or 'body' or 'none'
            }
    """
    newsletters = []
    total_scanned = 0
    
    # Determine if scanning all emails
    scan_all = max_results == "all"
    if scan_all:
        max_results = float('inf')  # No limit
        print("Scanning entire inbox for newsletters...")
    else:
        max_results = int(max_results)
        print(f"Scanning inbox for newsletters (max {max_results} emails)...")
    
    try:
        # Use custom query or default
        query = query_filter if query_filter else 'is:inbox "unsubscribe"'
        print(f"Search query: {query}")
        
        # Pagination handling
        page_token = None
        
        while total_scanned < max_results:
            # Calculate how many results to fetch in this batch (max 100 per API call)
            batch_size = min(100, max_results - total_scanned) if not scan_all else 100
            
            # Fetch message IDs matching the query
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=batch_size,
                pageToken=page_token
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print("No more messages found.")
                break
            
            print(f"Processing batch of {len(messages)} messages...")
            
            # Process each message
            for msg in messages:
                try:
                    newsletter_info = _process_message(service, msg['id'])
                    if newsletter_info:
                        newsletters.append(newsletter_info)
                    
                    total_scanned += 1
                    
                    # Progress logging and callback
                    if total_scanned % 50 == 0:
                        progress_msg = f"Processed {total_scanned} emails, found {len(newsletters)} newsletters..."
                        print(progress_msg)
                        if progress_callback:
                            progress_callback(total_scanned, max_results if not scan_all else '?', progress_msg)
                    
                    # Check if we've reached the limit
                    if total_scanned >= max_results:
                        break
                            
                except Exception as e:
                    print(f"Error processing message {msg['id']}: {e}")
                    total_scanned += 1
                    continue
            
            # Check if we've reached the limit
            if total_scanned >= max_results:
                break
            
            # Check if there are more pages
            page_token = results.get('nextPageToken')
            if not page_token:
                print("Reached end of search results.")
                break
        
        print(f"\nScan complete! Scanned {total_scanned} emails, found {len(newsletters)} newsletters.")
        
        # Return comprehensive results
        return {
            'newsletters': newsletters,
            'total_scanned': total_scanned,
            'total_found': len(newsletters),
            'scan_limit': 'all' if scan_all else max_results
        }
        
    except HttpError as error:
        print(f"Gmail API error: {error}")
        return {
            'newsletters': newsletters,
            'total_scanned': total_scanned,
            'total_found': len(newsletters),
            'scan_limit': 'all' if scan_all else max_results,
            'error': str(error)
        }
    except Exception as e:
        print(f"Unexpected error during scan: {e}")
        return {
            'newsletters': newsletters,
            'total_scanned': total_scanned,
            'total_found': len(newsletters),
            'scan_limit': 'all' if scan_all else max_results,
            'error': str(e)
        }


def _process_message(service, message_id):
    """
    Process a single message and extract newsletter information.
    
    Args:
        service: Gmail API service object
        message_id: ID of the message to process
        
    Returns:
        dict: Newsletter information or None if processing fails
    """
    try:
        # Fetch full message details
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload']['headers']
        
        # Extract email metadata
        sender_email = None
        sender_name = None
        subject = None
        date = None
        list_unsubscribe = None
        
        for header in headers:
            name = header['name'].lower()
            value = header['value']
            
            if name == 'from':
                # Parse sender: "Name <email@example.com>" or "email@example.com"
                match = re.match(r'(?:"?([^"]*)"?\s)?<?([^>]+)>?', value)
                if match:
                    sender_name = match.group(1) or match.group(2).split('@')[0]
                    sender_email = match.group(2)
            elif name == 'subject':
                subject = value
            elif name == 'date':
                try:
                    date = parsedate_to_datetime(value).isoformat()
                except:
                    date = value
            elif name == 'list-unsubscribe':
                list_unsubscribe = value
        
        # Try to find unsubscribe link
        unsubscribe_link = None
        unsubscribe_method = 'none'
        
        # Method 1: Check List-Unsubscribe header (RFC 2369)
        if list_unsubscribe:
            unsubscribe_link = parse_unsubscribe_header(list_unsubscribe)
            if unsubscribe_link:
                unsubscribe_method = 'header'
        
        # Method 2: Search email body if header method failed
        if not unsubscribe_link:
            email_body = _extract_email_body(message)
            if email_body:
                unsubscribe_link = find_unsubscribe_link_in_body(email_body)
                if unsubscribe_link:
                    unsubscribe_method = 'body'
        
        return {
            'id': message_id,
            'sender_email': sender_email,
            'sender_name': sender_name,
            'subject': subject,
            'date': date,
            'unsubscribe_link': unsubscribe_link,
            'unsubscribe_method': unsubscribe_method
        }
        
    except Exception as e:
        print(f"Error processing message details: {e}")
        return None


def _extract_email_body(message):
    """
    Extract email body from message payload.
    Handles both plain text and HTML parts, including nested multipart messages.
    
    Args:
        message: Gmail message object
        
    Returns:
        str: Email body content or None
    """
    
    def decode_data(data):
        """Helper function to safely decode base64 data."""
        if not data:
            return None
        # Ensure data is bytes for base64 decoding
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    def extract_from_parts(parts):
        """Recursively extract body from parts."""
        html_body = None
        text_body = None
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            
            # Handle nested multipart
            if 'parts' in part:
                result = extract_from_parts(part['parts'])
                if result:
                    return result
            
            # Extract HTML (preferred)
            if mime_type == 'text/html' and 'data' in part.get('body', {}):
                html_body = decode_data(part['body']['data'])
                if html_body:
                    return html_body
            
            # Extract plain text (fallback)
            elif mime_type == 'text/plain' and 'data' in part.get('body', {}):
                text_body = decode_data(part['body']['data'])
        
        return html_body or text_body
    
    try:
        payload = message['payload']
        
        # Check if message has parts (multipart)
        if 'parts' in payload:
            return extract_from_parts(payload['parts'])
        
        # Single part message
        elif 'body' in payload and 'data' in payload['body']:
            return decode_data(payload['body']['data'])
        
        return None
        
    except Exception as e:
        print(f"Error extracting email body: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_unsubscribe_header(header_value):
    """
    Parse List-Unsubscribe header and extract URL.
    
    RFC 2369 format examples:
    - <mailto:unsubscribe@example.com>
    - <http://example.com/unsubscribe>
    - <mailto:unsub@example.com>, <http://example.com/unsub>
    
    Args:
        header_value: Value of List-Unsubscribe header
        
    Returns:
        str: Cleaned unsubscribe URL (http/https preferred) or None
    """
    if not header_value:
        return None
    
    try:
        # Extract all URLs within angle brackets
        urls = re.findall(r'<([^>]+)>', header_value)
        
        # Prefer http/https URLs over mailto
        http_urls = [url for url in urls if url.startswith(('http://', 'https://'))]
        if http_urls:
            return http_urls[0]
        
        # Fall back to mailto if no http URL found
        mailto_urls = [url for url in urls if url.startswith('mailto:')]
        if mailto_urls:
            return mailto_urls[0]
        
        return None
        
    except Exception as e:
        print(f"Error parsing unsubscribe header: {e}")
        return None


def find_unsubscribe_link_in_body(email_body):
    """
    Find unsubscribe link in email body.
    Searches for links containing "unsubscribe" in href or anchor text.
    
    Args:
        email_body: HTML or plain text email body
        
    Returns:
        str: First valid unsubscribe URL or None
    """
    if not email_body:
        return None
    
    try:
        # Try parsing as HTML first
        soup = BeautifulSoup(email_body, 'html.parser')
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text().lower()
            
            # Check if link is related to unsubscribe
            if 'unsubscribe' in href.lower() or 'unsubscribe' in text:
                # Validate URL format
                if href.startswith(('http://', 'https://')):
                    return href
        
        # Fallback: regex search for URLs in plain text
        url_pattern = r'https?://[^\s<>"]+unsubscribe[^\s<>"]*'
        matches = re.findall(url_pattern, email_body, re.IGNORECASE)
        if matches:
            return matches[0]
        
        return None
        
    except Exception as e:
        print(f"Error finding unsubscribe link in body: {e}")
        return None


def get_inbox_stats(service):
    """
    Get statistics about the inbox to help users decide scan limits.
    
    Args:
        service: Authenticated Gmail API service object
        
    Returns:
        dict: Dictionary containing inbox statistics:
            {
                'total_emails': N,           # Total emails in inbox
                'estimated_newsletters': M,  # Estimated newsletters (with "unsubscribe")
                'recommended_limit': X       # Recommended scan limit
            }
    """
    try:
        # Get user profile for total message count
        profile = service.users().getProfile(userId='me').execute()
        total_emails = profile.get('messagesTotal', 0)
        
        # Estimate newsletters by counting messages with "unsubscribe"
        # Use a quick count query (doesn't fetch full messages)
        query = 'is:inbox "unsubscribe"'
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1  # We just need the count
        ).execute()
        
        estimated_newsletters = results.get('resultSizeEstimate', 0)
        
        # Recommend scan limit based on estimated count
        if estimated_newsletters <= 50:
            recommended_limit = 50
        elif estimated_newsletters <= 100:
            recommended_limit = 100
        elif estimated_newsletters <= 250:
            recommended_limit = 250
        elif estimated_newsletters <= 500:
            recommended_limit = 500
        else:
            recommended_limit = 1000
        
        print(f"Inbox Statistics:")
        print(f"  Total emails: {total_emails}")
        print(f"  Estimated newsletters: {estimated_newsletters}")
        print(f"  Recommended scan limit: {recommended_limit}")
        
        return {
            'total_emails': total_emails,
            'estimated_newsletters': estimated_newsletters,
            'recommended_limit': recommended_limit
        }
        
    except HttpError as error:
        print(f"Error fetching inbox stats: {error}")
        return {
            'total_emails': 0,
            'estimated_newsletters': 0,
            'recommended_limit': 100,
            'error': str(error)
        }


if __name__ == "__main__":
    # Test the scanner with configurable limits
    from gmail_auth import get_gmail_service
    import sys
    
    try:
        service = get_gmail_service()
        
        # Get inbox stats first
        print("\n" + "="*80)
        stats = get_inbox_stats(service)
        print("="*80)
        
        # Determine scan limit
        if len(sys.argv) > 1:
            scan_limit = sys.argv[1]
            if scan_limit.lower() == 'all':
                scan_limit = 'all'
            else:
                scan_limit = int(scan_limit)
        else:
            scan_limit = stats.get('recommended_limit', 100)
        
        print(f"\nScanning with limit: {scan_limit}")
        print("="*80)
        
        # Progress callback
        def progress(current, total, message):
            print(f"Progress: {message}")
        
        # Scan newsletters
        results = scan_newsletters(service, max_results=scan_limit, progress_callback=progress)
        
        newsletters = results['newsletters']
        
        print(f"\n{'='*80}")
        print(f"Scan Results:")
        print(f"  Total scanned: {results['total_scanned']}")
        print(f"  Newsletters found: {results['total_found']}")
        print(f"  Scan limit: {results['scan_limit']}")
        print(f"{'='*80}\n")
        
        # Show first 10 newsletters
        for i, newsletter in enumerate(newsletters[:10], 1):
            print(f"{i}. {newsletter['sender_name']} ({newsletter['sender_email']})")
            print(f"   Subject: {newsletter['subject']}")
            print(f"   Unsubscribe: {newsletter['unsubscribe_link']}")
            print(f"   Method: {newsletter['unsubscribe_method']}")
            print()
        
        if len(newsletters) > 10:
            print(f"... and {len(newsletters) - 10} more newsletters")
            
    except Exception as e:
        print(f"Error: {e}")
