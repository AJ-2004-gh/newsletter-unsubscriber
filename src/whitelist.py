"""
Whitelist Management Module

Manages a SQLite database of whitelisted newsletter senders.
Whitelisted senders will be excluded from unsubscribe operations.
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager


# Database file path
DB_PATH = os.path.join('data', 'whitelist.db')

# SQL schema
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_email TEXT UNIQUE NOT NULL,
    sender_name TEXT,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Ensures proper connection handling and automatic cleanup.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    conn = None
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def init_database():
    """
    Initialize the whitelist database.
    Creates the database file and whitelist table if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_TABLE_SQL)
            print(f"Database initialized at {DB_PATH}")
            return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


def add_to_whitelist(sender_email, sender_name=None):
    """
    Add a sender to the whitelist.
    
    Args:
        sender_email: Email address of the sender (required)
        sender_name: Display name of the sender (optional)
        
    Returns:
        bool: True if added successfully, False if already exists or error
    """
    if not sender_email:
        print("Error: sender_email is required")
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO whitelist (sender_email, sender_name) VALUES (?, ?)",
                (sender_email.lower(), sender_name)
            )
            print(f"Added {sender_email} to whitelist")
            return True
    except sqlite3.IntegrityError:
        print(f"{sender_email} is already in the whitelist")
        return False
    except Exception as e:
        print(f"Error adding to whitelist: {e}")
        return False


def remove_from_whitelist(sender_email):
    """
    Remove a sender from the whitelist.
    
    Args:
        sender_email: Email address of the sender to remove
        
    Returns:
        bool: True if removed successfully, False if not found or error
    """
    if not sender_email:
        print("Error: sender_email is required")
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM whitelist WHERE sender_email = ?",
                (sender_email.lower(),)
            )
            
            if cursor.rowcount > 0:
                print(f"Removed {sender_email} from whitelist")
                return True
            else:
                print(f"{sender_email} not found in whitelist")
                return False
    except Exception as e:
        print(f"Error removing from whitelist: {e}")
        return False


def is_whitelisted(sender_email):
    """
    Check if a sender is in the whitelist.
    
    Args:
        sender_email: Email address to check
        
    Returns:
        bool: True if whitelisted, False otherwise
    """
    if not sender_email:
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM whitelist WHERE sender_email = ?",
                (sender_email.lower(),)
            )
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        print(f"Error checking whitelist: {e}")
        return False


def get_all_whitelisted():
    """
    Get all whitelisted senders.
    
    Returns:
        list: List of dictionaries containing whitelist entries:
            [
                {
                    'id': 1,
                    'sender_email': 'newsletter@example.com',
                    'sender_name': 'Example Newsletter',
                    'added_date': '2025-12-07 10:30:00'
                },
                ...
            ]
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, sender_email, sender_name, added_date FROM whitelist ORDER BY added_date DESC"
            )
            rows = cursor.fetchall()
            
            # Convert rows to list of dictionaries
            whitelist = []
            for row in rows:
                whitelist.append({
                    'id': row['id'],
                    'sender_email': row['sender_email'],
                    'sender_name': row['sender_name'],
                    'added_date': row['added_date']
                })
            
            return whitelist
    except Exception as e:
        print(f"Error retrieving whitelist: {e}")
        return []


def clear_whitelist(confirm=False):
    """
    Remove all entries from the whitelist.
    Requires confirmation to prevent accidental deletion.
    
    Args:
        confirm: Must be True to actually clear the whitelist
        
    Returns:
        bool: True if cleared successfully, False otherwise
    """
    if not confirm:
        print("Error: Must pass confirm=True to clear whitelist")
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM whitelist")
            deleted_count = cursor.rowcount
            print(f"Cleared whitelist ({deleted_count} entries removed)")
            return True
    except Exception as e:
        print(f"Error clearing whitelist: {e}")
        return False


def get_whitelist_count():
    """
    Get the total number of whitelisted senders.
    
    Returns:
        int: Number of whitelisted senders
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM whitelist")
            count = cursor.fetchone()[0]
            return count
    except Exception as e:
        print(f"Error getting whitelist count: {e}")
        return 0


if __name__ == "__main__":
    # Test the whitelist functionality
    print("Testing Whitelist Management System\n")
    print("="*60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_database()
    
    # Add some test entries
    print("\n2. Adding test entries...")
    add_to_whitelist("newsletter@example.com", "Example Newsletter")
    add_to_whitelist("updates@company.com", "Company Updates")
    add_to_whitelist("digest@news.com", "Daily Digest")
    
    # Try adding duplicate
    print("\n3. Testing duplicate prevention...")
    add_to_whitelist("newsletter@example.com", "Duplicate Entry")
    
    # Check if whitelisted
    print("\n4. Checking whitelist status...")
    print(f"newsletter@example.com whitelisted: {is_whitelisted('newsletter@example.com')}")
    print(f"random@email.com whitelisted: {is_whitelisted('random@email.com')}")
    
    # Get all whitelisted
    print("\n5. Retrieving all whitelisted senders...")
    whitelist = get_all_whitelisted()
    print(f"Total whitelisted: {len(whitelist)}")
    for entry in whitelist:
        print(f"  - {entry['sender_name']} ({entry['sender_email']}) - Added: {entry['added_date']}")
    
    # Remove entry
    print("\n6. Removing an entry...")
    remove_from_whitelist("updates@company.com")
    print(f"Remaining entries: {get_whitelist_count()}")
    
    # Clear whitelist
    print("\n7. Clearing whitelist...")
    clear_whitelist(confirm=True)
    print(f"Remaining entries: {get_whitelist_count()}")
    
    print("\n" + "="*60)
    print("Test complete!")
