"""
Database components for Operator Rounds Tracking.

This package handles database connections, queries, and data models
for the operator rounds tracking application.
"""

# Import key components to expose at the package level
from operator_rounds.database.connection import get_db_connection
from operator_rounds.database.schema import init_db
from operator_rounds.database.models import Round, Section, RoundItem, Operator
from operator_rounds.database.queries import (
    start_round,
    save_round_section,
    load_last_round_data,
    get_round_by_id,
    get_operator_rounds,
    get_round_summary_for_period,
    get_all_operators,
    delete_round
)

# Define what gets imported with "from operator_rounds.database import *"
__all__ = [
    'get_db_connection', 'init_db',
    'Round', 'Section', 'RoundItem', 'Operator',
    'start_round', 'save_round_section', 'load_last_round_data',
    'get_round_by_id', 'get_operator_rounds', 'get_round_summary_for_period',
    'get_all_operators', 'delete_round'
]