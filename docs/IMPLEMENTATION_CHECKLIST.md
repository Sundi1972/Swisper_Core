# Implementation Checklist

## Step 1: Pipeline Infrastructure ✅ Ready to Start
- [ ] Create `contract_engine/pipelines/` directory
- [ ] Add `ResultLimiterComponent` class
- [ ] Create base pipeline creation functions
- [ ] Write unit tests for new components
- [ ] Verify: `poetry run pytest tests/test_pipeline_infrastructure.py`

## Step 2: Product Search Pipeline
- [ ] Implement `create_product_search_pipeline()`
- [ ] Add result limiting logic (≤50 vs too_many)
- [ ] Update existing components for pipeline use
- [ ] Write integration tests
- [ ] Verify: `poetry run pytest tests/test_product_search_pipeline.py`

## Step 3: Missing Pipeline Components
- [ ] Implement `SpecScraperComponent`
- [ ] Implement `CompatibilityCheckerComponent`
- [ ] Implement `PreferenceRankerComponent`
- [ ] Write unit tests for each
- [ ] Verify: `poetry run pytest tests/test_pipeline_components.py`

## Step 4: Preference Match Pipeline
- [ ] Implement `create_preference_match_pipeline()`
- [ ] Connect preference components
- [ ] Add pipeline orchestration
- [ ] Write integration tests
- [ ] Verify: `poetry run pytest tests/test_preference_match_pipeline.py`

## Step 5: FSM State Structure
- [ ] Break down monolithic `next()` method
- [ ] Add `StateTransition` class
- [ ] Create state-specific functions
- [ ] Ensure existing tests pass
- [ ] Verify: `poetry run pytest tests/test_fsm_integration.py`

## Step 6: FSM + Product Search
- [ ] Replace direct search with pipeline calls
- [ ] Update `search_products` state
- [ ] Add constraint refinement loop
- [ ] Write end-to-end search tests
- [ ] Verify: `poetry run pytest tests/test_fsm_search_integration.py`

## Step 7: FSM + Preference Pipeline
- [ ] Replace preference calls with pipeline
- [ ] Update preference states
- [ ] Add top-3 selection logic
- [ ] Write end-to-end preference tests
- [ ] Verify: `poetry run pytest tests/test_fsm_preference_integration.py`

## Step 8: Orchestrator Integration
- [ ] Modify orchestrator for new FSM
- [ ] Update session management
- [ ] Add pipeline error handling
- [ ] Write orchestrator tests
- [ ] Verify: `poetry run pytest tests/test_orchestrator_integration.py`

## Step 9: Error Handling
- [ ] Add pipeline fallback modes
- [ ] Implement graceful degradation
- [ ] Add user-friendly error messages
- [ ] Write error scenario tests
- [ ] Verify: `poetry run pytest tests/test_error_handling.py`

## Step 10: Memory & Persistence
- [ ] Update session store for new context
- [ ] Add pipeline state persistence
- [ ] Update memory management
- [ ] Write persistence tests
- [ ] Verify: `poetry run pytest tests/test_session_persistence.py`

## Step 11: Performance Optimization
- [ ] Add attribute analysis caching
- [ ] Optimize pipeline execution
- [ ] Add performance monitoring
- [ ] Write performance benchmarks
- [ ] Verify: `poetry run pytest tests/test_performance.py`

## Step 12: Documentation & Final Testing
- [ ] Update README with new architecture
- [ ] Add API documentation
- [ ] Create comprehensive integration tests
- [ ] Run full test suite
- [ ] Verify: `poetry run pytest` (all tests pass)

---

## Current Status: Ready to begin Step 1

**Next Action**: Create pipeline infrastructure and base components
