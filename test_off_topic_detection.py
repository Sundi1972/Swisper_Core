#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contract_engine.llm_helpers import is_response_relevant, is_cancel_request

def test_off_topic_detection():
    """Test off-topic response detection functionality"""
    
    print("🧪 Testing Off-Topic Response Detection")
    print("=" * 50)
    
    clarification_tests = [
        ("I need 16GB RAM and under 2000 CHF", True, "product criteria and specifications", "graphics card RTX 4070"),
        ("RTX 4070 or better", True, "product criteria and specifications", "graphics card"),
        ("Any brand is fine, just good performance", True, "product criteria and specifications", "laptop"),
        ("Under 1500 CHF please", True, "product criteria and specifications", "smartphone"),
        
        ("Who was Gerhard Schroeder?", False, "product criteria and specifications", "graphics card RTX 4070"),
        ("What's the weather today?", False, "product criteria and specifications", "laptop"),
        ("Tell me about quantum physics", False, "product criteria and specifications", "graphics card"),
        ("I want to buy a washing machine", False, "product criteria and specifications", "graphics card RTX 4070"),
    ]
    
    confirmation_tests = [
        ("yes", True, "yes/no confirmation for product purchase", "ASUS ROG Strix RTX 4070 at 899 CHF"),
        ("no", True, "yes/no confirmation for product purchase", "ASUS ROG Strix RTX 4070 at 899 CHF"),
        ("I'm not sure about the price", True, "yes/no confirmation for product purchase", "ASUS ROG Strix RTX 4070 at 899 CHF"),
        ("confirm", True, "yes/no confirmation for product purchase", "laptop at 1500 CHF"),
        
        ("Tell me about quantum physics", False, "yes/no confirmation for product purchase", "ASUS ROG Strix RTX 4070 at 899 CHF"),
        ("Who was the first president?", False, "yes/no confirmation for product purchase", "laptop at 1500 CHF"),
        ("I want a different product entirely", False, "yes/no confirmation for product purchase", "graphics card at 800 CHF"),
    ]
    
    cancel_tests = [
        ("cancel", True),
        ("I want to cancel", True),
        ("exit", True),
        ("stop", True),
        ("quit", True),
        ("nevermind", True),
        ("yes please", False),
        ("no thanks", False),
        ("16GB RAM", False),
    ]
    
    print("\n📋 Testing Clarification Context")
    print("-" * 30)
    for user_response, expected_relevant, context, product in clarification_tests:
        result = is_response_relevant(user_response, context, product)
        actual_relevant = result.get("is_relevant", True)
        status = "✅" if actual_relevant == expected_relevant else "❌"
        print(f"{status} '{user_response}' → {actual_relevant} (expected {expected_relevant})")
        if actual_relevant != expected_relevant:
            print(f"   Reason: {result.get('reason', 'No reason provided')}")
    
    print("\n📋 Testing Confirmation Context")
    print("-" * 30)
    for user_response, expected_relevant, context, product in confirmation_tests:
        result = is_response_relevant(user_response, context, product)
        actual_relevant = result.get("is_relevant", True)
        status = "✅" if actual_relevant == expected_relevant else "❌"
        print(f"{status} '{user_response}' → {actual_relevant} (expected {expected_relevant})")
        if actual_relevant != expected_relevant:
            print(f"   Reason: {result.get('reason', 'No reason provided')}")
    
    print("\n📋 Testing Cancellation Detection")
    print("-" * 30)
    for user_response, expected_cancel in cancel_tests:
        actual_cancel = is_cancel_request(user_response)
        status = "✅" if actual_cancel == expected_cancel else "❌"
        print(f"{status} '{user_response}' → {actual_cancel} (expected {expected_cancel})")
    
    print("\n🎯 Off-Topic Detection Test Complete!")

if __name__ == "__main__":
    test_off_topic_detection()
