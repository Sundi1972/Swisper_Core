# Session and Context Management Architecture

## Overview

The Session and Context Management system in Swisper Core provides robust state persistence, context serialization, and session recovery capabilities to ensure seamless user experiences across interactions.

## Session Architecture

### Session Lifecycle

```
Session Creation → Context Loading → State Execution → Context Updates → Session Persistence
       ↓                ↓               ↓               ↓                    ↓
   Generate ID    Load Previous    Execute Pipelines   Update Context    Save to Store
   Initialize     Context/State    Handle Transitions  Track Metadata    Cleanup Expired
```

### Session Components

**PipelineSessionManager**:
- Manages pipeline execution history
- Tracks performance metrics
- Handles session cleanup and expiration

**SwisperContext**:
- Maintains conversation state
- Stores pipeline results and metadata
- Handles context serialization/deserialization

**SessionStore**:
- Persistent storage backend (PostgreSQL/shelve)
- Session data encryption and security
- Automatic cleanup of expired sessions

## Context Management

### SwisperContext Structure

```python
@dataclass
class SwisperContext:
    # Core conversation data
    session_id: str
    user_id: str
    conversation_history: List[Message]
    current_state: str
    
    # Product search context
    product_query: str
    hard_constraints: List[str]
    soft_preferences: Dict[str, Any]
    search_results: List[Product]
    
    # Pipeline execution metadata
    pipeline_executions: List[PipelineExecution]
    performance_metrics: Dict[str, Any]
    cache_keys: List[str]
    
    # Memory management
    buffer_store: Dict[str, Any]  # Short-term memory
    summary_store: Dict[str, Any]  # Mid-term memory
    semantic_memory_refs: List[str]  # Long-term memory references
    
    # Privacy and compliance
    pii_extracted: List[PIIEntity]
    consent_status: Dict[str, bool]
    data_retention_policy: str
```

### Context Serialization

**Enhanced Serialization**:
```python
def serialize_context(context: SwisperContext) -> Dict[str, Any]:
    return {
        "session_id": context.session_id,
        "user_id": context.user_id,
        "conversation_history": [msg.to_dict() for msg in context.conversation_history],
        "current_state": context.current_state,
        
        # Pipeline metadata
        "pipeline_executions": [exec.to_dict() for exec in context.pipeline_executions],
        "performance_metrics": context.performance_metrics,
        "cache_keys": context.cache_keys,
        
        # Memory layers
        "buffer_store": context.buffer_store,
        "summary_store": context.summary_store,
        "semantic_memory_refs": context.semantic_memory_refs,
        
        # Privacy data
        "pii_extracted": [pii.to_dict() for pii in context.pii_extracted],
        "consent_status": context.consent_status,
        
        # Metadata
        "created_at": context.created_at.isoformat(),
        "updated_at": context.updated_at.isoformat(),
        "version": context.version
    }
```

## Session Persistence

### PipelineSessionManager

**Core Functionality**:
```python
class PipelineSessionManager:
    def __init__(self, session_store: SessionStore):
        self.session_store = session_store
        self.performance_cache = PerformanceCache()
        
    async def save_pipeline_execution(
        self, 
        session_id: str, 
        pipeline_name: str, 
        execution_data: Dict[str, Any]
    ):
        # Save pipeline execution metadata
        # Update performance metrics
        # Cache results for future use
        
    async def load_session_context(self, session_id: str) -> SwisperContext:
        # Load context from persistent storage
        # Restore pipeline execution history
        # Rebuild cache references
        
    async def cleanup_expired_sessions(self):
        # Remove sessions older than 24 hours
        # Clean up associated cache entries
        # Update performance metrics
```

### Session Storage Backend

**PostgreSQL Integration**:
```sql
-- Sessions table
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    context_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Pipeline executions table
CREATE TABLE pipeline_executions (
    execution_id UUID PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id),
    pipeline_name VARCHAR(255) NOT NULL,
    execution_data JSONB NOT NULL,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Performance Optimization

### Session Caching

**Multi-Level Caching Strategy**:
```python
class SessionCache:
    def __init__(self):
        self.memory_cache = {}  # In-memory for active sessions
        self.redis_cache = RedisCache()  # Distributed cache for recent sessions
        self.persistent_store = SessionStore()  # Long-term storage
        
    async def get_session(self, session_id: str) -> Optional[SwisperContext]:
        # Check memory cache first
        if session_id in self.memory_cache:
            return self.memory_cache[session_id]
            
        # Check Redis cache
        context = await self.redis_cache.get(session_id)
        if context:
            self.memory_cache[session_id] = context
            return context
            
        # Load from persistent storage
        context = await self.persistent_store.load_session(session_id)
        if context:
            await self.redis_cache.set(session_id, context, ttl=3600)
            self.memory_cache[session_id] = context
            
        return context
```

## Security and Privacy

### Session Security

**Encryption at Rest**:
```python
class EncryptedSessionStore:
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)
        
    def encrypt_context(self, context: SwisperContext) -> bytes:
        serialized = serialize_context(context)
        json_data = json.dumps(serialized).encode()
        return self.cipher.encrypt(json_data)
```

### PII Management in Sessions

**PII Extraction and Handling**:
```python
class PIISessionManager:
    def __init__(self, pii_extractor: PIIExtractor):
        self.pii_extractor = pii_extractor
        
    def extract_and_store_pii(self, context: SwisperContext):
        # Extract PII from conversation history
        for message in context.conversation_history:
            pii_entities = self.pii_extractor.extract(message.content)
            context.pii_extracted.extend(pii_entities)
            
        # Redact PII from stored content
        self.redact_pii_from_context(context)
```

For related documentation, see:
- [Memory Management](memory-management.md)
- [Tools and Contract Management](tools-and-contracts.md)
- [Testing Strategy](../testing/strategy.md)
