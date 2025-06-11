#!/usr/bin/env python3
"""Performance test script for enhanced T5 summarization"""
import os
import sys
import time
sys.path.append('.')

from websearch_pipeline.websearch_components import LLMSummarizerComponent


def test_t5_performance_with_enhanced_parameters():
    """Test T5 performance with increased token limits"""
    print("=== Testing Enhanced T5 Performance ===\n")
    
    component = LLMSummarizerComponent()
    
    test_cases = [
        {
            "name": "Short content",
            "results": [
                {"title": "Test 1", "snippet": "Short snippet", "full_content": "Short content about the topic"},
                {"title": "Test 2", "snippet": "Another snippet", "full_content": "More short content"}
            ]
        },
        {
            "name": "Medium content", 
            "results": [
                {"title": "Test 1", "snippet": "Medium snippet", "full_content": "Medium length content " * 50},
                {"title": "Test 2", "snippet": "Another snippet", "full_content": "More medium content " * 50}
            ]
        },
        {
            "name": "Long content",
            "results": [
                {"title": "Test 1", "snippet": "Long snippet", "full_content": "Long detailed content " * 200},
                {"title": "Test 2", "snippet": "Another snippet", "full_content": "More long content " * 200}
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"Testing {test_case['name']}:")
        
        start_time = time.time()
        result, _ = component.run(test_case["results"], "test query")
        end_time = time.time()
        
        execution_time = (end_time - start_time) * 1000
        
        print(f"  Execution time: {execution_time:.2f}ms")
        print(f"  Summary length: {len(result['summary'])} characters")
        print(f"  SLA compliance: {'✅ PASS' if execution_time < 200 else '❌ FAIL'}")
        print(f"  Summary preview: {result['summary'][:100]}...")
        print()
    
    print("Performance testing completed.")


if __name__ == "__main__":
    test_t5_performance_with_enhanced_parameters()
