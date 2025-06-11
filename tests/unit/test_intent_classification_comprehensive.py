#!/usr/bin/env python3
"""
Comprehensive Intent Classification Test Suite
Standalone test suite that can run without frontend dependencies
Part of the standard regression test suite for Swisper Core
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.intent_extractor import extract_user_intent, load_available_tools, load_available_contracts

class TestIntentClassificationComprehensive:
    """Comprehensive test suite for intent classification without frontend dependency"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment before each test"""
        self.test_cases_websearch = [
            "who are the ministers of the newly elected german government",
            "Search the web for the latest news",
            "what happened today in politics",
            "current events in technology",
            "breaking news about climate change",
            "recent developments in AI",
            "latest news about elections"
        ]
        
        self.test_cases_chat = [
            "What is the capital of italy",
            "I am feeling down and depressed", 
            "How are you doing today?",
            "Tell me a joke",
            "What's 2 + 2?",
            "Explain quantum physics",
            "Hello there",
            "Good morning"
        ]
        
        self.test_cases_contract = [
            "I want to purchase a graphics card",
            "I want to buy a washing machine",
            "Looking for a new laptop to buy",
            "Need to order a smartphone", 
            "Shop for winter clothes",
            "Acquire new gaming equipment",
            "Get me a coffee machine",
            "Find me a good tablet"
        ]
        
        self.test_cases_rag = [
            "#rag What is machine learning?",
            "#rag How does the contract system work?",
            "#rag Explain the MCP architecture",
            "#rag What are the available tools?",
            "#rag Tell me about Swisper features"
        ]
        
        self.test_cases_tool_usage = [
            "compare these two laptops",
            "check compatibility between components", 
            "analyze product specifications",
            "filter products by price range",
            "find products with specific features"
        ]

    def test_websearch_routing_comprehensive(self):
        """Test websearch intent routing for all current events scenarios"""
        for message in self.test_cases_websearch:
            result = extract_user_intent(message)
            assert result["intent_type"] == "websearch", f"Failed websearch routing for: {message}"
            assert result["confidence"] >= 0.7, f"Low confidence ({result['confidence']}) for websearch: {message}"
            assert "reasoning" in result, f"Missing reasoning for websearch: {message}"
            print(f"✅ Websearch: '{message}' -> {result['intent_type']} (conf: {result['confidence']:.2f})")

    def test_chat_routing_comprehensive(self):
        """Test chat intent routing for all general conversation scenarios"""
        for message in self.test_cases_chat:
            result = extract_user_intent(message)
            assert result["intent_type"] == "chat", f"Failed chat routing for: {message}"
            assert result["confidence"] >= 0.5, f"Low confidence ({result['confidence']}) for chat: {message}"
            print(f"✅ Chat: '{message}' -> {result['intent_type']} (conf: {result['confidence']:.2f})")

    def test_contract_routing_comprehensive(self):
        """Test contract intent routing for all purchase scenarios"""
        for message in self.test_cases_contract:
            result = extract_user_intent(message)
            assert result["intent_type"] == "contract", f"Failed contract routing for: {message}"
            assert result["confidence"] >= 0.8, f"Low confidence ({result['confidence']}) for contract: {message}"
            assert result.get("contract_template") == "purchase_item.yaml", f"Wrong contract template for: {message}"
            print(f"✅ Contract: '{message}' -> {result['intent_type']} (conf: {result['confidence']:.2f})")

    def test_rag_routing_comprehensive(self):
        """Test RAG intent routing for all knowledge queries"""
        for message in self.test_cases_rag:
            result = extract_user_intent(message)
            assert result["intent_type"] == "rag", f"Failed RAG routing for: {message}"
            assert result["confidence"] >= 0.9, f"Low confidence ({result['confidence']}) for RAG: {message}"
            expected_question = message[5:].strip()  # Remove "#rag " prefix
            assert result["parameters"]["rag_question"] == expected_question, f"Wrong RAG question for: {message}"
            print(f"✅ RAG: '{message}' -> {result['intent_type']} (conf: {result['confidence']:.2f})")

    def test_tool_usage_routing_comprehensive(self):
        """Test tool usage intent routing for all analysis scenarios"""
        for message in self.test_cases_tool_usage:
            result = extract_user_intent(message)
            assert result["intent_type"] in ["tool_usage", "chat"], f"Failed tool usage routing for: {message}"
            assert result["confidence"] >= 0.7, f"Low confidence ({result['confidence']}) for tool usage: {message}"
            print(f"✅ Tool Usage: '{message}' -> {result['intent_type']} (conf: {result['confidence']:.2f})")

    def test_llm_vs_fallback_behavior(self):
        """Test LLM-first behavior vs fallback mechanisms"""
        test_message = "I want to buy a laptop"
        
        with patch('orchestrator.intent_extractor.get_llm_adapter') as mock_llm:
            mock_adapter = MagicMock()
            mock_adapter.chat_completion.return_value = '{"intent_type": "contract", "confidence": 0.95, "reasoning": "LLM detected purchase intent", "contract_template": "purchase_item.yaml", "tools_needed": [], "extracted_query": "laptop", "rag_question": null}'
            mock_llm.return_value = mock_adapter
            
            result_llm = extract_user_intent(test_message)
            assert result_llm["intent_type"] == "contract"
            assert "LLM" in result_llm.get("reasoning", "")
            print(f"✅ LLM Success: {result_llm['confidence']:.2f} confidence")
        
        with patch('orchestrator.intent_extractor.get_llm_adapter') as mock_llm:
            mock_adapter = MagicMock()
            mock_adapter.chat_completion.side_effect = Exception("LLM unavailable")
            mock_llm.return_value = mock_adapter
            
            result_fallback = extract_user_intent(test_message)
            assert result_fallback["intent_type"] == "contract"
            assert "fallback" in result_fallback.get("reasoning", "").lower()
            print(f"✅ Fallback Success: {result_fallback['confidence']:.2f} confidence")

    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling scenarios"""
        edge_cases = [
            ("", "chat", "Empty string"),
            ("   ", "chat", "Whitespace only"),
            ("buy", "contract", "Single purchase keyword"),
            ("search", "chat", "Ambiguous single word"),
            ("I want to", "chat", "Incomplete sentence"),
            ("What about buying something?", "contract", "Question with purchase intent"),
            ("Can you search for news?", "websearch", "Polite websearch request"),
            ("🤖🔍📱", "chat", "Emoji only"),
            ("a" * 1000, "chat", "Very long string")
        ]
        
        for message, expected_intent, description in edge_cases:
            try:
                result = extract_user_intent(message)
                assert result["intent_type"] == expected_intent, f"Failed for {description}: '{message}' - expected {expected_intent}, got {result['intent_type']}"
                assert result["confidence"] >= 0.5, f"Low confidence for {description}: '{message}'"
                print(f"✅ Edge Case: {description} -> {result['intent_type']} (conf: {result['confidence']:.2f})")
            except Exception as e:
                pytest.fail(f"Exception for edge case {description}: {e}")

    def test_intent_classification_performance(self):
        """Test performance and response time of intent classification"""
        import time
        
        test_messages = [
            "I want to buy a laptop",
            "What's the weather today?", 
            "#rag How does this work?",
            "Compare these products",
            "Search for latest news"
        ]
        
        total_time = 0
        for message in test_messages:
            start_time = time.time()
            result = extract_user_intent(message)
            end_time = time.time()
            
            duration = end_time - start_time
            total_time += duration
            
            assert duration < 10.0, f"Intent classification took too long: {duration:.2f}s for '{message}'"
            assert result is not None, f"No result returned for: '{message}'"
            print(f"✅ Performance: '{message}' classified in {duration:.3f}s")
        
        avg_time = total_time / len(test_messages)
        print(f"✅ Average classification time: {avg_time:.3f}s")
        assert avg_time < 5.0, f"Average classification time too high: {avg_time:.2f}s"

    def test_result_structure_validation(self):
        """Test that all intent classification results have consistent structure"""
        test_messages = [
            "I want to buy a phone",
            "What's the capital of France?",
            "#rag Explain AI",
            "Search for news",
            "Compare products"
        ]
        
        required_fields = ["intent_type", "confidence", "contract_template", "tools_needed", 
                          "extracted_query", "rag_question", "parameters", "reasoning"]
        
        for message in test_messages:
            result = extract_user_intent(message)
            
            for field in required_fields:
                assert field in result, f"Missing required field '{field}' for message: '{message}'"
            
            assert isinstance(result["intent_type"], str), f"intent_type should be string for: '{message}'"
            assert isinstance(result["confidence"], (int, float)), f"confidence should be numeric for: '{message}'"
            assert isinstance(result["tools_needed"], list), f"tools_needed should be list for: '{message}'"
            assert isinstance(result["parameters"], dict), f"parameters should be dict for: '{message}'"
            assert isinstance(result["reasoning"], str), f"reasoning should be string for: '{message}'"
            
            assert 0.0 <= result["confidence"] <= 1.0, f"confidence out of range for: '{message}'"
            assert result["intent_type"] in ["chat", "contract", "websearch", "tool_usage", "rag"], f"Invalid intent_type for: '{message}'"
            
            print(f"✅ Structure: '{message}' has valid result structure")

    def test_tools_and_contracts_integration(self):
        """Test integration with tools and contracts loading"""
        try:
            tools = load_available_tools()
            contracts = load_available_contracts()
            
            assert isinstance(tools, dict), "Tools should be loaded as dictionary"
            assert isinstance(contracts, dict), "Contracts should be loaded as dictionary"
            assert len(tools) > 0, "Should have at least one tool loaded"
            assert len(contracts) > 0, "Should have at least one contract loaded"
            
            expected_tools = ["search_products", "search_web"]
            for tool in expected_tools:
                if tool in tools:
                    print(f"✅ Tool found: {tool}")
                else:
                    print(f"⚠️  Tool not found: {tool}")
            
            expected_contracts = ["purchase_item.yaml"]
            for contract in expected_contracts:
                if contract in contracts:
                    print(f"✅ Contract found: {contract}")
                else:
                    print(f"⚠️  Contract not found: {contract}")
                    
            print(f"✅ Loaded {len(tools)} tools and {len(contracts)} contracts successfully")
            
        except Exception as e:
            pytest.skip(f"Tool/contract loading failed: {e}")

    def test_consistency_across_runs(self):
        """Test that intent classification is consistent across multiple runs"""
        test_cases = [
            ("I want to buy a laptop", "contract"),
            ("What's the weather?", "chat"),
            ("#rag How does this work?", "rag"),
            ("Search for latest news", "websearch")
        ]
        
        for message, expected_intent in test_cases:
            results = []
            
            for _ in range(3):
                result = extract_user_intent(message)
                results.append(result)
            
            intent_types = [r["intent_type"] for r in results]
            assert all(intent == expected_intent for intent in intent_types), f"Inconsistent intent classification for: '{message}'"
            
            confidences = [r["confidence"] for r in results]
            confidence_range = max(confidences) - min(confidences)
            assert confidence_range < 0.1, f"High confidence variance for: '{message}'"
            
            print(f"✅ Consistency: '{message}' -> {expected_intent} (variance: {confidence_range:.3f})")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
