"""
Common validation utilities for Swisper Core
"""
from typing import Dict, Any, List

def validate_context_dict(context_dict: Dict[str, Any]) -> bool:
    """Fast context dictionary integrity validation"""
    required_fields = ["session_id", "current_state"]
    return all(field in context_dict and context_dict[field] for field in required_fields)

def validate_fsm_state(fsm) -> bool:
    """Fast FSM state consistency validation"""
    if not fsm or not fsm.context:
        return False
    if not fsm.context.session_id or not fsm.context.current_state:
        return False
    return True

def validate_pipeline_result(result: Dict[str, Any]) -> bool:
    """Validate pipeline execution result structure"""
    if not isinstance(result, dict):
        return False
    
    required_fields = ["status"]
    return all(field in result for field in required_fields)

VALID_FSM_STATES = [
    "start", "search", "refine_constraints", "collect_preferences", 
    "match_preferences", "confirm_purchase", "completed", "cancelled", "failed"
]

def validate_state_transition(from_state: str, to_state: str) -> bool:
    """Validate FSM state transition is allowed"""
    if from_state not in VALID_FSM_STATES or to_state not in VALID_FSM_STATES:
        return False
    
    return True
