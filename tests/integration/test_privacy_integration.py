import pytest
from unittest.mock import patch, MagicMock
from contract_engine.memory.memory_manager import MemoryManager

@patch('contract_engine.privacy.pii_redactor.pii_redactor')
def test_t5_summarization_with_pii_protection(mock_pii_redactor):
    """Test T5 summarization with PIIRedactor protection"""
    mock_pii_redactor.redact.return_value = "Contact [REDACTED_EMAIL] for laptop recommendations"
    
    from contract_engine.pipelines.rolling_summariser import summarize_messages
    
    messages = [
        {"content": "Contact john@example.com for laptop recommendations"},
        {"content": "Budget is around 2000 CHF"}
    ]
    
    with patch('contract_engine.pipelines.rolling_summariser.create_rolling_summariser_pipeline') as mock_pipeline:
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.run.return_value = {
            "Summarizer": ["User seeks laptop recommendations within 2000 CHF budget"]
        }
        
        summary = summarize_messages(messages)
        
        mock_pii_redactor.redact.assert_called_once()
        assert summary == "User seeks laptop recommendations within 2000 CHF budget"

@patch('contract_engine.privacy.pii_redactor.pii_redactor')
def test_milvus_semantic_memory_privacy_protection(mock_pii_redactor):
    """Test Milvus semantic memory with PIIRedactor protection"""
    mock_pii_redactor.is_text_safe_for_storage.return_value = False
    mock_pii_redactor.redact.return_value = "Contact [EMAIL_abc123] for details"
    
    from contract_engine.memory.milvus_store import MilvusSemanticStore
    
    with patch('contract_engine.memory.milvus_store.connections'), \
         patch('contract_engine.memory.milvus_store.Collection'), \
         patch('contract_engine.memory.milvus_store.SentenceTransformer'), \
         patch('contract_engine.memory.milvus_store.utility'):
        
        store = MilvusSemanticStore()
        
        store.collection = MagicMock()
        store.embedding_model = MagicMock()
        store.embedding_model.encode.return_value = [[0.1] * 384]
        
        result = store.add_memory("user123", "Contact john@example.com for details", "preference")
        
        mock_pii_redactor.is_text_safe_for_storage.assert_called_once()
        mock_pii_redactor.redact.assert_called_once()
        
        store.collection.insert.assert_called_once()
        insert_data = store.collection.insert.call_args[0][0][0]
        assert insert_data["content"] == "Contact [EMAIL_abc123] for details"

def test_gdpr_endpoints_integration():
    """Test GDPR compliance endpoints"""
    from fastapi.testclient import TestClient
    from gateway.main import app
    
    client = TestClient(app)
    
    with patch('contract_engine.memory.milvus_store.milvus_semantic_store') as mock_milvus, \
         patch('contract_engine.privacy.audit_store.audit_store') as mock_audit:
        
        mock_milvus.get_user_memory_stats.return_value = {"total_memories": 5}
        mock_audit.get_user_artifacts.return_value = []
        mock_audit.s3_client = MagicMock()
        
        response = client.get("/api/privacy/memories/test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user"
        assert "semantic_memories" in data
        assert "audit_artifacts" in data

def test_business_use_case_pii_scenarios():
    """Test business-critical PII scenarios"""
    from contract_engine.privacy.pii_redactor import PIIRedactor
    
    redactor = PIIRedactor(use_ner=True, use_llm_fallback=False)
    
    business_text = """
    Customer John Smith (john.smith@company.com) called about order #12345.
    His phone number +41 44 123 45 67 is on file.
    Payment was made with card ending in 1234.
    """
    
    redacted = redactor.redact(business_text, "hash")
    
    assert "john.smith@company.com" not in redacted
    assert "+41 44 123 45 67" not in redacted
    assert "John Smith" not in redacted
    
    assert "order #12345" in redacted
    assert "Customer" in redacted
    assert "called about" in redacted

def test_switzerland_hosting_compliance():
    """Test that all processing is local for Switzerland hosting"""
    from contract_engine.privacy.pii_redactor import PIIRedactor
    
    redactor = PIIRedactor(use_ner=True, use_llm_fallback=False)
    
    assert redactor.use_llm_fallback == False
    assert redactor.llm_client is None
    
    text = "Contact john@example.com or +41 44 123 45 67"
    redacted = redactor.redact(text)
    
    assert "john@example.com" not in redacted
    assert "+41 44 123 45 67" not in redacted
