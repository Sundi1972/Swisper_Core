"""
Test suite for FSM + Preference Match Pipeline Integration.

Tests the integration between FSM state handlers and the preference match pipeline.
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.state_transitions import ContractState, StateTransition


class TestFSMPreferenceIntegration:
    def test_fsm_initializes_with_preference_pipeline(self):
        """Test that FSM initializes with preference match pipeline"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        
        assert hasattr(fsm, 'preference_match_pipeline')
        assert fsm.preference_match_pipeline is not None
    
    @patch('contract_engine.contract_engine.run_preference_match')
    def test_handle_match_preferences_state_uses_pipeline(self, mock_run_preference):
        """Test that handle_match_preferences_state uses the pipeline instead of direct LLM calls"""
        async def async_mock_return(*args, **kwargs):
            return {
                "status": "success",
                "ranked_products": [
                    {"name": "Product A", "price": "100 CHF", "rating": 4.5},
                    {"name": "Product B", "price": "150 CHF", "rating": 4.2},
                    {"name": "Product C", "price": "200 CHF", "rating": 4.8}
                ],
                "scores": [0.9, 0.8, 0.7],
                "ranking_method": "pipeline"
            }
        
        mock_run_preference.side_effect = async_mock_return
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        fsm.context.search_results = [
            {"name": "Product A", "price": "100 CHF"},
            {"name": "Product B", "price": "150 CHF"},
            {"name": "Product C", "price": "200 CHF"}
        ]
        fsm.context.preferences = {"budget": "under 200 CHF"}
        
        transition = asyncio.run(fsm.handle_match_preferences_state())
        
        mock_run_preference.assert_called_once()
        call_args = mock_run_preference.call_args
        assert call_args[1]['products'] == fsm.context.search_results
        assert call_args[1]['preferences'] == {"budget": "under 200 CHF"}
        
        assert transition.next_state == ContractState.CONFIRM_PURCHASE
        assert "preference_match_pipeline" in transition.tools_used
        assert len(transition.context_updates["top_products"]) == 3
    
    @patch('contract_engine.contract_engine.run_preference_match')
    def test_handle_match_preferences_state_no_results(self, mock_run_preference):
        """Test preference matching when pipeline returns no results"""
        async def async_mock_return(*args, **kwargs):
            return {
                "status": "no_products",
                "ranked_products": [],
                "scores": [],
                "ranking_method": "none"
            }
        
        mock_run_preference.side_effect = async_mock_return
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "nonexistent product", "session_id": "test"})
        fsm.context.search_results = [{"name": "Product A", "price": "100 CHF"}]
        fsm.context.preferences = {"budget": "under 50 CHF"}
        
        transition = asyncio.run(fsm.handle_match_preferences_state())
        
        assert transition.requires_user_input()
        assert "couldn't find products" in transition.ask_user.lower()
    
    @patch('contract_engine.contract_engine.run_preference_match')
    def test_handle_match_preferences_state_pipeline_error(self, mock_run_preference):
        """Test handling when preference pipeline returns error"""
        async def async_mock_error(*args, **kwargs):
            raise Exception("Pipeline component failed")
        
        mock_run_preference.side_effect = async_mock_error
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        fsm.context.search_results = [{"name": "Product A", "price": "100 CHF"}]
        fsm.context.preferences = {"budget": "under 200 CHF"}
        
        transition = asyncio.run(fsm.handle_match_preferences_state())
        
        assert transition.requires_user_input()
        assert "error while matching" in transition.ask_user.lower()
    
    def test_handle_match_preferences_state_no_search_results(self):
        """Test preference matching when no search results available"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        fsm.context.search_results = []
        fsm.context.preferences = {"budget": "under 200 CHF"}
        
        transition = asyncio.run(fsm.handle_match_preferences_state())
        
        assert transition.requires_user_input()
        assert "no products found" in transition.ask_user.lower()
    
    @patch('contract_engine.contract_engine.run_preference_match')
    @patch('contract_engine.llm_helpers.generate_product_recommendation')
    def test_handle_match_preferences_state_with_llm_recommendation(self, mock_generate_rec, mock_run_preference):
        """Test preference matching with LLM recommendation generation"""
        async def async_mock_return(*args, **kwargs):
            return {
                "status": "success",
                "ranked_products": [
                    {"name": "Product A", "price": "100 CHF", "rating": 4.5},
                    {"name": "Product B", "price": "150 CHF", "rating": 4.2}
                ],
                "scores": [0.9, 0.8],
                "ranking_method": "pipeline"
            }
        
        mock_run_preference.side_effect = async_mock_return
        
        mock_generate_rec.return_value = {
            "numbered_products": [
                {"number": 1, "name": "Product A", "price": "100 CHF", "key_specs": "High rating"},
                {"number": 2, "name": "Product B", "price": "150 CHF", "key_specs": "Good value"}
            ],
            "recommendation": {
                "choice": 1,
                "reasoning": "Best value for money"
            }
        }
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        fsm.context.search_results = [
            {"name": "Product A", "price": "100 CHF"},
            {"name": "Product B", "price": "150 CHF"}
        ]
        fsm.context.preferences = {"budget": "under 200 CHF"}
        
        transition = asyncio.run(fsm.handle_match_preferences_state())
        
        assert transition.next_state == ContractState.CONFIRM_PURCHASE
        assert "Product A" in transition.ask_user
        assert "Product B" in transition.ask_user
        assert "My recommendation: Option 1" in transition.ask_user
        assert "Best value for money" in transition.ask_user
    
    @patch('contract_engine.contract_engine.run_preference_match')
    def test_handle_match_preferences_state_fallback_recommendation(self, mock_run_preference):
        """Test preference matching with fallback recommendation when LLM fails"""
        async def async_mock_return(*args, **kwargs):
            return {
                "status": "success",
                "ranked_products": [
                    {"name": "Product A", "price": "100 CHF", "rating": 4.5}
                ],
                "scores": [0.9],
                "ranking_method": "pipeline"
            }
        
        mock_run_preference.side_effect = async_mock_return
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        fsm.context.search_results = [{"name": "Product A", "price": "100 CHF"}]
        fsm.context.preferences = {"budget": "under 200 CHF"}
        
        with patch('contract_engine.llm_helpers.generate_product_recommendation') as mock_generate_rec:
            mock_generate_rec.side_effect = Exception("LLM failed")
            
            transition = asyncio.run(fsm.handle_match_preferences_state())
            
            assert transition.next_state == ContractState.CONFIRM_PURCHASE
            assert "preference_match_pipeline" in transition.tools_used
            assert "generate_product_recommendation" not in transition.tools_used
    
    def test_wait_for_preferences_transitions_to_match_preferences(self):
        """Test that wait_for_preferences state transitions to match_preferences"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "laptop", "session_id": "test"})
        fsm.context.search_results = [{"name": "Laptop A", "price": "1000 CHF"}]
        
        transition = fsm.handle_wait_for_preferences_state("under 1200 CHF, good performance")
        
        assert transition.next_state == ContractState.MATCH_PREFERENCES
        assert "preferences" in transition.context_updates
        assert "constraints" in transition.context_updates
    
    def test_async_preference_handler_integration_in_next_method(self):
        """Test that the next() method properly handles async preference state handlers"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test", "session_id": "test"})
        fsm.context.search_results = [{"name": "Product A", "price": "100 CHF"}]
        fsm.context.preferences = {"budget": "under 200 CHF"}
        
        with patch.object(fsm, 'handle_match_preferences_state') as mock_handler:
            mock_handler.side_effect = lambda user_input: StateTransition(
                next_state=ContractState.CONFIRM_PURCHASE,
                status="waiting_for_input",
                ask_user="Please select a product"
            )
            
            import asyncio
            mock_handler._is_coroutine = asyncio.coroutines._is_coroutine
            
            fsm.context.current_state = "match_preferences"
            
            result = fsm.next()
            
            mock_handler.assert_called_once()
            assert result["status"] == "waiting_for_input"
    
    @patch('contract_engine.contract_engine.run_preference_match')
    def test_end_to_end_preference_flow(self, mock_run_preference):
        """Test complete preference flow from wait_for_preferences to confirm_purchase"""
        async def async_mock_return(*args, **kwargs):
            return {
                "status": "success",
                "ranked_products": [
                    {"name": "Laptop Pro", "price": "1200 CHF", "rating": 4.8},
                    {"name": "Laptop Standard", "price": "800 CHF", "rating": 4.5},
                    {"name": "Laptop Basic", "price": "600 CHF", "rating": 4.2}
                ],
                "scores": [0.95, 0.85, 0.75],
                "ranking_method": "pipeline"
            }
        
        mock_run_preference.side_effect = async_mock_return
        
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "laptop", "session_id": "test"})
        fsm.context.search_results = [
            {"name": "Laptop Pro", "price": "1200 CHF"},
            {"name": "Laptop Standard", "price": "800 CHF"},
            {"name": "Laptop Basic", "price": "600 CHF"}
        ]
        
        transition1 = fsm.handle_wait_for_preferences_state("under 1000 CHF, good for gaming")
        assert transition1.next_state == ContractState.MATCH_PREFERENCES
        
        fsm.context.preferences = transition1.context_updates["preferences"]
        fsm.context.constraints = transition1.context_updates["constraints"]
        
        transition2 = asyncio.run(fsm.handle_match_preferences_state())
        assert transition2.next_state == ContractState.CONFIRM_PURCHASE
        assert len(transition2.context_updates["top_products"]) == 3
        assert "preference_match_pipeline" in transition2.tools_used
    
    def test_preference_pipeline_with_empty_preferences(self):
        """Test preference matching with empty preferences"""
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        fsm.context.search_results = [{"name": "Product A", "price": "100 CHF"}]
        fsm.context.preferences = {}
        fsm.context.constraints = {}
        
        with patch('contract_engine.contract_engine.run_preference_match') as mock_run_preference:
            async def async_mock_return(*args, **kwargs):
                return {
                    "status": "success",
                    "ranked_products": [{"name": "Product A", "price": "100 CHF"}],
                    "scores": [0.5],
                    "ranking_method": "fallback"
                }
            
            mock_run_preference.side_effect = async_mock_return
            
            transition = asyncio.run(fsm.handle_match_preferences_state())
            
            mock_run_preference.assert_called_once()
            call_args = mock_run_preference.call_args
            assert call_args[1]['preferences'] == {}
            
            assert transition.next_state == ContractState.CONFIRM_PURCHASE
