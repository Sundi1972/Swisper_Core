# Strategic Memory Architecture Implementation Plan
## Swisper Core - Multi-Phase Refactoring

**Date**: June 4, 2025  
**Branch**: devin/1749046679-fsm-debugging-clean  
**Estimated Total ACUs**: ~20 (4 phases × 5 ACUs each)

## Progress Tracking
- [ ] **Phase 1**: Fix FSM State Persistence (PR #1) - 5 ACUs
- [ ] **Phase 2**: Memory Manager Service (PR #2) - 5 ACUs  
- [ ] **Phase 3**: Haystack Pipeline Integration (PR #3) - 5 ACUs
- [ ] **Phase 4**: Privacy & Governance (PR #4) - 5 ACUs

---

## Phase 1: Fix FSM State Persistence (PR #1) - 5 ACUs

### User Stories
1. **As a user, I want my conversation state to persist correctly so I don't get stuck in infinite loops**
   - Fix infinite loop between search → refine_constraints states
   - Ensure FSM state transitions are atomic and consistent
   - Validate state integrity during save/load operations

2. **As a developer, I want unified session storage so there are no conflicts between storage mechanisms**
   - Consolidate PostgreSQL session store and enhanced session persistence
   - Remove dual session storage layer conflicts
   - Ensure single source of truth for FSM state

3. **As a system, I want reliable state reconstruction so FSM continues correctly after user interactions**
   - Fix state retrieval bug where "refine_constraints" becomes "search"
   - Ensure proper FSM context serialization/deserialization
   - Add comprehensive logging for state transitions

### Technical Implementation
- **Files to modify**: `contract_engine/contract_engine.py`, `orchestrator/postgres_session_store.py`, `contract_engine/session_persistence.py`
- **Root cause**: Multiple session storage mechanisms causing state corruption
- **Solution**: Unify storage layers with atomic state transitions

### Acceptance Criteria
- ✅ Users can complete full purchase flow without infinite loops
- ✅ FSM state persists correctly between user interactions
- ✅ All existing tests pass
- ✅ State transitions are logged and traceable

---

## Phase 2: Memory Manager Service (PR #2) - 5 ACUs

### User Stories
1. **As a user, I want my recent conversation to be immediately available so responses are contextually relevant**
   - Implement Redis-based BufferStore for 30-message ephemeral buffer
   - Add real-time message buffering with TTL management
   - Ensure sub-100ms buffer access times

2. **As a user, I want my conversation history summarized so context is preserved without token bloat**
   - Create SummaryStore with Redis→PostgreSQL persistence
   - Implement rolling summary generation when buffer exceeds 3k tokens
   - Store summaries in existing `short_summary` field

3. **As a system, I want intelligent memory management so performance remains optimal**
   - Add token counting and 3k threshold trigger mechanism
   - Implement automatic buffer overflow handling
   - Create memory cleanup policies (24h session retention)

4. **As a developer, I want a unified memory interface so all components can access memory consistently**
   - Develop MemoryManager service with clean API
   - Integrate with existing session persistence architecture
   - Add health monitoring and fallback mechanisms

### Technical Implementation
- **New components**: `MemoryManager`, `BufferStore`, `SummaryStore`
- **Dependencies**: Redis, existing PostgreSQL session store
- **Integration points**: Existing `SwisperSession` model, session persistence

### Acceptance Criteria
- ✅ 30-message buffer with automatic overflow to summaries
- ✅ Token counting triggers summarization at 3k tokens
- ✅ Memory operations complete within performance SLAs
- ✅ Graceful degradation when Redis unavailable

---

## Phase 3: Haystack Pipeline Integration (PR #3) - 5 ACUs

### User Stories
1. **As a user, I want my conversation history intelligently summarized so I don't lose important context**
   - Implement RollingSummariser pipeline with T5-base model
   - Create map-reduce summarization for buffer overflow
   - Generate 1-2 sentence summaries preserving key information

2. **As a user, I want the system to remember my preferences and facts so conversations feel personalized**
   - Create RAG pipeline with Dense retrieval and BM25 ranking
   - Implement Milvus vector store for semantic long-term memory
   - Store user preferences, facts, and interaction patterns

3. **As a user, I want relevant memories injected into conversations so the AI understands my context**
   - Retrieve top K=3 relevant memories for each user prompt
   - Inject memories into system prompts automatically
   - Ensure memory relevance scoring and ranking

4. **As a developer, I want memory pipelines integrated with existing architecture so they work seamlessly**
   - Connect memory pipelines to existing orchestrator
   - Integrate with current product search and preference matching
   - Maintain compatibility with existing pipeline architecture

### Technical Implementation
- **New pipelines**: `RollingSummariser`, `SemanticMemoryRAG`
- **Vector store**: Milvus cluster for semantic memory
- **Integration**: Existing Haystack pipeline architecture
- **Models**: T5-base for summarization, sentence-transformers for embeddings

### Acceptance Criteria
- ✅ Automatic summarization when buffer exceeds 3k tokens
- ✅ Semantic memory storage and retrieval working
- ✅ Memory-enhanced conversations show improved context awareness
- ✅ Pipeline performance meets latency requirements (<2s)

---

## Phase 4: Privacy & Governance (PR #4) - 5 ACUs

### User Stories
1. **As a user, I want my personal information protected so my privacy is maintained**
   - Implement PII hashing/redaction before vector storage
   - Add per-user encryption for sensitive memory data
   - Ensure GDPR compliance for all stored memories

2. **As a user, I want control over my stored memories so I can manage my data**
   - Create `/memory/list` endpoint to view stored memories
   - Implement `/memory/delete` endpoint for selective deletion
   - Add bulk memory deletion for "right to be forgotten"

3. **As a compliance officer, I want auditable memory storage so we can demonstrate data governance**
   - Implement S3-based ArtifactStore for complete audit trails
   - Store raw chat logs, FSM transitions, and contract artifacts
   - Add retention policies and automated compliance reporting

4. **As a system administrator, I want memory access controls so data is properly secured**
   - Add authentication middleware for memory endpoints
   - Implement user-scoped memory access controls
   - Create admin interfaces for memory management

### Technical Implementation
- **Security**: pgcrypto for encryption, PII detection/redaction
- **Storage**: S3/object storage for auditable artifacts
- **APIs**: RESTful memory management endpoints
- **Compliance**: GDPR-compliant data handling workflows

### Acceptance Criteria
- ✅ PII automatically detected and redacted/hashed
- ✅ Users can view and delete their memories
- ✅ Complete audit trail for all memory operations
- ✅ GDPR compliance verified through testing

---

## Memory Architecture Overview

### Memory Types & Lifecycle
| Layer | TTL / Size | Content | Purpose | Storage |
|-------|------------|---------|---------|---------|
| **Ephemeral Buffer** | ≤ 30 messages or 3k tokens | Full user/assistant turns | Immediate reasoning | Redis (hash per session) |
| **Short-Term Summary** | Session lifetime | Rolling abstractive summary + key contract state | Context continuity with low tokens | Redis + Postgres JSONB |
| **Long-Term Semantic Memory** | ∞ (user-opt-in) | Facts, preferences, biographies, finished contracts | Personalization & cross-session recall | **Milvus Vector DB** |
| **Auditable Artifacts** | ∞ | Complete raw chat, FSM logs, contract JSON | Compliance / debugging | S3 / object storage |

### Trigger Rules
- **Buffer Overflow**: When buffer tokens > 3k, feed oldest 10 turns to summarizer → append to Short-Term Summary, then drop from buffer
- **Memory Extraction**: Extract semantic facts/preferences from summaries → store in Milvus with embeddings
- **Cleanup**: Sessions inactive >24h → flush buffer → permanent summary → clear Redis cache

---

## Implementation Dependencies

### Phase 1 Prerequisites
- ✅ PostgreSQL session store (already implemented)
- ✅ FSM state machine architecture (exists)
- ✅ Session persistence framework (exists)

### Phase 2 Prerequisites
- ✅ Phase 1 completed (unified session storage)
- 🔄 Redis cluster setup
- 🔄 Token counting utilities

### Phase 3 Prerequisites
- ✅ Phase 2 completed (memory manager)
- 🔄 Milvus cluster deployment
- 🔄 T5-base model integration
- ✅ Existing Haystack pipeline architecture

### Phase 4 Prerequisites
- ✅ Phase 3 completed (memory pipelines)
- 🔄 S3/object storage setup
- 🔄 PII detection models
- 🔄 Encryption key management

---

## Risk Mitigation

### Technical Risks
- **Milvus Integration Complexity**: Start with simple vector operations, expand gradually
- **Performance Impact**: Implement caching and async processing for memory operations
- **Data Migration**: Plan careful migration from current session storage to new architecture

### Business Risks
- **Privacy Compliance**: Implement privacy-by-design from Phase 1
- **User Experience**: Ensure memory features enhance rather than slow down interactions
- **Scalability**: Design for horizontal scaling from the beginning

---

## Success Metrics

### Phase 1 Success
- Zero infinite loop incidents in FSM state transitions
- 100% state persistence accuracy
- All existing functionality preserved

### Phase 2 Success
- <100ms memory buffer access times
- Successful summarization at 3k token threshold
- 99.9% memory operation reliability

### Phase 3 Success
- Semantic memory retrieval accuracy >80%
- Memory-enhanced conversation quality improvement (user feedback)
- Pipeline latency <2s end-to-end

### Phase 4 Success
- 100% PII detection and protection
- GDPR compliance audit passed
- Complete audit trail for all memory operations

---

## Next Steps

1. **User Confirmation**: Confirm Phase 1 as starting point
2. **Environment Setup**: Ensure Redis and Milvus infrastructure ready
3. **Implementation**: Begin Phase 1 FSM state persistence fixes
4. **Testing Strategy**: Develop comprehensive test suite for each phase
5. **Documentation**: Update API documentation as each phase completes

**Ready to proceed with Phase 1 implementation upon confirmation.**
