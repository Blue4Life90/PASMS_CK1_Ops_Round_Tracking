"""
Section editor UI components for Operator Rounds Tracking.

This module provides the interface for:
- Viewing and editing sections within a unit
- Adding, editing, and removing items from sections
- Managing section data with database integration
"""
import streamlit as st
import pandas as pd
import sqlite3
from operator_rounds.database.connection import get_db_connection
from operator_rounds.utils.validation import validate_input_data, ValidationError
from operator_rounds.utils.helpers import generate_unique_form_key
from operator_rounds.database.queries import save_round_section

def render_section_editor(unit, section):
    """
    Render the interface for editing a section with validation.
    
    This provides a dedicated interface for editing existing items in a section.
    
    Args:
        unit (str): The unit name
        section (str): The section name
    """
    st.subheader(f"Section: {section}")
    
    section_data = st.session_state.rounds_data[st.session_state.current_round]["units"][unit]["sections"].get(section, {"items": []})
    
    edit_tab, add_tab = st.tabs(["Edit Existing Items", "Add New Item"])
    
    with edit_tab:
        if section_data["items"]:
            item_descriptions = [item["description"] for item in section_data["items"]]
            selected_item = st.selectbox(
                "Select item to edit",
                options=range(len(item_descriptions)),
                format_func=lambda x: item_descriptions[x]
            )
            
            form_key = generate_unique_form_key(unit, section, f"edit_item_{selected_item}")
            with st.form(form_key):
                item = section_data["items"][selected_item]
                description = st.text_input("Description", value=item["description"])
                value = st.text_input("Value", value=item.get("value", ""))
                output = st.text_input("Output", value=item.get("output", ""))
                mode = st.text_input("Mode", value=item.get("mode", ""))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Save Changes"):
                        try:
                            # Validate the input data
                            valid, error = validate_input_data("Description", description)
                            if not valid:
                                st.error(error)
                                return
                                
                            section_data["items"][selected_item] = {
                                "description": description,
                                "value": value,
                                "output": output,
                                "mode": mode
                            }
                            st.success("Item updated")
                            st.rerun()
                        except ValidationError as e:
                            st.error(str(e))
                
                with col2:
                    if st.form_submit_button("Remove Item"):
                        section_data["items"].pop(selected_item)
                        st.success("Item removed")
                        st.rerun()
        else:
            st.info("No items in this section yet. Use the 'Add New Item' tab to add items.")

