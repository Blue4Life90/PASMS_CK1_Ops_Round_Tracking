"""
Sidebar UI components for Operator Rounds Tracking.

This module handles all sidebar-related UI elements including:
- Round type selection
- Operator information input and display
- Navigation buttons for viewing rounds and changing operators
"""
import streamlit as st
import sqlite3
from operator_rounds.database.connection import get_db_connection
from operator_rounds.database.queries import start_round

def render_sidebar():
    """
    Render the complete sidebar UI including round selection and operator information.
    
    This function handles:
    1. Round type selection dropdown
    2. Operator login form when not logged in
    3. Operator information display when logged in
    4. Navigation buttons for viewing rounds and changing operators
    """
    with st.sidebar:
        st.header("Round Information")
        
        # Round type selection
        round_type = st.selectbox(
            "Select Round Sheet",
            options=list(st.session_state.rounds_data.keys())
        )
        st.session_state.current_round = round_type
        
        # Operator information section
        if not st.session_state.operator_info_set:
            render_operator_login_form()
        else:
            render_operator_info()

        st.write("---")
        st.write("### Control Mode Colors")
        st.markdown(
            """
            <div style="padding: 5px; background-color: rgba(255, 200, 87, 0.5); margin-bottom: 5px; color: white;">
            <strong>Manual</strong> - Valve in MAN control
            </div>
            <div style="padding: 5px; background-color: rgba(74, 222, 128, 0.5); margin-bottom: 5px; color: white;">
            <strong>Cascade</strong> - Valve in CASC control
            </div>
            <div style="padding: 5px; background-color: rgba(167, 139, 250, 0.5); margin-bottom: 5px; color: white;">
            <strong>Auto-Init</strong> - Valve in AUTO-INIT control
            </div>
            <div style="padding: 5px; background-color: rgba(6, 214, 160, 0.5); margin-bottom: 5px; color: white;">
            <strong>B-Cascade</strong> - Valve in BCAS control
            </div>
            """, 
            unsafe_allow_html=True
        )

def render_operator_login_form():
    """
    Render the operator login form for collecting operator name and shift.
    
    This form is displayed when an operator hasn't logged in yet.
    It collects the operator's name and shift, and initializes the round
    when submitted.
    """
    with st.form("operator_info_form"):
        st.session_state.operator_name = st.text_input(
            "Operator Name", 
            value=st.session_state.operator_name
        )
        st.session_state.shift = st.selectbox(
            "Shift", 
            options=["Days", "Nights"]
        )
        
        if st.form_submit_button("Set Operator Information"):
            if st.session_state.operator_name:
                st.session_state.operator_info_set = True
                
                # Start an initial round immediately
                round_id = start_round(st.session_state.current_round)
                if round_id:
                    st.session_state.current_round_id = round_id
                    
                    # Process any pending sections
                    process_pending_sections(round_id)
                    
                    st.success("Operator information saved and round started!")
                else:
                    st.error("Operator information saved but couldn't start round.")
                st.rerun()
            else:
                st.error("Please enter operator name")

def render_operator_info():
    """
    Render the operator information display and navigation buttons.
    
    This is shown when an operator is already logged in and displays:
    1. The current operator's name and shift
    2. Navigation buttons for viewing previous rounds or changing operator
    """
    st.write("---")  # Visual separator
    st.write(f"**Operator:** {st.session_state.operator_name}")
    st.write(f"**Shift:** {st.session_state.shift}")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Previous Rounds", use_container_width=True):
            st.session_state.viewing_rounds = True
            st.rerun()
    with col2:
        if st.button("Change Operator", use_container_width=True):
            st.session_state.operator_info_set = False
            st.rerun()

def process_pending_sections(round_id):
    """
    Process any sections that were created before the operator logged in.
    
    Args:
        round_id (int): The ID of the newly created round
    """
    if hasattr(st.session_state, 'pending_sections') and st.session_state.pending_sections:
        for unit_name, sections in st.session_state.pending_sections.items():
            for section_name, section_data in sections.items():
                # Save each pending section to the database
                with get_db_connection() as conn:
                    conn.execute("BEGIN TRANSACTION")
                    try:
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO sections (round_id, unit, section_name)
                            VALUES (?, ?, ?)
                        ''', (round_id, unit_name, section_name))
                        
                        # If there are any items, save those too
                        section_id = c.lastrowid
                        for item in section_data.get("items", []):
                            c.execute('''
                                INSERT INTO round_items 
                                (section_id, description, value, output, mode)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (section_id, 
                                  item.get("description", ""), 
                                  item.get("value", ""), 
                                  item.get("output", ""),
                                  item.get("mode", "")))
                        
                        conn.commit()
                    except sqlite3.Error as e:
                        conn.rollback()
                        st.error(f"Error saving pending section: {str(e)}")
        
        # Clear pending sections after processing
        st.session_state.pending_sections = {}