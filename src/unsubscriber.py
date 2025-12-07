"""
Unsubscribe Automation Module

Automates the unsubscribe process for newsletters using smart fallback handling:
1. One-click unsubscribe (HTTP requests for header links)
2. Browser automation (Selenium for body links)
3. Login detection and manual fallback
4. Complex flow and CAPTCHA detection
"""

import time
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)


# Request configuration
REQUEST_TIMEOUT = 10
ELEMENT_SEARCH_TIMEOUT = 5
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
RATE_LIMIT_DELAY = 2  # seconds between requests

# Domains known to require login
LOGIN_REQUIRED_DOMAINS = ['medium.com', 'quora.com', 'substack.com', 'patreon.com']


def unsubscribe_from_newsletter(newsletter_data):
    """
    Unsubscribe from a single newsletter with smart fallback handling.
    
    Attempts multiple methods with graceful degradation:
    - Method A: One-click unsubscribe (HTTP request for header links)
    - Method B: Browser automation (Selenium for body links)
    - Method C: Login detection & manual fallback
    - Method D: Complex flow detection (CAPTCHA, multi-step)
    
    Args:
        newsletter_data: Dictionary containing newsletter information:
            {
                'id': message_id,
                'sender_email': email,
                'sender_name': name,
                'unsubscribe_link': url,
                'unsubscribe_method': 'header' or 'body'
            }
    
    Returns:
        dict: Result of unsubscribe attempt:
            {
                'success': True/False,
                'method': 'header'/'browser'/'manual_action_needed'/'login_required'/'captcha'/'timeout'/'failed',
                'message': Descriptive message for user,
                'unsubscribe_url': Original URL (for manual fallback),
                'error_details': Optional error information
            }
    """
    unsubscribe_link = newsletter_data.get('unsubscribe_link')
    sender_name = newsletter_data.get('sender_name', 'Unknown')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"[{timestamp}] Attempting to unsubscribe from: {sender_name}")
    print(f"[{timestamp}] Link: {unsubscribe_link}")
    
    if not unsubscribe_link:
        return {
            'success': False,
            'method': 'failed',
            'message': 'No unsubscribe link found',
            'unsubscribe_url': None,
            'error_details': 'Missing unsubscribe link in email'
        }
    
    # Check if link is expired (common pattern)
    if _is_link_expired(unsubscribe_link):
        return {
            'success': False,
            'method': 'failed',
            'message': 'Unsubscribe link appears to be expired',
            'unsubscribe_url': unsubscribe_link,
            'error_details': 'Link contains expiration indicators'
        }
    
    # Method A: One-click unsubscribe (for header links or simple URLs)
    if unsubscribe_link.startswith('mailto:'):
        return _unsubscribe_mailto(unsubscribe_link, sender_name)
    elif unsubscribe_link.startswith(('http://', 'https://')):
        # Try simple HTTP request first
        result = _unsubscribe_http(unsubscribe_link, sender_name)
        
        # If HTTP method fails or requires manual action, try browser automation
        if not result['success'] and result['method'] not in ['manual_action_needed', 'login_required']:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HTTP method failed, trying browser automation...")
            return _unsubscribe_browser(unsubscribe_link, sender_name)
        
        return result
    else:
        return {
            'success': False,
            'method': 'failed',
            'message': f'Unsupported link format: {unsubscribe_link}',
            'unsubscribe_url': unsubscribe_link,
            'error_details': 'Link protocol not supported'
        }


def _is_link_expired(url):
    """
    Check if unsubscribe link appears to be expired.
    
    Args:
        url: Unsubscribe URL
        
    Returns:
        bool: True if link appears expired
    """
    # Check for common expiration patterns in URL
    expiration_patterns = [
        r'expired',
        r'exp=\d+',
        r'expires=\d+',
        r'valid_until=\d+'
    ]
    
    for pattern in expiration_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            # Check if expiration timestamp is in the past
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            for key in ['exp', 'expires', 'valid_until']:
                if key in params:
                    try:
                        exp_time = int(params[key][0])
                        if exp_time < time.time():
                            return True
                    except (ValueError, IndexError):
                        pass
    
    return False


