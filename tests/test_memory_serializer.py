import pytest
from contract_engine.memory.message_serializer import MessageSerializer
from swisper_core import SwisperContext

def test_message_serialization_roundtrip():
    """Test message serialization and deserialization roundtrip"""
    serializer = MessageSerializer()
    
    original_message = {
        "role": "user",
        "content": "I want to buy a laptop",
        "timestamp": 1234567890
    }
    
    serialized = serializer.serialize_message(original_message)
    deserialized = serializer.deserialize_message(serialized)
    
    assert deserialized == original_message

def test_context_serialization_roundtrip():
    """Test SwisperContext serialization roundtrip"""
    serializer = MessageSerializer()
    
    context = SwisperContext(
        session_id="test_session",
        current_state="search",
        product_query="laptop",
        preferences={"budget": "1000"}
    )
    
    serialized = serializer.serialize_context(context)
    deserialized_context = serializer.deserialize_context(serialized)
    
    assert deserialized_context.session_id == context.session_id
    assert deserialized_context.current_state == context.current_state
    assert deserialized_context.product_query == context.product_query
    assert deserialized_context.preferences == context.preferences

def test_batch_serialization():
    """Test batch message serialization"""
    serializer = MessageSerializer()
    
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "How are you?"}
    ]
    
    serialized_batch = serializer.serialize_batch(messages)
    deserialized_batch = serializer.deserialize_batch(serialized_batch)
    
    assert len(deserialized_batch) == len(messages)
    assert deserialized_batch == messages

def test_serialization_with_unicode():
    """Test serialization with unicode characters"""
    serializer = MessageSerializer()
    
    message = {
        "content": "Hello 世界! 🌍",
        "role": "user"
    }
    
    serialized = serializer.serialize_message(message)
    deserialized = serializer.deserialize_message(serialized)
    
    assert deserialized["content"] == "Hello 世界! 🌍"

def test_invalid_serialization_data():
    """Test handling of invalid serialization data"""
    serializer = MessageSerializer()
    
    with pytest.raises(ValueError, match="Failed to deserialize message"):
        serializer.deserialize_message("invalid json")
    
    with pytest.raises(ValueError, match="Invalid message format"):
        serializer.deserialize_message('{"no_data_field": true}')

def test_serialization_metadata():
    """Test that serialization includes metadata"""
    serializer = MessageSerializer()
    
    message = {"content": "test"}
    serialized = serializer.serialize_message(message)
    
    import json
    parsed = json.loads(serialized)
    
    assert "version" in parsed
    assert "timestamp" in parsed
    assert "data" in parsed
    assert parsed["version"] == "1.0"
    assert parsed["data"] == message
