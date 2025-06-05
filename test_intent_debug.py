#!/usr/bin/env python3
"""
Debug script to test intent extraction for the specific failing case
"""
import os
import sys
sys.path.append('.')

from orchestrator.intent_extractor import extract_user_intent, load_available_contracts, load_available_tools

def test_intent_extraction():
    print("=== Routing Manifest ===")
    from orchestrator.intent_extractor import _generate_routing_manifest
    manifest = _generate_routing_manifest()
    import json
    print(json.dumps(manifest, indent=2))
    
    print("\n=== Intent Classification Tests ===")
    test_cases = [
        "I want to buy a washingmachine under 1200 chf",
        "#rag What is this document about?",
        "Compare these two graphics cards",
        "Hello, how are you today?"
    ]
    
    for test_message in test_cases:
        print(f"\nTesting: '{test_message}'")
        result = extract_user_intent(test_message)
        print(f"Intent: {result['intent_type']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reasoning: {result['reasoning']}")
        if result.get('contract_template'):
            print(f"Contract: {result['contract_template']}")
        if result.get('parameters', {}).get('contract_template'):
            print(f"Contract Template: {result['parameters']['contract_template']}")
        if result.get('tools_needed'):
            print(f"Tools: {result['tools_needed']}")
        
        if "washingmachine" in test_message:
            if result['intent_type'] == 'contract' and result['confidence'] >= 0.6:
                print("✅ PASS: Purchase intent correctly classified")
            else:
                print(f"❌ FAIL: Expected contract intent with confidence >= 0.6")

if __name__ == "__main__":
    test_intent_extraction()
