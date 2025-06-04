# Phase 1 Detailed Implementation Plan: Fix FSM State Persistence

**Estimated ACUs**: 5  
**Target**: Single PR addressing FSM infinite loop bug  
**Priority**: Critical - blocking user transactions

---

## Problem Analysis

### Root Cause: Dual Session Storage Conflict
The infinite loop between `search → refine_constraints` states is caused by conflicting session storage mechanisms:

1. **Enhanced Session Persistence** (`contract_engine/session_persistence.py`) saves FSM state as "refine_constraints"
2. **PostgreSQL Session Store** (`orchestrator/postgres_session_store.py`) retrieves state as "search" 
3. **Result**: Infinite loop `search → refine_constraints (stored) → search (retrieved) → ...`

### Technical Details
- FSM stores state via `save_session_context()` in `contract_engine/contract_engine.py:204`
- State reconstruction happens in `orchestrator/session_store.py:132-171`
- Context serialization/deserialization mismatch causes state corruption

---

## Implementation Strategy

### 1. Unify Session Storage Mechanisms

**Current State**: Two parallel storage systems
- `PipelineSessionManager` in `session_persistence.py`
- Direct PostgreSQL storage in `postgres_session_store.py`

**Target State**: Single unified storage layer
- Consolidate into enhanced PostgreSQL session store
- Remove storage layer conflicts
- Ensure atomic state transitions

### 2. Fix State Serialization/Deserialization

**Issues**:
- `SwisperContext.to_dict()` and `SwisperContext.from_dict()` inconsistency
- FSM state not properly preserved during reconstruction
- Contract template path handling inconsistent

**Solutions**:
- Add state validation during serialization
- Ensure FSM state integrity in reconstruction
- Standardize contract template handling

### 3. Add Atomic State Transition Validation

**Current**: State transitions can be interrupted/corrupted
**Target**: Atomic state transitions with rollback capability

---

## Detailed Implementation Tasks

### Task 1: Analyze Current State Storage Flow
**Files**: `contract_engine/contract_engine.py`, `orchestrator/session_store.py`, `contract_engine/session_persistence.py`

**Actions**:
1. Map complete state storage flow from FSM → PostgreSQL
2. Identify exact point where state corruption occurs
3. Document current serialization format inconsistencies

### Task 2: Create Unified Session Storage Interface
**New File**: `contract_engine/unified_session_store.py`

**Implementation**:
```python
class UnifiedSessionStore:
    """Single source of truth for FSM session persistence"""
    
    def save_fsm_state(self, session_id: str, fsm: ContractStateMachine) -> bool:
        """Atomically save FSM state with validation"""
        
    def load_fsm_state(self, session_id: str) -> Optional[ContractStateMachine]:
        """Load FSM state with integrity validation"""
        
    def validate_state_integrity(self, context_dict: Dict) -> bool:
        """Validate state consistency before save/load"""
```

### Task 3: Fix Context Serialization
**Files**: `contract_engine/context.py`

**Enhancements**:
- Add state validation to `to_dict()` method
- Ensure `from_dict()` preserves FSM state exactly
- Add serialization version tracking for future compatibility

### Task 4: Update FSM State Transition Logic
**Files**: `contract_engine/contract_engine.py`

**Changes**:
- Replace direct `save_session_context()` calls with unified store
- Add pre/post state transition validation
- Implement rollback mechanism for failed transitions

### Task 5: Migrate Existing Session Data
**New File**: `scripts/migrate_session_storage.py`

**Purpose**: Safely migrate existing sessions to unified storage format

---

## Isolation Testing Strategy

### Unit Tests

#### Test 1: Context Serialization Integrity
**File**: `tests/test_context_serialization.py`
```python
def test_context_roundtrip_preserves_state():
    """Ensure to_dict() → from_dict() preserves exact FSM state"""
    
def test_state_validation_catches_corruption():
    """Validate state integrity checks work correctly"""
```

#### Test 2: Unified Session Store
**File**: `tests/test_unified_session_store.py`
```python
def test_atomic_state_save():
    """Test atomic state saving with rollback on failure"""
    
def test_state_load_validation():
    """Test state loading with integrity validation"""
    
def test_concurrent_state_access():
    """Test thread-safe state access"""
```