def render_section_content(unit_name, section_name, section_data):
    """
    Render the content of a section including item management with improved validation.
    
    This function provides the main interface for viewing section content and 
    managing items within a section.
    
    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        section_data (dict): The section data containing items
        
    Returns:
        str or None: "delete_section" if the section should be deleted, None otherwise
    """
    # Check if operator is logged in first
    if not check_operator_logged_in():
        st.error("⚠️ Please log in as an operator using the sidebar before accessing this section.")
        return
    
    items = section_data.get("items", [])

    if st.session_state.get('debug_mode', False):
        # Add debug information to help us understand the data structure
        st.write("Debug - Items:", items)
        st.write(f"Debug - Current round ID: {st.session_state.current_round_id}")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("➕ Add New Item", key=f"add_item_{unit_name}_{section_name}".replace(" ", "_")):
            if st.session_state.get('debug_mode', False):
                st.write("Debug - Add New Item button clicked")
                st.write(f"Debug - For unit: {unit_name}, section: {section_name}")
            st.session_state.adding_item = f"{unit_name}_{section_name}"
            st.session_state.editing_item = None
            st.rerun()
    with col2:
        if items and st.button("✏️ Edit Items", key=f"edit_items_{unit_name}_{section_name}".replace(" ", "_")):
            st.session_state.editing_item = f"{unit_name}_{section_name}"
            st.session_state.adding_item = None
    with col3:
        if st.button("🗑️ Remove Section", key=f"remove_{unit_name}_{section_name}".replace(" ", "_")):
            if st.session_state.get('confirm_delete') == f"{unit_name}_{section_name}":
                return "delete_section"
            else:
                st.session_state.confirm_delete = f"{unit_name}_{section_name}"
                st.warning("Click 'Remove Section' again to confirm deletion")
    
    # Add new item form with validation
    if st.session_state.get('adding_item') == f"{unit_name}_{section_name}":
        render_add_item_form(unit_name, section_name, section_data)

    # Edit items interface with validation
    if st.session_state.get('editing_item') == f"{unit_name}_{section_name}":
        render_edit_items_interface(unit_name, section_name, section_data, items)

    # Display current items as a dataframe
    if items:
        try:
            df = pd.DataFrame(items)
            if not df.empty:
                # Make sure the mode column exists (even if empty)
                if 'mode' not in df.columns:
                    df['mode'] = ""
                
                # Create a styling function that returns a proper DataFrame
                def highlight_mode(val, prop='background-color'):
                    if val == 'Manual':
                        return f'{prop}: rgba(255, 200, 87, 0.5); font-weight: bold; color: white;'  # Yellow
                    elif val == 'Cascade':
                        return f'{prop}: rgba(74, 222, 128, 0.5); font-weight: bold; color: white;'  # Green
                    elif val == 'Auto-Init':
                        return f'{prop}: rgba(167, 139, 250, 0.5); font-weight: bold; color: white;'  # Soft-Purple
                    elif val == 'B-Cascade':
                        return f'{prop}: rgba(6, 214, 160, 0.5); font-weight: bold; color: white;'  # Bright Turquoise
                    return ''
                
                # Apply styling using a standard pandas approach
                styled_df = df.style.map(
                    lambda x: highlight_mode(x),
                    subset=['mode']
                )
                
                # Add row styling for better visibility
                def highlight_row(row):
                    mode = row.get('mode', '')
                    if mode == 'Manual':
                        return ['background-color: rgba(255, 200, 87, 0.5); font-weight: bold; color: white;'] * len(row)
                    elif mode == 'Cascade':
                        return ['background-color: rgba(74, 222, 128, 0.5); font-weight: bold; color: white;'] * len(row)
                    elif mode == 'Auto-Init':
                        return ['background-color: rgba(167, 139, 250, 0.5); font-weight: bold; color: white;'] * len(row)
                    elif mode == 'B-Cascade':
                        return ['background-color: rgba(6, 214, 160, 0.5); font-weight: bold; color: white;'] * len(row)
                    return [''] * len(row)
                
                styled_df = styled_df.apply(highlight_row, axis=1)
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "description": "Item Description",
                        "value": "Last Value",
                        "output": "Last Output",
                        "mode": "Control Mode"
                    }
                )
            else:
                st.info("No items to display.")
        except Exception as e:
            st.error(f"Error displaying items: {str(e)}")
            if st.session_state.get('debug_mode', False):
                import traceback
                st.write("Debug - Exception with dataframe display:")
                st.write(traceback.format_exc())

def render_add_item_form(unit_name, section_name, section_data):
    """
    Render the form for adding a new item to a section.
    
    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        section_data (dict): The section data
    """
    if st.session_state.get('debug_mode', False):
        st.write("Debug - Displaying Add New Item form")
        
    form_key = f"add_item_form_{unit_name}_{section_name}".replace(" ", "_").lower()
    
    # Create session state keys for form inputs if they don't exist
    form_input_key = f"form_input_{unit_name}_{section_name}".replace(" ", "_")
    if form_input_key not in st.session_state:
        st.session_state[form_input_key] = {
            "description": "",
            "value": "",
            "output": "",
            "mode": ""
        }
    
    with st.form(key=form_key):
        st.subheader("Add New Item")
        
        # Use the session state to maintain values between reruns
        description = st.text_input(
            "Item Description", 
            value=st.session_state[form_input_key]["description"],
            key=f"desc_{form_input_key}"
        )
        
        value = st.text_input(
            "Default Value (optional)", 
            value=st.session_state[form_input_key]["value"],
            key=f"val_{form_input_key}"
        )
        
        output = st.text_input(
            "Default Output (optional)", 
            value=st.session_state[form_input_key]["output"],
            key=f"out_{form_input_key}"
        )

        # Add mode selector for all items - keeping it optional
        mode_options = ["", "Manual", "Auto", "Cascade", "Auto-Init", "B-Cascade"]
        current_mode = st.session_state[form_input_key].get("mode", "")
        
        # Find the index of the current mode, or 0 if not found
        try:
            current_index = mode_options.index(current_mode)
        except ValueError:
            current_index = 0
            
        mode = st.selectbox(
            "Control Mode (if applicable)",
            options=mode_options,
            index=current_index,
            key=f"mode_{form_input_key}"
        )
        
        # Simplified button logic with clear debug output
        submitted = st.form_submit_button("Save Item")
        canceled = st.form_submit_button("Cancel")
        
        # Debug the form submission state
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Save Item button state: {submitted}")

    # Handle form submission outside the form
    process_add_item_form_submission(
        submitted, canceled, unit_name, section_name, 
        description, value, output, mode, section_data, form_input_key
    )

