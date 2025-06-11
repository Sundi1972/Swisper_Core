# Memory Manager API Documentation

## Overview

The Memory Manager Service provides a unified interface for managing session memory in Swisper Core, implementing a multi-layered memory architecture with Redis-based ephemeral storage, PostgreSQL-backed summaries, and configurable token-based triggers.

## Architecture Components

### 1. BufferStore (Redis Lists)
- **Purpose**: Ephemeral 30-message/4k token buffer for immediate reasoning
- **Storage**: Redis Lists with TTL support
- **Performance**: <5ms read latency, <10ms write latency (95th percentile)

### 2. SummaryStore (Redis→PostgreSQL)
- **Purpose**: Rolling abstractive summaries of older chat history
- **Storage**: Redis cache with PostgreSQL persistence
- **Triggers**: Configurable token thresholds (default: 3k tokens)

### 3. TokenCounter (tiktoken)
- **Purpose**: Accurate token counting for OpenAI models
- **Features**: Batch processing, overflow detection, context estimation
- **Performance**: <50ms for large batches

### 4. CircuitBreaker
- **Purpose**: Redis resilience and graceful degradation
- **Integration**: SystemHealthMonitor for service monitoring
- **Recovery**: Automatic reset with configurable timeouts

## API Reference

### MemoryManager

#### `add_message(session_id: str, message: Dict[str, Any]) -> bool`
Add message to memory with automatic summarization.

```python
memory_manager = MemoryManager()
result = memory_manager.add_message("session_123", {
    "role": "user",
    "content": "I want to buy a laptop"
})
```

#### `get_context(session_id: str) -> Dict[str, Any]`
Get complete memory context for session.

```python
context = memory_manager.get_context("session_123")
# Returns:
# {
#     "buffer_messages": [...],
#     "current_summary": "...",
#     "buffer_info": {...},
#     "total_tokens": 1500,
#     "message_count": 25
# }
```

#### `save_context(session_id: str, context: SwisperContext) -> bool`
Save SwisperContext to memory (compatibility layer).

```python
swisper_context = SwisperContext(session_id="session_123", current_state="search")
result = memory_manager.save_context("session_123", swisper_context)
```

#### `set_session_config(session_id: str, config: Dict[str, Any])`
Configure per-session memory settings.

```python
memory_manager.set_session_config("session_123", {
    "summary_trigger_tokens": 2500,
    "max_buffer_tokens": 3500
})
```

#### `get_memory_stats(session_id: str) -> Dict[str, Any]`
Get comprehensive memory statistics.

```python
stats = memory_manager.get_memory_stats("session_123")
# Returns buffer info, summary stats, Redis metrics, session config
```

#### `clear_session_memory(session_id: str) -> bool`
Clear all memory for session.

```python
result = memory_manager.clear_session_memory("session_123")
```

#### `is_available() -> bool`
Check if memory system is available.

```python
if memory_manager.is_available():
    # Memory system operational
    pass
```

### BufferStore

#### `add_message(session_id: str, message: Dict[str, Any]) -> bool`
Add message to buffer with overflow handling.

#### `get_messages(session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]`
Get messages from buffer.

#### `get_buffer_info(session_id: str) -> Dict[str, Any]`
Get buffer metadata and statistics.

#### `should_trigger_summary(session_id: str, threshold: int = 3000) -> bool`
Check if buffer should trigger summarization.

#### `clear_buffer(session_id: str) -> bool`
Clear all messages from buffer.

### SummaryStore

#### `add_summary(session_id: str, summary_text: str, metadata: Optional[Dict[str, Any]] = None) -> bool`
Add new summary to rolling summary store.

#### `get_current_summary(session_id: str) -> Optional[str]`
Get current consolidated summary.

#### `get_summary_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]`
Get summary history with timestamps.

#### `get_summary_stats(session_id: str) -> Dict[str, Any]`
Get summary statistics for monitoring.

#### `clear_summaries(session_id: str) -> bool`
Clear all summaries for session.

### TokenCounter

#### `count_tokens(text: str) -> int`
Count tokens in a single text string.

#### `count_message_tokens(message: Dict[str, Any]) -> int`
Count tokens in a message dictionary.

#### `count_batch_tokens(messages: List[Dict[str, Any]]) -> int`
Count total tokens in a batch of messages.

#### `should_trigger_summary(messages: List[Dict[str, Any]], threshold: int = 3000) -> bool`
Check if message buffer should trigger summarization.

#### `get_overflow_messages(messages: List[Dict[str, Any]], max_tokens: int = 4000) -> List[Dict[str, Any]]`
Get messages that exceed token limit for removal.

## Configuration

### Environment Variables

```bash
REDIS_HOST=localhost          # Redis server host
REDIS_PORT=6379              # Redis server port  
REDIS_DB=0                   # Redis database number
```

### Session Configuration

```python
{
    "summary_trigger_tokens": 3000,    # Token threshold for summarization
    "max_buffer_tokens": 4000,         # Maximum buffer token limit
    "max_buffer_messages": 30          # Maximum buffer message count
}
```

### Production Settings

