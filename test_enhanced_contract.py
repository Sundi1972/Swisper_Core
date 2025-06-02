#!/usr/bin/env python3
"""Test script for enhanced contract flow"""

import sys
import asyncio
sys.path.insert(0, '.')

from contract_engine.contract_engine import ContractStateMachine

async def test_enhanced_flow():
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.fill_parameters({
        "product": "GPU RTX 4090",
        "session_id": "test_enhanced_123",
        "product_threshold": 5
    })
    
    print("=== Testing Enhanced Contract Flow ===")
    
    result = fsm.next()
    print(f"Step 1 - Start: {result}")
    
    if "ask_user" in result:
        print(f"Step 2 - Clarification asked: {result['ask_user']}")
        
        result = fsm.next("I need a GPU with good cooling and under 1000 CHF, compatible with my motherboard")
        print(f"Step 3 - After preferences: {result}")
        
        while "ask_user" in result and "confirm" not in result.get("ask_user", "").lower():
            result = fsm.next("yes")
            print(f"Next step: {result}")
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_enhanced_flow())
