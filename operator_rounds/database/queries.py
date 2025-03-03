"""
Database queries for Operator Rounds Tracking.

This module provides functions for interacting with the SQLite database,
including creating, reading, updating, and deleting records for rounds,
sections, items, and operators.
"""
import sqlite3
import traceback
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
import streamlit as st
import pandas as pd

from operator_rounds.database.connection import get_db_connection
from operator_rounds.database.models import Round, Section, RoundItem, Operator

def start_round(unit_name: str) -> Optional[int]:
    """
    Create a new round in the database.
    
    Args:
        unit_name (str): The name of the unit to start the round for
        
    Returns:
        Optional[int]: The ID of the newly created round, or None if an error occurred
    """
    try:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Attempting to start round with:")
            st.write(f"Operator: {st.session_state.operator_name}")
            st.write(f"Round type: {st.session_state.current_round}")
            st.write(f"Shift: {st.session_state.shift}")
            
        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            c = conn.cursor()
            
            # First try to get the operator
            c.execute('SELECT id FROM operators WHERE name = ?', (st.session_state.operator_name,))
            operator_result = c.fetchone()
            
            if operator_result:
                operator_id = operator_result[0]
            else:
                # Insert new operator
                c.execute('INSERT INTO operators (name) VALUES (?)', (st.session_state.operator_name,))
                operator_id = c.lastrowid
            
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - Got operator_id: {operator_id}")
            
            # Create new round
            c.execute('''
                INSERT INTO rounds (round_type, operator_id, shift)
                VALUES (?, ?, ?)
            ''', (st.session_state.current_round, operator_id, st.session_state.shift))
            
            round_id = c.lastrowid
            
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - Created round with ID: {round_id}")
                
            conn.commit()
            
            return round_id
            
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - SQLite error in start_round: {str(e)}")
            st.write(traceback.format_exc())
        return None

def save_round_section(unit: str, section: str, data: Dict[str, Any]) -> bool:
    """
    Save section data to the database, preserving historical round items.
    
    Args:
        unit (str): The unit name
        section (str): The section name
        data (Dict[str, Any]): The section data including items
        
    Returns:
        bool: True if successful, False otherwise
    """
    if st.session_state.get('debug_mode', False):
        st.write("Debug - save_round_section function called")
        st.write(f"Debug - Unit: {unit}, Section: {section}")
        st.write(f"Debug - Items count: {len(data['items'])}")
    
    # Verify we have a valid round ID
    if not st.session_state.current_round_id:
        st.error("No active round found. Please start a new round.")
        return False
        
    try:
        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            
            try:
                c = conn.cursor()
                
                # Find the section ID
                c.execute('''
                    SELECT id 
                    FROM sections 
                    WHERE round_id = ? AND LOWER(TRIM(unit)) = LOWER(TRIM(?)) 
                    AND LOWER(TRIM(section_name)) = LOWER(TRIM(?))
                ''', (st.session_state.current_round_id, unit, section))
                
                section_result = c.fetchone()
                
                if section_result:
                    section_id = section_result[0]
                    
                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Found existing section ID: {section_id}")
                    
                    # Instead of deleting all items, we'll update existing ones and add new ones
                    # First, get all existing items for this section
                    c.execute('SELECT id, description FROM round_items WHERE section_id = ?', (section_id,))
                    existing_items = {desc.strip().lower(): id for id, desc in c.fetchall()}
                    
                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Found {len(existing_items)} existing items")
                    
                    # Go through the items we want to save
                    for item in data["items"]:
                        item_desc = item["description"].strip()
                        item_desc_lower = item_desc.lower()
                        
                        if item_desc_lower in existing_items:
                            # Update existing item
                            item_id = existing_items[item_desc_lower]
                            c.execute('''
                                UPDATE round_items 
                                SET description = ?, value = ?, output = ?, mode = ?
                                WHERE id = ?
                            ''', (item_desc, item.get("value", "").strip(), 
                                 item.get("output", "").strip(), 
                                 item.get("mode", "").strip(),
                                 item_id))
                            
                            if st.session_state.get('debug_mode', False):
                                st.write(f"Debug - Updated item: {item_desc}")
                            
                            # Remove from existing_items so we know what's left
                            existing_items.pop(item_desc_lower)
                        else:
                            # Insert new item
                            c.execute('''
                                INSERT INTO round_items 
                                (section_id, description, value, output, mode)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (section_id, item_desc, item.get("value", "").strip(), 
                                 item.get("output", "").strip(),
                                 item.get("mode", "").strip()))
                            
                            if st.session_state.get('debug_mode', False):
                                st.write(f"Debug - Inserted new item: {item_desc}")
                else:
                    # Create a new section
                    c.execute('''
                        INSERT INTO sections (round_id, unit, section_name)
                        VALUES (?, ?, ?)
                    ''', (st.session_state.current_round_id, unit.strip(), section.strip()))
                    
                    section_id = c.lastrowid
                    
                    if st.session_state.get('debug_mode', False):
                        st.write(f"Debug - Created new section with ID: {section_id}")
                    
                    # Insert all items as new
                    for item in data["items"]:
                        c.execute('''
                            INSERT INTO round_items 
                            (section_id, description, value, output, mode)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (section_id, item["description"].strip(), 
                             item.get("value", "").strip(), 
                             item.get("output", "").strip(),
                             item.get("mode", "").strip()))
                
                # Commit changes
                conn.commit()
                return True
                
            except Exception as e:
                conn.rollback()
                st.error(f"Error saving section: {str(e)}")
                
                if st.session_state.get('debug_mode', False):
                    st.write("Debug - Exception details:")
                    st.write(traceback.format_exc())
                
                return False
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Connection error:")
            st.write(traceback.format_exc())
        
        return False

