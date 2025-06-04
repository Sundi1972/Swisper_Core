import pytest
from unittest.mock import patch, MagicMock
from contract_engine.privacy.audit_store import S3AuditStore

@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    with patch('boto3.client') as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client
        yield mock_client

def test_audit_store_initialization(mock_s3_client):
    """Test S3AuditStore initialization"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'SWISPER_AUDIT_BUCKET': 'test-bucket'
    }):
        store = S3AuditStore()
        assert store.bucket_name == 'test-bucket'
        assert store.region == 'eu-central-1'
        assert store.s3_client is not None

def test_store_chat_artifact(mock_s3_client):
    """Test storing chat history artifact"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        store = S3AuditStore()
        store.s3_client = mock_s3_client
        
        chat_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        result = store.store_chat_artifact("session_123", "user_456", chat_history)
        
        assert result == True
        mock_s3_client.put_object.assert_called_once()
        
        call_args = mock_s3_client.put_object.call_args
        assert 'audit/chat/' in call_args[1]['Key']
        assert call_args[1]['ContentType'] == 'application/gzip'
        assert call_args[1]['Metadata']['session_id'] == 'session_123'
        assert call_args[1]['Metadata']['user_id'] == 'user_456'

def test_store_fsm_artifact(mock_s3_client):
    """Test storing FSM logs artifact"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        store = S3AuditStore()
        store.s3_client = mock_s3_client
        
        fsm_logs = [
            {"from_state": "search", "to_state": "refine", "timestamp": "2024-06-04T14:30:00Z"},
            {"from_state": "refine", "to_state": "complete", "timestamp": "2024-06-04T14:35:00Z"}
        ]
        
        result = store.store_fsm_artifact("session_123", "user_456", fsm_logs)
        
        assert result == True
        mock_s3_client.put_object.assert_called_once()
        
        call_args = mock_s3_client.put_object.call_args
        assert 'audit/fsm/' in call_args[1]['Key']
        assert call_args[1]['Metadata']['artifact_type'] == 'fsm_logs'

def test_store_contract_artifact(mock_s3_client):
    """Test storing contract JSON artifact"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        store = S3AuditStore()
        store.s3_client = mock_s3_client
        
        contract_data = {
            "contract_id": "contract_789",
            "terms": {"duration": "2 years", "amount": "50000 CHF"},
            "status": "completed"
        }
        
        result = store.store_contract_artifact("session_123", "user_456", contract_data)
        
        assert result == True
        mock_s3_client.put_object.assert_called_once()
        
        call_args = mock_s3_client.put_object.call_args
        assert 'audit/contracts/' in call_args[1]['Key']
        assert call_args[1]['Metadata']['artifact_type'] == 'contract_json'

def test_get_user_artifacts(mock_s3_client):
    """Test retrieving user artifacts for GDPR compliance"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        store = S3AuditStore()
        store.s3_client = mock_s3_client
        
        mock_paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'audit/chat/2024/06/04/session_123_143000.json.gz',
                        'Size': 1024,
                        'LastModified': '2024-06-04T14:30:00Z'
                    }
                ]
            }
        ]
        
        mock_s3_client.head_object.return_value = {
            'Metadata': {
                'user_id': 'user_456',
                'artifact_type': 'chat_history',
                'session_id': 'session_123'
            }
        }
        
        artifacts = store.get_user_artifacts('user_456')
        
        assert len(artifacts) == 1
        assert artifacts[0]['artifact_type'] == 'chat_history'
        assert artifacts[0]['session_id'] == 'session_123'

def test_delete_user_artifacts(mock_s3_client):
    """Test deleting user artifacts for GDPR right to be forgotten"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        store = S3AuditStore()
        store.s3_client = mock_s3_client
        
        with patch.object(store, 'get_user_artifacts') as mock_get_artifacts:
            mock_get_artifacts.return_value = [
                {'key': 'audit/chat/2024/06/04/session_123_143000.json.gz'},
                {'key': 'audit/fsm/2024/06/04/session_123_143500.json.gz'}
            ]
            
            mock_s3_client.delete_objects.return_value = {
                'Deleted': [
                    {'Key': 'audit/chat/2024/06/04/session_123_143000.json.gz'},
                    {'Key': 'audit/fsm/2024/06/04/session_123_143500.json.gz'}
                ]
            }
            
            result = store.delete_user_artifacts('user_456')
            
            assert result == True
            mock_s3_client.delete_objects.assert_called_once()
            
            call_args = mock_s3_client.delete_objects.call_args
            delete_request = call_args[1]['Delete']
            assert len(delete_request['Objects']) == 2

def test_audit_store_without_credentials():
    """Test audit store behavior without AWS credentials"""
    with patch.dict('os.environ', {}, clear=True):
        with patch('boto3.client', side_effect=Exception("No credentials")):
            store = S3AuditStore()
            assert store.s3_client is None
            
            result = store.store_chat_artifact("session_123", "user_456", [])
            assert result == False

def test_compression_functionality():
    """Test artifact compression"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret'
    }):
        store = S3AuditStore()
        
        test_artifact = {
            "test_data": "This is a test artifact with some content",
            "numbers": [1, 2, 3, 4, 5],
            "nested": {"key": "value"}
        }
        
        compressed_data = store._compress_artifact(test_artifact)
        
        assert isinstance(compressed_data, bytes)
        assert len(compressed_data) > 0
        
        import json
        json_size = len(json.dumps(test_artifact).encode('utf-8'))
        assert len(compressed_data) > 50  # Reasonable minimum for gzipped data

def test_switzerland_hosting_compliance():
    """Test that audit store uses EU region for Switzerland hosting"""
    with patch.dict('os.environ', {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'AWS_REGION': 'eu-central-1'
    }):
        with patch('boto3.client') as mock_boto3:
            store = S3AuditStore()
            
            mock_boto3.assert_called_with(
                's3',
                region_name='eu-central-1',
                aws_access_key_id='test_key',
                aws_secret_access_key='test_secret'
            )
