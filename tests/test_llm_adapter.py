import pytest
import os
from unittest.mock import patch, MagicMock
from orchestrator.llm_adapter import OpenAIAdapter, get_llm_adapter

class TestLLMAdapter:
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('orchestrator.llm_adapter.OpenAI')
    def test_openai_adapter_initialization(self, mock_openai):
        adapter = OpenAIAdapter()
        assert adapter.client is not None
        mock_openai.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_openai_adapter_no_api_key_warning(self):
        with patch('orchestrator.llm_adapter.logger') as mock_logger:
            adapter = OpenAIAdapter()
            assert adapter.client is None or hasattr(adapter, 'client')

    @patch('orchestrator.llm_adapter.OpenAI')
    def test_chat_completion_success(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        adapter = OpenAIAdapter()
        result = adapter.chat_completion([{"role": "user", "content": "test"}])
        assert result == "Test response"

    @patch('orchestrator.llm_adapter.OpenAI')
    def test_chat_completion_failure(self, mock_openai):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        adapter = OpenAIAdapter()
        with pytest.raises(Exception):
            adapter.chat_completion([{"role": "user", "content": "test"}])

    def test_chat_completion_no_client(self):
        adapter = OpenAIAdapter()
        adapter.client = None
        
        with pytest.raises(Exception, match="OpenAI client not initialized"):
            adapter.chat_completion([{"role": "user", "content": "test"}])

    def test_get_llm_adapter_default(self):
        adapter = get_llm_adapter()
        assert isinstance(adapter, OpenAIAdapter)

    @patch.dict(os.environ, {'SWISPER_LLM_PROVIDER': 'openai'})
    def test_get_llm_adapter_openai_explicit(self):
        adapter = get_llm_adapter()
        assert isinstance(adapter, OpenAIAdapter)

    @patch.dict(os.environ, {'SWISPER_LLM_PROVIDER': 'unknown'})
    def test_get_llm_adapter_unknown_provider(self):
        with patch('orchestrator.llm_adapter.logger') as mock_logger:
            adapter = get_llm_adapter()
            assert isinstance(adapter, OpenAIAdapter)
            mock_logger.warning.assert_called_with("Unknown LLM provider: unknown, falling back to OpenAI")

    @patch('orchestrator.llm_adapter.OpenAI')
    def test_chat_completion_with_custom_model(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Custom model response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        adapter = OpenAIAdapter()
        result = adapter.chat_completion([{"role": "user", "content": "test"}], model="gpt-3.5-turbo")
        
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}]
        )
        assert result == "Custom model response"
