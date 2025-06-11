#!/usr/bin/env python3
import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from orchestrator.core import handle, Message
from orchestrator.intent_extractor import extract_user_intent, load_available_contracts, load_available_tools
import logging

logging.basicConfig(level=logging.INFO)

async def test_complete_flow():
    print("🧪 Testing Complete Orchestrator Flow")
    
    print("\n0️⃣ Testing contract and tool loading")
    try:
        contracts = load_available_contracts()
        tools = load_available_tools()
        print(f"Available contracts: {list(contracts.keys())}")
        print(f"Available tools: {list(tools.keys()) if tools else []}")
    except Exception as e:
        print(f"Error loading contracts/tools: {e}")
    
    test_message = "I want to buy a washingmachine"
    print(f"\n1️⃣ Testing intent extraction for: '{test_message}'")
    intent_data = extract_user_intent(test_message)
    print(f"Intent: {intent_data}")
    
    print(f"\n2️⃣ Testing full orchestrator flow")
    messages = [Message(role="user", content=test_message)]
    session_id = "debug_complete_flow"
    
    try:
        result = await handle(messages, session_id)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_flow())
