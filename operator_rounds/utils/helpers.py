"""Helper functions for Operator Rounds Tracking."""
import hashlib
from datetime import datetime

def generate_unique_form_key(unit, section, prefix=""):
    """Generate guaranteed unique form keys"""
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_string = f"{prefix}_{unit}_{section}_{timestamp}"
    
    hash_object = hashlib.md5(unique_string.encode())
    hash_value = hash_object.hexdigest()[:8]
    
    return f"{prefix}_{unit}_{section}_{hash_value}".replace(" ", "_").lower()