# Memory Management Architecture

## Overview

Swisper Core implements a sophisticated four-tier memory architecture designed to provide efficient context management, intelligent summarization, and semantic search capabilities while maintaining compliance with Swiss data sovereignty requirements.

## Four-Tier Memory System

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Ephemeral Buffer (Redis)                     │
├─────────────────────────────────────────────────────────────────┤
│  • Recent messages (≤30 messages or 4k tokens)                 │
│  • Immediate reasoning context                                  │
│  • Session-scoped temporary data                               │
│  • Retention: Session duration                                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                            Rolling Summarization
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                Short-Term Summary (Redis+Postgres)             │
├─────────────────────────────────────────────────────────────────┤
│  • Rolling abstractive summaries                               │
│  • Older chat history compression                              │
│  • Contract state summaries                                    │
│  • Retention: 7-30 days (configurable)                        │
└─────────────────────────────────────────────────────────────────┘
                                    │
                            Semantic Indexing
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│               Long-Term Semantic Memory (Vector DB)            │
├─────────────────────────────────────────────────────────────────┤
│  • User facts and preferences                                  │
│  • Completed contracts history                                 │
│  • Personalization data                                        │
│  • Retention: Indefinite (with privacy controls)              │
└─────────────────────────────────────────────────────────────────┘
                                    │
                            Compliance Archival
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Auditable Artifacts (S3)                     │
├─────────────────────────────────────────────────────────────────┤
│  • Complete raw chat logs                                      │
│  • FSM execution logs                                          │
│  • Contract JSON for compliance                                │
│  • Retention: Legal requirements                               │
└─────────────────────────────────────────────────────────────────┘
```

## Memory Manager Service

### Core Components

**BufferStore (Ephemeral Buffer)**:
```python
class BufferStore:
    def __init__(self, redis_client: Redis, max_messages: int = 30, max_tokens: int = 4000):
        self.redis = redis_client
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        
    async def add_message(self, session_id: str, message: Message):
        """Add message to buffer with automatic overflow handling"""
        buffer_key = f"buffer:{session_id}"
        
        # Add message to buffer
        await self.redis.lpush(buffer_key, message.to_json())
        
        # Trim buffer to size limits
        await self.redis.ltrim(buffer_key, 0, self.max_messages - 1)
        
        # Check token limit and trigger summarization if needed
        if await self.get_token_count(session_id) > self.max_tokens:
            await self.trigger_summarization(session_id)
            
    async def get_recent_context(self, session_id: str, limit: int = 10) -> List[Message]:
        """Retrieve recent messages for context"""
        buffer_key = f"buffer:{session_id}"
        messages = await self.redis.lrange(buffer_key, 0, limit - 1)
        return [Message.from_json(msg) for msg in messages]
```

**SummaryStore (Short-Term Summary)**:
```python
class SummaryStore:
    def __init__(self, redis_client: Redis, postgres_client: PostgresClient):
        self.redis = redis_client
        self.postgres = postgres_client
        self.summarizer = T5RollingSummarizer()
        
    async def create_summary(self, session_id: str, messages: List[Message]) -> Summary:
        """Create rolling summary using T5 model"""
        # Generate summary using local T5 model
        summary_text = await self.summarizer.summarize(messages)
        
        # Extract key decisions and preferences
        key_decisions = self.extract_key_decisions(messages)
        user_preferences = self.extract_preferences(messages)
        
        summary = Summary(
            session_id=session_id,
            text=summary_text,
            key_decisions=key_decisions,
            user_preferences=user_preferences,
            message_count=len(messages),
            created_at=datetime.utcnow()
        )
        
        # Store in both Redis (fast access) and Postgres (persistence)
        await self.store_summary(summary)
        return summary
        
    async def store_summary(self, summary: Summary):
        """Store summary in Redis and Postgres"""
        # Redis for fast access
        redis_key = f"summary:{summary.session_id}"
        await self.redis.setex(redis_key, 86400, summary.to_json())  # 24h TTL
        
        # Postgres for persistence
        await self.postgres.execute(
            "INSERT INTO summaries (session_id, summary_data, created_at) VALUES ($1, $2, $3)",
            summary.session_id, summary.to_json(), summary.created_at
        )
