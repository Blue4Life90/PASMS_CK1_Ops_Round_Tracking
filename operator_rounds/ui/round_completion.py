"""
Round completion UI components for Operator Rounds Tracking.

This module provides the interface for operators to complete rounds
by filling in values for each section in a step-by-step process.
"""
import streamlit as st
import logging
import sqlite3
import traceback
from operator_rounds.database.connection import get_db_connection
from operator_rounds.database.queries import start_round, save_round_section
from operator_rounds.utils.validation import validate_input_data

def render_round_completion(unit):
    """
    Render the interface for completing a round with improved form handling.
    This function manages the step-by-step process of completing a round for a specific unit.
    
    Args:
        unit (str): The name of the unit being checked
    """
    # Initialize unit-specific section tracking if it doesn't exist
    if 'unit_sections' not in st.session_state:
        st.session_state.unit_sections = {}
    
    # Create a tracking structure for this specific unit if it doesn't exist
    if unit not in st.session_state.unit_sections:
        st.session_state.unit_sections[unit] = {
            'current_section': None,  # Tracks which section we're currently working on
            'completed_sections': set(),  # Keeps track of finished sections
            'last_section_data': {}  # Stores the data from the last form submission
        }

    # Get all sections for this unit from the rounds data structure
    sections = st.session_state.rounds_data[st.session_state.current_round]["units"][unit]["sections"]
    current_section = st.session_state.unit_sections[unit]['current_section']
    
    if st.session_state.get('debug_mode', False):
        st.write(f"Debug - Unit: {unit}")
        st.write(f"Debug - Available sections: {list(sections.keys())}")
        st.write(f"Debug - Current section: {current_section}")
        st.write(f"Debug - Completed sections: {st.session_state.unit_sections[unit]['completed_sections']}")
    
    # If no section is selected and sections exist, start with the first one
    if not current_section and sections:
        sections_list = list(sections.keys())
        current_section = sections_list[0]
        st.session_state.unit_sections[unit]['current_section'] = current_section
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Setting initial section to: {current_section}")
    
    # Create a new round if one hasn't been started
    if not hasattr(st.session_state, 'current_round_id') or not st.session_state.current_round_id:
        round_id = start_round(unit)
        if not round_id:
            st.error("Failed to start round. Please ensure operator name is entered.")
            return
        st.session_state.current_round_id = round_id
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Started new round with ID: {round_id}")
    
    # Verify that there are sections to complete
    if not sections:
        st.error("No sections found for this unit. Please add sections before completing the round.")
        if st.button("Return to Unit View", key=f"return_empty_{unit}"):
            st.session_state.completing_round = False
            st.rerun()
        return
    
    # Get a stable ordered list of sections
    sections_list = list(sections.keys())
    
    # Handle the case where the current section doesn't exist (might have been deleted)
    if current_section not in sections:
        st.error(f"Section '{current_section}' not found. Starting from the first section.")
        current_section = sections_list[0]
        st.session_state.unit_sections[unit]['current_section'] = current_section
        st.rerun()
        return
    
    # Get the current section index for progress tracking
    current_index = sections_list.index(current_section)

    if st.session_state.get('debug_mode', False):
        st.write(f"Debug - Current section (raw): '{current_section}'")
        st.write(f"Debug - Section in list? {'Yes' if current_section in sections_list else 'No'}")
        
        # Print exact string representations to spot difference
        st.write(f"Debug - Current section (repr): {repr(current_section)}")
        for i, s in enumerate(sections_list):
            st.write(f"Debug - sections_list[{i}] (repr): {repr(s)}")
    
    # Display the current section header
    st.subheader(f"Completing Round: {current_section}")
    
    # Show progress indicator
    progress_text = f"Section {current_index + 1} of {len(sections_list)}"
    st.write(f"**{progress_text}**")
    st.progress((current_index + 1) / len(sections_list))
    
    # Get the data for the current section
    section_data = sections.get(current_section, {"items": []})
    
    # Create a unique form key for this section
    form_key = f"complete_section_{unit}_{current_section}_{current_index}".replace(" ", "_").lower()
    
    # Use session state to track form values between reruns
    form_values_key = f"form_values_{unit}_{current_section}".replace(" ", "_").lower()
    if form_values_key not in st.session_state:
        # Initialize with current values
        st.session_state[form_values_key] = {}
        for item in section_data["items"]:
            item_key = item["description"].replace(" ", "_").lower()
            st.session_state[form_values_key][f"value_{item_key}"] = item.get("value", "")
            st.session_state[form_values_key][f"output_{item_key}"] = item.get("output", "")
            st.session_state[form_values_key][f"mode_{item_key}"] = item.get("mode", "")
    
    # Start the form for data entry
    with st.form(form_key):
        updated_items = []
        
        # Display each item in the section for data entry
        for item in section_data["items"]:
            st.write(f"**{item['description']}**")
            
            # Create unique keys for input fields to prevent conflicts
            base_key = item['description'].replace(" ", "_").lower()
            
            try:
                # Validate any existing values
                if item.get("value"):
                    valid, error = validate_input_data("Value", item.get("value"))
                    if not valid and st.session_state.get('debug_mode', False):
                        st.warning(f"Previous value may be invalid: {error}")
                
                # Create input fields for value, output, and mode
                value_key = f"value_{base_key}"
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - {value_key}")

                output_key = f"output_{base_key}"
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - {output_key}")

                mode_key = f"mode_{base_key}"
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - {mode_key}")
                
                # Use session state to maintain values between reruns
                value = st.text_input(
                    "Value", 
                    value=st.session_state[form_values_key].get(value_key, item.get("value", "")),
                    key=value_key
                )
                
                output = st.text_input(
                    "Output (if applicable)", 
                    value=st.session_state[form_values_key].get(output_key, item.get("output", "")),
                    key=output_key
                )

                mode_options = ["", "Manual", "Auto", "Cascade", "Auto-Init", "B-Cascade"]
                current_mode = st.session_state[form_values_key].get(mode_key, item.get("mode", ""))
                
                # Find the index of the current mode, or 0 if not found
                try:
                    mode_index = mode_options.index(current_mode)
                except ValueError:
                    mode_index = 0
                    
                mode = st.selectbox(
                    "Control Mode (if applicable)",
                    options=mode_options,
                    index=mode_index,
                    key=mode_key
                )
                
                # Store in session state as user types
                st.session_state[form_values_key][value_key] = value
                st.session_state[form_values_key][output_key] = output
                st.session_state[form_values_key][mode_key] = mode
                
            except Exception as e:
                st.error(str(e))
                continue
            
            st.markdown("---")  # Visual separator between items
            
            # Store the updated values
            updated_items.append({
                "description": item["description"],
                "value": value,
                "output": output,
                "mode": mode
            })
        
        # Handle navigation and form submission
        if current_index < len(sections_list) - 1:
            # Not the last section - show "Next Section" button
            next_button = st.form_submit_button("Next Section", use_container_width=True)
        else:
            # Last section - show "Complete Round" button
            next_button = st.form_submit_button("Complete Round", use_container_width=True)
    
    # Handle form submission outside the form but in the function
    if next_button:
        handle_section_form_submission(
            unit, current_section, sections, sections_list, 
            current_index, updated_items
        )

