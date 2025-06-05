# Swisper Purchase Item Contract - Refactoring Plan

## Architectural Vision

**FSM (Control Plane)** – Owns the conversation: tracks contract state, user context, approvals and branching logic. Every state transition is an explicit, auditable Python function.

**Haystack Pipelines (Data Plane)** – Perform stateless data work (search, scrape, filter, rank). Each node is a pure function that receives / returns JSON. Pipelines can be reused by any contract or tool-reasoning path.

*The FSM asks and decides; Pipelines retrieve and transform.*

## Current State Analysis

### Existing Architecture Issues
1. **Mixed Concerns**: FSM directly calls LLM functions instead of using pipelines
2. **Missing Pipeline Abstractions**: No `product_search_pipeline` or `preference_match_pipeline` exist yet
3. **Monolithic FSM**: State machine handles both control logic and data processing
4. **Inconsistent Error Handling**: Some fallbacks exist but not systematically applied

### Current Components That Align
1. **SwisperContext**: Already tracks session state properly
2. **Haystack Components**: Stateless components exist but need pipeline orchestration
3. **Intent Extraction**: Basic routing exists in orchestrator

## Target Architecture

### Phase 1: Pipeline Architecture (Data Plane)
**Goal**: Create the two core pipelines as pure data transformation functions

#### 1.1 Create `product_search_pipeline`
```python
# contract_engine/pipelines/product_search_pipeline.py
def create_product_search_pipeline() -> Pipeline:
    pipeline = Pipeline()
    
    # Node 1: Search Component (Google Shopping ≤100 items)
    pipeline.add_node("search", MockGoogleShoppingComponent(), inputs=["Query"])
    
    # Node 2: Attribute Analyzer (detect key attributes & ranges)
    pipeline.add_node("analyze_attributes", AttributeAnalyzerComponent(), inputs=["search"])
    
    # Node 3: Result Limiter (if ≤50 pass, else return too_many_results)
    pipeline.add_node("limit_results", ResultLimiterComponent(), inputs=["analyze_attributes"])
    
    return pipeline
```

#### 1.2 Create `preference_match_pipeline`
```python
# contract_engine/pipelines/preference_match_pipeline.py  
def create_preference_match_pipeline() -> Pipeline:
    pipeline = Pipeline()
    
    # Node 1: Spec Scraper (enhance with web data)
    pipeline.add_node("scrape_specs", SpecScraperComponent(), inputs=["Query"])
    
    # Node 2: Compatibility Checker (hard constraints)
    pipeline.add_node("check_compat", CompatibilityCheckerComponent(), inputs=["scrape_specs"])
    
    # Node 3: Preference Ranker (soft prefs → LLM score 0-1)
    pipeline.add_node("rank_prefs", PreferenceRankerComponent(), inputs=["check_compat"])
    
    return pipeline
```

### Phase 2: FSM Refactoring (Control Plane)
**Goal**: Pure state machine that orchestrates pipelines

#### 2.1 Simplified FSM States
```python
class PurchaseItemFSM:
    STATES = [
        "extract_entities",      # Extract product + constraints from user input
        "search_products",       # Call product_search_pipeline
        "refine_constraints",    # If too_many_results, ask for more constraints (max 3x)
        "collect_preferences",   # Ask for soft preferences if not provided
        "match_preferences",     # Call preference_match_pipeline  
        "present_options",       # LLM recommendation + user selection
        "confirm_purchase",      # Final confirmation + Whisper auth if >CHF 500
        "complete_order",        # Checkout tool + order_id + Signals event
        "cancelled",             # Terminal state
        "completed"              # Terminal state
    ]
```

## Implementation Steps (Chunked for Separate Commits)

### Step 1: Create Pipeline Infrastructure
**Commit**: "Add pipeline infrastructure and base components"
- Create `contract_engine/pipelines/` directory
- Add `ResultLimiterComponent` to haystack_components.py
- Add base pipeline creation functions (empty implementations)
- **Test**: Unit tests for new components
- **Verification**: `poetry run pytest tests/test_pipeline_infrastructure.py`

### Step 2: Implement Product Search Pipeline
**Commit**: "Implement product search pipeline with result limiting"
- Complete `create_product_search_pipeline()` implementation
- Add result limiting logic (≤50 items vs too_many_results)
- Update existing components to work in pipeline
- **Test**: Integration test for product search pipeline
- **Verification**: `poetry run pytest tests/test_product_search_pipeline.py`

