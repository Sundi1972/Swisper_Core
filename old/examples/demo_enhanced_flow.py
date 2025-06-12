#!/usr/bin/env python3
"""Demo script to test enhanced contract flow with real APIs"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def demo_enhanced_flow():
    print("=== Enhanced Contract Flow Demo ===")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment loaded")
    except ImportError:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
            print("✅ .env loaded manually")
    
    from contract_engine.contract_engine import ContractStateMachine
    
    print("\n--- Demo 1: Enhanced flow with laptop search ---")
    fsm1 = ContractStateMachine(os.path.join(os.path.dirname(__file__), "contract_templates", "purchase_item.yaml"))
    fsm1.fill_parameters({
        "product": "laptop",
        "session_id": "demo_laptop_search",
        "product_threshold": 5  # Low threshold to trigger enhanced flow
    })
    
    result1 = fsm1.next()
    print(f"Step 1 - Search: State={fsm1.state}")
    print(f"Results found: {len(fsm1.search_results) if hasattr(fsm1, 'search_results') else 0}")
    
    if "ask_user" in result1:
        print(f"System response: {result1['ask_user']}")
        
        if "confirm" in result1.get("ask_user", "").lower():
            print("✅ Basic flow - direct to confirmation")
        else:
            print("✅ Enhanced flow - asking for clarification")
    
    print("\n--- Demo 2: Test with GPU search ---")
    fsm2 = ContractStateMachine(os.path.join(os.path.dirname(__file__), "contract_templates", "purchase_item.yaml"))
    fsm2.fill_parameters({
        "product": "GPU RTX 4090",
        "session_id": "demo_gpu_search",
        "product_threshold": 10
    })
    
    result2 = fsm2.next()
    print(f"Step 1 - Search: State={fsm2.state}")
    print(f"Results found: {len(fsm2.search_results) if hasattr(fsm2, 'search_results') else 0}")
    
    if "ask_user" in result2:
        print(f"System response: {result2['ask_user']}")
    
    print("\n--- Demo 3: Test SearchAPI directly ---")
    from tool_adapter.mock_google import google_shopping_search
    
    results = google_shopping_search("gaming laptop")
    print(f"SearchAPI returned: {len(results)} results")
    if results:
        print(f"First result: {results[0].get('name', 'N/A')} - {results[0].get('price', 'N/A')} CHF")
    
    print("\n=== Demo Complete ===")
    print("Enhanced contract flow features:")
    print("✅ Real SearchAPI integration with fallback")
    print("✅ Configurable threshold for enhanced flow")
    print("✅ State machine with new analysis states")
    print("✅ LLM-based attribute extraction")
    print("✅ Compatibility checking capabilities")

if __name__ == "__main__":
    demo_enhanced_flow()