def _unsubscribe_mailto(mailto_link, sender_name):
    """
    Handle mailto: unsubscribe links by sending email.
    
    Args:
        mailto_link: mailto: URL
        sender_name: Name of sender
        
    Returns:
        dict: Result dictionary
    """
    try:
        # Parse mailto link
        # Format: mailto:unsubscribe@example.com?subject=unsubscribe
        email_match = re.match(r'mailto:([^?]+)', mailto_link)
        if not email_match:
            return {
                'success': False,
                'method': 'failed',
                'message': 'Invalid mailto: format',
                'unsubscribe_url': mailto_link,
                'error_details': 'Could not parse email address from mailto link'
            }
        
        to_email = email_match.group(1)
        
        # Note: Actual email sending requires SMTP configuration
        # For now, return manual action needed
        return {
            'success': False,
            'method': 'manual_action_needed',
            'message': f'Please send an email to {to_email} with subject "unsubscribe"',
            'unsubscribe_url': mailto_link,
            'error_details': 'SMTP configuration required for automatic email sending'
        }
        
    except Exception as e:
        return {
            'success': False,
            'method': 'failed',
            'message': f'Error processing mailto link: {str(e)}',
            'unsubscribe_url': mailto_link,
            'error_details': str(e)
        }


def _unsubscribe_http(url, sender_name):
    """
    Attempt unsubscribe via HTTP GET/POST request with smart detection.
    
    Args:
        url: Unsubscribe URL
        sender_name: Name of sender
        
    Returns:
        dict: Result dictionary
    """
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Check if URL has "one-click" parameter (RFC 8058)
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        
        # Determine request method
        if 'List-Unsubscribe=One-Click' in url or 'one-click' in params:
            print(f"[{timestamp}] Sending POST request (one-click) to {url}")
            response = requests.post(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        else:
            print(f"[{timestamp}] Sending GET request to {url}")
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        
        # Handle rate limiting
        if response.status_code in [429, 503]:
            return {
                'success': False,
                'method': 'failed',
                'message': f'Rate limited by server (status {response.status_code}). Try again later.',
                'unsubscribe_url': url,
                'error_details': f'HTTP {response.status_code}: Rate limit or service unavailable'
            }
        
        # Check if successful (2xx or 3xx status codes)
        if 200 <= response.status_code < 400:
            response_text = response.text.lower()
            
            # Check for login requirement
            if _requires_login(response.text, response.url):
                return {
                    'success': False,
                    'method': 'login_required',
                    'message': f'Login required to unsubscribe from {sender_name}',
                    'unsubscribe_url': url,
                    'error_details': 'Page requires authentication'
                }
            
            # Check for confirmation email requirement
            if 'confirmation email' in response_text or 'check your email' in response_text:
                return {
                    'success': False,
                    'method': 'manual_action_needed',
                    'message': 'Confirmation email required. Please check your inbox.',
                    'unsubscribe_url': url,
                    'error_details': 'Requires email confirmation'
                }
            
            # Look for success indicators
            success_keywords = ['unsubscribed', 'removed', 'success', 'confirmed', 'opted out']
            
            if any(keyword in response_text for keyword in success_keywords):
                return {
                    'success': True,
                    'method': 'header',
                    'message': f'Unsubscribed successfully via HTTP (status {response.status_code})',
                    'unsubscribe_url': url
                }
            else:
                # Request succeeded but unclear if unsubscribed
                return {
                    'success': True,
                    'method': 'header',
                    'message': f'HTTP request completed (status {response.status_code}), confirmation unclear',
                    'unsubscribe_url': url
                }
        else:
            return {
                'success': False,
                'method': 'failed',
                'message': f'HTTP request failed with status {response.status_code}',
                'unsubscribe_url': url,
                'error_details': f'HTTP {response.status_code}'
            }
            
    except requests.Timeout:
        return {
            'success': False,
            'method': 'timeout',
            'message': 'Request timed out after 10 seconds',
            'unsubscribe_url': url,
            'error_details': 'Connection timeout'
        }
    except requests.RequestException as e:
        return {
            'success': False,
            'method': 'failed',
            'message': f'Network error: {str(e)}',
            'unsubscribe_url': url,
            'error_details': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'method': 'failed',
            'message': f'Unexpected error: {str(e)}',
            'unsubscribe_url': url,
            'error_details': str(e)
        }


def _requires_login(html_content, current_url):
    """
    Detect if page requires login.
    
    Args:
        html_content: HTML content of page
        current_url: Current URL after redirects
        
    Returns:
        bool: True if login is required
    """
    html_lower = html_content.lower()
    
    # Check URL patterns
    if any(pattern in current_url.lower() for pattern in ['/login', '/signin', '/sign-in', '/auth']):
        return True
    
    # Check for login form elements
    soup = BeautifulSoup(html_content, 'html.parser')
    if soup.find('input', {'type': 'password'}):
        return True
    
    # Check for login text
    login_keywords = ['sign in', 'log in', 'login required', 'please login', 'authentication required']
    if any(keyword in html_lower for keyword in login_keywords):
        return True
    
    # Check domain against known login-required services
    parsed = urlparse(current_url)
    if any(domain in parsed.netloc for domain in LOGIN_REQUIRED_DOMAINS):
        return True
    
    return False


def _unsubscribe_browser(url, sender_name):
    """
    Attempt unsubscribe via browser automation (Selenium) with smart detection.
    
    Args:
        url: Unsubscribe URL
        sender_name: Name of sender
        
    Returns:
        dict: Result dictionary
    """
    driver = None
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Setup headless Chrome with anti-detection
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        print(f"[{timestamp}] Starting headless browser...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(REQUEST_TIMEOUT)
        
        # Navigate to unsubscribe page
        print(f"[{timestamp}] Navigating to {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(2)
        
        # Method C: Check for login requirement
        if _detect_login_page(driver):
            return {
                'success': False,
                'method': 'login_required',
                'message': f'Login required to unsubscribe from {sender_name}',
                'unsubscribe_url': url,
                'error_details': 'Page requires authentication'
            }
        
        # Method D: Check for CAPTCHA
        if _detect_captcha(driver):
            return {
                'success': False,
                'method': 'captcha',
                'message': f'CAPTCHA detected. Manual action required for {sender_name}',
                'unsubscribe_url': url,
                'error_details': 'CAPTCHA verification required'
            }
        
        # Method D: Check for complex flow (preferences page, settings)
        if _detect_complex_flow(driver):
            return {
                'success': False,
                'method': 'manual_action_needed',
                'message': f'Complex unsubscribe flow detected. Please unsubscribe manually from {sender_name}',
                'unsubscribe_url': url,
                'error_details': 'Multi-step process or preferences page detected'
            }
        
        # Look for unsubscribe button/link patterns (expanded)
        unsubscribe_patterns = [
            # Button text patterns (case-insensitive)
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unsubscribe')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'yes')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'opt out')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'remove me')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'remove')]",
            # Link patterns
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unsubscribe')]",
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'opt out')]",
            # Input submit patterns
            "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unsubscribe')]",
            "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
        ]
        
        element_found = False
        for pattern in unsubscribe_patterns:
            try:
                element = WebDriverWait(driver, ELEMENT_SEARCH_TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, pattern))
                )
                element_text = element.text or element.get_attribute('value') or 'button'
                print(f"[{timestamp}] Found unsubscribe element: {element_text}")
                
                # Check for checkbox with "unsubscribe" label
                try:
                    checkbox_xpath = "//input[@type='checkbox' and (contains(translate(../label/text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unsubscribe') or contains(translate(following-sibling::text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unsubscribe'))]"
                    checkbox = driver.find_element(By.XPATH, checkbox_xpath)
                    if not checkbox.is_selected():
                        checkbox.click()
                        print(f"[{timestamp}] Checked unsubscribe checkbox")
                        time.sleep(1)
                except NoSuchElementException:
                    pass  # No checkbox found, continue
                
                # Check for email input form (some sites require email confirmation)
                try:
                    email_input = driver.find_element(By.XPATH, "//input[@type='email' or @name='email']")
                    # If email input exists but is empty, we need manual action
                    if not email_input.get_attribute('value'):
                        return {
                            'success': False,
                            'method': 'manual_action_needed',
                            'message': f'Email confirmation required. Please enter your email at {url}',
                            'unsubscribe_url': url,
                            'error_details': 'Form requires email input'
                        }
                except NoSuchElementException:
                    pass  # No email input, continue
                
                # Click the unsubscribe button
                element.click()
                print(f"[{timestamp}] Clicked unsubscribe button")
                element_found = True
                
                # Wait for confirmation page (up to 5 seconds)
                time.sleep(5)
                
                # Check for success message
                page_source = driver.page_source.lower()
                success_keywords = ['unsubscribed', 'removed', 'success', 'confirmed', 'opted out']
                
                if any(keyword in page_source for keyword in success_keywords):
                    return {
                        'success': True,
                        'method': 'browser',
                        'message': 'Unsubscribed successfully via browser automation',
                        'unsubscribe_url': url
                    }
                else:
                    return {
                        'success': True,
                        'method': 'browser',
                        'message': 'Browser automation completed, confirmation unclear',
                        'unsubscribe_url': url
                    }
                    
            except (TimeoutException, NoSuchElementException):
                continue  # Try next pattern
        
        if not element_found:
            return {
                'success': False,
                'method': 'manual_action_needed',
                'message': f'Could not find unsubscribe button. Please unsubscribe manually from {sender_name}',
                'unsubscribe_url': url,
                'error_details': 'No matching unsubscribe element found on page'
            }
            
    except TimeoutException:
        return {
            'success': False,
            'method': 'timeout',
            'message': 'Page load timeout after 10 seconds',
            'unsubscribe_url': url,
            'error_details': 'Browser timeout'
        }
    except WebDriverException as e:
        return {
            'success': False,
            'method': 'failed',
            'message': f'Browser crashed or failed: {str(e)}',
            'unsubscribe_url': url,
            'error_details': f'WebDriver error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'method': 'failed',
            'message': f'Browser automation error: {str(e)}',
            'unsubscribe_url': url,
            'error_details': str(e)
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass  # Ignore errors during cleanup


def _detect_login_page(driver):
    """
    Detect if current page requires login.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if login is required
    """
    try:
        # Check URL
        current_url = driver.current_url.lower()
        if any(pattern in current_url for pattern in ['/login', '/signin', '/sign-in', '/auth']):
            return True
        
        # Check for password input
        try:
            driver.find_element(By.XPATH, "//input[@type='password']")
            return True
        except NoSuchElementException:
            pass
        
        # Check page text
        page_text = driver.page_source.lower()
        login_keywords = ['sign in', 'log in', 'login required', 'please login']
        if any(keyword in page_text for keyword in login_keywords):
            return True
        
        return False
    except:
        return False


def _detect_captcha(driver):
    """
    Detect if page contains CAPTCHA.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if CAPTCHA is detected
    """
    try:
        # Check for reCAPTCHA iframe
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'recaptcha' in src.lower() or 'hcaptcha' in src.lower():
                return True
        
        # Check for CAPTCHA-related elements
        page_source = driver.page_source.lower()
        if 'recaptcha' in page_source or 'hcaptcha' in page_source or 'captcha' in page_source:
            return True
        
        return False
    except:
        return False


def _detect_complex_flow(driver):
    """
    Detect if page has complex multi-step unsubscribe flow.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if complex flow is detected
    """
    try:
        page_text = driver.page_source.lower()
        
        # Check for preferences/settings page indicators
        complex_keywords = [
            'email preferences',
            'manage subscriptions',
            'notification settings',
            'choose which emails',
            'select categories',
            'update preferences'
        ]
        
        if any(keyword in page_text for keyword in complex_keywords):
            # Check if there are multiple checkboxes (preferences page)
            checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            if len(checkboxes) > 3:
                return True
        
        return False
    except:
        return False


def batch_unsubscribe(newsletter_list, progress_callback=None):
    """
    Unsubscribe from multiple newsletters with categorized results.
    
    Args:
        newsletter_list: List of newsletter dictionaries from scanner
        progress_callback: Optional callback function(current, total, current_result)
        
    Returns:
        dict: Summary of batch operation:
            {
                'total': total_count,
                'auto_success_count': automatically_unsubscribed,
                'manual_required_count': needs_manual_action,
                'failed_count': failed_attempts,
                'results': [list of individual results with categories]
            }
    """
    total = len(newsletter_list)
    auto_success_count = 0
    manual_required_count = 0
    failed_count = 0
    results = []
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] Starting batch unsubscribe for {total} newsletters...")
    print("="*80)
    
    for i, newsletter in enumerate(newsletter_list, 1):
        sender_name = newsletter.get('sender_name', 'Unknown')
        sender_email = newsletter.get('sender_email', 'Unknown')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp}] [{i}/{total}] Processing: {sender_name} ({sender_email})")
        
        # Attempt unsubscribe
        result = unsubscribe_from_newsletter(newsletter)
        
        # Add newsletter info to result
        result['sender_name'] = sender_name
        result['sender_email'] = sender_email
        
        # Categorize result
        if result['success']:
            result['category'] = 'auto_success'
            auto_success_count += 1
            print(f"✓ SUCCESS: {result['message']}")
        elif result['method'] in ['manual_action_needed', 'login_required', 'captcha']:
            result['category'] = 'manual_required'
            manual_required_count += 1
            print(f"⚠ MANUAL ACTION NEEDED: {result['message']}")
            print(f"  URL: {result.get('unsubscribe_url', 'N/A')}")
        else:
            result['category'] = 'failed'
            failed_count += 1
            print(f"✗ FAILED: {result['message']}")
        
        results.append(result)
        
        # Call progress callback with current result
        if progress_callback:
            progress_callback(i, total, result)
        
        # Rate limiting (except for last item)
        if i < total:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Waiting {RATE_LIMIT_DELAY} seconds...")
            time.sleep(RATE_LIMIT_DELAY)
    
    print("\n" + "="*80)
    print(f"Batch unsubscribe complete!")
    print(f"Total: {total}")
    print(f"  ✓ Auto Success: {auto_success_count}")
    print(f"  ⚠ Manual Required: {manual_required_count}")
    print(f"  ✗ Failed: {failed_count}")
    print("="*80)
    
    return {
        'total': total,
        'auto_success_count': auto_success_count,
        'manual_required_count': manual_required_count,
        'failed_count': failed_count,
        'results': results
    }


