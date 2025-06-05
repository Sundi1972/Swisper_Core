import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from orchestrator.core import handle, Message

class TestGraphicsCardBuying:
    @pytest.mark.asyncio
    async def test_gpu_purchase_flow_end_to_end(self):
        with patch('orchestrator.core.session_store') as mock_store, \
             patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_criteria:
            
            mock_store.get_pending_confirmation.return_value = None
            mock_store.get_contract_fsm.return_value = None
            
            mock_intent.return_value = {
                "intent_type": "contract",
                "confidence": 0.9,
                "parameters": {"contract_template": "purchase_item.yaml", "extracted_query": "I want to buy a GPU"}
            }
            
            mock_criteria.return_value = {
                "specifications": {"type": "GPU", "brand": "NVIDIA"},
                "budget": None,
                "preferences": []
            }
            
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {"ask_user": "I found this GPU: RTX 4090 (Price: $1599.99). Would you like to confirm?"}
            mock_fsm.context.search_results = [{"name": "RTX 4090", "price": 1599.99}]
            mock_fsm.context.current_state = "search"
            mock_fsm.context.selected_product = None
            mock_fsm_class.return_value = mock_fsm
            
            messages = [Message(role="user", content="I want to buy a GPU")]
            response = await handle(messages, "test_session")
            
            assert "RTX 4090" in response["reply"]
            assert "1599.99" in response["reply"]
            mock_fsm.next.assert_called_once()

    @pytest.mark.asyncio
    @patch('tool_adapter.mock_google.google_shopping_search')
    async def test_gpu_search_functionality(self, mock_search):
        mock_search.return_value = [
            {"name": "RTX 4090", "price": 1599.99, "specs": "24GB VRAM"},
            {"name": "RTX 4080", "price": 1199.99, "specs": "16GB VRAM"}
        ]
        
        results = mock_search("GPU RTX")
        
        assert len(results) == 2
        assert any("RTX 4090" in str(result) for result in results)
        assert any("RTX 4080" in str(result) for result in results)

    @pytest.mark.asyncio
    async def test_gpu_purchase_confirmation_flow(self):
        with patch('orchestrator.core.get_pending_confirmation') as mock_get_pending, \
             patch('orchestrator.core.clear_pending_confirmation') as mock_clear_pending, \
             patch('orchestrator.core.session_store') as mock_store:
            
            mock_get_pending.return_value = {
                "name": "RTX 4090", "price": 1599.99
            }
            mock_store.get_contract_fsm.return_value = None
            mock_store.get_chat_history.return_value = []
            mock_store.add_chat_message = MagicMock()
            mock_store.save_session = MagicMock()
            
            messages = [Message(role="user", content="yes")]
            response = await handle(messages, "test_session")
            
            assert "confirmed" in response["reply"].lower()
            mock_clear_pending.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpu_purchase_cancellation_flow(self):
        with patch('orchestrator.core.get_pending_confirmation') as mock_get_pending, \
             patch('orchestrator.core.clear_pending_confirmation') as mock_clear_pending, \
             patch('orchestrator.core.session_store') as mock_store:
            
            mock_get_pending.return_value = {
                "name": "RTX 4090", "price": 1599.99
            }
            mock_store.get_contract_fsm.return_value = None
            mock_store.get_chat_history.return_value = []
            mock_store.add_chat_message = MagicMock()
            mock_store.save_session = MagicMock()
            
            messages = [Message(role="user", content="no")]
            response = await handle(messages, "test_session")
            
            assert "cancelled" in response["reply"].lower()
            mock_clear_pending.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpu_search_no_results(self):
        with patch('orchestrator.core.session_store') as mock_store, \
             patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_criteria:
            
            mock_store.get_pending_confirmation.return_value = None
            mock_store.get_contract_fsm.return_value = None
            
            mock_intent.return_value = {
                "intent_type": "contract",
                "confidence": 0.9,
                "parameters": {"contract_template": "purchase_item.yaml", "extracted_query": "buy a nonexistent GPU"}
            }
            
            mock_criteria.return_value = {
                "specifications": {"type": "GPU", "brand": "NVIDIA"},
                "budget": None,
                "preferences": []
            }
            
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {"ask_user": "Sorry, I couldn't find any suitable products for your request."}
            mock_fsm.context.search_results = []
            mock_fsm.context.current_state = "search"
            mock_fsm.context.selected_product = None
            mock_fsm_class.return_value = mock_fsm
            
            messages = [Message(role="user", content="buy a nonexistent GPU")]
            response = await handle(messages, "test_session")
            
            assert "couldn't find" in response["reply"].lower()
            mock_store.set_pending_confirmation.assert_not_called()

    @pytest.mark.asyncio
    async def test_gpu_purchase_ambiguous_confirmation(self):
        with patch('orchestrator.core.get_pending_confirmation') as mock_get_pending, \
             patch('orchestrator.core.clear_pending_confirmation') as mock_clear_pending, \
             patch('orchestrator.core.session_store') as mock_store:
            
            mock_get_pending.return_value = {
                "name": "RTX 4090", "price": 1599.99
            }
            mock_store.get_contract_fsm.return_value = None
            mock_store.get_chat_history.return_value = []
            mock_store.add_chat_message = MagicMock()
            mock_store.save_session = MagicMock()
            
            messages = [Message(role="user", content="maybe later")]
            response = await handle(messages, "test_session")
            
            assert "didn't quite understand" in response["reply"]
            assert "RTX 4090" in response["reply"]
            mock_clear_pending.assert_not_called()

    @pytest.mark.asyncio
    async def test_gpu_purchase_with_specifications(self):
        with patch('orchestrator.core.session_store') as mock_store, \
             patch('orchestrator.intent_extractor.extract_user_intent') as mock_intent, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_criteria:
            
            mock_store.get_pending_confirmation.return_value = None
            mock_store.get_contract_fsm.return_value = None
            
            mock_intent.return_value = {
                "intent_type": "contract",
                "confidence": 0.9,
                "parameters": {"contract_template": "purchase_item.yaml", "extracted_query": "I want to buy a RTX 4090 with 24GB VRAM"}
            }
            
            mock_criteria.return_value = {
                "specifications": {"type": "GPU", "brand": "NVIDIA", "memory": "24GB"},
                "budget": None,
                "preferences": []
            }
            
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {"ask_user": "I found this GPU: RTX 4090 24GB (Price: $1599.99). Would you like to confirm?"}
            mock_fsm.context.search_results = [{"name": "RTX 4090 24GB", "price": 1599.99, "specs": "24GB VRAM"}]
            mock_fsm.context.current_state = "search"
            mock_fsm.context.selected_product = None
            mock_fsm_class.return_value = mock_fsm
            
            messages = [Message(role="user", content="I want to buy a RTX 4090 with 24GB VRAM")]
            response = await handle(messages, "test_session")
            
            assert "RTX 4090" in response["reply"]
            assert "24GB" in response["reply"]
            mock_fsm.fill_parameters.assert_called_once()
