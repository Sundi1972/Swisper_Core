import pytest
from contract_engine.memory.token_counter import TokenCounter

def test_token_counting_basic():
    """Test basic token counting functionality"""
    counter = TokenCounter()
    
    text = "Hello world"
    token_count = counter.count_tokens(text)
    
    assert isinstance(token_count, int)
    assert token_count > 0

def test_message_token_counting():
    """Test token counting for message dictionaries"""
    counter = TokenCounter()
    
    message = {
        "role": "user",
        "content": "I want to buy a laptop for work"
    }
    
    token_count = counter.count_message_tokens(message)
    assert isinstance(token_count, int)
    assert token_count > 0

def test_batch_token_counting():
    """Test token counting for message batches"""
    counter = TokenCounter()
    
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "How are you?"}
    ]
    
    total_tokens = counter.count_batch_tokens(messages)
    individual_sum = sum(counter.count_message_tokens(msg) for msg in messages)
    
    assert total_tokens == individual_sum
    assert total_tokens > 0

def test_context_token_estimation():
    """Test token estimation for SwisperContext"""
    counter = TokenCounter()
    
    context = {
        "product_query": "laptop for programming",
        "enhanced_query": "high performance laptop for software development",
        "step_log": ["searched products", "analyzed preferences"]
    }
    
    token_count = counter.estimate_context_tokens(context)
    assert isinstance(token_count, int)
    assert token_count > 0

def test_summary_trigger_logic():
    """Test summarization trigger logic"""
    counter = TokenCounter()
    
    short_messages = [
        {"content": "Hi"},
        {"content": "Hello"}
    ]
    
    long_messages = [
        {"content": "This is a very long message " * 100},
        {"content": "Another long message " * 100}
    ]
    
    assert not counter.should_trigger_summary(short_messages, threshold=3000)
    assert counter.should_trigger_summary(long_messages, threshold=100)

def test_overflow_message_detection():
    """Test overflow message detection"""
    counter = TokenCounter()
    
    messages = [
        {"content": "Short message"},
        {"content": "This is a longer message " * 50},
        {"content": "Another long message " * 50},
        {"content": "Final message"}
    ]
    
    overflow = counter.get_overflow_messages(messages, max_tokens=100)
    
    assert isinstance(overflow, list)
    assert len(overflow) <= len(messages)

def test_token_counting_error_handling():
    """Test error handling in token counting"""
    counter = TokenCounter()
    
    invalid_message = None
    token_count = counter.count_message_tokens(invalid_message)
    assert token_count == 0
    
    empty_context = {}
    context_tokens = counter.estimate_context_tokens(empty_context)
    assert context_tokens == 0

def test_different_model_encodings():
    """Test token counting with different model encodings"""
    gpt4_counter = TokenCounter("gpt-4o")
    gpt35_counter = TokenCounter("gpt-3.5-turbo")
    
    text = "This is a test message for token counting"
    
    gpt4_tokens = gpt4_counter.count_tokens(text)
    gpt35_tokens = gpt35_counter.count_tokens(text)
    
    assert isinstance(gpt4_tokens, int)
    assert isinstance(gpt35_tokens, int)
    assert gpt4_tokens > 0
    assert gpt35_tokens > 0
