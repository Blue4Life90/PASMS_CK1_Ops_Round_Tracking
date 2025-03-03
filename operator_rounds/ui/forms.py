"""
Form utilities for Operator Rounds Tracking.

This module provides reusable components and utilities for building
and managing forms throughout the application. It helps maintain
consistency in form appearance and behavior while reducing code duplication.
"""
import streamlit as st
import sqlite3
import traceback
from datetime import datetime
import hashlib
from operator_rounds.utils.validation import validate_input_data, ValidationError
from operator_rounds.database.connection import get_db_connection

def generate_unique_form_key(unit, section, prefix=""):
    """
    Generate a guaranteed unique form key to prevent form conflicts in Streamlit.
    
    This function creates keys that are stable for the same inputs but unique
    across different forms by combining input parameters with a timestamp
    and applying a hash function.
    
    Args:
        unit (str): The unit name
        section (str): The section name
        prefix (str): Optional prefix to identify form type
        
    Returns:
        str: A unique form key safe for use in Streamlit forms
    """
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_string = f"{prefix}_{unit}_{section}_{timestamp}"
    
    hash_object = hashlib.md5(unique_string.encode())
    hash_value = hash_object.hexdigest()[:8]
    
    return f"{prefix}_{unit}_{section}_{hash_value}".replace(" ", "_").lower()

def create_section_form(unit_name, section_name, form_key, on_submit=None):
    """
    Create and render a form for adding or editing a section.
    
    This function provides a consistent form for section data entry
    across the application.
    
    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section (empty for new sections)
        form_key (str): A unique key for the form
        on_submit (callable, optional): Callback function when form is submitted
        
    Returns:
        dict: Form data if submitted, None otherwise
    """
    with st.form(key=form_key):
        section_name_input = st.text_input(
            "Section Name", 
            value=section_name,
            disabled=bool(section_name)  # Disable if editing existing section
        )
        
        submit_button = st.form_submit_button("Save Section")
        
        if submit_button:
            try:
                # Validate section name
                valid, error = validate_input_data("Section Name", section_name_input)
                if not valid:
                    st.error(error)
                    return None
                
                # Return form data
                form_data = {
                    "section_name": section_name_input,
                    "unit_name": unit_name
                }
                
                # Call the submit callback if provided
                if on_submit:
                    on_submit(form_data)
                
                return form_data
            except ValidationError as e:
                st.error(str(e))
                return None
            except Exception as e:
                st.error(f"Error in form: {str(e)}")
                if st.session_state.get('debug_mode', False):
                    st.write("Debug - Exception details:")
                    st.write(traceback.format_exc())
                return None
    
    return None

