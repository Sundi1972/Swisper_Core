#!/usr/bin/env python3
"""Script to reproduce and test T5 use_auth_token error fix"""

import sys
import os
sys.path.append('.')

def test_websearch_t5_component():
    """Test T5 initialization from websearch_pipeline"""
    print("=== Testing WebSearch T5 Component ===")
    try:
        from websearch_pipeline.websearch_components import LLMSummarizerComponent
        component = LLMSummarizerComponent()
        print(f"Fallback mode: {component.fallback_mode}")
        print(f"Summarizer available: {component.summarizer is not None}")
        
        if component.summarizer:
            test_text = "Angela Merkel was a German politician who served as Chancellor."
            result = component.summarizer(test_text, max_length=50, min_length=20)
            print(f"✅ Predict successful: {result}")
            return True
        else:
            print("❌ Summarizer not available")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_contract_engine_t5_pipeline():
    """Test T5 pipeline from contract_engine"""
    print("\n=== Testing Contract Engine T5 Pipeline ===")
    try:
        from contract_engine.pipelines.rolling_summariser import create_rolling_summariser_pipeline
        from haystack.schema import Document
        
        pipeline = create_rolling_summariser_pipeline()
        
        test_documents = [Document(content="Test message for summarization. This is a longer text that needs to be summarized using T5 model.")]
        result = pipeline.run(documents=test_documents)
        print(f"✅ Pipeline successful: {result}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transformers_version():
    """Check transformers version compatibility"""
    try:
        import transformers
        print(f"Transformers version: {transformers.__version__}")
        return True
    except ImportError:
        print("❌ Transformers not available")
        return False

if __name__ == "__main__":
    print("=== T5 Error Reproduction Test ===")
    version_ok = test_transformers_version()
    websearch_ok = test_websearch_t5_component()
    contract_ok = test_contract_engine_t5_pipeline()
    print(f"\nResults: Version={version_ok}, WebSearch={websearch_ok}, Contract={contract_ok}")
    print("All tests passed!" if all([version_ok, websearch_ok, contract_ok]) else "Some tests failed!")