def handle_section_form_submission(unit, current_section, sections, sections_list, current_index, updated_items):
    """
    Handle the submission of a section form during round completion.
    
    This function processes the data entered in the form, saves it to the database,
    and advances to the next section or completes the round.
    
    Args:
        unit (str): The unit being checked
        current_section (str): The current section being completed
        sections (dict): All sections for this unit
        sections_list (list): Ordered list of section names
        current_index (int): Index of the current section in the list
        updated_items (list): The updated items from the form
    """
    if st.session_state.get('debug_mode', False):
        st.write("Debug - Next/Complete button clicked")
        st.write(f"Debug - Current index: {current_index}")
        st.write(f"Debug - Total sections: {len(sections_list)}")
        st.write(f"Debug - Updated items: {updated_items}")
    
    try:
        # Validate all values before saving
        validation_errors = []
        for item in updated_items:
            valid, error = validate_input_data("Value", item["value"])
            if not valid:
                validation_errors.append(error)
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
                logging.error(error)
            return
        
        # Save the current section data
        sections[current_section]["items"] = updated_items
        save_success = save_round_section(unit, current_section, {"items": updated_items})
        
        if not save_success:
            st.error("Failed to save section data")
            return
        
        # Mark this section as completed
        st.session_state.unit_sections[unit]['completed_sections'].add(current_section)
        
        if current_index < len(sections_list) - 1:
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - sections list: {sections_list}")
                st.write(f"Debug - TRUE")

            # Move to next section
            next_section = sections_list[current_index + 1]
            st.session_state.unit_sections[unit]['current_section'] = next_section
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - next section: {next_section}")
            
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - Moving to next section: {next_section}")
            
            # Clear form values for the next section
            next_form_key = f"form_values_{unit}_{next_section}".replace(" ", "_").lower()
            if next_form_key not in st.session_state:
                st.session_state[next_form_key] = {}
            
            st.success(f"Section '{current_section}' completed. Moving to '{next_section}'")
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - next form key: {next_form_key}")
            st.rerun()
        else:
            # This was the last section, complete the round
            st.session_state.completing_round = False
            st.session_state.unit_sections[unit]['current_section'] = None
            st.session_state.unit_sections[unit]['completed_sections'] = set()
            
            # Don't reset current_round_id here as it's needed for other operations
            
            st.success("Round completed successfully!")

            st.rerun()
            
    except Exception as e:
        st.error(f"Error processing form: {str(e)}")
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Exception details:")
            st.write(traceback.format_exc())
            logging.error(e)
