#!/usr/bin/env python3
"""Test script to verify intent detection consistency across multiple queries in the same session"""
import os
import sys
import requests
import json
import time
sys.path.append('.')

os.environ['OPENAI_API_KEY'] = os.environ.get('OpenAI_API_Key', '')

def test_consecutive_intent_detections():
    """Test two consecutive intent detections in the same session via /chat endpoint"""
    print("=== Testing Consecutive Intent Detections in Same Session ===\n")
    
    base_url = "http://localhost:8000"
    
    test_queries = [
        {
            "query": "Who is Angela Merkel",
            "expected_intent": "chat",
            "description": "Historical biographical query (should route to chat)"
        },
        {
            "query": "who is the current german finance minister", 
            "expected_intent": "websearch",
            "description": "Time-sensitive government position query (should route to websearch)"
        }
    ]
    
    session_results = []
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"Query {i}: {test_case['description']}")
        print(f"Testing: '{test_case['query']}'")
        print(f"Expected intent: {test_case['expected_intent']}")
        
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={"messages": [{"role": "user", "content": test_case['query']}]},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                reply = result.get('reply', '')
                response_text = reply
                
                sources = []
                if "Sources:" in reply:
                    sources_text = reply.split("Sources:")[-1].strip()
                    if sources_text:
                        sources = [{"url": url.strip()} for url in sources_text.split(",") if url.strip()]
                
                has_sources = len(sources) > 0
                actual_intent = "websearch" if has_sources else "chat"
                
                print(f"  Status: ✅ SUCCESS (HTTP {response.status_code})")
                print(f"  Actual intent: {actual_intent}")
                print(f"  Has sources: {has_sources}")
                print(f"  Sources count: {len(sources)}")
                print(f"  Response length: {len(response_text)} chars")
                
                intent_match = actual_intent == test_case['expected_intent']
                print(f"  Intent match: {'✅ YES' if intent_match else '❌ NO'}")
                
                if not intent_match:
                    print(f"  ⚠️  MISMATCH: Expected {test_case['expected_intent']}, got {actual_intent}")
                
                session_results.append({
                    "query": test_case['query'],
                    "expected": test_case['expected_intent'],
                    "actual": actual_intent,
                    "match": intent_match,
                    "has_sources": has_sources,
                    "response_length": len(response_text)
                })
                
                preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                print(f"  Response preview: {preview}")
                
                if sources:
                    print(f"  Sources:")
                    for j, source in enumerate(sources[:3], 1):  # Show first 3 sources
                        print(f"    {j}. {source.get('title', 'No title')} - {source.get('url', 'No URL')}")
                
            else:
                print(f"  ❌ ERROR: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
        
        print()
        
        if i < len(test_queries):
            time.sleep(2)
    
    print("=== Session Analysis ===")
    print(f"Total queries tested: {len(session_results)}")
    
    successful_matches = sum(1 for r in session_results if r['match'])
    print(f"Successful intent matches: {successful_matches}/{len(session_results)}")
    
    if successful_matches == len(session_results):
        print("✅ ALL QUERIES ROUTED CORRECTLY IN SESSION")
    else:
        print("❌ SOME QUERIES ROUTED INCORRECTLY")
        for result in session_results:
            if not result['match']:
                print(f"  - '{result['query']}': expected {result['expected']}, got {result['actual']}")
    
    websearch_queries = [r for r in session_results if r['expected'] == 'websearch']
    chat_queries = [r for r in session_results if r['expected'] == 'chat']
    
    if websearch_queries:
        websearch_success = all(r['match'] for r in websearch_queries)
        print(f"Websearch routing consistency: {'✅ GOOD' if websearch_success else '❌ ISSUES'}")
    
    if chat_queries:
        chat_success = all(r['match'] for r in chat_queries)
        print(f"Chat routing consistency: {'✅ GOOD' if chat_success else '❌ ISSUES'}")

if __name__ == "__main__":
    test_consecutive_intent_detections()
