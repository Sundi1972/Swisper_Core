"""
Test suite for orchestrator integration with new FSM architecture.

Tests orchestrator initialization, pipeline integration, and error scenarios.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from orchestrator.core import handle, Message
from contract_engine.contract_engine import ContractStateMachine


class TestOrchestratorIntegration:
    """Test orchestrator integration with new FSM architecture"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initializes_pipelines(self):
        """Test that orchestrator properly initializes new pipeline architecture"""
        import orchestrator.core
        
        assert hasattr(orchestrator.core, 'PRODUCT_SEARCH_PIPELINE')
        assert hasattr(orchestrator.core, 'PREFERENCE_MATCH_PIPELINE')
    
    @pytest.mark.asyncio
    async def test_contract_initialization_with_pipelines(self):
        """Test that contract FSM is initialized with pipelines"""
        messages = [Message(role="user", content="I want to buy a laptop")]
        session_id = "test_session"
        
        with patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_extract, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('orchestrator.core.session_store') as mock_session_store, \
             patch('orchestrator.core.PRODUCT_SEARCH_PIPELINE', MagicMock()) as mock_search_pipeline, \
             patch('orchestrator.core.PREFERENCE_MATCH_PIPELINE', MagicMock()) as mock_pref_pipeline:
            
            mock_extract.return_value = {"product": "laptop", "specifications": {}}
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {"ask_user": "What type of laptop are you looking for?"}
            mock_fsm.context.current_state = "search"
            mock_fsm_class.return_value = mock_fsm
            
            mock_session_store.add_chat_message = MagicMock()
            mock_session_store.save_session = MagicMock()
            mock_session_store.get_pending_confirmation.return_value = None
            mock_session_store.get_contract_fsm.return_value = None
            mock_session_store.set_contract_fsm = MagicMock()
            
            result = await handle(messages, session_id)
            
            assert mock_fsm_class.called
            assert hasattr(mock_fsm, 'product_search_pipeline')
            assert hasattr(mock_fsm, 'preference_match_pipeline')
            assert mock_fsm.product_search_pipeline == mock_search_pipeline
            assert mock_fsm.preference_match_pipeline == mock_pref_pipeline
            
            assert "reply" in result
            assert result["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test graceful handling when pipeline initialization fails"""
        messages = [Message(role="user", content="I want to buy a laptop")]
        session_id = "test_session"
        
        with patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_extract, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('orchestrator.core.session_store') as mock_session_store, \
             patch('orchestrator.core.PRODUCT_SEARCH_PIPELINE', None), \
             patch('orchestrator.core.PREFERENCE_MATCH_PIPELINE', None):
            
            mock_extract.return_value = {"product": "laptop", "specifications": {}}
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {"ask_user": "What type of laptop are you looking for?"}
            mock_fsm.context.current_state = "search"
            mock_fsm_class.return_value = mock_fsm
            
            mock_session_store.add_chat_message = MagicMock()
            mock_session_store.save_session = MagicMock()
            mock_session_store.get_pending_confirmation.return_value = None
            mock_session_store.get_contract_fsm.return_value = None
            mock_session_store.set_contract_fsm = MagicMock()
            
            result = await handle(messages, session_id)
            
            assert mock_fsm_class.called
            
            assert "reply" in result
            assert result["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_session_management_with_new_context(self):
        """Test session management works with new context structure"""
        messages = [Message(role="user", content="yes")]
        session_id = "test_session"
        
        mock_fsm = MagicMock()
        mock_fsm.context.current_state = "wait_for_preferences"
        mock_fsm.context.search_results = [{"name": "Product A", "price": "100 CHF"}]
        mock_fsm.context.preferences = {"budget": "under 200 CHF"}
        mock_fsm.next.return_value = {"ask_user": "Here are your top 3 products..."}
        
        with patch('orchestrator.core.session_store') as mock_session_store:
            mock_session_store.add_chat_message = MagicMock()
            mock_session_store.save_session = MagicMock()
            mock_session_store.get_pending_confirmation.return_value = None
            mock_session_store.get_contract_fsm.return_value = mock_fsm
            mock_session_store.set_contract_fsm = MagicMock()
            
            result = await handle(messages, session_id)
            
            assert mock_fsm.next.called
            assert mock_session_store.set_contract_fsm.called
            
            assert "reply" in result
            assert result["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback(self):
        """Test error recovery when FSM processing fails"""
        messages = [Message(role="user", content="I want to buy a laptop")]
        session_id = "test_session"
        
        with patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_extract, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('orchestrator.core.session_store') as mock_session_store:
            
            mock_extract.return_value = {"product": "laptop", "specifications": {}}
            mock_fsm_class.side_effect = Exception("FSM initialization failed")
            
            mock_session_store.add_chat_message = MagicMock()
            mock_session_store.save_session = MagicMock()
            mock_session_store.get_pending_confirmation.return_value = None
            mock_session_store.get_contract_fsm.return_value = None
            
            result = await handle(messages, session_id)
            
            assert "reply" in result
            assert "error" in result["reply"].lower()
            assert result["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_fsm_continuation_error_handling(self):
        """Test error handling during FSM continuation"""
        messages = [Message(role="user", content="yes")]
        session_id = "test_session"
        
        mock_fsm = MagicMock()
        mock_fsm.context.current_state = "search"
        mock_fsm.next.side_effect = Exception("FSM processing failed")
        
        with patch('orchestrator.core.session_store') as mock_session_store:
            mock_session_store.add_chat_message = MagicMock()
            mock_session_store.save_session = MagicMock()
            mock_session_store.get_pending_confirmation.return_value = None
            mock_session_store.get_contract_fsm.return_value = mock_fsm
            mock_session_store.set_contract_fsm = MagicMock()
            
            result = await handle(messages, session_id)
            
            mock_session_store.set_contract_fsm.assert_called_with(session_id, None)
            
            assert "reply" in result
            assert "error" in result["reply"].lower()
            assert result["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_pipeline_availability_fallback(self):
        """Test fallback behavior when new pipelines are not available"""
        messages = [Message(role="user", content="I want to buy a laptop")]
        session_id = "test_session"
        
        with patch('orchestrator.core.create_product_search_pipeline', None), \
             patch('orchestrator.core.create_preference_match_pipeline', None), \
             patch('contract_engine.llm_helpers.extract_initial_criteria') as mock_extract, \
             patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class, \
             patch('orchestrator.core.session_store') as mock_session_store:
            
            mock_extract.return_value = {"product": "laptop", "specifications": {}}
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {"ask_user": "What type of laptop are you looking for?"}
            mock_fsm.context.current_state = "search"
            mock_fsm_class.return_value = mock_fsm
            
            mock_session_store.add_chat_message = MagicMock()
            mock_session_store.save_session = MagicMock()
            mock_session_store.get_pending_confirmation.return_value = None
            mock_session_store.get_contract_fsm.return_value = None
            mock_session_store.set_contract_fsm = MagicMock()
            
            result = await handle(messages, session_id)
            
            assert mock_fsm_class.called
            
            assert "reply" in result
            assert result["session_id"] == session_id
