"""
Test suite for FSM + Product Search Pipeline Integration.

Tests the integration between FSM state handlers and the product search pipeline.
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.state_transitions import ContractState, StateTransition


class TestFSMSearchIntegration:
    def test_fsm_initializes_with_pipeline(self):
        """Test that FSM initializes with product search pipeline"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        assert hasattr(fsm, 'product_search_pipeline')
        assert fsm.product_search_pipeline is not None
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_handle_search_state_uses_pipeline(self, mock_run_search):
        """Test that handle_search_state uses the pipeline instead of direct search"""
        mock_run_search.return_value = {
            "status": "ok",
            "items": [{"name": "Test Product", "price": "100 CHF"}],
            "attributes": ["brand", "price"]
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        
        transition = asyncio.run(fsm.handle_search_state())
        
        mock_run_search.assert_called_once()
        call_args = mock_run_search.call_args
        assert call_args[1]['query'] == "test product"
        
        assert transition.next_state == ContractState.PRESENT_OPTIONS
        assert "product_search_pipeline" in transition.tools_used
        assert len(transition.context_updates["search_results"]) == 1
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_handle_search_state_too_many_results(self, mock_run_search):
        """Test constraint refinement when pipeline returns too_many_results"""
        mock_run_search.return_value = {
            "status": "too_many_results",
            "items": [],
            "attributes": ["brand", "price", "capacity"]
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "washing machine", "session_id": "test"})
        
        transition = asyncio.run(fsm.handle_search_state())
        
        assert transition.next_state == ContractState.REFINE_CONSTRAINTS
        assert transition.requires_user_input()
        assert "brand, price, capacity" in transition.ask_user
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_handle_search_state_no_results(self, mock_run_search):
        """Test handling when pipeline returns no results"""
        mock_run_search.return_value = {
            "status": "ok",
            "items": [],
            "attributes": []
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "nonexistent product", "session_id": "test"})
        
        transition = asyncio.run(fsm.handle_search_state())
        
        assert transition.requires_user_input()
        assert "couldn't find any products" in transition.ask_user.lower()
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_handle_search_state_pipeline_error(self, mock_run_search):
        """Test handling when pipeline returns error"""
        mock_run_search.return_value = {
            "status": "error",
            "items": [],
            "attributes": [],
            "error": "Pipeline component failed"
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        
        transition = asyncio.run(fsm.handle_search_state())
        
        assert transition.requires_user_input()
        assert "encountered an error" in transition.ask_user.lower()
    
    def test_constraint_refinement_message_generation(self):
        """Test constraint refinement message generation"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "laptop", "session_id": "test"})
        
        message = fsm._generate_constraint_refinement_message(["brand", "price", "memory"])
        assert "brand, price, memory" in message
        assert "laptop" in message
        
        message = fsm._generate_constraint_refinement_message([])
        assert "brand, price range" in message
        assert "laptop" in message
    
    def test_parse_user_constraints_price(self):
        """Test parsing price constraints from user input"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        constraints = fsm._parse_user_constraints("under 500")
        assert len(constraints) == 1
        assert constraints[0]["type"] == "price"
        assert constraints[0]["value"] == 500
        
        constraints = fsm._parse_user_constraints("maximum 1000 CHF")
        assert constraints[0]["type"] == "price"
        assert constraints[0]["value"] == 1000
    
    def test_parse_user_constraints_brand(self):
        """Test parsing brand constraints from user input"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        constraints = fsm._parse_user_constraints("brand Samsung")
        assert len(constraints) == 1
        assert constraints[0]["type"] == "brand"
        assert constraints[0]["value"] == "Samsung"
    
    def test_parse_user_constraints_general(self):
        """Test parsing general constraints from user input"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        constraints = fsm._parse_user_constraints("energy efficient with large capacity")
        assert len(constraints) == 1
        assert constraints[0]["type"] == "general"
        assert "energy efficient" in constraints[0]["value"]
    
    def test_handle_refine_constraints_state_first_time(self):
        """Test refine_constraints state when called first time (no user input)"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "washing machine", "session_id": "test"})
        fsm.context.extracted_attributes = ["brand", "capacity", "energy_rating"]
        
        transition = fsm.handle_refine_constraints_state()
        
        assert transition.requires_user_input()
        assert "brand, capacity, energy_rating" in transition.ask_user
    
    def test_handle_refine_constraints_state_with_input(self):
        """Test refine_constraints state with user input"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "washing machine", "session_id": "test"})
        
        transition = fsm.handle_refine_constraints_state("under 800 CHF")
        
        assert transition.next_state == ContractState.SEARCH
        assert len(transition.context_updates["constraints"]) == 1
        assert transition.context_updates["refinement_attempts"] == 1
    
    def test_constraint_refinement_loop_limit(self):
        """Test that constraint refinement has a maximum attempt limit"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "laptop", "session_id": "test"})
        setattr(fsm.context, 'refinement_attempts', 3)  # Already at max
        
        transition = fsm.handle_refine_constraints_state("more constraints")
        
        assert transition.context_updates["refinement_attempts"] == 4
    
    @patch('contract_engine.pipelines.product_search_pipeline.run_product_search')
    def test_end_to_end_search_flow_with_refinement(self, mock_run_search):
        """Test complete search flow with constraint refinement"""
        first_result = {
            "status": "too_many_results",
            "items": [],
            "attributes": ["brand", "price"]
        }
        
        second_result = {
            "status": "ok",
            "items": [{"name": "Refined Product", "price": "200 CHF"}],
            "attributes": ["brand", "price"]
        }
        
        mock_run_search.side_effect = [first_result, second_result]
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "smartphone", "session_id": "test"})
        
        transition1 = asyncio.run(fsm.handle_search_state())
        assert transition1.next_state == ContractState.REFINE_CONSTRAINTS
        
        transition2 = fsm.handle_refine_constraints_state("under 300 CHF")
        assert transition2.next_state == ContractState.SEARCH
        
        fsm.context.constraints = transition2.context_updates["constraints"]
        
        transition3 = asyncio.run(fsm.handle_search_state())
        assert transition3.next_state == ContractState.PRESENT_OPTIONS
        assert len(transition3.context_updates["search_results"]) == 1
    
    def test_async_handler_integration_in_next_method(self):
        """Test that the next() method properly handles async state handlers"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test", "session_id": "test"})
        
        with patch.object(fsm, 'handle_search_state') as mock_handler:
            mock_handler.side_effect = lambda user_input: StateTransition(
                next_state=ContractState.PRESENT_OPTIONS,
                status="continue",
                ask_user="Please select a product"  # Requires user input to prevent recursive call
            )
            
            import asyncio
            mock_handler._is_coroutine = asyncio.coroutines._is_coroutine
            
            fsm.context.current_state = "search"
            
            result = fsm.next()
            
            mock_handler.assert_called_once()
            assert result["status"] == "continue"
