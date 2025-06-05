# Swisper Core Refactoring - Implementation Steps

This document breaks down the comprehensive refactoring plan into smaller, independently testable and committable chunks.

## Overview

The refactoring transforms the Swisper Core contract engine from a monolithic FSM to a clean architecture with:
- **FSM (Control Plane)**: Manages conversation flow and state transitions
- **Haystack Pipelines (Data Plane)**: Handle stateless data processing

## Implementation Phases

### Phase 1: Pipeline Infrastructure ✅ COMPLETED
**Status**: All tasks completed and tested
- [x] Create pipeline directory structure
- [x] Implement `ResultLimiterComponent`
- [x] Create base pipeline functions
- [x] Write comprehensive tests

### Phase 2: Product Search Pipeline ✅ COMPLETED  
**Status**: All tasks completed and tested
- [x] Implement `create_product_search_pipeline()`
- [x] Add result limiting logic (≤50 vs too_many)
- [x] Write integration tests
- [x] Verify pipeline connectivity

### Phase 3: Missing Pipeline Components ✅ COMPLETED
**Status**: All tasks completed and tested
- [x] Implement `SpecScraperComponent`
- [x] Enhance `CompatibilityCheckerComponent`
- [x] Implement `PreferenceRankerComponent`
- [x] Write comprehensive unit tests

---

## Remaining Implementation Steps

### Step 4: Preference Match Pipeline
**Estimated Time**: 2-3 hours
**Dependencies**: Step 3 completed

#### Tasks:
1. **Create preference match pipeline** (30 min)
   - Implement `create_preference_match_pipeline()` in new file
   - Connect SpecScraper → CompatibilityChecker → PreferenceRanker
   - Add pipeline orchestration logic

2. **Add pipeline runner function** (30 min)
   - Implement `run_preference_match()` async function
   - Handle pipeline errors and fallbacks
   - Return structured results

3. **Write integration tests** (60 min)
   - Test complete pipeline flow
   - Test error handling scenarios
   - Test with/without preferences

4. **Verify implementation** (30 min)
   - Run: `poetry run pytest tests/test_preference_match_pipeline.py`
   - Ensure all tests pass

#### Success Criteria:
- Pipeline processes products through all 3 components
- Returns top 3 ranked products with scores
- Handles errors gracefully with fallbacks
- All tests pass

#### Commit Message:
```
Step 4: Implement preference match pipeline

- Create preference_match_pipeline.py with component orchestration
- Add async run_preference_match() function with error handling
- Write comprehensive integration tests
- Verify pipeline connectivity and data flow
```

---

### Step 5: FSM State Structure Refactoring
**Estimated Time**: 3-4 hours
**Dependencies**: Step 4 completed

#### Tasks:
1. **Create StateTransition class** (45 min)
   - Define clear state transition data structure
   - Include next_state, user_message, context_updates
   - Add validation and helper methods

2. **Break down monolithic next() method** (90 min)
   - Extract state-specific handler functions
   - Create `handle_extract_entities()`, `handle_search_products()`, etc.
   - Maintain existing functionality

3. **Update state management** (60 min)
   - Modify FSM to use new state handlers
   - Ensure backward compatibility
   - Add comprehensive logging

4. **Write state transition tests** (45 min)
   - Test each state handler independently
   - Verify state transitions work correctly
   - Test error scenarios

#### Success Criteria:
- FSM uses explicit state handler functions
- All existing tests continue to pass
- New state transition tests pass
- No regression in functionality

#### Commit Message:
```
Step 5: Refactor FSM state structure with explicit transitions

- Add StateTransition class for structured state changes
- Break down monolithic next() method into state handlers
- Maintain backward compatibility with existing functionality
- Add comprehensive state transition tests
```

---

### Step 6: FSM + Product Search Integration
**Estimated Time**: 2-3 hours
**Dependencies**: Step 5 completed