def process_add_item_form_submission(submitted, canceled, unit_name, section_name, 
                                     description, value, output, mode, section_data, form_input_key):
    """
    Process the submission of the add item form.
    
    Args:
        submitted (bool): Whether the form was submitted
        canceled (bool): Whether the form was canceled
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        description (str): The item description
        value (str): The item value
        output (str): The item output
        mode (str): The item mode
        section_data (dict): The section data
        form_input_key (str): The key for the form inputs in session state
    """
    if submitted:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Form was submitted!")
            st.write(f"Debug - Description: {description}")
            st.write(f"Debug - Value: {value}")
            st.write(f"Debug - Output: {output}")
            st.write(f"Debug - Mode: {mode}")
        
        # Update session state with the form values
        st.session_state[form_input_key]["description"] = description
        st.session_state[form_input_key]["value"] = value
        st.session_state[form_input_key]["output"] = output
        st.session_state[form_input_key]["mode"] = mode
        
        # Process the submission
        try:
            # First validate the inputs
            valid, error = validate_input_data("Description", description)
            if not valid:
                st.error(error)
            else:
                # Directly attempt to add the item to the database
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - Attempting database operation")
                    st.write(f"Debug - Current round ID: {st.session_state.current_round_id}")
                
                # Verify the database exists and is accessible
                try:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("SELECT 1")  # Simple test query
                        if st.session_state.get('debug_mode', False):
                            st.write("Debug - Database connection successful")
                        
                        # Start a transaction
                        conn.execute("BEGIN TRANSACTION")
                        
                        try:
                            # Check if section exists first
                            c.execute('''
                                SELECT id FROM sections 
                                WHERE round_id = ? AND LOWER(TRIM(unit)) = LOWER(TRIM(?)) 
                                AND LOWER(TRIM(section_name)) = LOWER(TRIM(?))
                            ''', (st.session_state.current_round_id, unit_name, section_name))
                            
                            section_result = c.fetchone()
                            
                            if section_result:
                                section_id = section_result[0]
                                if st.session_state.get('debug_mode', False):
                                    st.write(f"Debug - Found existing section ID: {section_id}")
                            else:
                                # Create a new section
                                if st.session_state.get('debug_mode', False):
                                    st.write(f"Debug - Creating new section")
                                
                                c.execute('''
                                    INSERT INTO sections (round_id, unit, section_name)
                                    VALUES (?, ?, ?)
                                ''', (st.session_state.current_round_id, unit_name, section_name))
                                
                                section_id = c.lastrowid
                                if st.session_state.get('debug_mode', False):
                                    st.write(f"Debug - Created new section with ID: {section_id}")
                            
                            # Now insert the item
                            if st.session_state.get('debug_mode', False):
                                st.write(f"Debug - Inserting item for section ID: {section_id}")
                            
                            c.execute('''
                                INSERT INTO round_items 
                                (section_id, description, value, output, mode)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (section_id, 
                                  description.strip(), 
                                  value.strip(), 
                                  output.strip(),
                                  mode.strip()))
                            
                            # Get the new item ID
                            item_id = c.lastrowid
                            if st.session_state.get('debug_mode', False):
                                st.write(f"Debug - Item inserted with ID: {item_id}")
                            
                            # Update session state with the new item
                            section_data["items"].append({
                                "description": description.strip(),
                                "value": value.strip(),
                                "output": output.strip(),
                                "mode": mode.strip()
                            })
                            
                            # Commit the transaction
                            conn.commit()
                            
                            if st.session_state.get('debug_mode', False):
                                st.write(f"Debug - Transaction committed")
                            
                            # Reset the form
                            st.session_state[form_input_key] = {
                                "description": "",
                                "value": "",
                                "output": "",
                                "mode": ""
                            }
                            
                            # Hide the form
                            st.session_state.adding_item = None
                            
                            # Show success message and refresh
                            st.success("Item added successfully!")
                            st.rerun()
                            
                        except sqlite3.Error as e:
                            # Roll back on error
                            conn.rollback()
                            st.error(f"Database error: {str(e)}")
                            if st.session_state.get('debug_mode', False):
                                import traceback
                                st.write(f"Debug - SQLite error: {str(e)}")
                                st.write(traceback.format_exc())
                except Exception as e:
                    st.error(f"Database connection error: {str(e)}")
                    if st.session_state.get('debug_mode', False):
                        import traceback
                        st.write(f"Debug - Connection error: {str(e)}")
                        st.write(traceback.format_exc())
        except Exception as e:
            st.error(f"Error: {str(e)}")
            if st.session_state.get('debug_mode', False):
                import traceback
                st.write(f"Debug - General error: {str(e)}")
                st.write(traceback.format_exc())
    
    # Handle cancel button
    if canceled:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Form was canceled")
        # Reset the form
        st.session_state[form_input_key] = {
            "description": "",
            "value": "",
            "output": "",
            "mode": ""
        }
        st.session_state.adding_item = None
        st.rerun()

def render_edit_items_interface(unit_name, section_name, section_data, items):
    """
    Render the interface for editing multiple items in a section.

    Args:
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        section_data (dict): The section data
        items (list): The list of items in the section
    """
    st.subheader("Edit Items")
    for idx, item in enumerate(items):
        form_key = f"edit_item_{unit_name}_{section_name}_{idx}".replace(" ", "_").lower()
        
        # Create form state keys if they don't exist
        form_state_key = f"edit_form_{unit_name}_{section_name}_{idx}".replace(" ", "_").lower()
        if form_state_key not in st.session_state:
            st.session_state[form_state_key] = {
                "description": item["description"],
                "value": item.get("value", ""),
                "output": item.get("output", ""),
                "mode": item.get("mode", "")
            }
        
        with st.expander(f"Edit: {item['description']}", expanded=False):
            with st.form(form_key):
                # Use the session state to maintain values between reruns
                edited_desc = st.text_input(
                    "Description", 
                    value=st.session_state[form_state_key]["description"],
                    key=f"desc_{form_state_key}"
                )
                
                edited_value = st.text_input(
                    "Default Value", 
                    value=st.session_state[form_state_key]["value"],
                    key=f"val_{form_state_key}"
                )
                
                edited_output = st.text_input(
                    "Default Output", 
                    value=st.session_state[form_state_key]["output"],
                    key=f"out_{form_state_key}"
                )

                mode_options = ["", "Manual", "Auto", "Cascade", "Auto-Init", "B-Cascade"]
                current_mode = st.session_state[form_state_key].get("mode", "")
                
                # Find the index of the current mode, or 0 if not found
                try:
                    current_index = mode_options.index(current_mode)
                except ValueError:
                    current_index = 0
                    
                edited_mode = st.selectbox(
                    "Control Mode (if applicable)",
                    options=mode_options,
                    index=current_index,
                    key=f"mode_{form_state_key}"
                )
                
                # Update session state as user types
                st.session_state[form_state_key]["description"] = edited_desc
                st.session_state[form_state_key]["value"] = edited_value
                st.session_state[form_state_key]["output"] = edited_output
                st.session_state[form_state_key]["mode"] = edited_mode
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    save_changes = st.form_submit_button("Save Changes")
                
                with col2:
                    delete_item = st.form_submit_button("Delete Item")
                
                # Debug output
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - Save Changes button state: {save_changes}")
                    st.write(f"Debug - Delete Item button state: {delete_item}")
            
            # Process edit form submission outside the form
            process_edit_item_form_submission(
                save_changes, delete_item, unit_name, section_name, 
                section_data, idx, edited_desc, edited_value, edited_output, edited_mode, 
                form_state_key
            )
    
    if st.button("Done Editing"):
        st.session_state.editing_item = None
        st.rerun()

def process_edit_item_form_submission(save_changes, delete_item, unit_name, section_name, 
                                     section_data, idx, edited_desc, edited_value, edited_output, 
                                     edited_mode, form_state_key):
    """
    Process the submission of an edit item form.
    
    Args:
        save_changes (bool): Whether the save changes button was clicked
        delete_item (bool): Whether the delete item button was clicked
        unit_name (str): The name of the unit
        section_name (str): The name of the section
        section_data (dict): The section data
        idx (int): The index of the item being edited
        edited_desc (str): The edited description
        edited_value (str): The edited value
        edited_output (str): The edited output
        edited_mode (str): The edited mode
        form_state_key (str): The key for the form state in session state
    """
    if save_changes:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Save Changes clicked for item:", idx)
            st.write(f"Debug - New values: {edited_desc}, {edited_value}, {edited_output}, {edited_mode}")
            st.write(f"Debug - Current round ID: {st.session_state.current_round_id}")
            st.write(f"Debug - Unit name: '{unit_name}'")
            st.write(f"Debug - Section name: '{section_name}'")
        
        try:
            # Validate inputs
            valid, error = validate_input_data("Description", edited_desc)
            if not valid:
                st.error(error)
                return
            
            if edited_value:  # Only validate if value is provided
                valid, error = validate_input_data("Value", edited_value)
                if not valid:
                    st.error(error)
                    return
            
            # Save the original item in case we need to roll back
            original_item = dict(section_data["items"][idx])
            original_desc = original_item["description"].strip()
            
            # Update in session state
            section_data["items"][idx] = {
                "description": edited_desc.strip(),
                "value": edited_value.strip(),
                "output": edited_output.strip(),
                "mode": edited_mode
            }
            
            try:
                with get_db_connection() as conn:
                    c = conn.cursor()
                    
                    # Start transaction
                    conn.execute("BEGIN TRANSACTION")
                    
                    # Improved section lookup that's more tolerant of differences
                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Looking for sections with unit='{unit_name}', section='{section_name}' in ANY round")

                    # Get all sections matching the unit and section name across ALL rounds
                    c.execute('''
                        SELECT id, round_id FROM sections 
                        WHERE LOWER(TRIM(unit)) = LOWER(TRIM(?)) 
                        AND LOWER(TRIM(section_name)) = LOWER(TRIM(?))
                    ''', (unit_name, section_name))
                    
                    section_results = c.fetchall()

                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Found {len(section_results)} matching sections across all rounds")
                        for sec in section_results:
                            st.write(f"  Section ID: {sec[0]}, Round ID: {sec[1]}")
                    
                    if not section_results:
                        raise Exception(f"No sections found with unit '{unit_name}' and name '{section_name}' in any round")
                    
                    # Check if the new description would conflict with any existing item
                    if original_desc.lower() != edited_desc.lower():
                        for section_id, _ in section_results:
                            c.execute('''
                                SELECT COUNT(*) FROM round_items 
                                WHERE section_id = ? AND LOWER(TRIM(description)) = LOWER(TRIM(?))
                            ''', (section_id, edited_desc))
                            
                            if c.fetchone()[0] > 0:
                                conn.rollback()
                                st.error("An item with this description already exists. Please use a different description.")
                                section_data["items"][idx] = original_item
                                return
                    
                    # Update items across ALL relevant sections
                    updated_count = 0
                    
                    for section_id, _ in section_results:
                        c.execute('''
                            SELECT id FROM round_items 
                            WHERE section_id = ? AND LOWER(TRIM(description)) = LOWER(TRIM(?))
                        ''', (section_id, original_desc))
                        
                        item_results = c.fetchall()
                        
                        for item_row in item_results:
                            item_id = item_row[0]
                            
                            c.execute('''
                                UPDATE round_items 
                                SET description = ?, value = ?, output = ?, mode = ?
                                WHERE id = ?
                            ''', (edited_desc.strip(), 
                                  edited_value.strip(), 
                                  edited_output.strip(), 
                                  edited_mode.strip(), 
                                  item_id))
                            
                            updated_count += 1
                    
                    if updated_count > 0:
                        # Force refresh on next load
                        st.session_state.rounds_data_needs_refresh = True
                        
                        # Commit changes
                        conn.commit()
                        
                        if st.session_state.get('debug_mode', False):
                            st.write(f"Debug - Updated {updated_count} items across all sections")
                        
                        st.success(f"Item updated successfully in {updated_count} places!")
                        st.rerun()
                    else:
                        # No items found with this description
                        conn.rollback()
                        section_data["items"][idx] = original_item
                        st.error(f"Could not find any items with description '{original_desc}' to update")
            
            except Exception as e:
                # Handle errors
                try:
                    conn.rollback()
                except:
                    pass
                
                # Rollback session state changes
                section_data["items"][idx] = original_item
                
                if st.session_state.get('debug_mode', False):
                    import traceback
                    st.write(f"Debug - Error updating item: {str(e)}")
                    st.write(traceback.format_exc())
                
                st.error(f"Error: {str(e)}")
        
        except Exception as e:
            if st.session_state.get('debug_mode', False):
                import traceback
                st.write(f"Debug - Error updating item: {str(e)}")
                st.write(traceback.format_exc())
            st.error(f"Error: {str(e)}")

    if delete_item:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Delete Item clicked for item:", idx)
            st.write(f"Debug - Current round ID: {st.session_state.current_round_id}")
            st.write(f"Debug - Unit name: '{unit_name}'")
            st.write(f"Debug - Section name: '{section_name}'")
        
        try:
            # Store the item we're about to delete in case we need to roll back
            deleted_item = dict(section_data["items"][idx])
            deleted_desc = deleted_item["description"].strip()
            
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - Item description: '{deleted_item['description']}'")
            
            # Delete the item directly from the database
            try:
                with get_db_connection() as conn:
                    c = conn.cursor()
                    
                    # Start transaction
                    conn.execute("BEGIN TRANSACTION")
                    
                    # Improved section lookup that's more tolerant of differences
                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Looking for sections with unit='{unit_name}', section='{section_name}' in ANY round")
                
                    # Get all sections matching the unit and section name across ALL rounds
                    c.execute('''
                        SELECT id, round_id FROM sections 
                        WHERE LOWER(TRIM(unit)) = LOWER(TRIM(?)) 
                        AND LOWER(TRIM(section_name)) = LOWER(TRIM(?))
                    ''', (unit_name, section_name))
                    
                    section_results = c.fetchall()
                    
                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Found {len(section_results)} matching sections across all rounds")
                        for sec in section_results:
                            st.write(f"  Section ID: {sec[0]}, Round ID: {sec[1]}")
                    
                    if not section_results:
                        raise Exception(f"No sections found with unit '{unit_name}' and name '{section_name}' in any round")
                    
                    # Delete items across ALL relevant sections
                    deleted_count = 0
                    
                    for section_id, _ in section_results:
                        c.execute('''
                            SELECT id FROM round_items 
                            WHERE section_id = ? AND LOWER(TRIM(description)) = LOWER(TRIM(?))
                        ''', (section_id, deleted_desc))
                        
                        item_results = c.fetchall()
                        
                        for item_row in item_results:
                            item_id = item_row[0]
                            
                            c.execute('DELETE FROM round_items WHERE id = ?', (item_id,))
                            deleted_count += 1
                    
                    if deleted_count > 0:
                        # Remove from session state
                        section_data["items"].pop(idx)
                        
                        # Force refresh on next load
                        st.session_state.rounds_data_needs_refresh = True
                        
                        # Commit changes
                        conn.commit()
                        
                        if st.session_state.get('debug_mode', False):
                            st.write(f"Debug - Deleted {deleted_count} items across all sections")
                        
                        st.success(f"Item deleted successfully from {deleted_count} places!")
                        st.rerun()
                    else:
                        # No items found with this description
                        conn.rollback()
                        st.error(f"Could not find any items with description '{deleted_desc}' to delete")
                
            except Exception as e:
                try:
                    conn.rollback()
                except:
                    pass
                
                if st.session_state.get('debug_mode', False):
                    import traceback
                    st.write(f"Debug - Database error deleting item: {str(e)}")
                    st.write(traceback.format_exc())
                
                st.error(f"Error: {str(e)}")
        
        except Exception as e:
            if st.session_state.get('debug_mode', False):
                import traceback
                st.write(f"Debug - Error deleting item: {str(e)}")
                st.write(traceback.format_exc())
            st.error(f"Error: {str(e)}")

def check_operator_logged_in():
    """
    Check if an operator is logged in and return appropriate status.
    
    Returns:
        bool: True if operator is logged in, False otherwise
    """
    is_logged_in = (
        hasattr(st.session_state, 'operator_info_set') 
        and st.session_state.operator_info_set 
        and st.session_state.operator_name
    )
    
    return is_logged_in