def categorize_unsubscribe_difficulty(newsletter_data):
    """
    Pre-analyze newsletter to estimate unsubscribe difficulty.
    
    Args:
        newsletter_data: Dictionary containing newsletter information
        
    Returns:
        str: Difficulty level - 'easy', 'medium', or 'hard'
    """
    unsubscribe_link = newsletter_data.get('unsubscribe_link', '')
    unsubscribe_method = newsletter_data.get('unsubscribe_method', '')
    sender_email = newsletter_data.get('sender_email', '')
    
    # Convert bytes to string if needed
    if isinstance(unsubscribe_link, bytes):
        unsubscribe_link = unsubscribe_link.decode('utf-8', errors='ignore')
    if isinstance(unsubscribe_method, bytes):
        unsubscribe_method = unsubscribe_method.decode('utf-8', errors='ignore')
    if isinstance(sender_email, bytes):
        sender_email = sender_email.decode('utf-8', errors='ignore')
    
    # Ensure we have a string
    unsubscribe_link = str(unsubscribe_link) if unsubscribe_link else ''
    unsubscribe_method = str(unsubscribe_method) if unsubscribe_method else ''
    
    # Easy: Has List-Unsubscribe header
    if unsubscribe_method == 'header':
        return 'easy'
    
    # If no unsubscribe link, return medium
    if not unsubscribe_link:
        return 'medium'
    
    try:
        # Hard: Known domains that require login
        parsed = urlparse(unsubscribe_link)
        netloc = parsed.netloc
        
        # Ensure netloc is a string
        if isinstance(netloc, bytes):
            netloc = netloc.decode('utf-8', errors='ignore')
        netloc = str(netloc).lower()
        
        if any(domain in netloc for domain in LOGIN_REQUIRED_DOMAINS):
            return 'hard'
        
        # Hard: mailto links (require SMTP setup)
        if unsubscribe_link.startswith('mailto:'):
            return 'hard'
        
        # Medium: Simple body link to common domains
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
        
        # Medium: Has unsubscribe link in body
        if unsubscribe_method == 'body':
            return 'medium'
        
    except Exception as e:
        # If parsing fails, default to medium
        print(f"Error categorizing difficulty: {e}")
        return 'medium'
    
    # Default to medium
    return 'medium'


