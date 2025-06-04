# FSM State Persistence Debugging Session Summary

**Date**: June 4, 2025  
**Session Focus**: Debugging FSM infinite loop and state persistence issues in Swisper Core contract flow

## Problem Overview

The Finite State Machine (FSM) contract flow is stuck in an infinite loop, preventing users from completing purchase transactions.

### Core Issues Identified

1. **Infinite Loop**: FSM cycles endlessly between `search → refine_constraints → search → refine_constraints`
2. **State Persistence Bug**: FSM correctly saves "refine_constraints" state but retrieves "search" state on next user interaction
3. **No Flow Progression**: Users never see product recommendations or complete purchases
4. **Broken State Transitions**: System collects preferences but cannot progress to matching/selection phases

## What Was Successfully Implemented

### ✅ Working Features
- **LLM Preference Generation**: Replaced hardcoded preference messages with dynamic LLM-generated content
- **20-Result Threshold**: Correctly triggers preference refinement when >20 search results found
- **Search Pipeline**: Successfully finds and returns product results (25 RTX 4070 models)
- **Initial State Transitions**: FSM correctly transitions from `search` to `refine_constraints`
- **Context Storage**: FSM context is properly serialized and stored in PostgreSQL

### ✅ Technical Improvements
- Reduced search result threshold from 50 to 20 results
- Added `generate_preference_refinement_message()` function for dynamic messaging
- Enhanced logging throughout FSM state transitions
- Improved session persistence with explicit context parameter in ContractStateMachine constructor
- Added refinement attempt counter logic (limit of 2 attempts)

## Current Problems

### ❌ Critical Issues

1. **State Retrieval Bug**: 
   - FSM stores state as "refine_constraints" 
   - Next interaction retrieves state as "search"
   - Logs show: "Storing FSM context with state=refine_constraints" but "Retrieved context data with state=search"

2. **Infinite Loop Mechanism**:
   - User input triggers search state instead of refine_constraints state
   - `handle_refine_constraints_state()` never receives user input
   - System continuously asks for preferences without processing them

3. **Session Storage Conflicts**:
   - Multiple session storage mechanisms may be conflicting
   - PostgreSQL session store vs legacy session persistence
   - State reconstruction not maintaining correct FSM state

## Technical Details

### FSM State Flow (Current vs Expected)

**Current Broken Flow**:
```
search → refine_constraints (stored) → search (retrieved) → refine_constraints (stored) → ...
```

**Expected Flow**:
```
search → refine_constraints → refine_constraints (with user input) → match_preferences → recommendations
```

### Key Files Modified

1. **contract_engine/contract_engine.py**: Enhanced FSM state handling and LLM integration
2. **contract_engine/llm_helpers.py**: Added dynamic preference message generation
3. **orchestrator/core.py**: Removed conflicting legacy session loading
4. **orchestrator/postgres_session_store.py**: Enhanced FSM state persistence logging
5. **orchestrator/session_store.py**: Improved context restoration mechanism

### Browser Testing Results

- **RTX 4070 Search**: Consistently finds 25 results, triggers refinement
- **User Preferences**: System asks for preferences but never processes them
- **LLM Messages**: Dynamic messages work correctly instead of hardcoded text
- **State Persistence**: Visible infinite loop in browser interface

## Root Cause Analysis

The fundamental issue appears to be in the state persistence mechanism where:
1. FSM correctly transitions to "refine_constraints" state
2. State is properly saved to PostgreSQL with correct context
3. On next user interaction, state is retrieved as "search" instead of "refine_constraints"
4. This causes the FSM to restart the search process instead of handling user preferences

## Next Steps Required

1. **Architectural Review**: Design proper FSM state persistence architecture
2. **State Storage Audit**: Identify and resolve conflicting session storage mechanisms
3. **Flow Redesign**: Ensure proper state transitions through complete purchase flow
4. **Testing Framework**: Implement comprehensive FSM state transition testing

## Configuration Files

Example configuration files are stored in this docs folder:
- `example-docker-compose.yml` - Docker composition template

Note: For environment variables, copy the main `.env` file and replace API keys with placeholder values.

## Session Outcome

While LLM preference generation was successfully implemented, the core FSM state persistence issue remains unresolved. The system requires architectural redesign to fix the infinite loop and enable complete purchase transactions.
