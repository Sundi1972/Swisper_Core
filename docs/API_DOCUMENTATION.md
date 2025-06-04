# Swisper Core API Documentation

## Overview

Swisper Core provides a modular pipeline architecture for product search and recommendation contracts. This document covers the key APIs for pipeline components, FSM state management, and session persistence.

## Pipeline Components API

### Product Search Pipeline

#### `create_product_search_pipeline()`
Creates a pipeline for product search with attribute analysis and result limiting.

```python
from contract_engine.pipelines.product_search_pipeline import create_product_search_pipeline

pipeline = create_product_search_pipeline()
result = await pipeline.run(
    query="gaming laptop",
    hard_constraints=["price < 2000 CHF", "brand = ASUS"]
)
```

**Returns:**
```python
{
    "status": "success" | "too_many_results" | "error",
    "items": [{"name": str, "price": str, "url": str, ...}],
    "attributes": [str],  # Discovered product attributes
    "execution_time": float
}
```

### Preference Match Pipeline

#### `create_preference_match_pipeline()`
Creates a pipeline for preference-based product ranking and selection.

```python
from contract_engine.pipelines.preference_match_pipeline import create_preference_match_pipeline

pipeline = create_preference_match_pipeline()
result = await pipeline.run(
    items=[...],  # Product list from search pipeline
    preferences={"brand": "Apple", "screen_size": "15 inch"}
)
```

**Returns:**
```python
{
    "status": "success" | "fallback" | "error",
    "ranked_products": [{"name": str, "score": float, ...}],
    "ranking_method": "llm" | "fallback",
    "execution_time": float
}
```

## Pipeline Components

### SearchComponent
Searches products using Google Shopping API.

```python
from contract_engine.haystack_components import SearchComponent

component = SearchComponent()
result = component.run(query="laptop", max_results=100)
```

### AttributeAnalyzerComponent
Analyzes product attributes with intelligent caching.

```python
from contract_engine.haystack_components import AttributeAnalyzerComponent

component = AttributeAnalyzerComponent()
result = component.run(products=[...], query="gaming laptop")
```

**Features:**
- 60-minute TTL caching for attribute analysis
- LLM-based attribute extraction with category fallbacks
- Performance monitoring integration

### CompatibilityCheckerComponent
Validates products against hard constraints.

```python
from contract_engine.haystack_components import CompatibilityCheckerComponent

component = CompatibilityCheckerComponent()
result = component.run(
    products=[...],
    constraints=["price < 2000 CHF", "brand = Apple"]
)
```

### PreferenceRankerComponent
Ranks products based on soft preferences using LLM scoring.

```python
from contract_engine.haystack_components import PreferenceRankerComponent

component = PreferenceRankerComponent()
result = component.run(
    products=[...],
    preferences={"brand": "Apple", "performance": "high"},
    top_k=3
)
```

## FSM State Management API

### ContractStateMachine
Main FSM class for managing contract flow.

```python
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.context import SwisperContext

fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
fsm.context = SwisperContext(
    session_id="session_123",
    product_query="gaming laptop",
    preferences={"brand": "ASUS"}
)

result = fsm.next("I want to buy a gaming laptop")
```

### State Transition API

#### StateTransition Class
Encapsulates state transition results.

```python
from contract_engine.state_transitions import StateTransition

transition = StateTransition(
    next_state="search",
    user_message="Starting product search...",
    internal_data={"search_query": "laptop"}
)
```

#### State Handler Methods
Each FSM state has a dedicated handler method:

- `handle_start_state()` - Initial product validation
- `handle_search_state()` - Product search execution
- `handle_match_preferences_state()` - Preference-based ranking
- `handle_confirm_selection_state()` - User selection confirmation
- `handle_complete_state()` - Order completion

## Session Persistence API

### Enhanced Session Management

#### `save_session_context(session_id, context)`
Saves enhanced session context with pipeline metadata.

```python
from contract_engine.session_persistence import save_session_context

save_session_context("session_123", fsm.context)
```

#### `load_session_context(session_id)`
Loads session context with pipeline execution history.

```python
from contract_engine.session_persistence import load_session_context

context = load_session_context("session_123")
if context:
    fsm.context = context
```

#### `save_pipeline_execution(session_id, pipeline_name, result, execution_time)`
Records pipeline execution for session recovery.

```python
from contract_engine.session_persistence import save_pipeline_execution

save_pipeline_execution(
    "session_123", 
    "product_search", 
    search_result, 
    2.5
)
```

### SwisperContext API
Enhanced context class with pipeline metadata tracking.

```python
from contract_engine.context import SwisperContext

context = SwisperContext(
    session_id="session_123",
    product_query="laptop",
    preferences={"brand": "Apple"}
)

# Record pipeline execution
context.record_pipeline_execution("product_search", result, 2.5)

# Get pipeline history
history = context.get_pipeline_history("product_search")

# Get last pipeline result
last_result = context.get_last_pipeline_result("product_search")

# Get performance metrics
metrics = context.pipeline_performance_metrics
```

## Performance Monitoring API

### PerformanceCache
Thread-safe caching with TTL support.