#### Test 3: FSM State Transitions
**File**: `tests/test_fsm_state_persistence.py`
```python
def test_search_to_refine_constraints_persistence():
    """Specifically test the problematic state transition"""
    
def test_state_transition_rollback():
    """Test rollback on failed state transitions"""
```

### Integration Tests

#### Test 4: End-to-End FSM Flow
**File**: `tests/test_fsm_flow_persistence.py`
```python
def test_complete_purchase_flow_with_persistence():
    """Test full user flow: search → refine → recommend → purchase"""
    
def test_session_recovery_after_interruption():
    """Test FSM recovery after simulated system interruption"""
```

#### Test 5: Session Store Migration
**File**: `tests/test_session_migration.py`
```python
def test_migrate_existing_sessions():
    """Test migration of existing session data"""
    
def test_backward_compatibility():
    """Ensure old sessions still work during transition"""
```

### Mock Strategy

#### Database Mocking
```python
@pytest.fixture
def mock_postgres_session():
    """Mock PostgreSQL session for isolated testing"""
    
@pytest.fixture  
def mock_redis_cache():
    """Mock Redis cache for pipeline testing"""
```

#### FSM Mocking
```python
@pytest.fixture
def mock_fsm_with_known_state():
    """Create FSM in specific state for testing transitions"""
    
@pytest.fixture
def corrupted_session_data():
    """Create corrupted session data for error handling tests"""
```

---

## Test Execution Plan

### Phase 1A: Unit Test Development (1 ACU)
1. Create context serialization tests
2. Develop unified session store tests  
3. Build FSM state transition tests
4. **Validation**: All unit tests pass in isolation

### Phase 1B: Integration Test Development (1 ACU)
1. Create end-to-end FSM flow tests
2. Develop session migration tests
3. Build concurrent access tests
4. **Validation**: Integration tests pass with mocked dependencies

### Phase 1C: Core Implementation (2 ACUs)
1. Implement unified session store
2. Fix context serialization issues
3. Update FSM state transition logic
4. **Validation**: All new tests pass

### Phase 1D: Migration & Validation (1 ACU)
1. Create session migration script
2. Test with existing session data
3. Validate no regressions in existing functionality
4. **Validation**: Complete test suite passes

---

## Success Criteria

### Functional Requirements
- ✅ Zero infinite loop incidents in FSM state transitions
- ✅ 100% state persistence accuracy across user sessions
- ✅ All existing functionality preserved
- ✅ Session recovery works after system interruption

### Technical Requirements  
- ✅ Single unified session storage mechanism
- ✅ Atomic state transitions with rollback capability
- ✅ State integrity validation on save/load
- ✅ Thread-safe concurrent session access

### Testing Requirements
- ✅ >95% code coverage for modified components
- ✅ All unit tests pass in isolation
- ✅ All integration tests pass with real database
- ✅ Performance regression tests pass

---

## Risk Mitigation

### Data Loss Prevention
- **Risk**: Session data corruption during migration
- **Mitigation**: Backup existing sessions before migration, rollback capability

### Performance Impact
- **Risk**: Unified storage adds latency
- **Mitigation**: Benchmark current performance, optimize critical paths

### Backward Compatibility
- **Risk**: Breaking existing sessions
- **Mitigation**: Gradual migration with fallback to old storage

---

## Files to Modify

### Core Implementation
- `contract_engine/context.py` - Fix serialization
- `contract_engine/contract_engine.py` - Update state transitions  
- `orchestrator/session_store.py` - Integrate unified storage
- `contract_engine/session_persistence.py` - Consolidate with unified store

### New Files
- `contract_engine/unified_session_store.py` - New unified storage interface
- `scripts/migrate_session_storage.py` - Migration script

### Test Files
- `tests/test_context_serialization.py` - Context serialization tests
- `tests/test_unified_session_store.py` - Unified store tests
- `tests/test_fsm_state_persistence.py` - FSM persistence tests
- `tests/test_fsm_flow_persistence.py` - End-to-end flow tests
- `tests/test_session_migration.py` - Migration tests

---

## Ready for Implementation

This detailed plan provides:
- ✅ **Isolated testing strategy** for each component
- ✅ **Clear implementation tasks** with specific file targets
- ✅ **Risk mitigation** for data safety and performance
- ✅ **Success criteria** for validation

**Next Step**: Begin Phase 1A (Unit Test Development) upon approval.
