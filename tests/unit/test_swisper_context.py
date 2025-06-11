#!/usr/bin/env python3
"""Unit tests for SwisperContext functionality"""

import sys
import os
import pytest
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swisper_core import SwisperContext
from contract_engine.contract_engine import ContractStateMachine

class TestSwisperContext:
    def test_context_initialization(self):
        """Test SwisperContext initialization with defaults"""
        context = SwisperContext(session_id="test_session")
        
        assert context.session_id == "test_session"
        assert context.contract_type == "purchase_item"
        assert context.current_state == "start"
        assert context.step_log == []
        assert context.search_results == []
        assert context.preferences == []
        assert context.constraints == {}
        assert context.contract_status == "active"
        assert context.confirmation_pending is False
        assert context.is_cancelled is False
        
    def test_context_state_transitions(self):
        """Test state transition logging"""
        context = SwisperContext(session_id="test_session")
        
        context.update_state("search")
        assert context.current_state == "search"
        assert "start -> search" in context.step_log
        assert context.updated_at is not None
        
        context.update_state("rank_and_select")
        assert context.current_state == "rank_and_select"
        assert "search -> rank_and_select" in context.step_log
        assert len(context.step_log) == 2
        
    def test_context_serialization(self):
        """Test context to_dict and from_dict"""
        original = SwisperContext(
            session_id="test_session",
            product_query="RTX 4090",
            preferences=["low noise", "under 1000 CHF"]
        )
        
        data = original.to_dict()
        assert isinstance(data, dict)
        assert data["session_id"] == "test_session"
        assert data["product_query"] == "RTX 4090"
        assert data["preferences"] == ["low noise", "under 1000 CHF"]
        
        restored = SwisperContext.from_dict(data)
        assert restored.session_id == original.session_id
        assert restored.product_query == original.product_query
        assert restored.preferences == original.preferences

class TestContractStateMachineWithContext:
    def test_fsm_context_initialization(self):
        """Test FSM initializes with SwisperContext"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        assert hasattr(fsm, 'context')
        assert isinstance(fsm.context, SwisperContext)
        assert fsm.context.current_state == "start"
        assert fsm.context.contract_template_path == "contract_templates/purchase_item.yaml"
        
    def test_fsm_context_parameter_filling(self):
        """Test context updates when parameters are filled"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        fsm.fill_parameters({
            "session_id": "test_123",
            "product": "GPU RTX 4090",
            "preferences": ["gaming", "quiet"]
        })
        
        assert fsm.context.session_id == "test_123"
        assert fsm.context.product_query == "GPU RTX 4090"
        assert fsm.context.preferences == ["gaming", "quiet"]
        assert fsm.context.updated_at is not None

if __name__ == "__main__":
    pytest.main([__file__])