def create_item_form(unit_name, section_name, item=None, form_key=None):
    """
    Create and render a form for adding or editing an item within a section.
    
    This function provides a consistent form for item data entry
    across the application. It handles both new items and editing existing ones.
    
    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        item (dict, optional): Existing item data for editing
        form_key (str, optional): A unique key for the form
        
    Returns:
        tuple: (bool, dict) - (was_submitted, form_data)
    """
    # Generate form key if not provided
    if not form_key:
        form_key = generate_unique_form_key(
            unit_name, 
            section_name, 
            f"item_form_{datetime.now().strftime('%H%M%S')}"
        )
    
    # Create form state key for persisting values between reruns
    form_state_key = f"form_state_{form_key}"
    if form_state_key not in st.session_state:
        st.session_state[form_state_key] = {
            "description": item.get("description", "") if item else "",
            "value": item.get("value", "") if item else "",
            "output": item.get("output", "") if item else "",
            "mode": item.get("mode", "") if item else ""
        }
    
    with st.form(key=form_key):
        st.subheader("Item Details")
        
        # Item fields with session state for value persistence
        description = st.text_input(
            "Description *", 
            value=st.session_state[form_state_key]["description"],
            key=f"desc_{form_key}"
        )
        
        value = st.text_input(
            "Default Value", 
            value=st.session_state[form_state_key]["value"],
            key=f"val_{form_key}"
        )
        
        output = st.text_input(
            "Default Output", 
            value=st.session_state[form_state_key]["output"],
            key=f"out_{form_key}"
        )


        # Add mode selector for editing
        mode_options = ["", "Manual", "Auto", "Cascade", "Auto-Init", "B-Cascade"]
        current_mode = st.session_state[form_state_key].get("mode", "")
        
        # Find the index of the current mode, or 0 if not found
        try:
            current_index = mode_options.index(current_mode)
        except ValueError:
            current_index = 0
            
        mode = st.selectbox(
            "Control Mode (if applicable)",
            options=mode_options,
            index=current_index,
            key=f"mode_{form_key}"
        )
        
        # Update session state as user types
        st.session_state[form_state_key]["description"] = description
        st.session_state[form_state_key]["value"] = value
        st.session_state[form_state_key]["output"] = output
        st.session_state[form_state_key]["mode"] = mode
        
        # Form buttons - different labels based on edit vs add
        submit_label = "Update Item" if item else "Add Item"
        submitted = st.form_submit_button(submit_label)
        canceled = st.form_submit_button("Cancel")
        
    # Return early if form wasn't submitted
    if not submitted and not canceled:
        return (False, None)
    
    # Handle cancelation
    if canceled:
        # Reset form state
        st.session_state[form_state_key] = {
            "description": "",
            "value": "",
            "output": "",
            "mode": ""
        }
        return (True, {"action": "cancel"})
    
    # Process submission
    if submitted:
        try:
            # Validate required fields
            valid, error = validate_input_data("Description", description)
            if not valid:
                st.error(error)
                return (True, {"action": "error", "message": error})
            
            # Return the form data
            form_data = {
                "action": "save",
                "data": {
                    "description": description.strip(),
                    "value": value.strip(),
                    "output": output.strip(),
                    "mode": mode.strip()
                },
                "is_edit": bool(item)
            }
            
            # Reset form state on successful submission for add (not edit)
            if not item:
                st.session_state[form_state_key] = {
                    "description": "",
                    "value": "",
                    "output": "",
                    "mode": ""
                }
            
            return (True, form_data)
            
        except Exception as e:
            st.error(f"Error processing form: {str(e)}")
            if st.session_state.get('debug_mode', False):
                st.write("Debug - Exception details:")
                st.write(traceback.format_exc())
            return (True, {"action": "error", "message": str(e)})
    
    return (False, None)

def create_multi_item_form(unit_name, section_name, items, form_key=None):
    """
    Create and render a form for completing a round section with multiple items.
    
    This specialized form is used during round completion to present
    all items in a section for the operator to fill in values.
    
    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        items (list): The list of items to include in the form
        form_key (str, optional): A unique key for the form
        
    Returns:
        tuple: (bool, dict) - (was_submitted, updated_items)
    """
    if not form_key:
        form_key = f"multi_item_{unit_name}_{section_name}".replace(" ", "_").lower()
    
    # Form values key for session state
    form_values_key = f"multi_values_{form_key}"
    if form_values_key not in st.session_state:
        # Initialize with current values
        st.session_state[form_values_key] = {}
        for item in items:
            item_key = item["description"].replace(" ", "_").lower()
            st.session_state[form_values_key][f"value_{item_key}"] = item.get("value", "")
            st.session_state[form_values_key][f"output_{item_key}"] = item.get("output", "")
            st.session_state[form_values_key][f"mode_{item_key}"] = item.get("mode", "")
    
    with st.form(form_key):
        updated_items = []
        
        for item in items:
            st.write(f"**{item['description']}**")
            
            # Create unique keys for input fields
            base_key = item['description'].replace(" ", "_").lower()
            value_key = f"value_{base_key}"
            output_key = f"output_{base_key}"
            mode_key = f"mode_{base_key}"
            
            # Create input fields with session state
            value = st.text_input(
                "Value", 
                value=st.session_state[form_values_key].get(value_key, item.get("value", "")),
                key=f"{form_key}_{value_key}"
            )
            
            output = st.text_input(
                "Output (if applicable)", 
                value=st.session_state[form_values_key].get(output_key, item.get("output", "")),
                key=f"{form_key}_{output_key}"
            )

            # Add mode selector for editing
            mode_options = ["", "Manual", "Auto", "Cascade", "Auto-Init", "B-Cascade"]
            current_mode = st.session_state[form_values_key].get(mode_key, item.get("mode", ""))
            
            # Find the index of the current mode, or 0 if not found
            try:
                current_index = mode_options.index(current_mode)
            except ValueError:
                current_index = 0
                
            mode = st.selectbox(
                "Control Mode (if applicable)",
                options=mode_options,
                index=current_index,
                key=f"{form_key}_{mode_key}"
            )
            
            # Store in session state
            st.session_state[form_values_key][value_key] = value
            st.session_state[form_values_key][output_key] = output
            st.session_state[form_values_key][mode_key] = mode
            
            # Add to updated items
            updated_items.append({
                "description": item["description"],
                "value": value,
                "output": output,
                "mode": mode
            })
            
            st.markdown("---")
        
        # Submit button
        submitted = st.form_submit_button("Save", use_container_width=True)
    
    if submitted:
        # Validate all items
        validation_errors = []
        for item in updated_items:
            if item.get("value"):
                valid, error = validate_input_data("Value", item["value"])
                if not valid:
                    validation_errors.append(f"Error in '{item['description']}': {error}")
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
            return (True, {"action": "error", "messages": validation_errors})
        
        return (True, {"action": "save", "items": updated_items})
    
    return (False, None)

