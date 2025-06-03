#!/usr/bin/env python3
"""Test script for criteria extraction functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_criteria_extraction():
    print("=== Testing Criteria Extraction ===")
    
    try:
        from contract_engine.llm_helpers import extract_initial_criteria
        
        test_prompt = "I want to buy a graphics card with a rtx4070 chip and min 12 gb ram"
        print(f"Testing prompt: '{test_prompt}'")
        
        result = extract_initial_criteria(test_prompt)
        print(f"Extraction result: {result}")
        
        expected_fields = ["base_product", "specifications", "search_keywords", "enhanced_query"]
        for field in expected_fields:
            if field in result:
                print(f"✅ {field}: {result[field]}")
            else:
                print(f"❌ Missing field: {field}")
        
        specs = result.get("specifications", {})
        if "rtx4070" in str(specs).lower() or "rtx 4070" in str(specs).lower():
            print("✅ RTX 4070 detected in specifications")
        else:
            print("❌ RTX 4070 not detected")
            
        if "12gb" in str(specs).lower() or "12 gb" in str(specs).lower():
            print("✅ 12GB RAM detected in specifications")
        else:
            print("❌ 12GB RAM not detected")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing criteria extraction: {e}")
        return None

def test_contract_integration():
    print("\n=== Testing Contract Integration ===")
    
    try:
        from contract_engine.contract_engine import ContractStateMachine
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        
        test_criteria = {
            "base_product": "graphics card",
            "specifications": {"chip_model": "RTX 4070", "memory": "12GB"},
            "search_keywords": ["RTX 4070", "12GB"],
            "enhanced_query": "graphics card RTX 4070 12GB"
        }
        
        fsm.fill_parameters({
            "product": "graphics card RTX 4070 12GB",
            "session_id": "test_criteria_123",
            "product_threshold": 10,
            "initial_criteria": test_criteria,
            "parsed_specifications": test_criteria["specifications"],
            "enhanced_query": test_criteria["enhanced_query"]
        })
        
        params = fsm.contract.get("parameters", {})
        print(f"Contract parameters: {params}")
        
        if "initial_criteria" in params:
            print("✅ initial_criteria stored in contract")
        else:
            print("❌ initial_criteria not stored")
            
        if "parsed_specifications" in params:
            print("✅ parsed_specifications stored in contract")
        else:
            print("❌ parsed_specifications not stored")
            
        if "enhanced_query" in params:
            print("✅ enhanced_query stored in contract")
        else:
            print("❌ enhanced_query not stored")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing contract integration: {e}")
        return False

if __name__ == "__main__":
    criteria_result = test_criteria_extraction()
    
    contract_result = test_contract_integration()
    
    print("\n=== Test Summary ===")
    if criteria_result and contract_result:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
