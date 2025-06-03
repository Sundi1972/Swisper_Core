import pytest
from unittest.mock import patch, MagicMock
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.context import SwisperContext

class TestFSMIntegration:
    def test_fsm_initialization(self):
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        assert fsm.context.current_state == "start"
        assert fsm.contract is not None

    def test_fsm_parameter_filling(self):
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({
            "product": "GPU RTX 4090",
            "session_id": "test_session"
        })
        assert fsm.context.product_query == "GPU RTX 4090"
        assert fsm.context.session_id == "test_session"

    @patch('contract_engine.contract_engine.search_product')
    def test_fsm_product_search_flow(self, mock_search):
        mock_search.return_value = [{"name": "RTX 4090", "price": 1599.99}]
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "RTX 4090", "session_id": "test"})
        
        result = fsm.next()
        result_str = str(result) if isinstance(result, dict) else result
        assert "RTX 4090" in result_str
        assert fsm.context.current_state in ["search", "analyze_attributes", "confirm_order"]

    def test_fsm_state_transitions(self):
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        initial_state = fsm.context.current_state
        
        fsm.fill_parameters({"product": "test", "session_id": "test"})
        fsm.next()
        
        assert fsm.context.current_state != initial_state

    def test_context_serialization(self):
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({
            "product": "GPU RTX 4090",
            "session_id": "test_session"
        })
        
        context_dict = fsm.context.to_dict()
        assert context_dict["product_query"] == "GPU RTX 4090"
        assert context_dict["session_id"] == "test_session"
        
        new_context = SwisperContext.from_dict(context_dict)
        assert new_context.product_query == "GPU RTX 4090"
        assert new_context.session_id == "test_session"

    @patch('contract_engine.contract_engine.search_product')
    def test_fsm_no_products_found(self, mock_search):
        mock_search.return_value = []
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "nonexistent item", "session_id": "test"})
        
        result = fsm.next()
        result_str = str(result).lower() if isinstance(result, dict) else result.lower()
        assert "no suitable product" in result_str or "couldn't find" in result_str or "no products found" in result_str

    def test_fsm_multiple_state_transitions(self):
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.fill_parameters({"product": "test product", "session_id": "test"})
        
        states = [fsm.context.current_state]
        
        for _ in range(3):
            try:
                fsm.next()
                states.append(fsm.context.current_state)
            except:
                break
        
        assert len(set(states)) > 1

    def test_context_update_state(self):
        context = SwisperContext(session_id="test")
        assert context.current_state == "start"
        
        context.update_state("search")
        assert context.current_state == "search"
        
        context.update_state("confirm_order")
        assert context.current_state == "confirm_order"

    def test_context_metadata_handling(self):
        context = SwisperContext(session_id="test")
        
        context_dict = context.to_dict()
        assert "session_id" in context_dict
        assert context_dict["session_id"] == "test"
        
        restored_context = SwisperContext.from_dict(context_dict)
        assert restored_context.session_id == "test"
