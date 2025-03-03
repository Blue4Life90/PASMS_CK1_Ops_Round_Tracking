"""
Configuration settings for Operator Rounds Tracking application.

This module centralizes all configuration parameters used across the application,
including database settings, UI customization options, default values, and feature flags.
Changing these values allows customization of the application without modifying code.
"""
import os
from pathlib import Path
from typing import Dict, List, Any

# Application metadata
APP_NAME = "Operator Rounds Tracking"
APP_VERSION = "1.0.0"
APP_AUTHOR = "MDGL"
APP_DESCRIPTION = "A Streamlit application for tracking operator rounds in FCC Cracking 1."

# Database configuration
DATABASE = {
    "filename": "rounds.db",  # SQLite database filename
    "path": "",  # Empty string means use current directory
    "backup_enabled": True,  # Whether to create periodic backups
    "backup_interval_days": 7,  # How often to back up the database
    "max_backups": 5,  # Maximum number of backup files to keep
    "foreign_keys": True,  # Whether to enable SQLite foreign key support
}

# Get full database path
def get_database_path() -> str:
    """Return the full path to the database file."""
    if DATABASE["path"]:
        return os.path.join(DATABASE["path"], DATABASE["filename"])
    return DATABASE["filename"]

# Feature flags - control which features are enabled
FEATURES = {
    "export_csv": True,  # Allow exporting rounds to CSV
    "import_csv": False,  # Allow importing rounds from CSV (future feature)
    "advanced_analytics": False,  # Enable advanced analytics dashboard (future feature)
    "user_management": False,  # Enable user roles and permissions (future feature)
    "notifications": False,  # Enable email/SMS notifications (future feature)
    "dark_mode": True,  # Enable dark mode option in UI
}

# Default application settings
DEFAULTS = {
    "shift_options": ["Days", "Nights", "Relief"],  # Available shift options
    "debug_mode": False,  # Default debug mode setting
    "include_metadata_in_exports": True,  # Include round metadata in exports by default
    "items_per_page": 20,  # Number of items to show per page in tables
    "session_expiry_hours": 12,  # Session expiry time in hours
    "date_format": "%Y-%m-%d %H:%M:%S",  # Default date format
    "short_date_format": "%Y-%m-%d",  # Format for dates without time
}

# Round types and default units/sections
ROUND_TEMPLATES = {
    "Alky Console Round Sheet": {
        "units": {
            "017 Alky I": {"sections": {}},
            "010 Olefin Splitter": {"sections": {}},
            "122 Iso Octene": {"sections": {}},
            "067 Hydrofiner": {"sections": {}},
            "040 LER II": {"sections": {}}
        }
    },
    "FCC Console Round Sheet": {
        "units": {}
    }
}


# UI Customization
UI = {
    "primary_color": "#272553",  # Primary theme color (Steel Blue)
    "secondary_color": "#FF8C00",  # Secondary accent color (Dark Orange)
    "sidebar_width": "medium",  # Sidebar width: "small", "medium", or "large"
    "max_content_width": 1200,  # Maximum width of content area in pixels
    "show_logo": True,  # Whether to show company logo in sidebar
    "logo_path": "assets/logo.png",  # Path to logo image
    "favicon_path": "assets/favicon.ico",  # Path to favicon
    "custom_css": """
        /* Custom CSS can be added here */
        .st-bq {
            border-left-color: #4682B4;
        }
        .stButton>button {
            border-radius: 4px;
        }
    """
}

# Error messages - centralizing error messages makes internationalization easier
ERROR_MESSAGES = {
    "db_connection_error": "Could not connect to the database. Please check your connection settings.",
    "db_query_error": "An error occurred while querying the database: {error}",
    "validation_error": "Validation error: {error}",
    "item_not_found": "Item not found: {item}",
    "section_not_found": "Section not found: {section}",
    "operator_required": "Please enter operator name before starting round",
    "section_required": "Section name is required",
    "item_required": "Item description is required",
    "duplicate_section": "A section with this name already exists",
    "duplicate_item": "An item with this description already exists",
    "round_not_started": "No active round found. Please start a new round.",
    "save_failed": "Failed to save data. Please try again.",
    "export_failed": "Failed to export data: {error}",
}

# Success messages
SUCCESS_MESSAGES = {
    "round_started": "Round started successfully",
    "round_completed": "Round completed successfully!",
    "section_added": "Section '{section}' added successfully",
    "section_deleted": "Section '{section}' removed successfully",
    "item_added": "Item added successfully",
    "item_updated": "Item updated successfully",
    "item_deleted": "Item deleted successfully",
    "export_success": "Data exported successfully",
}

# Paths configuration
PATHS = {
    "exports": os.path.join("data", "exports"),
    "imports": os.path.join("data", "imports"),
    "backups": os.path.join("data", "backups"),
    "logs": os.path.join("logs"),
}

# Create directories if they don't exist
def create_directories():
    """Create necessary directories for the application."""
    for path in PATHS.values():
        Path(path).mkdir(parents=True, exist_ok=True)

# Helper function to get configuration as dictionary
def get_config_dict() -> Dict[str, Any]:
    """Return all configuration as a dictionary for easy access."""
    return {
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "author": APP_AUTHOR,
            "description": APP_DESCRIPTION,
        },
        "database": DATABASE,
        "features": FEATURES,
        "defaults": DEFAULTS,
        "round_templates": ROUND_TEMPLATES,
        "ui": UI,
        "error_messages": ERROR_MESSAGES,
        "success_messages": SUCCESS_MESSAGES,
        "paths": PATHS,
    }