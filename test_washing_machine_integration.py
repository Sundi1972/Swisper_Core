#!/usr/bin/env python3
"""
Integration test for the complete washing machine contract flow
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from debug_logging_config import setup_debug_logging
from contract_engine.contract_engine import ContractStateMachine

def test_complete_washing_machine_flow():
    """Test the complete washing machine contract flow with logging"""
    setup_debug_logging()
    
    print("🧪 Testing complete washing machine contract flow...")
    
    fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(__file__)), "contract_templates", "purchase_item.yaml"))
    fsm.fill_parameters({
        "product": "washing machine", 
        "session_id": "test_washing_machine_integration"
    })
    
    print("\n1️⃣ Starting search...")
    fsm.context.update_state("search")
    result1 = fsm.next()
    print(f"Search result: {result1}")
    print(f"Found {len(fsm.context.search_results)} products")
    
    print("\n2️⃣ Providing preferences...")
    fsm.context.update_state("wait_for_preferences")
    user_input = "Price should be below 1600 chf it should be energy efficient below B, and it should take at least 6kg of laundry"
    result2 = fsm.next(user_input)
    print(f"Preferences result: {result2}")
    print(f"Current state: {fsm.context.current_state}")
    print(f"Extracted preferences: {fsm.context.preferences}")
    print(f"Extracted constraints: {fsm.context.constraints}")
    
    if fsm.context.current_state == "filter_products":
        print("\n3️⃣ Filtering products...")
        result3 = fsm.next()
        print(f"Filter result: {result3}")
        print(f"Filtered to {len(fsm.context.search_results)} products")
    
    print("\n📊 Validation:")
    print(f"✅ Preferences extracted: {len(fsm.context.preferences) > 0}")
    print(f"✅ Constraints extracted: {len(fsm.context.constraints) > 0}")
    print(f"✅ Price constraint: {'price' in fsm.context.constraints}")
    print(f"✅ Energy efficiency constraint: {'energy_efficiency' in fsm.context.constraints}")
    print(f"✅ Capacity constraint: {'capacity' in fsm.context.constraints}")

if __name__ == "__main__":
    try:
        test_complete_washing_machine_flow()
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
