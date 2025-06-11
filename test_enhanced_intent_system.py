#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))

from orchestrator.intent_extractor import extract_user_intent

def test_specific_cases():
    """Test the specific cases mentioned by the user"""
    
    os.environ['OPENAI_API_KEY'] = os.environ.get('OpenAI_API_Key', '')
    
    test_cases = [
        ("Who is Angela Merkel", "chat"),
        ("What is the capital of Germany", "chat"),
        ("Explain quantum computing", "chat"),
        
        ("Who are the ministers of German government", "websearch"),
        ("Who are the current ministers of German government", "websearch"),
        ("Who is the CEO of UBS?", "websearch"),
        ("Price of Bitcoin today", "websearch"),
        ("Latest news about German politics", "websearch"),
    ]
    
    print("=== Testing Enhanced Intent Detection System ===\n")
    
    for query, expected_intent in test_cases:
        print(f"Testing: '{query}'")
        try:
            result = extract_user_intent(query)
            actual_intent = result["intent_type"]
            confidence = result["confidence"]
            reasoning = result.get("reasoning", "No reasoning provided")
            
            status = "✅ PASS" if actual_intent == expected_intent else "❌ FAIL"
            print(f"  Expected: {expected_intent}")
            print(f"  Actual: {actual_intent}")
            print(f"  Confidence: {confidence}")
            print(f"  Status: {status}")
            print(f"  Reasoning: {reasoning}")
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
        
        print()

if __name__ == "__main__":
    test_specific_cases()