if __name__ == "__main__":
    # Test with sample newsletter data
    test_newsletters = [
        {
            'id': 'test1',
            'sender_email': 'newsletter@example.com',
            'sender_name': 'Test Newsletter',
            'subject': 'Weekly Update',
            'unsubscribe_link': 'https://example.com/unsubscribe',
            'unsubscribe_method': 'body'
        },
        {
            'id': 'test2',
            'sender_email': 'updates@medium.com',
            'sender_name': 'Medium Digest',
            'subject': 'Your Daily Digest',
            'unsubscribe_link': 'https://medium.com/unsubscribe',
            'unsubscribe_method': 'body'
        }
    ]
    
    print("Testing unsubscribe functionality...")
    print("="*80)
    
    # Test difficulty categorization
    print("\nDifficulty Analysis:")
    for newsletter in test_newsletters:
        difficulty = categorize_unsubscribe_difficulty(newsletter)
        print(f"  {newsletter['sender_name']}: {difficulty}")
    
    # Test single unsubscribe
    print("\n" + "="*80)
    print("Testing single unsubscribe:")
    result = unsubscribe_from_newsletter(test_newsletters[0])
    print(f"\nResult: {result}")
    
    # Test batch unsubscribe
    print("\n" + "="*80)
    print("Testing batch unsubscribe:")
    
    def progress_callback(current, total, result):
        print(f"Progress: {current}/{total} - {result['sender_name']}: {result['category']}")
    
    summary = batch_unsubscribe(test_newsletters, progress_callback=progress_callback)
    print(f"\nSummary: {summary}")