#### Tasks:
1. **Replace direct search calls** (60 min)
   - Update `handle_search_products()` to use pipeline
   - Remove direct LLM calls from FSM
   - Add pipeline error handling

2. **Implement constraint refinement loop** (60 min)
   - Add logic for too_many_results handling
   - Implement max 3 refinement iterations
   - Add user prompting for additional constraints

3. **Update search state handlers** (45 min)
   - Modify `handle_refine_constraints()` state
   - Add attribute discovery and storage
   - Ensure smooth state transitions

4. **Write end-to-end search tests** (45 min)
   - Test complete search flow with constraints
   - Test refinement loop scenarios
   - Test error handling and fallbacks

#### Success Criteria:
- FSM uses product search pipeline exclusively
- Constraint refinement loop works correctly
- No direct LLM calls in search logic
- All search tests pass

#### Commit Message:
```
Step 6: Integrate FSM with product search pipeline

- Replace direct search calls with pipeline integration
- Implement constraint refinement loop (max 3 iterations)
- Add comprehensive error handling and fallbacks
- Write end-to-end search integration tests
```

---

### Step 7: FSM + Preference Pipeline Integration
**Estimated Time**: 2-3 hours
**Dependencies**: Step 6 completed

#### Tasks:
1. **Replace preference calls with pipeline** (60 min)
   - Update `handle_match_preferences()` to use pipeline
   - Remove direct LLM preference calls
   - Add pipeline result processing

2. **Implement top-3 selection logic** (45 min)
   - Process pipeline ranking results
   - Format for user presentation
   - Add recommendation generation

3. **Update preference state handlers** (45 min)
   - Modify `handle_collect_preferences()` state
   - Add preference validation and storage
   - Ensure smooth state transitions

4. **Write end-to-end preference tests** (60 min)
   - Test complete preference flow
   - Test with/without user preferences
   - Test ranking and selection logic

#### Success Criteria:
- FSM uses preference match pipeline exclusively
- Top-3 product selection works correctly
- No direct LLM calls in preference logic
- All preference tests pass

#### Commit Message:
```
Step 7: Integrate FSM with preference match pipeline

- Replace direct preference calls with pipeline integration
- Implement top-3 product selection and ranking
- Add comprehensive preference handling logic
- Write end-to-end preference integration tests
```

---

### Step 8: Orchestrator Integration
**Estimated Time**: 2 hours
**Dependencies**: Step 7 completed

#### Tasks:
1. **Update orchestrator for new FSM** (45 min)
   - Modify contract instantiation to use pipelines
   - Update session management for new context
   - Add pipeline initialization

2. **Add pipeline error handling** (30 min)
   - Implement graceful degradation
   - Add fallback mechanisms
   - Ensure system resilience

3. **Update session management** (30 min)
   - Modify context serialization/deserialization
   - Update session persistence logic
   - Maintain backward compatibility

4. **Write orchestrator tests** (45 min)
   - Test contract initialization
   - Test pipeline integration
   - Test error scenarios

#### Success Criteria:
- Orchestrator properly initializes new FSM
- Pipeline errors are handled gracefully
- Session management works correctly
- All orchestrator tests pass

#### Commit Message:
```
Step 8: Update orchestrator for new FSM architecture

- Modify contract instantiation to use pipeline architecture
- Add comprehensive pipeline error handling
- Update session management for new context structure
- Write orchestrator integration tests
```

---

### Step 9: Error Handling & Resilience
**Estimated Time**: 2 hours
**Dependencies**: Step 8 completed

#### Tasks:
1. **Add pipeline fallback modes** (45 min)
   - Implement degraded operation when LLM unavailable
   - Add caching for attribute analysis
   - Ensure basic functionality always works

2. **Implement graceful degradation** (45 min)
   - Add fallback recommendation logic
   - Implement basic product filtering
   - Maintain user experience quality

3. **Add user-friendly error messages** (30 min)
   - Create clear error communication
   - Add helpful suggestions for users
   - Maintain conversation flow