### Step 3: Add Missing Pipeline Components
**Commit**: "Add spec scraper and compatibility checker components"
- Implement `SpecScraperComponent`
- Implement `CompatibilityCheckerComponent` 
- Implement `PreferenceRankerComponent`
- **Test**: Unit tests for each new component
- **Verification**: `poetry run pytest tests/test_pipeline_components.py`

### Step 4: Implement Preference Match Pipeline
**Commit**: "Implement preference matching pipeline"
- Complete `create_preference_match_pipeline()` implementation
- Connect all preference matching components
- Add pipeline orchestration logic
- **Test**: Integration test for preference pipeline
- **Verification**: `poetry run pytest tests/test_preference_match_pipeline.py`

### Step 5: Refactor FSM State Structure
**Commit**: "Refactor FSM to use explicit state functions"
- Break down monolithic `next()` method into state-specific functions
- Add `StateTransition` class for clean state changes
- Keep existing functionality but organize better
- **Test**: Existing FSM tests should still pass
- **Verification**: `poetry run pytest tests/test_fsm_integration.py`

### Step 6: Connect FSM to Product Search Pipeline
**Commit**: "Connect FSM to product search pipeline"
- Replace direct search calls with pipeline calls in FSM
- Update `search_products` state to use pipeline
- Add constraint refinement loop (max 3 iterations)
- **Test**: End-to-end test for search flow
- **Verification**: `poetry run pytest tests/test_fsm_search_integration.py`

### Step 7: Connect FSM to Preference Pipeline
**Commit**: "Connect FSM to preference matching pipeline"
- Replace direct preference calls with pipeline calls
- Update preference collection and matching states
- Add top-3 product selection logic
- **Test**: End-to-end test for preference flow
- **Verification**: `poetry run pytest tests/test_fsm_preference_integration.py`

### Step 8: Update Orchestrator Integration
**Commit**: "Update orchestrator to use new FSM architecture"
- Modify orchestrator to initialize FSM with pipelines
- Update session management for new context structure
- Add proper error handling for pipeline failures
- **Test**: Full orchestrator integration test
- **Verification**: `poetry run pytest tests/test_orchestrator_integration.py`

### Step 9: Add Comprehensive Error Handling
**Commit**: "Add comprehensive error handling and fallbacks"
- Add fallback modes for all pipeline components
- Implement graceful degradation when LLM unavailable
- Add user-friendly error messages
- **Test**: Error scenario tests
- **Verification**: `poetry run pytest tests/test_error_handling.py`

### Step 10: Memory and Persistence Updates
**Commit**: "Update session storage for new architecture"
- Modify session store to handle new context structure
- Add pipeline state persistence if needed
- Update memory management for vector summaries
- **Test**: Session persistence tests
- **Verification**: `poetry run pytest tests/test_session_persistence.py`

### Step 11: Performance Optimization
**Commit**: "Optimize pipeline performance and caching"
- Add caching for attribute analysis per category
- Optimize pipeline execution order
- Add performance monitoring
- **Test**: Performance benchmarks
- **Verification**: `poetry run pytest tests/test_performance.py`

### Step 12: Documentation and Final Testing
**Commit**: "Add documentation and comprehensive test suite"
- Update README with new architecture
- Add API documentation for pipelines
- Create comprehensive integration tests
- **Test**: Full test suite
- **Verification**: `poetry run pytest` (all tests)

## Testing Strategy

Each step includes:
1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test pipeline flows end-to-end
3. **Regression Tests**: Ensure existing functionality still works
4. **Error Tests**: Verify graceful handling of failures

## Benefits of This Chunked Approach

1. **Incremental Progress**: Each commit adds value and can be tested
2. **Easy Rollback**: If a step fails, only that step needs to be reverted
3. **Parallel Development**: Different team members can work on different steps
4. **Clear Milestones**: Progress is visible and measurable
5. **Reduced Risk**: Smaller changes are easier to debug and validate

## Next Steps

1. Start with Step 1 (Pipeline Infrastructure)
2. Get approval for each step before proceeding
3. Run full test suite after each commit
4. Document any deviations from the plan as we discover them

---
*This plan implements the 20-step end-to-end flow specified in the architectural requirements while maintaining backward compatibility and ensuring comprehensive testing at each stage.*
