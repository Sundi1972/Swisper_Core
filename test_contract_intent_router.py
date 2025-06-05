#!/usr/bin/env python3
"""Test script for contract-aware intent router architecture"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

def test_contract_loading():
    """Test contract template loading with absolute paths"""
    print("=== Contract Loading Test ===")
    from orchestrator.intent_extractor import load_available_contracts
    
    contracts = load_available_contracts()
    print(f"Contracts found: {contracts}")
    
    if contracts:
        print("✅ SUCCESS: Contracts loaded successfully")
        for filename, info in contracts.items():
            print(f"  - {filename}: {info}")
    else:
        print("❌ FAIL: No contracts found")
    
    return contracts

def test_routing_manifest():
    """Test routing manifest generation"""
    print("\n=== Routing Manifest Test ===")
    from orchestrator.intent_extractor import _generate_routing_manifest
    
    manifest = _generate_routing_manifest()
    print(json.dumps(manifest, indent=2))
    
    contract_options = []
    for option in manifest.get("routing_options", []):
        if option.get("intent_type") == "contract":
            contract_options = option.get("contracts", [])
            break
    
    if contract_options:
        print("✅ SUCCESS: Contract options found in manifest")
    else:
        print("❌ FAIL: No contract options in manifest")
    
    return manifest

def test_intent_classification():
    """Test intent classification for purchase requests"""
    print("\n=== Intent Classification Test ===")
    from orchestrator.intent_extractor import extract_user_intent
    
    test_cases = [
        "I want to buy a washingmachine under 1200 chf",
        "#rag What is this document about?", 
        "Compare these two graphics cards",
        "Hello, how are you today?"
    ]
    
    results = []
    for test_message in test_cases:
        print(f"\nTesting: '{test_message}'")
        try:
            result = extract_user_intent(test_message)
            print(f"Intent: {result['intent_type']}")
            print(f"Confidence: {result['confidence']}")
            print(f"Contract Template: {result.get('contract_template')}")
            print(f"Reasoning: {result['reasoning']}")
            
            results.append((test_message, result))
            
            if "washingmachine" in test_message:
                if result['intent_type'] == 'contract' and result['confidence'] >= 0.6:
                    print("✅ PASS: Purchase intent correctly classified")
                else:
                    print(f"❌ FAIL: Expected contract intent with confidence >= 0.6")
                    print(f"  Got: {result['intent_type']} with confidence {result['confidence']}")
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((test_message, {"error": str(e)}))
    
    return results

def main():
    """Run all tests"""
    print("🧪 Testing Contract-Aware Intent Router Architecture")
    print("=" * 60)
    
    os.environ["OPENAI_API_KEY"] = os.getenv("OpenAI_API_Key", "")
    os.environ["SEARCHAPI_API_KEY"] = os.getenv("SearchAPI_API_Key", "")
    
    if not os.environ["OPENAI_API_KEY"]:
        print("❌ WARNING: OpenAI API key not found")
    
    try:
        contracts = test_contract_loading()
        
        manifest = test_routing_manifest()
        
        results = test_intent_classification()
        
        print("\n" + "=" * 60)
        print("🎯 SUMMARY")
        print("=" * 60)
        
        if contracts:
            print("✅ Contract loading: WORKING")
        else:
            print("❌ Contract loading: FAILED")
            
        contract_options = []
        for option in manifest.get("routing_options", []):
            if option.get("intent_type") == "contract":
                contract_options = option.get("contracts", [])
                break
                
        if contract_options:
            print("✅ Routing manifest: WORKING")
        else:
            print("❌ Routing manifest: FAILED")
            
        washing_machine_result = None
        for test_message, result in results:
            if "washingmachine" in test_message and "error" not in result:
                washing_machine_result = result
                break
                
        if (washing_machine_result and 
            washing_machine_result['intent_type'] == 'contract' and 
            washing_machine_result['confidence'] >= 0.6):
            print("✅ Purchase intent classification: WORKING")
            print("🎉 CONTRACT-AWARE INTENT ROUTER IS READY!")
        else:
            print("❌ Purchase intent classification: FAILED")
            if washing_machine_result:
                print(f"  Expected: contract intent with confidence >= 0.6")
                print(f"  Got: {washing_machine_result['intent_type']} with confidence {washing_machine_result['confidence']}")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
