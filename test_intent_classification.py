#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator.intent_extractor import extract_user_intent, load_available_tools, load_available_contracts
import json

def test_intent_classification():
    """Test intent classification with specific test cases"""
    
    print("Loading available tools and contracts...")
    try:
        available_tools = load_available_tools()
        available_contracts = load_available_contracts()
        print(f"Loaded {len(available_tools)} tools and {len(available_contracts)} contracts")
    except Exception as e:
        print(f"Error loading tools/contracts: {e}")
        available_tools = {}
        available_contracts = {}
    
    test_cases = [
        {
            "input": "who are the ministers of the newly elected german government",
            "expected": "websearch",
            "reason": "Current events query about government"
        },
        {
            "input": "Search the web for the latest news", 
            "expected": "websearch",
            "reason": "Explicit web search request"
        },
        {
            "input": "What is the capital of italy",
            "expected": "chat", 
            "reason": "General knowledge question"
        },
        {
            "input": "I am feeling down and depressed",
            "expected": "chat",
            "reason": "Personal/emotional statement"
        },
        {
            "input": "I want to purchase a graphics card",
            "expected": "contract",
            "reason": "Purchase intent with 'purchase' keyword"
        },
        {
            "input": "I want to buy a washing machine",
            "expected": "contract", 
            "reason": "Purchase intent with 'buy' keyword"
        }
    ]
    
    print("\n" + "="*80)
    print("INTENT CLASSIFICATION TEST RESULTS")
    print("="*80)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['input']}")
        print(f"Expected: {test_case['expected']} ({test_case['reason']})")
        
        try:
            intent_result = extract_user_intent(test_case['input'])
            
            actual_intent = intent_result.get('intent_type', 'unknown')
            confidence = intent_result.get('confidence', 0.0)
            reasoning = intent_result.get('reasoning', 'No reasoning provided')
            
            if actual_intent == "contract":
                contract_template = intent_result.get('contract_template', 'none')
                if contract_template == "purchase_item.yaml":
                    actual_intent = "contract (purchase_item)"
            
            if actual_intent == "websearch" or (actual_intent == "tool_usage" and "websearch" in str(intent_result)):
                actual_intent = "websearch"
            
            if test_case['expected'] == "contract":
                success = actual_intent.startswith("contract")
            elif test_case['expected'] == "websearch":
                success = actual_intent == "websearch"
            else:
                success = actual_intent == test_case['expected']
            
            status = "✅ PASS" if success else "❌ FAIL"
            
            print(f"Actual: {actual_intent} (confidence: {confidence:.2f})")
            print(f"Reasoning: {reasoning}")
            print(f"Result: {status}")
            
            results.append({
                "test_case": i,
                "input": test_case['input'],
                "expected": test_case['expected'],
                "actual": actual_intent,
                "confidence": confidence,
                "success": success,
                "reasoning": reasoning
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_case": i,
                "input": test_case['input'],
                "expected": test_case['expected'],
                "actual": "ERROR",
                "confidence": 0.0,
                "success": False,
                "reasoning": str(e)
            })
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed < total:
        print("\n❌ FAILED TESTS:")
        for r in results:
            if not r['success']:
                print(f"  - Test {r['test_case']}: '{r['input']}'")
                print(f"    Expected: {r['expected']}, Got: {r['actual']}")
                print(f"    Reasoning: {r['reasoning']}")
    
    print("\n📊 DETAILED RESULTS:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"{status} Test {r['test_case']}: {r['expected']} -> {r['actual']} (conf: {r['confidence']:.2f})")
    
    return results

if __name__ == "__main__":
    test_intent_classification()