```

**VectorMemory (Long-Term Semantic Memory)**:
```python
class VectorMemory:
    def __init__(self, milvus_client: MilvusClient, embedder: SentenceTransformer):
        self.milvus = milvus_client
        self.embedder = embedder
        self.collection_name = "swisper_semantic_memory"
        
    async def store_semantic_memory(self, user_id: str, content: str, metadata: Dict):
        """Store content in vector database for semantic search"""
        # Generate embedding using local sentence transformer
        embedding = self.embedder.encode(content)
        
        # Store in Milvus
        entity = {
            "user_id": user_id,
            "content": content,
            "embedding": embedding.tolist(),
            "metadata": metadata,
            "created_at": int(datetime.utcnow().timestamp())
        }
        
        await self.milvus.insert(self.collection_name, [entity])
        
    async def search_similar_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 10
    ) -> List[MemoryItem]:
        """Search for semantically similar memories"""
        # Generate query embedding
        query_embedding = self.embedder.encode(query)
        
        # Search in Milvus
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        results = await self.milvus.search(
            collection_name=self.collection_name,
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=limit,
            expr=f"user_id == '{user_id}'"
        )
        
        return [MemoryItem.from_milvus_result(result) for result in results[0]]
```

**ArtifactStore (Auditable Artifacts)**:
```python
class ArtifactStore:
    def __init__(self, s3_client: S3Client, bucket_name: str):
        self.s3 = s3_client
        self.bucket = bucket_name
        
    async def store_chat_log(self, session_id: str, messages: List[Message]):
        """Store complete chat log for compliance"""
        log_data = {
            "session_id": session_id,
            "messages": [msg.to_dict() for msg in messages],
            "stored_at": datetime.utcnow().isoformat(),
            "compliance_version": "1.0"
        }
        
        key = f"chat_logs/{session_id}/{datetime.utcnow().strftime('%Y/%m/%d')}.json"
        await self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(log_data),
            ServerSideEncryption='AES256'
        )
        
    async def store_fsm_log(self, session_id: str, fsm_transitions: List[StateTransition]):
        """Store FSM execution log for audit trail"""
        fsm_data = {
            "session_id": session_id,
            "transitions": [transition.to_dict() for transition in fsm_transitions],
            "stored_at": datetime.utcnow().isoformat()
        }
        
        key = f"fsm_logs/{session_id}/{datetime.utcnow().strftime('%Y/%m/%d')}.json"
        await self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(fsm_data),
            ServerSideEncryption='AES256'
        )
```

## T5-Based Rolling Summarization

### Local T5 Implementation

```python
class T5RollingSummarizer:
    def __init__(self, model_name: str = "t5-small"):
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.max_input_length = 512
        self.max_output_length = 150
        
    async def summarize(self, messages: List[Message]) -> str:
        """Create summary of conversation messages"""
        # Prepare input for T5
        input_text = self.prepare_input(messages)
        
        # Generate summary
        inputs = self.tokenizer.encode(input_text, return_tensors="pt", max_length=self.max_input_length, truncation=True)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=self.max_output_length,
                num_beams=4,
                early_stopping=True,
                temperature=0.7
            )
            
        summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return summary
        
    def prepare_input(self, messages: List[Message]) -> str:
        """Format messages for T5 summarization"""
        formatted_text = "summarize: "
        for message in messages:
            role = "user" if message.is_user else "assistant"
            formatted_text += f"{role}: {message.content} "
            
        return formatted_text
```

## RAG Integration with Haystack

### RAG Pipeline Implementation

```python
class RAGPipeline:
    def __init__(self, vector_memory: VectorMemory, llm_client: OpenAIClient):
        self.vector_memory = vector_memory
        self.llm = llm_client
        
    async def answer_with_context(self, user_id: str, query: str) -> str:
        """Answer query using retrieved context from memory"""
        # Retrieve relevant memories
        relevant_memories = await self.vector_memory.search_similar_memories(
            user_id=user_id,
            query=query,
            limit=5
        )
        
        # Prepare context for LLM
        context = self.prepare_context(relevant_memories)
        
        # Generate response with context
        prompt = f"""
        Context from user's previous interactions:
        {context}
        
        User question: {query}
        
        Please answer the question using the provided context when relevant.
        """
        
        response = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    def prepare_context(self, memories: List[MemoryItem]) -> str:
        """Format retrieved memories as context"""
        context_parts = []
        for memory in memories:
            context_parts.append(f"- {memory.content} (from {memory.created_at.strftime('%Y-%m-%d')})")
        return "\n".join(context_parts)
