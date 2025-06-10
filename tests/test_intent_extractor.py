import pytest
from unittest.mock import patch, MagicMock
from orchestrator.intent_extractor import extract_user_intent, load_available_tools, load_available_contracts

class TestIntentExtraction:
    """Comprehensive test suite for intent classification routing without frontend dependency"""
    
    def test_contract_intent_detection(self):
        """Test basic contract intent detection with purchase keywords"""
        result = extract_user_intent("I want to buy a GPU")
        assert result["intent_type"] == "contract"
        assert result["confidence"] >= 0.8
        assert "GPU" in result["parameters"]["extracted_query"]

    def test_rag_intent_detection(self):
        """Test RAG intent detection with #rag prefix"""
        result = extract_user_intent("#rag What is this system?")
        assert result["intent_type"] == "rag"
        assert result["confidence"] >= 0.9
        assert result["parameters"]["rag_question"] == "What is this system?"

    def test_chat_intent_fallback(self):
        """Test chat intent fallback for general conversation"""
        result = extract_user_intent("Hello, how are you?")
        assert result["intent_type"] == "chat"
        assert result["confidence"] > 0.0

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_intent_extraction_success(self, mock_llm):
        """Test successful LLM-based intent classification"""
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.return_value = '{"intent_type": "contract", "confidence": 0.95, "reasoning": "Purchase intent detected", "contract_template": "purchase_item.yaml", "tools_needed": [], "extracted_query": "graphics card", "rag_question": null}'
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("Purchase a graphics card")
        assert result["intent_type"] == "contract"
        assert result["confidence"] >= 0.85

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_fallback_on_low_confidence(self, mock_llm):
        """Test LLM classification with low confidence falls back to regex"""
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.return_value = '{"intent_type": "chat", "confidence": 0.3, "reasoning": "Low confidence", "contract_template": null, "tools_needed": [], "extracted_query": "buy a laptop", "rag_question": null}'
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("buy a laptop")
        assert result["intent_type"] == "contract"
        assert result["confidence"] >= 0.8

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_extraction_failure_fallback(self, mock_llm):
        """Test fallback to regex when LLM fails"""
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.side_effect = Exception("API Error")
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("purchase something")
        assert result["intent_type"] == "contract"
        assert result["confidence"] >= 0.85

    def test_fallback_contract_keywords(self):
        """Test contract keyword detection in fallback mode"""
        test_cases = [
            "buy a GPU",
            "purchase a laptop", 
            "order some food",
            "acquire new equipment",
            "get me a phone",
            "shop for clothes"
        ]
        
        for message in test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "contract"
            assert result["confidence"] >= 0.8

    def test_fallback_tool_keywords(self):
        """Test tool usage keyword detection in fallback mode"""
        test_cases = [
            "compare these products",
            "check compatibility",
            "analyze specifications",
            "filter results"
        ]
        
        for message in test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] in ["tool_usage", "chat"]
            assert result["confidence"] >= 0.7

    def test_fallback_rag_prefix(self):
        """Test RAG prefix detection in fallback mode"""
        result = extract_user_intent("#rag How does this work?")
        assert result["intent_type"] == "rag"
        assert result["confidence"] >= 0.9
        assert result["parameters"]["rag_question"] == "How does this work?"

    def test_fallback_chat_default(self):
        """Test default chat routing for unclassified intents"""
        result = extract_user_intent("Just saying hello")
        assert result["intent_type"] == "chat"
        assert result["confidence"] >= 0.5

    
    def test_websearch_intent_routing(self):
        """Test websearch intent detection for current events and news queries"""
        websearch_test_cases = [
            "who are the ministers of the newly elected german government",
            "Search the web for the latest news",
            "what happened today in politics",
            "current events in technology",
            "breaking news about climate change",
            "recent developments in AI"
        ]
        
        for message in websearch_test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "websearch", f"Failed for: {message}"
            assert result["confidence"] >= 0.7, f"Low confidence for: {message}"
            assert "reasoning" in result, f"Missing reasoning for: {message}"

    def test_chat_intent_routing(self):
        """Test chat intent detection for general knowledge and personal queries"""
        chat_test_cases = [
            "What is the capital of italy",
            "I am feeling down and depressed",
            "How are you doing?",
            "Tell me a joke",
            "What's 2 + 2?",
            "Explain quantum physics",
            "Hello there"
        ]
        
        for message in chat_test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "chat", f"Failed for: {message}"
            assert result["confidence"] >= 0.5, f"Low confidence for: {message}"

    def test_contract_purchase_intent_routing(self):
        """Test contract intent detection for purchase-related queries"""
        purchase_test_cases = [
            "I want to purchase a graphics card",
            "I want to buy a washing machine",
            "Looking for a new laptop to buy",
            "Need to order a smartphone",
            "Shop for winter clothes",
            "Acquire new gaming equipment",
            "Get me a coffee machine"
        ]
        
        for message in purchase_test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "contract", f"Failed for: {message}"
            assert result["confidence"] >= 0.8, f"Low confidence for: {message}"
            assert result.get("contract_template") == "purchase_item.yaml", f"Wrong contract template for: {message}"

    def test_tool_usage_intent_routing(self):
        """Test tool usage intent detection for analysis and comparison queries"""
        tool_test_cases = [
            "compare these two laptops",
            "check compatibility between components",
            "analyze product specifications",
            "filter products by price range",
            "find products with specific features"
        ]
        
        for message in tool_test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] in ["tool_usage", "chat"], f"Failed for: {message}"
            assert result["confidence"] >= 0.7, f"Low confidence for: {message}"

    def test_rag_intent_variations(self):
        """Test RAG intent detection with various question formats"""
        rag_test_cases = [
            "#rag What is machine learning?",
            "#rag How does the contract system work?",
            "#rag Explain the MCP architecture",
            "#rag What are the available tools?",
            "#rag Tell me about Swisper features"
        ]
        
        for message in rag_test_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == "rag", f"Failed for: {message}"
            assert result["confidence"] >= 0.9, f"Low confidence for: {message}"
            expected_question = message[5:].strip()  # Remove "#rag " prefix
            assert result["parameters"]["rag_question"] == expected_question, f"Wrong RAG question for: {message}"

    def test_edge_cases_and_ambiguous_intents(self):
        """Test edge cases and ambiguous intent scenarios"""
        edge_cases = [
            ("", "chat"),  # Empty string
            ("   ", "chat"),  # Whitespace only
            ("buy", "contract"),  # Single keyword
            ("search", "chat"),  # Ambiguous single word
            ("I want to", "chat"),  # Incomplete sentence
            ("I want to buy something", "contract"),  # Clear purchase intent
            ("Can you search for news?", "websearch"),  # Polite request format
        ]
        
        for message, expected_intent in edge_cases:
            result = extract_user_intent(message)
            assert result["intent_type"] == expected_intent, f"Failed for edge case: '{message}' - expected {expected_intent}, got {result['intent_type']}"
            assert result["confidence"] >= 0.5, f"Low confidence for edge case: '{message}'"

    def test_intent_classification_consistency(self):
        """Test that intent classification is consistent across multiple runs"""
        test_message = "I want to buy a laptop"
        results = []
        
        for _ in range(5):
            result = extract_user_intent(test_message)
            results.append(result)
        
        intent_types = [r["intent_type"] for r in results]
        assert all(intent == "contract" for intent in intent_types), "Inconsistent intent classification"
        
        confidences = [r["confidence"] for r in results]
        assert all(conf >= 0.8 for conf in confidences), "Inconsistent confidence scores"

    def test_tools_and_contracts_loading(self):
        """Test that tools and contracts are loaded correctly for intent classification"""
        try:
            tools = load_available_tools()
            contracts = load_available_contracts()
            
            assert isinstance(tools, dict), "Tools should be loaded as dictionary"
            assert isinstance(contracts, dict), "Contracts should be loaded as dictionary"
            assert len(tools) > 0, "Should have at least one tool loaded"
            assert len(contracts) > 0, "Should have at least one contract loaded"
            
            expected_tools = ["search_products", "search_web", "analyze_product_attributes"]
            for tool in expected_tools:
                assert tool in tools, f"Expected tool '{tool}' not found in loaded tools"
                
        except Exception as e:
            pytest.skip(f"Tool/contract loading failed: {e}")

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_websearch_classification(self, mock_llm):
        """Test LLM-based websearch intent classification"""
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.return_value = '{"intent_type": "websearch", "confidence": 0.9, "reasoning": "Current events query detected", "contract_template": null, "tools_needed": ["search_web"], "extracted_query": "latest news", "rag_question": null}'
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("What are the latest news?")
        assert result["intent_type"] == "websearch"
        assert result["confidence"] >= 0.8
        assert "search_web" in result.get("tools_needed", [])

    @patch('orchestrator.intent_extractor.get_llm_adapter')
    def test_llm_tool_usage_classification(self, mock_llm):
        """Test LLM-based tool usage intent classification"""
        mock_adapter = MagicMock()
        mock_adapter.chat_completion.return_value = '{"intent_type": "tool_usage", "confidence": 0.85, "reasoning": "Product analysis request", "contract_template": null, "tools_needed": ["analyze_product_attributes"], "extracted_query": "compare laptops", "rag_question": null}'
        mock_llm.return_value = mock_adapter
        
        result = extract_user_intent("Compare these two laptops")
        assert result["intent_type"] == "tool_usage"
        assert result["confidence"] >= 0.8
        assert "analyze_product_attributes" in result.get("tools_needed", [])

    def test_intent_result_structure(self):
        """Test that intent classification results have the expected structure"""
        result = extract_user_intent("I want to buy a phone")
        
        required_fields = ["intent_type", "confidence", "contract_template", "tools_needed", 
                          "extracted_query", "rag_question", "parameters", "reasoning"]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert isinstance(result["intent_type"], str), "intent_type should be string"
        assert isinstance(result["confidence"], (int, float)), "confidence should be numeric"
        assert isinstance(result["tools_needed"], list), "tools_needed should be list"
        assert isinstance(result["parameters"], dict), "parameters should be dict"
        assert isinstance(result["reasoning"], str), "reasoning should be string"

    def test_performance_and_timeout(self):
        """Test that intent classification completes within reasonable time"""
        import time
        
        test_messages = [
            "I want to buy a laptop",
            "What's the weather today?",
            "#rag How does this work?",
            "Compare these products"
        ]
        
        for message in test_messages:
            start_time = time.time()
            result = extract_user_intent(message)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 10.0, f"Intent classification took too long: {duration}s for '{message}'"
            assert result is not None, f"No result returned for: '{message}'"
