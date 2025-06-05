import os
import sys
import json
sys.path.append('.')

from orchestrator.intent_extractor import _generate_routing_manifest, _classify_intent_with_llm

def test_intent_classification():
    print("=== Testing Intent Classification ===")
    
    os.environ['OPENAI_API_KEY'] = os.environ.get('OpenAI_API_Key', '')
    
    manifest = _generate_routing_manifest()
    print("Routing manifest generated successfully")
    
    test_message = "I want to buy a washingmachine under 1200 chf"
    print(f"\nTesting message: '{test_message}'")
    
    try:
        result = _classify_intent_with_llm(test_message, manifest)
        print(f"Classification successful: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Classification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_intent_classification()