def load_last_round_data() -> Dict[str, Any]:
    """
    Load the most recent round data for all sections.
    
    This function retrieves all sections and the most recent values
    for items in those sections to populate the initial application state.
    
    Returns:
        Dict[str, Any]: Round data in the application's expected structure
    """
    if 'rounds_data_needs_refresh' in st.session_state and st.session_state.rounds_data_needs_refresh:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Forcing refresh of rounds data from database")
        # Reset the flag after we've acknowledged it
        st.session_state.rounds_data_needs_refresh = False
    
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # First, get all existing sections
            c.execute('''
                SELECT DISTINCT r.round_type, s.unit, s.section_name
                FROM sections s
                JOIN rounds r ON s.round_id = r.id
                ORDER BY s.unit, s.section_name
            ''')
            
            section_results = c.fetchall()
            
            # Modified query to correctly fetch the most recent round items
            c.execute('''
                SELECT r.id, r.round_type, r.timestamp,
                       s.unit, s.section_name,
                       ri.description, ri.value, ri.output, ri.mode
                FROM rounds r
                JOIN sections s ON s.round_id = r.id
                LEFT JOIN round_items ri ON ri.section_id = s.id
                WHERE ri.description IS NOT NULL
                ORDER BY r.timestamp DESC
            ''')
            
            item_results = c.fetchall()
            
            # Initialize with default structure
            from operator_rounds.utils.state import initialize_round_data_structure
            round_data = initialize_round_data_structure()
            
            # First, ensure all sections exist
            for row in section_results:
                round_type, unit, section = row
                
                # Ensure the unit exists in the structure
                if unit not in round_data[round_type]["units"]:
                    round_data[round_type]["units"][unit] = {"sections": {}}
                
                # Create section if it doesn't exist
                if section not in round_data[round_type]["units"][unit]["sections"]:
                    round_data[round_type]["units"][unit]["sections"][section] = {"items": []}
            
            # Process items - we need to track which items we've already added
            added_items = set()
            
            # Then process the most recent items
            for row in item_results:
                round_id, round_type, timestamp, unit, section, desc, value, output, mode = row
                
                # Add item if it exists and description is not None
                if desc:
                    # Create a unique identifier for this item
                    item_key = f"{unit}_{section}_{desc}"
                    
                    # Only add if we haven't seen this item before
                    if item_key not in added_items:
                        # The section should already exist from previous step
                        round_data[round_type]["units"][unit]["sections"][section]["items"].append({
                            "description": desc,
                            "value": value,
                            "output": output,
                            "mode": mode
                        })
                        
                        # Mark this item as added
                        added_items.add(item_key)
            
            return round_data
            
    except sqlite3.Error as e:
        st.error(f"Error loading round data: {str(e)}")
        from operator_rounds.utils.state import initialize_round_data_structure
        return initialize_round_data_structure()

