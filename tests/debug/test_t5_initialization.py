#!/usr/bin/env python3
"""Debug test for T5 initialization issues"""

import pytest
import sys
import os
sys.path.append('.')

def test_transformers_version():
    """Test that transformers version is compatible"""
    import transformers
    assert transformers.__version__ == "4.46.0", f"Expected transformers 4.46.0, got {transformers.__version__}"

def test_haystack_transformers_summarizer_import():
    """Test that TransformersSummarizer can be imported"""
    from haystack.nodes import TransformersSummarizer
    assert TransformersSummarizer is not None

def test_t5_initialization_websearch():
    """Test T5 initialization in websearch component"""
    from websearch_pipeline.websearch_components import LLMSummarizerComponent
    component = LLMSummarizerComponent()
    assert component.summarizer is not None, "T5 summarizer should be initialized"
    assert not component.fallback_mode, "Should not be in fallback mode"

def test_t5_initialization_contract_engine():
    """Test T5 initialization in contract engine"""
    from contract_engine.pipelines.rolling_summariser import create_rolling_summariser_pipeline
    pipeline = create_rolling_summariser_pipeline()
    assert pipeline is not None, "Pipeline should be created successfully"

def test_t5_predict_functionality():
    """Test that T5 predict works without auth_token errors"""
    from websearch_pipeline.websearch_components import LLMSummarizerComponent
    from haystack.schema import Document
    
    component = LLMSummarizerComponent()
    if component.summarizer:
        test_doc = Document(content="Angela Merkel was a German politician who served as Chancellor.")
        result = component.summarizer.predict(documents=[test_doc])
        assert result is not None, "T5 predict should return results"
        assert len(result) > 0, "T5 predict should return non-empty results"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