```yaml
# Redis Configuration
maxmemory: 4gb
maxmemory-policy: allkeys-lru
save: "900 1 300 10"
appendonly: no

# Performance SLAs
read_latency_p95: 5ms
write_latency_p95: 10ms
summarization_latency: 200ms
context_packaging_latency: 50ms
```

## Integration with Existing Systems

### Orchestrator Integration

```python
from contract_engine.memory import memory_manager

# In orchestrator/core.py
def handle_user_message(session_id: str, message: str):
    # Add message to memory
    memory_manager.add_message(session_id, {
        "role": "user", 
        "content": message,
        "timestamp": int(time.time())
    })
    
    # Get context for processing
    context = memory_manager.get_context(session_id)
    
    # Process with existing session store as fallback
    # ... existing logic ...
```

### Session Store Coexistence

```python
# Wrapper pattern for transition period
class EnhancedSessionStore:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.legacy_store = PostgresSessionStore()
    
    def add_chat_message(self, session_id: str, message: Dict[str, Any]):
        # Add to memory manager
        self.memory_manager.add_message(session_id, message)
        
        # Fallback to legacy store
        self.legacy_store.add_chat_message(session_id, message)
```

## Monitoring and Alerting

### Key Metrics

```python
# Buffer metrics
buffer_message_count
buffer_token_count
buffer_ttl_remaining

# Summary metrics  
summary_count
summary_generation_rate
summary_merge_rate

# Redis metrics
redis_used_memory
redis_evicted_keys
redis_expired_keys
redis_hit_ratio

# Performance metrics
read_latency_p95
write_latency_p95
summarization_latency
context_packaging_latency
```

### Health Checks

```python
# Memory system health
if not memory_manager.is_available():
    # Fallback to legacy persistence
    # Alert operations team
    pass

# Circuit breaker status
from contract_engine.memory.circuit_breaker import redis_circuit_breaker
if redis_circuit_breaker.get_state() == CircuitState.OPEN:
    # Redis unavailable, using fallbacks
    pass
```

## Error Handling

### Graceful Degradation

1. **Redis Unavailable**: Falls back to PostgreSQL session store
2. **Serialization Errors**: Logs warning, continues with raw data
3. **Token Counting Errors**: Uses character-based estimation
4. **Summary Generation Errors**: Skips summarization, maintains buffer

### Circuit Breaker Pattern

```python
# Automatic failure detection
@redis_circuit_breaker
def redis_operation():
    # Redis operation that may fail
    pass

# Manual circuit breaker control
redis_circuit_breaker.reset()  # Force reset
state = redis_circuit_breaker.get_state()  # Check current state
```

## Performance Optimization

### Best Practices

1. **Batch Operations**: Use batch methods for multiple messages
2. **TTL Management**: Configure appropriate TTL for session lifecycle
3. **Token Optimization**: Cache token counts for repeated content
4. **Connection Pooling**: Redis connection pool with 20 max connections
5. **Memory Limits**: Configure Redis maxmemory and eviction policies

### Scaling Considerations

1. **Redis Clustering**: Use Redis Cluster for horizontal scaling
2. **Sharding**: Distribute sessions across multiple Redis instances
3. **Read Replicas**: Use Redis replicas for read-heavy workloads
4. **Monitoring**: Implement comprehensive metrics collection

## Testing

### Unit Tests
```bash
poetry run pytest tests/test_memory_serializer.py -v
poetry run pytest tests/test_token_counter.py -v
poetry run pytest tests/test_buffer_store.py -v
poetry run pytest tests/test_summary_store.py -v
poetry run pytest tests/test_circuit_breaker.py -v
poetry run pytest tests/test_memory_manager.py -v
```

### Integration Tests
```bash
poetry run pytest tests/test_memory_integration.py -v
```

### Performance Tests
```bash
poetry run pytest tests/test_memory_performance.py -v
```

## Migration Guide

### Phase 1: Coexistence
1. Deploy Memory Manager alongside existing session store
2. Configure dual-write to both systems
3. Monitor performance and reliability

### Phase 2: Gradual Migration
1. Route read operations to Memory Manager
2. Maintain write operations to both systems
3. Validate data consistency

### Phase 3: Full Migration
1. Route all operations to Memory Manager
2. Use legacy store as backup only
3. Deprecate legacy session persistence

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Check Redis maxmemory settings and eviction policy
2. **Slow Performance**: Monitor Redis latency and connection pool usage
3. **Circuit Breaker Open**: Check Redis connectivity and health
4. **Token Count Mismatch**: Verify tiktoken model configuration
5. **Summary Quality**: Review summarization logic and token thresholds

### Debug Commands

```python
# Check memory system status
stats = memory_manager.get_memory_stats("session_id")
print(f"Redis available: {memory_manager.is_available()}")

# Inspect buffer contents
buffer_info = memory_manager.buffer_store.get_buffer_info("session_id")
messages = memory_manager.buffer_store.get_messages("session_id")

# Check circuit breaker state
from contract_engine.memory.circuit_breaker import redis_circuit_breaker
print(f"Circuit breaker state: {redis_circuit_breaker.get_state()}")
```
