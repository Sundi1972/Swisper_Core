"""
Test suite for FSM state handler methods.

Tests individual state handlers and state transitions.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.state_transitions import ContractState, StateTransition


class TestFSMStateHandlers:
    def test_handle_start_state_with_product(self):
        """Test start state handler when product is set"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        
        transition = fsm.handle_start_state()
        
        assert transition.next_state == ContractState.SEARCH
        assert not transition.requires_user_input()
    
    def test_handle_start_state_without_product(self):
        """Test start state handler when product is not set"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        
        transition = fsm.handle_start_state()
        
        assert transition.requires_user_input()
        assert "What product are you looking for?" in transition.ask_user
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_handle_search_state_success(self, mock_run_search):
        """Test search state handler with successful search"""
        mock_run_search.return_value = {
            "status": "ok",
            "items": [{"name": "Test Product", "price": "100 CHF"}],
            "attributes": ["brand", "price"]
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        
        import asyncio
        transition = asyncio.run(fsm.handle_search_state())
        
        assert transition.next_state == ContractState.PRESENT_OPTIONS
        assert not transition.requires_user_input()
        assert "product_search_pipeline" in transition.tools_used
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_handle_search_state_no_results(self, mock_run_search):
        """Test search state handler with no search results"""
        mock_run_search.return_value = {
            "status": "ok",
            "items": [],
            "attributes": []
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "nonexistent product", "session_id": "test"})
        
        import asyncio
        transition = asyncio.run(fsm.handle_search_state())
        
        assert transition.requires_user_input()
        assert "couldn't find any products" in transition.ask_user.lower()
    
    def test_handle_search_state_no_product_query(self):
        """Test search state handler when product query is empty"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        
        import asyncio
        transition = asyncio.run(fsm.handle_search_state())
        
        assert transition.is_error()
        assert "No product specified" in transition.error_message
    
    def test_handle_completed_state(self):
        """Test completed state handler"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        
        transition = fsm.handle_completed_state()
        
        assert transition.next_state == ContractState.COMPLETED
        assert transition.status == "completed"
        assert transition.is_terminal()
    
    def test_handle_cancelled_state(self):
        """Test cancelled state handler"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        
        transition = fsm.handle_cancelled_state()
        
        assert transition.next_state == ContractState.CANCELLED
        assert transition.status == "cancelled"
        assert transition.is_terminal()
    
    def test_handle_error_state(self):
        """Test error state handler"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        
        transition = fsm.handle_error_state()
        
        assert transition.next_state == ContractState.FAILED
        assert transition.status == "failed"
        assert transition.is_terminal()
    
    def test_process_state_transition_updates_context(self):
        """Test that _process_state_transition updates context correctly"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test", "product": "test product"})
        
        transition = StateTransition(
            next_state=ContractState.SEARCH,
            context_updates={"test_field": "test_value"},
            tools_used=["test_tool"],
            ask_user="Please provide input",
            status="waiting_for_input"
        )
        
        result = fsm._process_state_transition(transition)
        
        assert fsm.context.current_state == "search"
        assert "test_tool" in fsm.context.tools_used
        assert result["status"] == "waiting_for_input"
    
    def test_get_session_id(self):
        """Test _get_session_id helper method"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test_session_123"})
        
        session_id = fsm._get_session_id()
        
        assert session_id == "test_session_123"
    
    def test_get_session_id_default(self):
        """Test _get_session_id with no session ID set"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        session_id = fsm._get_session_id()
        
        assert session_id == "default_fsm_session"
    
    def test_state_handler_mapping(self):
        """Test that all expected states have handlers"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        expected_states = [
            "start", "search", "refine_constraints", "ask_clarification",
            "wait_for_preferences", "filter_products", "check_compatibility",
            "rank_and_select", "confirm_selection", "confirm_order",
            "completed", "cancelled", "error"
        ]
        
        for state in expected_states:
            handler_name = f"handle_{state}_state"
            assert hasattr(fsm, handler_name), f"Missing handler for state: {state}"
            assert callable(getattr(fsm, handler_name)), f"Handler not callable for state: {state}"
    
    def test_next_method_delegates_to_handlers(self):
        """Test that next() method properly delegates to state handlers"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test", "session_id": "test"})
        
        with patch.object(fsm, 'handle_start_state') as mock_handler:
            mock_handler.return_value = StateTransition(
                next_state=ContractState.SEARCH,
                status="waiting_for_input",
                ask_user="Please provide input"
            )
            
            result = fsm.next()
            
            mock_handler.assert_called_once_with(None)
            assert result["status"] == "waiting_for_input"
    
    def test_next_method_handles_unknown_state(self):
        """Test that next() method handles unknown states gracefully"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        fsm.context.current_state = "unknown_state"
        
        result = fsm.next()
        
        assert result["status"] == "failed"
        assert "invalid state" in result["message"]
    
    def test_next_method_handles_handler_exceptions(self):
        """Test that next() method handles handler exceptions gracefully"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"session_id": "test"})
        
        with patch.object(fsm, 'handle_start_state') as mock_handler:
            mock_handler.side_effect = Exception("Test exception")
            
            result = fsm.next()
            
            assert result["status"] == "failed"
            assert "Error processing state" in result["message"]