4. **Write error scenario tests** (30 min)
   - Test all fallback mechanisms
   - Test degraded operation modes
   - Verify user experience quality

#### Success Criteria:
- System works without OpenAI API key
- Fallback mechanisms provide good user experience
- Error messages are clear and helpful
- All error scenario tests pass

#### Commit Message:
```
Step 9: Add comprehensive error handling and resilience

- Implement pipeline fallback modes for degraded operation
- Add graceful degradation when LLM services unavailable
- Create user-friendly error messages and suggestions
- Write comprehensive error scenario tests
```

---

### Step 10: Performance & Optimization
**Estimated Time**: 1-2 hours
**Dependencies**: Step 9 completed

#### Tasks:
1. **Add attribute analysis caching** (30 min)
   - Implement persistent cache for product attributes
   - Add cache invalidation logic
   - Optimize repeated analysis calls

2. **Optimize pipeline execution** (30 min)
   - Add parallel processing where possible
   - Optimize component data flow
   - Reduce unnecessary processing

3. **Add performance monitoring** (30 min)
   - Add timing metrics for pipeline stages
   - Implement performance logging
   - Add bottleneck identification

4. **Write performance benchmarks** (30 min)
   - Create performance test suite
   - Set performance baselines
   - Verify optimization effectiveness

#### Success Criteria:
- Pipeline execution time improved by 20%+
- Caching reduces redundant processing
- Performance monitoring provides insights
- Benchmarks show measurable improvements

#### Commit Message:
```
Step 10: Add performance optimization and monitoring

- Implement attribute analysis caching for efficiency
- Optimize pipeline execution with parallel processing
- Add comprehensive performance monitoring and metrics
- Create performance benchmark test suite
```

---

### Step 11: Documentation & Final Testing
**Estimated Time**: 1-2 hours
**Dependencies**: Step 10 completed

#### Tasks:
1. **Update README with new architecture** (30 min)
   - Document FSM and Pipeline separation
   - Add architecture diagrams
   - Update setup instructions

2. **Add API documentation** (30 min)
   - Document pipeline interfaces
   - Add usage examples
   - Create developer guide

3. **Create comprehensive integration tests** (45 min)
   - Test complete user scenarios
   - Test all error paths
   - Verify end-to-end functionality

4. **Run full test suite** (15 min)
   - Execute: `poetry run pytest`
   - Verify all tests pass
   - Check test coverage

#### Success Criteria:
- Documentation is complete and accurate
- All tests pass (100% success rate)
- Test coverage meets requirements
- System ready for production

#### Commit Message:
```
Step 11: Complete documentation and final testing

- Update README with new FSM/Pipeline architecture
- Add comprehensive API documentation and examples
- Create complete integration test suite
- Verify 100% test success rate
```

---

## Testing Strategy

### Per-Step Testing
Each step includes:
- **Unit Tests**: Test individual components
- **Integration Tests**: Test component interactions
- **Regression Tests**: Ensure no functionality loss

### Continuous Verification
- Run tests after each commit
- Verify no regressions introduced
- Maintain test coverage above 90%

### End-to-End Testing
- Test complete user scenarios
- Verify system resilience
- Validate performance requirements

## Risk Mitigation

### Rollback Strategy
- Each step is independently committable
- Can rollback to any previous working state
- Maintain backward compatibility throughout

### Dependency Management
- Clear step dependencies defined
- No circular dependencies
- Can pause/resume at any step

### Quality Assurance
- Comprehensive test coverage
- Code review for each step
- Performance validation

## Success Metrics

### Technical Metrics
- All tests pass (100% success rate)
- No performance regression
- Clean separation of concerns achieved

### Architectural Metrics
- FSM only handles control logic
- Pipelines only handle data processing
- Clear, testable interfaces

### Maintainability Metrics
- Reduced code complexity
- Improved test coverage
- Better error handling
