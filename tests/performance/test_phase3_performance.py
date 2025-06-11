import pytest
import time
from unittest.mock import patch, MagicMock
from contract_engine.pipelines.rolling_summariser import summarize_messages
from contract_engine.memory.milvus_store import MilvusSemanticStore

def test_t5_summarization_performance():
    """Test T5 summarization meets <200ms SLA"""
    messages = [
        {"content": "User wants to buy a laptop for programming and gaming"},
        {"content": "Budget is flexible but prefers under 1500 dollars"},
        {"content": "Needs good graphics card and fast processor"},
        {"content": "Portability is important for travel"},
        {"content": "Battery life should be at least 6 hours"}
    ]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {
            "Summarizer": [{"summary": "User seeks gaming/programming laptop under $1500 with portability"}]
        }
        
        start_time = time.time()
        summary = summarize_messages(messages)
        end_time = time.time()
        
        summarization_time = (end_time - start_time) * 1000
        assert summarization_time < 200
        assert len(summary) > 0

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_semantic_search_performance(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test semantic search performance"""
    mock_embedding_model = MagicMock()
    mock_embedding_model.encode.return_value = [[0.1] * 384]
    mock_sentence_transformer.return_value = mock_embedding_model
    
    mock_collection_instance = MagicMock()
    mock_collection_instance.search.return_value = [[]]
    mock_collection.return_value = mock_collection_instance
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    
    start_time = time.time()
    memories = store.search_memories("user123", "laptop preferences", top_k=3)
    end_time = time.time()
    
    search_time = (end_time - start_time) * 1000
    assert search_time < 100
    assert isinstance(memories, list)

def test_sentence_transformers_embedding_performance():
    """Test sentence-transformers embedding performance"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_instance = MagicMock()
        mock_instance.encode.return_value = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
        mock_model.return_value = mock_instance
        
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        test_texts = [
            "User prefers gaming laptops with high-end graphics",
            "Budget constraint of 1000 dollars maximum",
            "Needs laptop for programming and development work"
        ]
        
        start_time = time.time()
        embeddings = model.encode(test_texts)
        end_time = time.time()
        
        encoding_time = (end_time - start_time) * 1000
        assert encoding_time < 50
        assert len(embeddings) == 3

def test_memory_manager_enhanced_context_performance():
    """Test Memory Manager enhanced context performance"""
    from contract_engine.memory.memory_manager import MemoryManager
    
    memory_manager = MemoryManager()
    
    with patch.object(memory_manager, 'get_context') as mock_get_context:
        mock_get_context.return_value = {
            "buffer_messages": [{"content": f"Message {i}"} for i in range(10)],
            "current_summary": "Test summary",
            "total_tokens": 500
        }
        
        with patch.object(memory_manager, 'get_semantic_context') as mock_semantic:
            mock_semantic.return_value = [
                {"content": "Semantic memory 1", "similarity_score": 0.9},
                {"content": "Semantic memory 2", "similarity_score": 0.8}
            ]
            
            start_time = time.time()
            context = memory_manager.get_enhanced_context("session123", "user123", "test query")
            end_time = time.time()
            
            context_time = (end_time - start_time) * 1000
            assert context_time < 50
            assert "semantic_memories" in context
            assert len(context["semantic_memories"]) == 2

def test_concurrent_summarization_performance():
    """Test concurrent T5 summarization performance"""
    import threading
    import concurrent.futures
    
    def summarize_test_messages():
        messages = [{"content": f"Test message {i} for concurrent processing"} for i in range(5)]
        
        with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
            mock_pipeline_instance = MagicMock()
            mock_pipeline.return_value = mock_pipeline_instance
            mock_pipeline_instance.run.return_value = {
                "Summarizer": [{"summary": "Concurrent test summary"}]
            }
            
            return summarize_messages(messages)
    
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(summarize_test_messages) for _ in range(3)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    end_time = time.time()
    
    total_time = (end_time - start_time) * 1000
    assert total_time < 600
    assert len(results) == 3
    assert all("summary" in result for result in results)
