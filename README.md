# Swisper Core

Swisper contract engine backend with modular pipeline architecture.

## Architecture Overview

Swisper Core implements a clean separation between the **Finite State Machine (FSM)** as a control plane and **Haystack Pipelines** as a data plane:

- **FSM (Control Plane)**: Manages conversation flow, user context, approvals, and state transitions
- **Pipelines (Data Plane)**: Handle stateless data processing (search, scrape, filter, rank)

## Components

### Core Components
- **Contract Engine**: FSM-based contract flow management with explicit state transitions
- **Gateway**: FastAPI-based API gateway with session management
- **Haystack Pipeline**: Modular data processing pipelines for product search and preference matching
- **Orchestrator**: Intent routing and session orchestration
- **Tool Adapter**: External service integrations (Google Shopping, checkout tools)

### Pipeline Architecture

#### Product Search Pipeline
```
SearchComponent → AttributeAnalyzer → ResultLimiter
```
- Searches products via Google Shopping API
- Analyzes product attributes and ranges
- Limits results (≤50 products) or requests constraint refinement

#### Preference Match Pipeline
```
SpecScraper → CompatibilityChecker → PreferenceRanker
```
- Scrapes detailed product specifications
- Validates hard constraints compatibility
- Ranks products by soft preferences using LLM scoring

## Key Features

### Performance Optimization
- **Intelligent Caching**: 60-minute TTL for attribute analysis, 30-minute for pipeline results
- **Performance Monitoring**: Comprehensive timing and metrics collection
- **Graceful Degradation**: Fallback mechanisms when external services unavailable

### Session Management
- **Enhanced Persistence**: Pipeline execution history and performance metrics
- **Automatic Cleanup**: 24-hour session retention with expired data removal
- **Context Recovery**: Session restoration with cached pipeline results

### Error Handling & Resilience
- **Health Monitoring**: System health tracking for external services
- **User-Friendly Errors**: Clear error messages for common failure scenarios
- **Fallback Modes**: Graceful degradation when LLM or web services fail

## Quick Start

### Installation
```bash
poetry install
```

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_performance.py          # Performance tests
poetry run pytest tests/test_pipeline_components.py # Pipeline component tests
poetry run pytest tests/test_fsm_integration.py     # FSM integration tests
```

### Development
```bash
# Run linting
poetry run pylint contract_engine gateway haystack_pipeline orchestrator tool_adapter

# Start development server
poetry run python gateway/main.py
```

## Architecture Benefits

### Separation of Concerns
- FSM handles conversation logic, pipelines handle data processing
- Clear boundaries between control flow and data transformation
- Reusable pipeline components across different contracts

### Testability & Maintainability
- Each pipeline component is a pure function with clear inputs/outputs
- State transitions are explicit and auditable
- Comprehensive test coverage with isolated unit tests

### Performance & Scalability
- Pipeline results cached to reduce redundant processing
- Performance monitoring for optimization insights
- Async pipeline execution for improved responsiveness

## Contract Flow Example

```python
# 1. Intent Detection
intent = extract_intent("I want to buy a washing machine")

# 2. FSM Initialization
fsm = ContractStateMachine("purchase_item.yaml")
fsm.context = SwisperContext(product_query="washing machine")

# 3. Product Search Pipeline
search_result = await product_search_pipeline.run(
    query="washing machine",
    hard_constraints=["price < 2000 CHF"]
)

# 4. Preference Match Pipeline  
preference_result = await preference_match_pipeline.run(
    items=search_result["items"],
    soft_preferences={"brand": "Bosch", "energy_rating": "A+++"}
)

# 5. User Confirmation & Checkout
selected_product = user_selection(preference_result["ranked_products"][:3])
order_id = checkout_tool.place_order(selected_product)
```

## Documentation

- [Refactoring Plan](docs/REFACTORING_PLAN.md) - Complete architectural vision and implementation strategy
- [Implementation Steps](docs/IMPLEMENTATION_STEPS.md) - Detailed breakdown of refactoring phases
- [Implementation Checklist](docs/IMPLEMENTATION_CHECKLIST.md) - Progress tracking and completion status
