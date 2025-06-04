import pytest
from unittest.mock import patch, MagicMock
from contract_engine.pipelines.rolling_summariser import create_rolling_summariser_pipeline, summarize_messages

def test_rolling_summariser_pipeline_creation():
    """Test T5 pipeline creation"""
    with patch('contract_engine.pipelines.rolling_summariser.TransformersSummarizer') as mock_summarizer:
        with patch('contract_engine.pipelines.rolling_summariser.PreProcessor') as mock_preprocessor:
            mock_summarizer_instance = MagicMock()
            mock_summarizer_instance._component_config = {"type": "TransformersSummarizer"}
            mock_summarizer.return_value = mock_summarizer_instance
            
            mock_preprocessor_instance = MagicMock()
            mock_preprocessor_instance._component_config = {"type": "PreProcessor"}
            mock_preprocessor.return_value = mock_preprocessor_instance
            
            with patch('haystack.pipelines.Pipeline.add_node'):
                pipeline = create_rolling_summariser_pipeline()
                assert pipeline is not None
                mock_summarizer.assert_called_once()
                mock_preprocessor.assert_called_once()

def test_summarize_messages_basic():
    """Test basic message summarization"""
    messages = [
        {"content": "User wants to buy a laptop for programming"},
        {"content": "Budget is around 1000 dollars"},
        {"content": "Prefers lightweight and good battery life"}
    ]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {
            "Summarizer": [{"summary": "User seeks programming laptop under $1000 with portability"}]
        }
        
        summary = summarize_messages(messages)
        assert "programming laptop" in summary.lower()
        assert len(summary) > 0

def test_summarize_messages_empty():
    """Test summarization with empty messages"""
    summary = summarize_messages([])
    assert summary == ""

def test_summarize_messages_short_content():
    """Test summarization with content too short to summarize"""
    messages = [{"content": "Short"}]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {"Summarizer": []}  # Empty result
        
        summary = summarize_messages(messages)
        assert summary == "Short"

def test_summarize_messages_fallback():
    """Test fallback when T5 pipeline fails"""
    messages = [{"content": "Test message " * 50}]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline.side_effect = Exception("T5 failed")
        
        summary = summarize_messages(messages)
        assert summary.endswith("...")
        assert len(summary) <= 203

def test_summarize_messages_invalid_pipeline_output():
    """Test handling of invalid pipeline output"""
    messages = [{"content": "Test message"}]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {"Summarizer": []}
        
        summary = summarize_messages(messages)
        assert summary == "Test message"

def test_summarize_messages_string_output():
    """Test handling of string output from pipeline"""
    messages = [{"content": "Test message"}]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {
            "Summarizer": ["Direct string summary"]
        }
        
        summary = summarize_messages(messages)
        assert summary == "Direct string summary"

@patch('contract_engine.pipelines.rolling_summariser.TransformersSummarizer')
@patch('contract_engine.pipelines.rolling_summariser.PreProcessor')
def test_pipeline_configuration(mock_preprocessor, mock_summarizer):
    """Test pipeline component configuration"""
    mock_summarizer_instance = MagicMock()
    mock_summarizer_instance._component_config = {"type": "TransformersSummarizer"}
    mock_summarizer.return_value = mock_summarizer_instance
    
    mock_preprocessor_instance = MagicMock()
    mock_preprocessor_instance._component_config = {"type": "PreProcessor"}
    mock_preprocessor.return_value = mock_preprocessor_instance
    
    with patch('haystack.pipelines.Pipeline.add_node'):
        pipeline = create_rolling_summariser_pipeline()
        
        mock_summarizer.assert_called_with(
            model_name_or_path='t5-small',
            use_gpu=False,
            max_length=150,
            min_length=30,
            do_sample=False,
            num_beams=2,
            early_stopping=True
        )
        
        mock_preprocessor.assert_called_with(
            split_by='sentence',
            split_length=10,
            split_overlap=2,
            max_seq_len=512,
            split_respect_sentence_boundary=True
        )

def test_summarize_messages_mixed_content():
    """Test summarization with mixed message types"""
    messages = [
        {"content": "User message", "role": "user"},
        {"content": "Assistant response", "role": "assistant"},
        {"invalid": "message"},
        {"content": 123},
        {"content": ""}
    ]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {
            "Summarizer": [{"summary": "Mixed content summary"}]
        }
        
        summary = summarize_messages(messages)
        assert summary == "Mixed content summary"
