# Debug Utilities

This directory contains debugging utilities and diagnostic scripts for troubleshooting the Swisper Core system.

## Available Debug Scripts

### Core System Debugging
- **`debug_complete_flow.py`** - Tests the complete orchestrator flow end-to-end
- **`debug_fsm_retrieval.py`** - Debugs Finite State Machine session persistence and retrieval
- **`debug_intent_classification.py`** - Tests intent classification and routing mechanisms
- **`debug_llm_adapter.py`** - Tests OpenAI API integration and LLM adapter functionality
- **`debug_preference_extraction.py`** - Tests user preference parsing for various product scenarios

### Configuration & Utilities
- **`debug_logging_config.py`** - Sets up comprehensive logging for debugging sessions

### Test Debugging
- **`test_intent_debug.py`** - Debug version of intent classification tests
- **`test_preference_restructure_fix.py`** - Debugging contract flow and state transitions
- **`test_websearch_manual.py`** - Manual testing utilities for websearch functionality

## Usage

Run debug scripts individually to isolate and troubleshoot specific issues:

```bash
# Test intent classification
python tests/debug/debug_intent_classification.py

# Test LLM adapter connectivity
python tests/debug/debug_llm_adapter.py

# Test preference extraction
python tests/debug/debug_preference_extraction.py

# Test complete flow
python tests/debug/debug_complete_flow.py

# Test FSM session persistence
python tests/debug/debug_fsm_retrieval.py
```

## Environment Setup

Most debug scripts require environment variables:
- `OpenAI_API_Key` - OpenAI API key for LLM functionality
- Other API keys as needed for specific integrations

## Common Issues Addressed

1. **FSM State Persistence** - Session retrieval and state management problems
2. **Intent Classification** - Routing accuracy and classification issues
3. **LLM Integration** - OpenAI API connectivity and response handling
4. **Preference Extraction** - User constraint parsing and product matching
5. **Complete Flow** - End-to-end orchestrator workflow validation
