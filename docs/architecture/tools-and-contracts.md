# Tools and Contract Management Architecture

## Overview

The Tools and Contract Management system in Swisper Core provides a robust framework for executing user contracts through a combination of Finite State Machine (FSM) control and Haystack Pipeline data processing.

## Contract Engine Architecture

### FSM-Based Contract Execution

The Contract Engine uses a Finite State Machine to manage conversation flow and contract execution:

```python
# Contract Flow Example
fsm = ContractStateMachine("purchase_item.yaml")
fsm.context = SwisperContext(product_query="washing machine")

# State transitions are explicit and auditable
transition = fsm.next()
assert transition.from_state == "initial"
assert transition.to_state == "search_products"
```

### Contract Definition Structure

Contracts are defined in YAML format with clear state definitions:

```yaml
# purchase_item.yaml
states:
  initial:
    description: "Starting state for product purchase"
    transitions:
      - to: "search_products"
        condition: "has_product_query"
  
  search_products:
    description: "Search for products matching user criteria"
    pipeline: "product_search"
    transitions:
      - to: "refine_constraints"
        condition: "too_many_results"
      - to: "match_preferences"
        condition: "results_within_limit"
```

### State Management

**StateTransition Class**:
```python
@dataclass
class StateTransition:
    from_state: str
    to_state: str
    trigger: str
    context_updates: Dict[str, Any]
    timestamp: datetime
```

**State Handlers**:
- `handle_search_products_state()`: Executes product search pipeline
- `handle_match_preferences_state()`: Runs preference matching pipeline
- `handle_user_confirmation_state()`: Manages user approval workflow

## Haystack Pipeline Integration

### Product Search Pipeline

**Architecture**:
```
SearchComponent → AttributeAnalyzer → ResultLimiter
```

**SearchComponent**:
- Integrates with Google Shopping API
- Handles query formatting and API authentication
- Implements retry logic and error handling

**AttributeAnalyzer**:
- Uses LLM analysis to extract product attributes
- Identifies price ranges and feature categories
- Implements intelligent caching (60-minute TTL)

**ResultLimiter**:
- Enforces result limits (≤50 products)
- Triggers constraint refinement when needed
- Provides user feedback for optimization

### Preference Match Pipeline

**Architecture**:
```
SpecScraper → CompatibilityChecker → PreferenceRanker
```

**SpecScraper**:
- Scrapes detailed product specifications
- Handles multiple vendor website formats
- Implements rate limiting and respectful crawling

**CompatibilityChecker**:
- Validates hard constraints (price, compatibility)
- Batch processing for efficiency
- Binary compatibility decisions

**PreferenceRanker**:
- LLM-based soft preference scoring
- Confidence metrics for rankings
- Top-3 product selection logic

## Tool Adapter Framework

### External Service Integration

**Google Shopping API Integration**:
```python
class GoogleShoppingAdapter:
    def search_products(self, query: str, constraints: Dict) -> List[Product]:
        # API authentication and request formatting
        # Error handling and retry logic
        # Response parsing and normalization
```

**Service Health Monitoring**:
```python
class SystemHealthMonitor:
    def check_service_health(self, service: str) -> HealthStatus:
        # Service availability checking
        # Performance threshold monitoring
        # Automatic failover coordination
```

### Tool Registry

**JSON Schema-Based Tool Definitions**:
```json
{
  "tool_id": "google_shopping_search",
  "name": "Google Shopping Product Search",
  "description": "Search for products using Google Shopping API",
  "parameters": {
    "query": {"type": "string", "required": true},
    "max_price": {"type": "number", "required": false}
  },
  "output_schema": {
    "products": {"type": "array", "items": {"$ref": "#/definitions/Product"}}
  }
}
```

**Dynamic Tool Loading**:
- Runtime tool discovery and registration
- Schema validation for tool inputs/outputs
- Automatic API documentation generation

## Pipeline Orchestration

### FSM-Pipeline Integration

