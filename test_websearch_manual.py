#!/usr/bin/env python3
"""Manual test script for WebSearch pipeline"""

import sys
import os
import logging

sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def test_websearch_import():
    """Test WebSearch pipeline import"""
    try:
        from websearch_pipeline.websearch_pipeline import create_websearch_pipeline
        logger.info("✓ WebSearch pipeline import successful")
        return True
    except Exception as e:
        logger.error(f"✗ WebSearch pipeline import failed: {e}")
        return False

def test_websearch_creation():
    """Test WebSearch pipeline creation"""
    try:
        from websearch_pipeline.websearch_pipeline import create_websearch_pipeline
        pipeline = create_websearch_pipeline()
        logger.info("✓ WebSearch pipeline creation successful")
        return True
    except Exception as e:
        logger.error(f"✗ WebSearch pipeline creation failed: {e}")
        return False

def test_websearch_components():
    """Test individual WebSearch components"""
    try:
        from websearch_pipeline.websearch_components import (
            SearchAPIComponent,
            DeduplicateComponent,
            SnippetFetcherComponent,
            SimilarityRankerComponent,
            LLMSummarizerComponent
        )
        
        search_comp = SearchAPIComponent(api_key=None)  # Use mock
        dedupe_comp = DeduplicateComponent()
        snippet_comp = SnippetFetcherComponent()
        rank_comp = SimilarityRankerComponent(max_results=3)
        summarize_comp = LLMSummarizerComponent()
        
        logger.info("✓ All WebSearch components created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ WebSearch components creation failed: {e}")
        return False

def test_searchapi_adapter():
    """Test SearchAPI tool adapter"""
    try:
        from tool_adapter.searchapi import searchapi_web_search
        
        results = searchapi_web_search("test query")
        logger.info(f"✓ SearchAPI adapter returned {len(results)} mock results")
        return True
    except Exception as e:
        logger.error(f"✗ SearchAPI adapter test failed: {e}")
        return False

def test_orchestrator_integration():
    """Test orchestrator integration"""
    try:
        import asyncio
        from orchestrator.core import handle
        from orchestrator.core import Message
        
        messages = [Message(role="user", content="Who are the new German ministers 2025?")]
        session_id = "test_session_websearch"
        
        result = asyncio.run(handle(messages, session_id))
        logger.info(f"✓ Orchestrator integration test completed: {result.get('reply', '')[:100]}...")
        return True
    except Exception as e:
        logger.error(f"✗ Orchestrator integration test failed: {e}")
        return False

def main():
    """Run all WebSearch tests"""
    logger.info("Starting WebSearch manual tests...")
    
    tests = [
        ("Import Test", test_websearch_import),
        ("Creation Test", test_websearch_creation),
        ("Components Test", test_websearch_components),
        ("SearchAPI Adapter Test", test_searchapi_adapter),
        ("Orchestrator Integration Test", test_orchestrator_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            if test_func():
                passed += 1
            else:
                logger.error(f"{test_name} failed")
        except Exception as e:
            logger.error(f"{test_name} crashed: {e}")
    
    logger.info(f"\n=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        logger.info("🎉 All WebSearch tests passed!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
