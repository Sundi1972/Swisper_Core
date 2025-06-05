import pytest
from swisper_core import SwisperContext

def test_context_roundtrip_preserves_fsm_state():
    """Ensure SwisperContext.to_dict() → from_dict() preserves exact FSM state"""
    context = SwisperContext(
        session_id="test_001",
        current_state="refine_constraints",
        preferences={"budget": "1000"},  # Use string to match Pydantic behavior
        constraints=["energy efficient"]
    )
    context_dict = context.to_dict()
    restored_context = SwisperContext.from_dict(context_dict)
    
    assert restored_context.current_state == "refine_constraints"
    assert restored_context.preferences == {"budget": "1000"}
    assert restored_context.constraints == ["energy efficient"]

def test_state_validation_catches_corruption():
    """Validate state integrity checks work correctly"""
    corrupted_dict = {"current_state": None, "session_id": "test"}
    with pytest.raises(ValueError, match="Missing required field"):
        SwisperContext.from_dict(corrupted_dict)

def test_serialization_version_tracking():
    """Test serialization includes version for future compatibility"""
    context = SwisperContext(session_id="test", current_state="search")
    context_dict = context.to_dict()
    assert "serialization_version" in context_dict
    assert context_dict["serialization_version"] == "1.0"

def test_context_preserves_all_fields():
    """Test that all context fields are preserved during serialization"""
    context = SwisperContext(
        session_id="test_002",
        current_state="match_preferences",
        product_query="laptop",
        preferences={"brand": "Apple", "budget": "2000"},  # Use string to match Pydantic behavior
        constraints=["lightweight", "long battery"],
        search_results=[{"id": 1, "name": "MacBook"}],
        selected_product={"id": 1, "name": "MacBook"}
    )
    
    context_dict = context.to_dict()
    restored_context = SwisperContext.from_dict(context_dict)
    
    assert restored_context.session_id == "test_002"
    assert restored_context.current_state == "match_preferences"
    assert restored_context.product_query == "laptop"
    assert restored_context.preferences == {"brand": "Apple", "budget": "2000"}
    assert restored_context.constraints == ["lightweight", "long battery"]
    assert restored_context.search_results == [{"id": 1, "name": "MacBook"}]
    assert restored_context.selected_product == {"id": 1, "name": "MacBook"}

def test_invalid_state_values_rejected():
    """Test that invalid state values are rejected during deserialization"""
    invalid_states = ["invalid_state", 123, []]
    
    for invalid_state in invalid_states:
        corrupted_dict = {
            "session_id": "test",
            "current_state": invalid_state
        }
        with pytest.raises(ValueError, match="Invalid state"):
            SwisperContext.from_dict(corrupted_dict)
    
    for empty_state in ["", None]:
        corrupted_dict = {
            "session_id": "test",
            "current_state": empty_state
        }
        with pytest.raises(ValueError, match="Invalid state|Missing required field"):
            SwisperContext.from_dict(corrupted_dict)

def test_missing_required_fields_rejected():
    """Test that missing required fields are rejected"""
    with pytest.raises(ValueError, match="Missing required field"):
        SwisperContext.from_dict({"current_state": "search"})
    
    with pytest.raises(ValueError, match="Missing required field"):
        SwisperContext.from_dict({"session_id": "test"})
