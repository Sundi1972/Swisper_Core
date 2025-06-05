#!/usr/bin/env python3
"""Test script for LLM-based intent extraction"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.intent_extractor import extract_user_intent

def test_intent_extraction():
    """Test various user inputs for intent classification"""
    
    test_cases = [
        ("I want to buy a graphics card", "contract"),
        ("Purchase a laptop for gaming", "contract"),
        ("Find me a washing machine", "contract"),
        
        ("#rag What is the company policy on remote work?", "rag"),
        ("#rag How do I configure the database?", "rag"),
        
        ("Compare the specifications of RTX 4090 vs RTX 4080", "tool_usage"),
        ("Check if this motherboard is compatible with DDR5 RAM", "tool_usage"),
        
        ("Hello, how are you?", "chat"),
        ("What's the weather like today?", "chat"),
        ("Tell me a joke", "chat"),
    ]
    
    print("Testing LLM-based Intent Extraction")
    print("=" * 50)
    
    for user_input, expected_intent in test_cases:
        print(f"\nInput: {user_input}")
        try:
            result = extract_user_intent(user_input)
            actual_intent = result.get("intent_type")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")
            
            status = "✅ PASS" if actual_intent == expected_intent else "❌ FAIL"
            print(f"Expected: {expected_intent}")
            print(f"Actual: {actual_intent} (confidence: {confidence:.2f})")
            print(f"Reasoning: {reasoning}")
            print(f"Status: {status}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_intent_extraction()