def save_item_to_database(unit_name, section_name, item_data):
    """
    Save an item to the database with proper error handling.
    
    This utility function handles the database operations for saving
    an item, either as a new item or updating an existing one.
    
    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        item_data (dict): The item data to save
        
    Returns:
        tuple: (bool, str) - (success, message)
    """
    if not st.session_state.current_round_id:
        return (False, "No active round found")
    
    try:
        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            c = conn.cursor()
            
            # Find or create the section
            c.execute('''
                SELECT id FROM sections 
                WHERE round_id = ? AND LOWER(TRIM(unit)) = LOWER(TRIM(?)) 
                AND LOWER(TRIM(section_name)) = LOWER(TRIM(?))
            ''', (st.session_state.current_round_id, unit_name, section_name))
            
            section_result = c.fetchone()
            
            if section_result:
                section_id = section_result[0]
            else:
                # Create new section
                c.execute('''
                    INSERT INTO sections (round_id, unit, section_name)
                    VALUES (?, ?, ?)
                ''', (st.session_state.current_round_id, unit_name, section_name))
                section_id = c.lastrowid
            
            # Check if item already exists (for update)
            original_desc = item_data.get("original_description")
            new_desc = item_data["description"]
            
            if original_desc:
                # This is an update - find the existing item
                c.execute('''
                    SELECT id FROM round_items 
                    WHERE section_id = ? AND LOWER(TRIM(description)) = LOWER(TRIM(?))
                ''', (section_id, original_desc))
                
                item_result = c.fetchone()
                
                if item_result:
                    # Update the item
                    item_id = item_result[0]
                    c.execute('''
                        UPDATE round_items 
                        SET description = ?, value = ?, output = ?, mode = ?
                        WHERE id = ?
                    ''', (new_desc, 
                          item_data["value"], 
                          item_data["output"], 
                          item_data["mode"], 
                          item_id))
                    
                    conn.commit()
                    return (True, f"Item '{new_desc}' updated successfully")
                else:
                    conn.rollback()
                    return (False, f"Item '{original_desc}' not found for update")
            else:
                # This is a new item - check if description already exists
                c.execute('''
                    SELECT id FROM round_items 
                    WHERE section_id = ? AND LOWER(TRIM(description)) = LOWER(TRIM(?))
                ''', (section_id, new_desc))
                
                if c.fetchone():
                    conn.rollback()
                    return (False, f"An item with description '{new_desc}' already exists")
                
                # Insert new item
                c.execute('''
                    INSERT INTO round_items (section_id, description, value, output, mode)
                    VALUES (?, ?, ?, ?, ?)
                ''', (section_id, new_desc, 
                      item_data["value"], 
                      item_data["output"], 
                      item_data["mode"]))
                
                conn.commit()
                return (True, f"Item '{new_desc}' added successfully")
                
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Database error: {str(e)}")
            st.write(traceback.format_exc())
        return (False, f"Database error: {str(e)}")
        
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Error: {str(e)}")
            st.write(traceback.format_exc())
        return (False, f"Error: {str(e)}")
    