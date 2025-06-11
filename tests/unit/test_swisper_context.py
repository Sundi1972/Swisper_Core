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



if __name__ == "__main__":
    pytest.main([__file__])
