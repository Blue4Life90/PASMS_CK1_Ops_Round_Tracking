"""
View rounds UI components for Operator Rounds Tracking.

This module provides the interface for viewing completed rounds,
including filtering, sorting, and exporting round data.
"""
import streamlit as st
import pandas as pd
import sqlite3
import traceback
from datetime import datetime, timedelta
from operator_rounds.database.connection import get_db_connection
from operator_rounds.utils.export import export_round_to_csv

def view_saved_rounds():
    """
    Render the interface for viewing and interacting with saved rounds.
    
    This function displays a filterable list of completed rounds with
    expandable details and export options.
    """
    st.header("Completed Rounds History")
    
    # Add filtering options at the top
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Date range filter
        date_filter = st.selectbox(
            "Date Range",
            options=["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom"],
            index=0
        )
        
        if date_filter == "Custom":
            # Show custom date range picker if "Custom" is selected
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=7)
            )
            end_date = st.date_input(
                "End Date",
                value=datetime.now()
            )
            
            # Validate date range
            if start_date > end_date:
                st.error("Start date must be before end date")
    
    with col2:
        # Round type filter
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT DISTINCT round_type FROM rounds ORDER BY round_type")
                round_types = [r[0] for r in c.fetchall()]
                
                # Add "All" option at the beginning
                round_types = ["All Round Types"] + round_types
                
                selected_round_type = st.selectbox(
                    "Round Type",
                    options=round_types,
                    index=0
                )
        except sqlite3.Error as e:
            st.error(f"Error loading round types: {str(e)}")
            round_types = ["All Round Types"]
            selected_round_type = "All Round Types"
    
    with col3:
        # Operator filter
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT DISTINCT o.name 
                    FROM operators o
                    JOIN rounds r ON o.id = r.operator_id
                    ORDER BY o.name
                """)
                operators = [r[0] for r in c.fetchall()]
                
                # Add "All" option at the beginning
                operators = ["All Operators"] + operators
                
                selected_operator = st.selectbox(
                    "Operator",
                    options=operators,
                    index=0
                )
        except sqlite3.Error as e:
            st.error(f"Error loading operators: {str(e)}")
            operators = ["All Operators"]
            selected_operator = "All Operators"
    
    # Build the SQL query based on filters
    query, params = build_rounds_query(
        date_filter, 
        selected_round_type, 
        selected_operator,
        start_date if date_filter == "Custom" else None,
        end_date if date_filter == "Custom" else None
    )
    
    # Export all data option
    if st.checkbox("Include metadata in exports", value=True):
        st.session_state.include_metadata = True
    else:
        st.session_state.include_metadata = False
    
    # Execute query and display results
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(query, params)
            results = c.fetchall()
            
            if not results:
                st.info("No rounds found matching the selected filters.")
                return
            
            # Process results into a more usable structure
            rounds_data = process_rounds_data(results)
            
            # Display the rounds
            display_rounds(rounds_data)
                
    except sqlite3.Error as e:
        st.error(f"Error retrieving saved rounds: {str(e)}")
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Database error: {str(e)}")
            st.write(traceback.format_exc())

def build_rounds_query(date_filter, round_type, operator, start_date=None, end_date=None):
    """
    Build the SQL query for retrieving rounds based on filter criteria.
    
    Args:
        date_filter (str): The selected date filter
        round_type (str): The selected round type
        operator (str): The selected operator
        start_date (datetime.date, optional): Start date for custom range
        end_date (datetime.date, optional): End date for custom range
        
    Returns:
        tuple: (query_string, parameters)
    """
    base_query = """
        SELECT 
            r.id,
            r.round_type,
            o.name as operator_name,
            r.shift,
            r.timestamp,
            s.unit,
            s.section_name,
            ri.description,
            ri.value,
            ri.output,
            ri.mode
        FROM rounds r
        JOIN operators o ON r.operator_id = o.id
        JOIN sections s ON s.round_id = r.id
        JOIN round_items ri ON ri.section_id = s.id
    """
    
    where_clauses = []
    params = []
    
    # Date filter
    if date_filter == "Today":
        where_clauses.append("DATE(r.timestamp) = DATE('now', 'localtime')")
    elif date_filter == "Last 7 Days":
        where_clauses.append("r.timestamp >= DATE('now', 'localtime', '-7 days')")
    elif date_filter == "Last 30 Days":
        where_clauses.append("r.timestamp >= DATE('now', 'localtime', '-30 days')")
    elif date_filter == "Custom" and start_date and end_date:
        where_clauses.append("DATE(r.timestamp) BETWEEN ? AND ?")
        # Add one day to end_date to make it inclusive
        end_date_adjusted = end_date + timedelta(days=1)
        params.extend([start_date.strftime("%Y-%m-%d"), end_date_adjusted.strftime("%Y-%m-%d")])
    
    # Round type filter
    if round_type != "All Round Types":
        where_clauses.append("r.round_type = ?")
        params.append(round_type)
    
    # Operator filter
    if operator != "All Operators":
        where_clauses.append("o.name = ?")
        params.append(operator)
    
    # Combine where clauses
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    # Add ordering
    base_query += " ORDER BY r.timestamp DESC, s.unit, s.section_name"
    
    return base_query, params

def process_rounds_data(results):
    """
    Process the raw query results into a structured format for display.
    
    Args:
        results (list): The raw query results
        
    Returns:
        dict: A nested dictionary of round data organized by round ID
    """
    rounds_data = {}
    
    for row in results:
        round_id, round_type, operator, shift, timestamp, unit, section, desc, value, output, mode = row
        
        # Initialize round if not exists
        if round_id not in rounds_data:
            rounds_data[round_id] = {
                "round_id": round_id,
                "round_type": round_type,
                "operator": operator,
                "shift": shift,
                "timestamp": timestamp,
                "units": {}
            }
        
        # Initialize unit if not exists
        if unit not in rounds_data[round_id]["units"]:
            rounds_data[round_id]["units"][unit] = {}
        
        # Initialize section if not exists
        if section not in rounds_data[round_id]["units"][unit]:
            rounds_data[round_id]["units"][unit][section] = []
        
        # Add item to section
        rounds_data[round_id]["units"][unit][section].append({
            "description": desc,
            "value": value,
            "output": output,
            "mode": mode
        })
    
    return rounds_data

def display_rounds(rounds_data):
    """
    Display the processed rounds data in an expandable format.
    
    Args:
        rounds_data (dict): The processed rounds data structure
    """
    # Sort rounds by timestamp (most recent first)
    sorted_rounds = sorted(
        rounds_data.values(), 
        key=lambda x: x["timestamp"], 
        reverse=True
    )
    
    # Display each round
    for round_data in sorted_rounds:
        round_id = round_data["round_id"]
        timestamp = round_data["timestamp"]
        operator = round_data["operator"]
        
        # Round header with export option
        col1, col2 = st.columns([5, 1])
        
        with col1:
            expander_label = f"Round {round_id} - {timestamp} by {operator}"
            expander = st.expander(expander_label, expanded=False)
        
        with col2:
            # Create a download button for this specific round
            csv_data, filename = export_round_to_csv(round_id)
            if csv_data:
                st.download_button(
                    label="Export CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    key=f"download_{round_id}"
                )
            else:
                st.error("Export error")
        
        # Display round details in the expander
        with expander:
            st.write(f"**Round Type:** {round_data['round_type']}")
            st.write(f"**Shift:** {round_data['shift']}")
            
            # Create tabular data for this round
            table_data = []

            for unit, sections in round_data["units"].items():
                for section, items in sections.items():
                    for item in items:
                        table_data.append({
                            "Unit": unit,
                            "Section": section,
                            "Item Description": item["description"],
                            "Value": item["value"],
                            "Output": item["output"],
                            "Mode": item["mode"]
                        })
            
            # Store table data in session state for potential export
            st.session_state[f"table_data_{round_id}"] = table_data
            
            # Display as dataframe
            if table_data:
                df = pd.DataFrame(table_data)
                
                # Make sure the Mode column exists
                if 'Mode' not in df.columns:
                    df['Mode'] = ""
                
                # Define a row styling function
                def style_row(row):
                    if row['Mode'] == 'Manual':
                        return ['background-color: rgba(255, 200, 87, 0.5); font-weight: bold;'] * len(row)
                    elif row['Mode'] == 'Cascade':
                        return ['background-color: rgba(74, 222, 128, 0.5); font-weight: bold; color: white;'] * len(row)
                    elif row['Mode'] == 'Auto-Init':
                        return ['background-color: rgba(167, 139, 250, 0.5); font-weight: bold; color: white;'] * len(row)
                    elif row['Mode'] == 'B-Cascade':
                        return ['background-color: rgba(6, 214, 160, 0.5); font-weight: bold; color: white;'] * len(row)
                    return [''] * len(row)
                
                # Apply styling row by row
                styled_df = df.style.apply(style_row, axis=1)
                
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("No items found for this round.")

def render_round_details(round_id):
    """
    Render a detailed view of a specific round.
    
    This function provides a more in-depth view of a single round,
    including all items and values.
    
    Args:
        round_id (int): The ID of the round to display
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get round information
            c.execute("""
                SELECT r.round_type, o.name, r.shift, r.timestamp
                FROM rounds r
                JOIN operators o ON r.operator_id = o.id
                WHERE r.id = ?
            """, (round_id,))
            
            round_info = c.fetchone()
            
            if not round_info:
                st.error(f"Round {round_id} not found")
                return
                
            round_type, operator_name, shift, timestamp = round_info
            
            # Display round header
            st.header(f"Round {round_id} Details")
            st.write(f"**Type:** {round_type}")
            st.write(f"**Operator:** {operator_name}")
            st.write(f"**Shift:** {shift}")
            st.write(f"**Timestamp:** {timestamp}")
            
            # Get all items for this round
            c.execute("""
                SELECT s.unit, s.section_name, ri.description, ri.value, ri.output, ri.mode
                FROM sections s
                JOIN round_items ri ON ri.section_id = s.id
                WHERE s.round_id = ?
                ORDER BY s.unit, s.section_name, ri.id
            """, (round_id,))
            
            items = c.fetchall()
            
            if not items:
                st.info("No items found for this round.")
                return
            
            # Process items by unit and section
            units = {}
            for item in items:
                unit, section, desc, value, output, mode = item
                
                if unit not in units:
                    units[unit] = {}
                
                if section not in units[unit]:
                    units[unit][section] = []
                
                units[unit][section].append({
                    "description": desc,
                    "value": value,
                    "output": output,
                    "mode": mode
                })
            
            # Display units in tabs
            unit_tabs = st.tabs(list(units.keys()))
            
            for unit_tab, unit_name in zip(unit_tabs, units.keys()):
                with unit_tab:
                    # Display sections in expandable sections
                    for section_name, section_items in units[unit_name].items():
                        with st.expander(section_name, expanded=True):
                            # Create dataframe for items
                            df = pd.DataFrame(section_items)

                            # Create dataframe for items
                            df = pd.DataFrame(section_items)

                            # Make sure the mode column exists
                            if 'mode' not in df.columns:
                                df['mode'] = ""

                            # Define a row styling function
                            def style_row(row):
                                if row['mode'] == 'Manual':
                                    return ['background-color: rgba(255, 200, 87, 0.5); font-weight: bold;'] * len(row)
                                elif row['mode'] == 'Cascade':
                                    return ['background-color: rgba(74, 222, 128, 0.5); font-weight: bold; color: white;'] * len(row)
                                elif row['mode'] == 'Auto-Init':
                                    return ['background-color: rgba(167, 139, 250, 0.5); font-weight: bold; color: white;'] * len(row)
                                elif row['mode'] == 'B-Cascade':
                                    return ['background-color: rgba(6, 214, 160, 0.5); font-weight: bold; color: white;'] * len(row)
                                return [''] * len(row)

                            # Apply styling row by row
                            styled_df = df.style.apply(style_row, axis=1)

                            st.dataframe(styled_df, use_container_width=True)
            
            # Export option
            csv_data, filename = export_round_to_csv(round_id)
            if csv_data:
                st.download_button(
                    label="Export as CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv"
                )
            
    except sqlite3.Error as e:
        st.error(f"Error retrieving round details: {str(e)}")
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Database error: {str(e)}")
            st.write(traceback.format_exc())

