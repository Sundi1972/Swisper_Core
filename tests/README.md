# Tests Directory Structure

This directory contains all tests for the Swisper Core project, organized by category:

## Directory Structure

- **`unit/`** - Unit tests for individual components that don't require external dependencies
- **`integration/`** - Integration tests that verify component interactions and full workflows
- **`performance/`** - Performance tests focused on metrics, caching, and optimization
- **`debug/`** - Debugging utilities and diagnostic scripts

## Running Tests

### All Tests
```bash
poetry run pytest tests/
```

### By Category
```bash
# Unit tests only
poetry run pytest tests/unit/

# Integration tests only
poetry run pytest tests/integration/

# Performance tests only
poetry run pytest tests/performance/
```

### Debug Utilities
Debug scripts in `tests/debug/` are standalone utilities for troubleshooting:
```bash
# Run individual debug scripts
python tests/debug/debug_intent_classification.py
python tests/debug/debug_llm_adapter.py
```

## Test Organization Guidelines

- **Unit tests**: Test individual functions, classes, or modules in isolation
- **Integration tests**: Test complete workflows and component interactions
- **Performance tests**: Measure and validate performance characteristics
- **Debug utilities**: Diagnostic tools for troubleshooting specific issues

Each test category should be runnable independently and not depend on tests from other categories.
