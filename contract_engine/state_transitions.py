"""
State transition classes for FSM refactoring.

This module defines the StateTransition class and related structures
for clean state management in the contract engine FSM.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class ContractState(Enum):
    """Enumeration of all possible contract states."""
    START = "start"
    EXTRACT_ENTITIES = "extract_entities"
    SEARCH_PRODUCTS = "search_products"
    REFINE_CONSTRAINTS = "refine_constraints"
    COLLECT_PREFERENCES = "collect_preferences"
    MATCH_PREFERENCES = "match_preferences"
    PRESENT_OPTIONS = "present_options"
    CONFIRM_PURCHASE = "confirm_purchase"
    COMPLETE_ORDER = "complete_order"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    
    SEARCH = "search"
    FILTER = "filter"
    RANK = "rank"
    RECOMMEND = "recommend"
    CONFIRM = "confirm"


@dataclass
class StateTransition:
    """
    Represents a state transition with all necessary information.
    
    This class encapsulates the result of a state handler function,
    including the next state, user message, and any context updates.
    """
    next_state: Optional[ContractState]
    user_message: Optional[str] = None
    ask_user: Optional[str] = None
    status: str = "continue"
    context_updates: Optional[Dict[str, Any]] = None
    contract_updates: Optional[Dict[str, Any]] = None
    tools_used: Optional[List[str]] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate the state transition after initialization."""
        if self.context_updates is None:
            self.context_updates = {}
        if self.contract_updates is None:
            self.contract_updates = {}
        if self.tools_used is None:
            self.tools_used = []
    
    def is_terminal(self) -> bool:
        """Check if this transition leads to a terminal state."""
        terminal_states = {
            ContractState.COMPLETED,
            ContractState.CANCELLED,
            ContractState.FAILED
        }
        return self.next_state in terminal_states
    
    def is_error(self) -> bool:
        """Check if this transition represents an error state."""
        return self.status == "failed" or self.next_state == ContractState.FAILED
    
    def requires_user_input(self) -> bool:
        """Check if this transition requires user input."""
        return self.ask_user is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the state transition to a dictionary for API responses."""
        result = {
            "status": self.status,
            "next_state": self.next_state.value if self.next_state else None,
        }
        
        if self.user_message:
            result["message"] = self.user_message
        
        if self.ask_user:
            result["ask_user"] = self.ask_user
        
        if self.error_message:
            result["error"] = self.error_message
        
        if self.tools_used:
            result["tools_used"] = self.tools_used
        
        return result


@dataclass
class StateHandlerResult:
    """
    Result from a state handler function.
    
    This is used internally by state handlers to return their results
    before being converted to a StateTransition.
    """
    success: bool
    next_state: Optional[ContractState] = None
    user_message: Optional[str] = None
    ask_user: Optional[str] = None
    context_updates: Optional[Dict[str, Any]] = None
    contract_updates: Optional[Dict[str, Any]] = None
    tools_used: Optional[List[str]] = None
    error_message: Optional[str] = None
    
    def to_transition(self) -> StateTransition:
        """Convert to a StateTransition object."""
        status = "continue" if self.success else "failed"
        
        return StateTransition(
            next_state=self.next_state,
            user_message=self.user_message,
            ask_user=self.ask_user,
            status=status,
            context_updates=self.context_updates or {},
            contract_updates=self.contract_updates or {},
            tools_used=self.tools_used or [],
            error_message=self.error_message
        )


def create_success_transition(
    next_state: ContractState,
    user_message: Optional[str] = None,
    context_updates: Optional[Dict[str, Any]] = None,
    tools_used: Optional[List[str]] = None
) -> StateTransition:
    """Helper function to create a successful state transition."""
    return StateTransition(
        next_state=next_state,
        user_message=user_message,
        status="continue",
        context_updates=context_updates or {},
        tools_used=tools_used or []
    )


def create_error_transition(
    error_message: str,
    current_state: Optional[ContractState] = None
) -> StateTransition:
    """Helper function to create an error state transition."""
    return StateTransition(
        next_state=ContractState.FAILED,
        status="failed",
        error_message=error_message,
        user_message=f"An error occurred: {error_message}"
    )


def create_user_input_transition(
    ask_user: str,
    current_state: Optional[ContractState] = None
) -> StateTransition:
    """Helper function to create a transition that asks for user input."""
    return StateTransition(
        next_state=current_state,  # Stay in current state
        ask_user=ask_user,
        status="waiting_for_input"
    )


def create_completion_transition(
    user_message: str,
    context_updates: Optional[Dict[str, Any]] = None
) -> StateTransition:
    """Helper function to create a completion transition."""
    return StateTransition(
        next_state=ContractState.COMPLETED,
        user_message=user_message,
        status="completed",
        context_updates=context_updates or {}
    )