**Pipeline Execution in State Handlers**:
```python
async def handle_search_products_state(self, context: SwisperContext) -> StateTransition:
    # Execute product search pipeline
    search_result = await self.product_search_pipeline.run(
        query=context.product_query,
        hard_constraints=context.hard_constraints
    )
    
    # Update context with results
    context.search_results = search_result["items"]
    context.attribute_analysis = search_result["attribute_analysis"]
    
    # Determine next state based on results
    if len(search_result["items"]) > 50:
        return StateTransition(
            from_state="search_products",
            to_state="refine_constraints",
            trigger="too_many_results"
        )
    else:
        return StateTransition(
            from_state="search_products",
            to_state="match_preferences",
            trigger="results_within_limit"
        )
```

### Error Handling and Fallbacks

**Pipeline Error Recovery**:
- Graceful degradation when LLM services unavailable
- Alternative processing paths for web scraping failures
- User notification with actionable error messages

**Service Health Integration**:
- Real-time service availability monitoring
- Automatic fallback to alternative providers
- Performance threshold alerting

## Performance Optimization

### Caching Strategy

**Multi-Level Caching**:
- **Attribute Analysis**: 60-minute TTL for LLM-processed data
- **Pipeline Results**: 30-minute TTL for complete pipeline outputs
- **API Responses**: 15-minute TTL for external service calls

**Cache Key Generation**:
```python
def generate_cache_key(query: str, constraints: Dict) -> str:
    # Normalize query and constraints
    # Generate deterministic hash
    # Include version information for cache invalidation
```

### Performance Monitoring

**Pipeline Timing**:
```python
class PipelineTimer:
    def time_pipeline_execution(self, pipeline_name: str):
        # Context manager for timing pipeline execution
        # Automatic metrics collection
        # Performance threshold monitoring
```

**Metrics Collection**:
- Pipeline execution times
- Cache hit/miss ratios
- External service response times
- Error rates and types

## Contract Execution Flow

### Complete Purchase Flow Example

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

### State Persistence

**Context Serialization**:
- Pipeline execution metadata
- Performance metrics
- User interaction history
- Error and recovery information

**Session Recovery**:
- Automatic state restoration after interruption
- Pipeline result caching for efficiency
- Context continuity across sessions

## Security and Compliance

### Tool Security Framework

**API Key Management**:
- Secure credential storage
- Automatic key rotation
- Access logging and auditing

**Request Validation**:
- Input sanitization for all tool inputs
- Output validation against schemas
- Rate limiting and abuse prevention

### Privacy Protection

**PII Handling in Tools**:
- Automatic PII detection in tool inputs/outputs
- Secure processing and storage
- User consent verification before external API calls

**Data Sovereignty**:
- Local processing for sensitive operations
- Minimal external data transmission
- Compliance with Swiss privacy regulations

## Testing Strategy

### Unit Testing

**Pipeline Component Testing**:
```python
def test_search_component():
    component = SearchComponent()
    result = component.run(query="laptop", max_results=10)
    assert len(result["items"]) <= 10
    assert all("price" in item for item in result["items"])
```

**FSM State Handler Testing**:
```python
def test_search_products_state_handler():
    fsm = ContractStateMachine("purchase_item.yaml")
    context = SwisperContext(product_query="laptop")
    
    transition = fsm.handle_search_products_state(context)
    assert transition.to_state in ["refine_constraints", "match_preferences"]
```

### Integration Testing

**End-to-End Pipeline Testing**:
- Complete contract execution flows
- Error scenario testing
- Performance benchmark validation

**Tool Integration Testing**:
- External service integration validation
- Error handling and fallback testing
- Security and authentication testing

## Future Enhancements

### Planned Improvements

**Advanced Pipeline Features**:
- Dynamic pipeline composition
- Machine learning-based optimization
- Real-time performance adaptation

**Enhanced Tool Framework**:
- Plugin architecture for custom tools
- Automatic tool discovery and registration
- Advanced security and sandboxing

**Monitoring and Analytics**:
- Real-time performance dashboards
- Predictive failure detection
- User behavior analytics

For related documentation, see:
- [Session and Context Management](session-management.md)
- [Memory Management](memory-management.md)
- [Testing Strategy](../testing/strategy.md)
