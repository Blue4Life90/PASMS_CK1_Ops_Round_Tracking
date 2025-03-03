"""
Operator Rounds Tracking Application
-----------------------------------
A Streamlit application for tracking operator rounds in industrial facilities.
"""
import streamlit as st
from operator_rounds.database.schema import init_db
from operator_rounds.database.schema import add_mode_column_to_round_items
from operator_rounds.utils.state import init_session_state
from operator_rounds.ui.sidebar import render_sidebar
from operator_rounds.ui.view_rounds import view_saved_rounds
from operator_rounds.ui.round_completion import render_round_completion
from operator_rounds.ui.section_editor import render_section_content
from operator_rounds.database.queries import toggle_expand_all
from operator_rounds.utils.validation import validate_input_data

# Page configuration
st.set_page_config(page_title="Operator Rounds Tracking", layout="wide")

# Initialize database and session state
init_db()

mode_column_success, mode_column_message = add_mode_column_to_round_items()

init_session_state()

# Debug toggle (keep in main app.py)
if st.sidebar.checkbox("Enable Debug Mode", value=st.session_state.get('debug_mode', False), key="debug_toggle"):
    st.session_state.debug_mode = True
else:
    st.session_state.debug_mode = False

st.title("Operator Rounds Tracking")

if st.session_state.get('debug_mode', False) and mode_column_success:
    st.write(f"Debug - {mode_column_message}")

# Render the sidebar
render_sidebar()

# Main content area
if st.session_state.get('viewing_rounds'):
    st.header("Saved Rounds History")
    view_saved_rounds()
    if st.button("Return to Round Entry"):
        st.session_state.viewing_rounds = False
        st.rerun()
    st.markdown("---")

# Main rounds interface
if st.session_state.current_round:
    units = st.session_state.rounds_data[st.session_state.current_round]["units"]

    # Debug information
    if st.session_state.get('debug_mode', False) and st.checkbox("Show Debug Info"):
        st.write("Current round type:", st.session_state.current_round)
        st.write("Available units:", list(units.keys()))
    
    if isinstance(units, dict) and len(units) > 0:
        unit_names = list(units.keys())
        if unit_names:
            unit_tabs = st.tabs(unit_names)
            
            for tab, unit_name in zip(unit_tabs, unit_names):
                with tab:
                    if not st.session_state.get('completing_round', False):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.subheader(unit_name)
                        with col2:
                            if st.button("Expand All", key=f"expand_all_{unit_name}", use_container_width=True):
                                toggle_expand_all(unit_name, units[unit_name].get("sections", {}).keys())
                        with col3:
                            if st.button("Complete Round", key=f"complete_{unit_name}", use_container_width=True):
                                if not st.session_state.operator_name:
                                    st.error("Please enter operator name before starting round")
                                else:
                                    st.session_state.completing_round = True
                                    st.session_state.current_section = None
                                    st.rerun()
                        
                        with st.expander("➕ Add New Section", expanded=False):
                            with st.form(f"new_section_{unit_name}"):
                                section_name = st.text_input("Section Name")
                                submit_pressed = st.form_submit_button("Add Section")
                                
                                if submit_pressed:
                                    if not section_name:
                                        st.error("Section name is required")
                                    else:
                                        try:
                                            valid, error = validate_input_data("Section Name", section_name)
                                            if not valid:
                                                st.error(error)
                                            else:
                                                sections = units[unit_name].get("sections", {})
                                                if section_name not in sections:
                                                    # Add section to session state
                                                    sections[section_name] = {"items": []}
                                                    
                                                    # Create initial database entry for this section
                                                    if st.session_state.current_round_id is None:
                                                        # No round exists yet, store in pending sections
                                                        if 'pending_sections' not in st.session_state:
                                                            st.session_state.pending_sections = {}
                                                        
                                                        if unit_name not in st.session_state.pending_sections:
                                                            st.session_state.pending_sections[unit_name] = {}
                                                            
                                                        st.session_state.pending_sections[unit_name][section_name] = {"items": []}
                                                        st.success(f"Section '{section_name}' added (will be saved when operator info is set)")
                                                        st.rerun()
                                                    else:
                                                        # Now save the empty section to database
                                                        from operator_rounds.database.connection import get_db_connection
                                                        import sqlite3
                                                        
                                                        with get_db_connection() as conn:
                                                            conn.execute("BEGIN TRANSACTION")
                                                            try:
                                                                c = conn.cursor()
                                                                c.execute('''
                                                                    INSERT INTO sections (round_id, unit, section_name)
                                                                    VALUES (?, ?, ?)
                                                                ''', (st.session_state.current_round_id, unit_name, section_name))
                                                                conn.commit()
                                                                st.success(f"Section '{section_name}' added")
                                                                st.rerun()
                                                            except sqlite3.Error as e:
                                                                conn.rollback()
                                                                st.error(f"Database error when adding section: {str(e)}")
                                                else:
                                                    st.error("Section already exists")
                                        except Exception as e:
                                            st.error(str(e))
                        
                        # Display existing sections
                        sections = units[unit_name].get("sections", {})
                        if sections:
                            st.write("### Unit Sections")
                            
                            sections_container = st.container()
                            
                            with sections_container:
                                for section_name in sections:
                                    section_id = f"{unit_name}_{section_name}"
                                    
                                    col1, col2 = st.columns([4, 1])
                                    with col1:
                                        st.write(f"#### 📋 {section_name}")
                                    with col2:
                                        if st.button("Edit Section", key=f"edit_{section_id}"):
                                            if section_id in st.session_state.expanded_sections:
                                                st.session_state.expanded_sections.remove(section_id)
                                            else:
                                                st.session_state.expanded_sections.add(section_id)
                                            st.rerun()
                                    
                                    if section_id in st.session_state.expanded_sections:
                                        result = render_section_content(unit_name, section_name, sections[section_name])
                                        if result == "delete_section":
                                            del sections[section_name]
                                            st.session_state.pop('confirm_delete')
                                            st.success(f"Section '{section_name}' removed")
                                            st.rerun()
                                    
                                    st.markdown("---")
                        else:
                            st.info("No sections added yet. Click '➕ Add New Section' above to create your first section.")
                    else:
                        render_round_completion(unit_name)
        else:
            st.warning("No units configured for this round type. Please contact your administrator.")
    else:
        st.warning("No units configured for this round type. Please contact your administrator.")
else:
    st.info("Please select a round sheet from the sidebar to begin.")