```python
from contract_engine.performance_monitor import PerformanceCache

cache = PerformanceCache(default_ttl_minutes=30)
cache.set("key", value)
cached_value = cache.get("key")
```

### PipelineTimer
Context manager for timing operations.

```python
from contract_engine.performance_monitor import PipelineTimer

with PipelineTimer("product_search") as timer:
    result = await search_pipeline.run(query="laptop")
    
print(f"Search took {timer.duration:.2f} seconds")
```

### PerformanceMonitor
Global performance metrics collection.

```python
from contract_engine.performance_monitor import PerformanceMonitor

# Record operation
PerformanceMonitor.record_operation("product_search", 2.5)

# Get statistics
stats = PerformanceMonitor.get_stats("product_search")
# Returns: {"count": 10, "avg_duration": 2.3, "min_duration": 1.8, ...}

# Get all statistics
all_stats = PerformanceMonitor.get_all_stats()
```

### Performance Decorators

#### `@timed_operation(operation_name)`
Automatically times function execution.

```python
from contract_engine.performance_monitor import timed_operation

@timed_operation("attribute_analysis")
def analyze_attributes(products):
    # Function implementation
    return attributes
```

#### `@cached_operation(cache, key_func=None)`
Caches function results with TTL.

```python
from contract_engine.performance_monitor import cached_operation, attribute_cache

@cached_operation(attribute_cache)
def expensive_analysis(products, query):
    # Expensive computation
    return result
```

## Error Handling API

### SystemHealthMonitor
Tracks external service availability.

```python
from contract_engine.error_handling import health_monitor

# Check service health
is_healthy = health_monitor.is_service_healthy("openai_api")

# Record service failure
health_monitor.record_failure("openai_api", "API timeout")

# Get health status
status = health_monitor.get_health_status()
```

### Error Handling Functions

#### `create_user_friendly_error_message(error_type, context=None)`
Creates user-friendly error messages.

```python
from contract_engine.error_handling import create_user_friendly_error_message

message = create_user_friendly_error_message(
    "search_failed", 
    {"query": "laptop"}
)
```

#### `get_degraded_operation_message(operation)`
Gets degraded operation messages.

```python
from contract_engine.error_handling import get_degraded_operation_message

message = get_degraded_operation_message("preference_ranking")
```

## Orchestrator API

### SwisperOrchestrator
Main orchestrator for intent routing and session management.

```python
from orchestrator.core import SwisperOrchestrator

orchestrator = SwisperOrchestrator()
response = await orchestrator.process_message(
    session_id="session_123",
    message="I want to buy a laptop",
    user_profile={"preferences": {"brand": "Apple"}}
)
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key for LLM operations
- `GOOGLE_SHOPPING_API_KEY` - Google Shopping API key
- `DATABASE_URL` - PostgreSQL connection string for session storage

### Pipeline Configuration
Pipeline behavior can be configured through environment variables:

- `ATTRIBUTE_CACHE_TTL_MINUTES` - Attribute analysis cache TTL (default: 60)
- `PIPELINE_CACHE_TTL_MINUTES` - Pipeline result cache TTL (default: 30)
- `MAX_SEARCH_RESULTS` - Maximum search results (default: 100)
- `RESULT_LIMIT_THRESHOLD` - Result limiting threshold (default: 50)

## Testing

### Running Tests
```bash
# All tests
poetry run pytest

# Specific test suites
poetry run pytest tests/test_performance.py
poetry run pytest tests/test_pipeline_components.py
poetry run pytest tests/test_fsm_integration.py
poetry run pytest tests/test_session_persistence.py
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Pipeline and FSM integration
- **Performance Tests**: Caching and timing verification
- **Error Handling Tests**: Fallback and resilience testing
- **Session Tests**: Persistence and recovery testing

## Examples

### Complete Contract Flow
```python
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.context import SwisperContext
from contract_engine.pipelines.product_search_pipeline import create_product_search_pipeline
from contract_engine.pipelines.preference_match_pipeline import create_preference_match_pipeline

# Initialize FSM with pipelines
fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
fsm.product_search_pipeline = create_product_search_pipeline()
fsm.preference_match_pipeline = create_preference_match_pipeline()

# Set up context
fsm.context = SwisperContext(
    session_id="demo_session",
    product_query="gaming laptop",
    constraints=["price < 2500 CHF"],
    preferences={"brand": "ASUS", "screen_size": "15 inch"}
)

# Process user input
result = fsm.next("I want to buy a gaming laptop under 2500 CHF")
print(result["user_message"])

# Continue conversation
result = fsm.next("I prefer ASUS brand with 15 inch screen")
print(result["user_message"])
```

### Custom Pipeline Component
```python
from haystack import component
from typing import List, Dict, Any

@component
class CustomFilterComponent:
    @component.output_types(filtered_products=List[Dict[str, Any]])
    def run(self, products: List[Dict[str, Any]], filter_criteria: Dict[str, Any]):
        filtered = []
        for product in products:
            if self._matches_criteria(product, filter_criteria):
                filtered.append(product)
        
        return {"filtered_products": filtered}
    
    def _matches_criteria(self, product: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        # Custom filtering logic
        return True
```
