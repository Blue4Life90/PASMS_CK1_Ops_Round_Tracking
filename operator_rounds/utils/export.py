"""Export functionality for Operator Rounds Tracking."""
import pandas as pd
from datetime import datetime
import streamlit as st
import sqlite3
import traceback
from operator_rounds.database.connection import get_db_connection

def export_round_to_csv(round_id):
    """
    Export a specific round to a CSV file.
    
    Args:
        round_id (int): The ID of the round to export
        
    Returns:
        tuple: (csv_string, filename) - The CSV data as a string and the suggested filename
    """
    try:
        # First, ensure round_id is an integer
        try:
            round_id = int(round_id)
        except ValueError:
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - Invalid round ID format: {round_id}")
            return None, f"Invalid round ID: {round_id}"
        
        with get_db_connection() as conn:
            # Get round information with more flexible query
            c = conn.cursor()
            
            if st.session_state.get('debug_mode', False):
                st.write(f"Debug - Looking for round with ID: {round_id}")
                # Check if the round exists at all
                c.execute("SELECT COUNT(*) FROM rounds WHERE id = ?", (round_id,))
                count = c.fetchone()[0]
                st.write(f"Debug - Found {count} rounds with ID {round_id}")
            
            # First try to get the round directly
            c.execute('''
                SELECT r.round_type, o.name, r.shift, r.timestamp
                FROM rounds r
                JOIN operators o ON r.operator_id = o.id
                WHERE r.id = ?
            ''', (round_id,))
            
            round_info = c.fetchone()
            
            # If not found, try as a string (just in case)
            if not round_info:
                c.execute('''
                    SELECT r.round_type, o.name, r.shift, r.timestamp
                    FROM rounds r
                    JOIN operators o ON r.operator_id = o.id
                    WHERE r.id = ?
                ''', (str(round_id),))
                round_info = c.fetchone()
            
            # If still not found, try to look for any round data directly
            if not round_info:
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - Round {round_id} not found through joins. Trying direct table access.")
                
                # Try to get the round directly without joins
                c.execute("SELECT round_type, timestamp FROM rounds WHERE id = ?", (round_id,))
                basic_info = c.fetchone()
                
                if basic_info:
                    # We found the round but operator info might be missing
                    round_type, timestamp = basic_info
                    operator_name = "Unknown"  # Default if we can't find the operator
                    shift = "Unknown"  # Default if shift is missing
                    
                    # Try to get operator info
                    c.execute("SELECT operator_id, shift FROM rounds WHERE id = ?", (round_id,))
                    op_data = c.fetchone()
                    if op_data and op_data[0]:
                        operator_id, shift = op_data
                        c.execute("SELECT name FROM operators WHERE id = ?", (operator_id,))
                        op_name = c.fetchone()
                        if op_name:
                            operator_name = op_name[0]
                    
                    round_info = (round_type, operator_name, shift or "Unknown", timestamp)
            
            # If we still couldn't find any round info, as a last resort
            # let's try to get data directly from the sections and round_items
            if not round_info:
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - Round {round_id} not found in rounds table. Trying to extract from sections.")
                
                # Check if there are any sections with this round_id
                c.execute("SELECT COUNT(*) FROM sections WHERE round_id = ?", (round_id,))
                section_count = c.fetchone()[0]
                
                if section_count > 0:
                    # We have sections but no round info, create defaults
                    round_info = ("Unknown Round Type", "Unknown Operator", "Unknown Shift", 
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    # No data found at all
                    return None, f"Round {round_id} not found"
            
            # Now get the round items with more flexible query to ensure we get data
            c.execute('''
                SELECT s.unit, s.section_name, ri.description, ri.value, ri.output, ri.mode
                FROM sections s
                JOIN round_items ri ON ri.section_id = s.id
                WHERE s.round_id = ?
                ORDER BY s.unit, s.section_name, ri.id
            ''', (round_id,))
            
            items = c.fetchall()
            
            # If we found no items but the round exists, try to get at least the sections
            if not items and round_info:
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - No items found for round {round_id}. Checking sections only.")
                
                c.execute("SELECT unit, section_name FROM sections WHERE round_id = ?", (round_id,))
                sections = c.fetchall()
                
                if sections:
                    # We have sections but no items
                    items = [(s[0], s[1], "No items found", "", "") for s in sections]
            
            # If we literally have no data at all, use the table data directly
            if not items and hasattr(st, 'session_state') and f'table_data_{round_id}' in st.session_state:
                if st.session_state.get('debug_mode', False):
                    st.write(f"Debug - Using UI table data as fallback for export")
                
                # Use the data from the table shown in the UI
                items = []
                table_data = st.session_state[f'table_data_{round_id}']
                for row in table_data:
                    items.append((
                        row.get("Unit", ""),
                        row.get("Section", ""),
                        row.get("Item Description", ""),
                        row.get("Value", ""),
                        row.get("Output", ""),
                        row.get("Mode", "")
                    ))
                
                # Also create some basic round info if we don't have it
                if not round_info:
                    round_info = ("Round Data", "Unknown", "Unknown", 
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # If after all our efforts we still have no data, then truly nothing exists
            if not items:
                return None, f"No data found for round {round_id}"
                
            round_type, operator_name, shift, timestamp = round_info
            
            # Create a DataFrame
            df = pd.DataFrame(items, columns=["Unit", "Section", "Item Description", "Value", "Output", "Mode"])
            
            # Add metadata
            if st.session_state.get('include_metadata', True):
                # Add a header row with round information
                metadata_df = pd.DataFrame([
                    ["Round ID", round_id],
                    ["Round Type", round_type],
                    ["Operator", operator_name],
                    ["Shift", shift],
                    ["Timestamp", timestamp]
                ], columns=["Metadata", "Value"])
                
                # Combine metadata and data with a separator row
                separator_df = pd.DataFrame([["---", "---", "---", "---", "---", "---"]], columns=df.columns)
                header_df = pd.DataFrame([df.columns.tolist()], columns=df.columns)
                
                # Convert metadata to match main DataFrame structure
                expanded_metadata = pd.DataFrame([
                    [metadata_df.iloc[0, 1], "", "", "", "", ""],  # Round ID
                    [metadata_df.iloc[1, 1], "", "", "", "", ""],  # Round Type
                    [metadata_df.iloc[2, 1], "", "", "", "", ""],  # Operator
                    [metadata_df.iloc[3, 1], "", "", "", "", ""],  # Shift
                    [metadata_df.iloc[4, 1], "", "", "", "", ""]   # Timestamp
                ], columns=df.columns)
                
                metadata_headers = pd.DataFrame([
                    ["Round ID", "", "", "", "", ""],
                    ["Round Type", "", "", "", "", ""],
                    ["Operator", "", "", "", "", ""],
                    ["Shift", "", "", "", "", ""],
                    ["Timestamp", "", "", "", "", ""]
                ], columns=df.columns)
                
                # Create final DataFrame with metadata at the top
                final_df = pd.concat([
                    metadata_headers,
                    expanded_metadata,
                    separator_df,
                    df
                ], ignore_index=True)
            else:
                final_df = df
            
            # Generate a sensible filename
            try:
                date_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d")
            except:
                date_str = datetime.now().strftime("%Y%m%d")
                
            filename = f"Round_{round_id}_{date_str}.csv"
            
            # Convert to CSV
            csv_string = final_df.to_csv(index=False)
            
            return csv_string, filename
            
    except sqlite3.Error as e:
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug - Database error in export: {str(e)}")
        return None, f"Database error: {str(e)}"
        
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            st.write("Debug - Export error:")
            st.write(traceback.format_exc())
        return None, f"Export error: {str(e)}"