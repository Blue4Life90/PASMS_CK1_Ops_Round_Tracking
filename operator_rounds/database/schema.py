"""Database schema definition and initialization."""
import sqlite3
from operator_rounds.database.connection import get_db_connection

def add_mode_column_to_round_items():
    """Add mode column to round_items table if it doesn't exist yet"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Check if the column already exists
            c.execute("PRAGMA table_info(round_items)")
            columns = [info[1] for info in c.fetchall()]
            
            if 'mode' not in columns:
                # Add the column
                c.execute("ALTER TABLE round_items ADD COLUMN mode TEXT")
                conn.commit()
                return True, "Mode column added successfully"
            else:
                return True, "Mode column already exists"
                
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"

def init_db():
    """Initialize SQLite database with necessary tables"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Create operators table
            c.execute('''
                CREATE TABLE IF NOT EXISTS operators (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create rounds table
            c.execute('''
                CREATE TABLE IF NOT EXISTS rounds (
                    id INTEGER PRIMARY KEY,
                    round_type TEXT NOT NULL,
                    operator_id INTEGER,
                    shift TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (operator_id) REFERENCES operators (id)
                )
            ''')
            
            # Create sections table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sections (
                    id INTEGER PRIMARY KEY,
                    round_id INTEGER,
                    unit TEXT NOT NULL,
                    section_name TEXT NOT NULL,
                    completed BOOLEAN DEFAULT 0,
                    FOREIGN KEY (round_id) REFERENCES rounds (id)
                )
            ''')
            
            # Create round items table
            c.execute('''
                CREATE TABLE IF NOT EXISTS round_items (
                    id INTEGER PRIMARY KEY,
                    section_id INTEGER,
                    description TEXT NOT NULL,
                    value TEXT,
                    output TEXT,
                    mode TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (section_id) REFERENCES sections (id)
                )
            ''')
            
            conn.commit()
            return True
            
    except sqlite3.Error as e:
        print(f"Database initialization error: {str(e)}")
        return False
    