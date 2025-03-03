"""
User interface components for Operator Rounds Tracking.

This package provides the Streamlit UI components for the operator rounds
tracking application, including forms, views, and interactive elements.
"""

# Import key UI components to expose at the package level
from operator_rounds.ui.sidebar import render_sidebar
from operator_rounds.ui.section_editor import render_section_editor, render_section_content
from operator_rounds.ui.round_completion import render_round_completion
from operator_rounds.ui.view_rounds import view_saved_rounds, render_round_details
from operator_rounds.ui.forms import (
    create_section_form,
    create_item_form,
    create_multi_item_form
)

# Define what gets imported with "from operator_rounds.ui import *"
__all__ = [
    'render_sidebar',
    'render_section_editor',
    'render_section_content',
    'render_round_completion',
    'view_saved_rounds',
    'render_round_details',
    'create_section_form',
    'create_item_form',
    'create_multi_item_form'
]