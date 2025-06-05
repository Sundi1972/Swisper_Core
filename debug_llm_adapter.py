import os
import sys
sys.path.append('.')

from orchestrator.llm_adapter import get_llm_adapter

def test_llm_adapter():
    print("=== Testing LLM Adapter ===")
    
    os.environ['OPENAI_API_KEY'] = os.environ.get('OpenAI_API_Key', '')
    print(f"API Key set: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
    
    try:
        adapter = get_llm_adapter()
        print(f"Adapter initialized: {adapter.client is not None}")
        print(f"Adapter type: {type(adapter).__name__}")
    except Exception as e:
        print(f"Adapter initialization failed: {e}")
        return
    
    print("\n=== Testing Simple Completion ===")
    try:
        response = adapter.chat_completion([
            {'role': 'user', 'content': 'Respond with just the word TEST'}
        ])
        print(f"Response: {repr(response)}")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(response) if response else 0}")
    except Exception as e:
        print(f"Simple completion failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testing JSON Completion ===")
    try:
        response = adapter.chat_completion([
            {'role': 'system', 'content': 'Respond with valid JSON only: {"test": "value"}'},
            {'role': 'user', 'content': 'Give me a JSON response'}
        ])
        print(f"JSON Response: {repr(response)}")
        
        import json
        parsed = json.loads(response)
        print(f"JSON parsed successfully: {parsed}")
    except Exception as e:
        print(f"JSON completion failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_adapter()
