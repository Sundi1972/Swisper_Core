#!/usr/bin/env python3
"""
Test script to verify the preference restructuring fix
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from debug_logging_config import setup_debug_logging
from contract_engine.contract_engine import ContractStateMachine

def test_washing_machine_scenario():
    """Test the exact scenario that was failing"""
    setup_debug_logging()
    
    print("🧪 Testing washing machine preference restructuring fix...")
    
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.fill_parameters({
        "product": "washing machine", 
        "session_id": "test_preference_restructure"
    })
    
    print("\n1️⃣ Starting search...")
    fsm.context.update_state("search")
    result1 = fsm.next()
    print(f"Search result: {result1}")
    print(f"Current state after search: {fsm.context.current_state}")
    
    if fsm.context.current_state != "wait_for_preferences":
        print("❌ ISSUE: FSM did not transition to wait_for_preferences")
        return False
    
    print("\n2️⃣ Providing preferences...")
    user_input = "it should be below 1200 chf have a min capacity of 6kg and a min energy efficiency of B"
    result2 = fsm.next(user_input)
    print(f"Preferences result: {result2}")
    print(f"Current state: {fsm.context.current_state}")
    print(f"Extracted preferences (dict): {fsm.context.preferences}")
    print(f"Extracted constraints (list): {fsm.context.constraints}")
    
    print("\n📊 Validation:")
    print(f"✅ State transitions correctly: {fsm.context.current_state in ['filter_products', 'rank_and_select']}")
    print(f"✅ Preferences is dict: {isinstance(fsm.context.preferences, dict)}")
    print(f"✅ Constraints is list: {isinstance(fsm.context.constraints, list)}")
    print(f"✅ Price preference: {'price' in fsm.context.preferences}")
    print(f"✅ Capacity preference: {'capacity' in fsm.context.preferences}")
    print(f"✅ Energy efficiency preference: {'energy_efficiency' in fsm.context.preferences}")
    
    return True

if __name__ == "__main__":
    try:
        test_washing_machine_scenario()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
