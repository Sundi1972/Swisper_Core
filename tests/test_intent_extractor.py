import pytest
from unittest.mock import patch, MagicMock
from orchestrator.intent_extractor import extract_user_intent, _fallback_intent_extraction

class TestIntentExtraction:
    def test_contract_intent_detection(self):
        result = extract_user_intent("I want to buy a GPU")
        assert result["intent_type"] == "contract"
        assert result["confidence"] > 0.8
        assert "GPU" in result["parameters"]["extracted_query"]

    def test_rag_intent_detection(self):
        result = extract_user_intent("#rag What is this system?")
        assert result["intent_type"] == "rag"
        assert result["confidence"] >= 0.9
        assert result["parameters"]["rag_question"] == "What is this system?"

    def test_chat_intent_fallback(self):
        result = extract_user_intent("Hello, how are you?")
        assert result["intent_type"] == "chat"
        assert result["confidence"] > 0.0

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_intent_extraction_success(self, mock_llm):
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.return_value = '{"intent_type": "contract", "confidence": 0.95, "parameters": {"extracted_query": "graphics card"}}'
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("Purchase a graphics card")
        assert result["intent_type"] == "contract"
        assert result["confidence"] == 0.95

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_fallback_on_low_confidence(self, mock_llm):
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.return_value = '{"intent_type": "chat", "confidence": 0.5, "parameters": {}}'
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("buy a laptop")
        assert result["intent_type"] == "contract"
        assert result["confidence"] == 0.9

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_extraction_failure_fallback(self, mock_llm):
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.side_effect = Exception("API Error")
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("purchase something")
        assert result["intent_type"] == "contract"
        assert result["confidence"] == 0.9

    def test_fallback_contract_keywords(self):
        test_cases = [
            "buy a GPU",
            "purchase a laptop", 
            "order some food",
            "acquire new equipment",
            "get me a phone",
            "shop for clothes"
        ]
        
        for message in test_cases:
            result = _fallback_intent_extraction(message)
            assert result["intent_type"] == "contract"
            assert result["confidence"] == 0.9

    def test_fallback_tool_keywords(self):
        test_cases = [
            "compare these products",
            "check compatibility",
            "analyze specifications",
            "filter results"
        ]
        
        for message in test_cases:
            result = _fallback_intent_extraction(message)
            assert result["intent_type"] == "tool_usage"
            assert result["confidence"] == 0.8

    def test_fallback_rag_prefix(self):
        result = _fallback_intent_extraction("#rag How does this work?")
        assert result["intent_type"] == "rag"
        assert result["confidence"] == 1.0
        assert result["parameters"]["rag_question"] == "How does this work?"

    def test_fallback_chat_default(self):
        result = _fallback_intent_extraction("Just saying hello")
        assert result["intent_type"] == "chat"
        assert result["confidence"] == 0.8
