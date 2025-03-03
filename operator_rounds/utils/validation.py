"""Validation utilities for Operator Rounds Tracking."""

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_input_data(data_type, value, max_length=255):
    """Validate input data with comprehensive checks"""
    if value is None:
        return False, f"{data_type} cannot be None"
        
    if isinstance(value, str):
        value = value.strip()
        
    if len(str(value)) == 0:
        return False, f"{data_type} cannot be empty"
        
    if len(str(value)) > max_length:
        return False, f"{data_type} exceeds maximum length of {max_length} characters"
    
    return True, None