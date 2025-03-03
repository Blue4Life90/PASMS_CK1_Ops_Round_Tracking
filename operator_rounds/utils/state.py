"""Session state management for Operator Rounds Tracking."""
import streamlit as st
from datetime import datetime

def initialize_round_data_structure():
    """Initialize the basic structure for rounds data with improved data handling"""
    return {
        "Alky Console Round Sheet": {
            "units": {
                "017 Alky I": {"sections": {}},
                "010 Olefin Splitter": {"sections": {}},
                "122 Iso Octene": {"sections": {}},
                "067 Hydrofiner": {"sections": {}},
                "040 LER II": {"sections": {}}
            }
        },
        "FCC Console Round Sheet": {
            "units": {}
        }
    }

def init_session_state():
    """Initialize session state variables with better organization"""
    if 'initialized' not in st.session_state:
        # Add a debug mode flag (default to False for production)
        st.session_state.debug_mode = False
        # Add this right after setting the debug mode
        if st.session_state.get('debug_mode', False):
            st.write("Debug mode is ENABLED")
            st.write(f"Current timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        st.session_state.initialized = True
        st.session_state.rounds_data = initialize_round_data_structure()
        
        # Add the refresh flag during initialization
        st.session_state.rounds_data_needs_refresh = False

        # Operator information
        st.session_state.operator_info_set = False
        st.session_state.operator_name = ""
        st.session_state.shift = "Days"
        
        # Round tracking
        st.session_state.current_round = None
        st.session_state.current_round_id = None
        st.session_state.completing_round = False
        st.session_state.pending_sections = {}
        
        # Unit and section tracking
        st.session_state.unit_state = {
            'sections': {},
            'expanded_sections': set()
        }
        
        # UI state
        st.session_state.adding_item = None
        st.session_state.editing_item = None
        st.session_state.confirm_delete = None
        st.session_state.expanded_sections = set()
        st.session_state.viewing_rounds = False
        st.session_state.unit_sections = {}
        
        # Load last round data
        from operator_rounds.database.queries import load_last_round_data
        last_round_data = load_last_round_data()
        if last_round_data:
            st.session_state.rounds_data.update(last_round_data)