def get_round_by_id(round_id: int) -> Optional[Round]:
    """
    Retrieve a complete round by its ID.
    
    Args:
        round_id (int): The ID of the round to retrieve
        
    Returns:
        Optional[Round]: The round object if found, None otherwise
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get round information
            c.execute('''
                SELECT r.round_type, r.shift, r.timestamp, o.id, o.name
                FROM rounds r
                JOIN operators o ON r.operator_id = o.id
                WHERE r.id = ?
            ''', (round_id,))
            
            round_result = c.fetchone()
            
            if not round_result:
                return None
                
            round_type, shift, timestamp, operator_id, operator_name = round_result
            
            # Create the operator object
            operator = Operator(
                id=operator_id,
                name=operator_name
            )
            
            # Create the round object
            round_obj = Round(
                id=round_id,
                round_type=round_type,
                operator=operator,
                shift=shift,
                timestamp=timestamp
            )
            
            # Get all sections for this round
            c.execute('''
                SELECT id, unit, section_name, completed
                FROM sections
                WHERE round_id = ?
                ORDER BY unit, section_name
            ''', (round_id,))
            
            section_results = c.fetchall()
            
            for section_row in section_results:
                section_id, unit, section_name, completed = section_row
                
                # Create the section object
                section = Section(
                    id=section_id,
                    unit=unit,
                    section_name=section_name,
                    completed=bool(completed),
                    round_id=round_id
                )
                
                # Get all items for this section
                c.execute('''
                    SELECT id, description, value, output, mode, timestamp
                    FROM round_items
                    WHERE section_id = ?
                    ORDER BY id
                ''', (section_id,))
                
                item_results = c.fetchall()
                
                for item_row in item_results:
                    item_id, description, value, output, mode, item_timestamp = item_row
                    
                    # Create the item object
                    item = RoundItem(
                        id=item_id,
                        description=description,
                        value=value,
                        output=output,
                        mode=mode,
                        section_id=section_id,
                        timestamp=item_timestamp
                    )
                    
                    # Add the item to the section
                    section.items.append(item)
                
                # Add the section to the round
                round_obj.sections.append(section)
            
            return round_obj
            
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Error in get_round_by_id: {str(e)}")
            st.write(traceback.format_exc())
        return None

def get_operator_rounds(operator_name: str) -> List[Dict[str, Any]]:
    """
    Get all rounds completed by a specific operator.
    
    Args:
        operator_name (str): The name of the operator
        
    Returns:
        List[Dict[str, Any]]: A list of round summary dictionaries
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT r.id, r.round_type, r.shift, r.timestamp, 
                       (SELECT COUNT(*) FROM sections WHERE round_id = r.id) as section_count
                FROM rounds r
                JOIN operators o ON r.operator_id = o.id
                WHERE o.name = ?
                ORDER BY r.timestamp DESC
            ''', (operator_name,))
            
            round_results = c.fetchall()
            
            rounds = []
            for row in round_results:
                round_id, round_type, shift, timestamp, section_count = row
                
                rounds.append({
                    "id": round_id,
                    "round_type": round_type,
                    "shift": shift,
                    "timestamp": timestamp,
                    "section_count": section_count
                })
            
            return rounds
            
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Error in get_operator_rounds: {str(e)}")
            st.write(traceback.format_exc())
        return []

def get_round_summary_for_period(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Get a summary of rounds completed during a specific period.
    
    Args:
        start_date (str): The start date in ISO format (YYYY-MM-DD)
        end_date (str): The end date in ISO format (YYYY-MM-DD)
        
    Returns:
        pd.DataFrame: A dataframe containing round summary statistics
    """
    try:
        with get_db_connection() as conn:
            # Query to get round counts by operator and type
            query = """
                SELECT 
                    o.name as operator_name,
                    r.round_type,
                    COUNT(r.id) as round_count,
                    MIN(r.timestamp) as first_round,
                    MAX(r.timestamp) as last_round
                FROM rounds r
                JOIN operators o ON r.operator_id = o.id
                WHERE DATE(r.timestamp) BETWEEN ? AND ?
                GROUP BY o.name, r.round_type
                ORDER BY o.name, r.round_type
            """
            
            # Execute the query
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            
            return df
            
    except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Error in get_round_summary_for_period: {str(e)}")
            st.write(traceback.format_exc())
        
        # Return an empty DataFrame with the expected columns
        return pd.DataFrame(columns=[
            "operator_name", "round_type", "round_count", 
            "first_round", "last_round"
        ])

def toggle_expand_all(unit_name: str, sections: List[str]) -> None:
    """
    Helper function to handle expand/collapse all functionality for a unit's sections.
    
    Args:
        unit_name (str): The name of the unit
        sections (List[str]): List of section names in the unit
    """
    unit_sections = {f"{unit_name}_{section}" for section in sections}
    
    if not hasattr(st.session_state, 'expanded_sections'):
        st.session_state.expanded_sections = set()
    
    # If all sections are expanded, collapse all. Otherwise, expand all
    if unit_sections.issubset(st.session_state.expanded_sections):
        st.session_state.expanded_sections -= unit_sections
    else:
        st.session_state.expanded_sections.update(unit_sections)

def get_all_operators() -> List[Operator]:
    """
    Get all operators in the system.
    
    Returns:
        List[Operator]: A list of all operators
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT id, name, created_at
                FROM operators
                ORDER BY name
            ''')
            
            operator_results = c.fetchall()
            
            operators = []
            for row in operator_results:
                operator_id, name, created_at = row
                
                operators.append(Operator(
                    id=operator_id,
                    name=name,
                    created_at=created_at
                ))
            
            return operators
            
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Error in get_all_operators: {str(e)}")
            st.write(traceback.format_exc())
        return []

def delete_round(round_id: int) -> bool:
    """
    Delete a round and all its associated sections and items.
    
    Args:
        round_id (int): The ID of the round to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            c = conn.cursor()
            
            # Get all sections for this round
            c.execute('SELECT id FROM sections WHERE round_id = ?', (round_id,))
            section_ids = [row[0] for row in c.fetchall()]
            
            # Delete all items for each section
            for section_id in section_ids:
                c.execute('DELETE FROM round_items WHERE section_id = ?', (section_id,))
            
            # Delete all sections
            c.execute('DELETE FROM sections WHERE round_id = ?', (round_id,))
            
            # Delete the round
            c.execute('DELETE FROM rounds WHERE id = ?', (round_id,))
            
            # Commit changes
            conn.commit()
            return True
            
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Error in delete_round: {str(e)}")
            st.write(traceback.format_exc())
        return False