```

## PII Extraction and Privacy

### PII Detection and Redaction

```python
class PIIExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
        }
        
    def extract_pii(self, text: str) -> List[PIIEntity]:
        """Extract PII entities from text"""
        entities = []
        
        # Named entity recognition
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE"]:
                entities.append(PIIEntity(
                    type=ent.label_,
                    value=ent.text,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.9
                ))
        
        # Pattern matching
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entities.append(PIIEntity(
                    type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                ))
                
        return entities
        
    def redact_pii(self, text: str, entities: List[PIIEntity]) -> str:
        """Redact PII from text while preserving structure"""
        redacted_text = text
        
        # Sort entities by position (reverse order to maintain indices)
        entities.sort(key=lambda x: x.start, reverse=True)
        
        for entity in entities:
            placeholder = f"[{entity.type.upper()}]"
            redacted_text = redacted_text[:entity.start] + placeholder + redacted_text[entity.end:]
            
        return redacted_text
```

## Performance and Monitoring

### Memory Performance Metrics

```python
class MemoryMetrics:
    def __init__(self):
        self.metrics = {}
        
    def track_buffer_performance(self, session_id: str, operation: str, duration: float):
        """Track buffer operation performance"""
        key = f"buffer_{operation}"
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append(duration)
        
    def track_summarization_performance(self, message_count: int, duration: float):
        """Track summarization performance"""
        self.metrics.setdefault("summarization_times", []).append({
            "message_count": message_count,
            "duration": duration,
            "timestamp": datetime.utcnow()
        })
        
    def track_vector_search_performance(self, query_length: int, result_count: int, duration: float):
        """Track vector search performance"""
        self.metrics.setdefault("vector_searches", []).append({
            "query_length": query_length,
            "result_count": result_count,
            "duration": duration,
            "timestamp": datetime.utcnow()
        })
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary"""
        return {
            "buffer_avg_time": np.mean(self.metrics.get("buffer_add", [])),
            "summarization_avg_time": np.mean([m["duration"] for m in self.metrics.get("summarization_times", [])]),
            "vector_search_avg_time": np.mean([m["duration"] for m in self.metrics.get("vector_searches", [])]),
            "total_operations": sum(len(v) for v in self.metrics.values())
        }
```

## Data Retention and Cleanup

### Automated Cleanup Policies

```python
class MemoryCleanupService:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.retention_policies = {
            "buffer": timedelta(hours=24),
            "summary": timedelta(days=30),
            "vector_memory": timedelta(days=365),  # Configurable
            "artifacts": timedelta(days=2555)  # 7 years for compliance
        }
        
    async def cleanup_expired_data(self):
        """Clean up expired data across all memory tiers"""
        now = datetime.utcnow()
        
        # Clean up expired buffers
        await self.cleanup_buffers(now - self.retention_policies["buffer"])
        
        # Clean up expired summaries
        await self.cleanup_summaries(now - self.retention_policies["summary"])
        
        # Clean up expired vector memories (with user consent)
        await self.cleanup_vector_memories(now - self.retention_policies["vector_memory"])
        
    async def cleanup_buffers(self, cutoff_time: datetime):
        """Remove expired buffer data"""
        # Implementation for Redis buffer cleanup
        pass
        
    async def cleanup_summaries(self, cutoff_time: datetime):
        """Remove expired summary data"""
        # Implementation for summary cleanup
        pass
```

## Testing Strategy

### Memory System Testing

```python
def test_buffer_overflow_handling():
    """Test buffer overflow and summarization trigger"""
    buffer_store = BufferStore(redis_client, max_messages=5)
    
    # Add messages beyond limit
    for i in range(10):
        message = Message(content=f"Message {i}", is_user=i % 2 == 0)
        await buffer_store.add_message("test_session", message)
    
    # Verify buffer size limit
    recent_messages = await buffer_store.get_recent_context("test_session")
    assert len(recent_messages) <= 5

def test_semantic_search_accuracy():
    """Test semantic search retrieval accuracy"""
    vector_memory = VectorMemory(milvus_client, embedder)
    
    # Store test memories
    await vector_memory.store_semantic_memory(
        "user123", 
        "I prefer Italian restaurants", 
        {"type": "preference"}
    )
    
    # Search for similar content
    results = await vector_memory.search_similar_memories(
        "user123", 
        "What kind of food do I like?", 
        limit=5
    )
    
    assert len(results) > 0
    assert "Italian" in results[0].content
```

For related documentation, see:
- [Session and Context Management](session-management.md)
- [Tools and Contract Management](tools-and-contracts.md)
- [Testing Strategy](../testing/strategy.md)
