import pytest
from unittest.mock import patch, MagicMock
from contract_engine.memory.milvus_store import MilvusSemanticStore

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_milvus_store_initialization(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test Milvus store initialization"""
    mock_sentence_transformer.return_value = MagicMock()
    mock_collection.return_value = MagicMock()
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    assert store.collection is not None
    assert store.embedding_model is not None
    mock_connections.connect.assert_called_once()

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_add_memory(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test adding memory to Milvus"""
    mock_embedding_model = MagicMock()
    import numpy as np
    mock_embedding_model.encode.return_value = np.array([[0.1] * 384])
    mock_sentence_transformer.return_value = mock_embedding_model
    
    mock_collection_instance = MagicMock()
    mock_collection.return_value = mock_collection_instance
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    result = store.add_memory("user123", "Likes gaming laptops", "preference")
    
    assert result is True
    mock_collection_instance.insert.assert_called_once()
    mock_collection_instance.flush.assert_called_once()

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_search_memories(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test searching memories in Milvus"""
    mock_embedding_model = MagicMock()
    import numpy as np
    mock_embedding_model.encode.return_value = np.array([[0.1] * 384])
    mock_sentence_transformer.return_value = mock_embedding_model
    
    mock_collection_instance = MagicMock()
    mock_hit = MagicMock()
    mock_hit.score = 0.8
    mock_hit.entity.get.side_effect = lambda key, default=None: {
        "content": "User prefers gaming laptops",
        "metadata": '{"type": "preference"}',
        "timestamp": 1234567890
    }.get(key, default)
    
    mock_collection_instance.search.return_value = [[mock_hit]]
    mock_collection.return_value = mock_collection_instance
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    memories = store.search_memories("user123", "laptop preferences")
    
    assert len(memories) == 1
    assert "gaming laptops" in memories[0]["content"]
    assert memories[0]["similarity_score"] == 0.8

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_search_memories_low_similarity(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test filtering memories by similarity threshold"""
    mock_embedding_model = MagicMock()
    import numpy as np
    mock_embedding_model.encode.return_value = np.array([[0.1] * 384])
    mock_sentence_transformer.return_value = mock_embedding_model
    
    mock_collection_instance = MagicMock()
    mock_hit = MagicMock()
    mock_hit.score = 0.5
    
    mock_collection_instance.search.return_value = [[mock_hit]]
    mock_collection.return_value = mock_collection_instance
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    memories = store.search_memories("user123", "laptop preferences")
    
    assert len(memories) == 0

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_get_user_memory_stats(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test getting user memory statistics"""
    mock_sentence_transformer.return_value = MagicMock()
    
    mock_collection_instance = MagicMock()
    mock_collection_instance.query.return_value = [{"id": 1}, {"id": 2}, {"id": 3}]
    mock_collection.return_value = mock_collection_instance
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    stats = store.get_user_memory_stats("user123")
    
    assert stats["total_memories"] == 3
    assert stats["user_id"] == "user123"

def test_milvus_store_error_handling():
    """Test Milvus store error handling"""
    with patch('contract_engine.memory.milvus_store.connections') as mock_connections:
        mock_connections.connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            MilvusSemanticStore()

@patch('contract_engine.memory.milvus_store.connections')
@patch('contract_engine.memory.milvus_store.Collection')
@patch('contract_engine.memory.milvus_store.SentenceTransformer')
@patch('contract_engine.memory.milvus_store.utility')
def test_add_memory_with_metadata(mock_utility, mock_sentence_transformer, mock_collection, mock_connections):
    """Test adding memory with custom metadata"""
    mock_embedding_model = MagicMock()
    import numpy as np
    mock_embedding_model.encode.return_value = np.array([[0.1] * 384])
    mock_sentence_transformer.return_value = mock_embedding_model
    
    mock_collection_instance = MagicMock()
    mock_collection.return_value = mock_collection_instance
    mock_utility.has_collection.return_value = False
    
    store = MilvusSemanticStore()
    
    custom_metadata = {"source": "conversation", "confidence": 0.9}
    result = store.add_memory("user123", "Custom preference", "preference", custom_metadata)
    
    assert result is True
    
    insert_call = mock_collection_instance.insert.call_args[0][0][0]
    metadata = insert_call["metadata"]
    assert "source" in metadata
    assert "confidence" in metadata
