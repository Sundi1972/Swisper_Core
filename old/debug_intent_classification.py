#!/usr/bin/env python3
"""Debug script to test intent classification for specific queries"""
import os
import sys
sys.path.append('.')

os.environ['OPENAI_API_KEY'] = os.environ.get('OpenAI_API_Key', '')

from orchestrator.intent_extractor import extract_user_intent
from orchestrator.volatility_classifier import classify_entity_category
from orchestrator.prompt_preprocessor import has_temporal_cue

def debug_query(query):
    """Debug a specific query through the intent classification pipeline"""
    print(f"=== Debugging Query: '{query}' ===\n")
    
    print("1. Volatility Classification:")
    try:
        volatility_result = classify_entity_category(query)
        print(f"   Volatility: {volatility_result['volatility']}")
        print(f"   Reason: {volatility_result['reason']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        volatility_result = {"volatility": "unknown", "reason": f"Error: {e}"}
    
    print("\n2. Temporal Cue Detection:")
    try:
        temporal_cue = has_temporal_cue(query)
        print(f"   Has temporal cue: {temporal_cue}")
    except Exception as e:
        print(f"   ERROR: {e}")
        temporal_cue = False
    
    print("\n3. Full Intent Extraction:")
    try:
        result = extract_user_intent(query)
        print(f"   Intent type: {result['intent_type']}")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
        print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
        print(f"   Volatility level: {result.get('volatility_level', 'N/A')}")
        print(f"   Requires websearch: {result.get('requires_websearch', 'N/A')}")
        
        expected_intent = "websearch" if temporal_cue or volatility_result['volatility'] == 'volatile' else "chat"
        actual_intent = result['intent_type']
        
        print(f"\n4. Analysis:")
        print(f"   Expected intent: {expected_intent}")
        print(f"   Actual intent: {actual_intent}")
        print(f"   Match: {'✅ YES' if expected_intent == actual_intent else '❌ NO'}")
        
        if expected_intent != actual_intent:
            print(f"   Issue: Query with volatility='{volatility_result['volatility']}' and temporal_cue={temporal_cue} should route to {expected_intent}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    debug_query("who is the current german finance minister")
    
    debug_query("Who is Angela Merkel")
    debug_query("Who are the ministers of German government")
    debug_query("Latest news about German politics")
