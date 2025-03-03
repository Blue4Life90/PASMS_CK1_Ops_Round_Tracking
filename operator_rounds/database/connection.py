"""Database connection management for Operator Rounds Tracking."""
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Context manager for database connections with improved error handling"""
    conn = None
    try:
        conn = sqlite3.connect('rounds.db')
        conn.execute("PRAGMA foreign_keys = 1")  # Enable foreign key support
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.close()
        raise e
    finally:
        if conn:
            conn.close()