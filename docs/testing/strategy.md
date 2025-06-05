# Testing Strategy

## Overview

Swisper Core implements a comprehensive testing strategy covering unit tests, integration tests, and end-to-end browser tests to ensure system reliability, performance, and user experience quality.

## Testing Philosophy

### Core Principles

**Test Pyramid Structure**:
- **Unit Tests (70%)**: Fast, isolated component testing
- **Integration Tests (20%)**: Component interaction testing
- **End-to-End Tests (10%)**: Complete user journey testing

**Quality Standards**:
- Minimum 80% code coverage for critical components
- All tests must be deterministic and repeatable
- Tests should be fast enough for continuous integration
- Each component must be testable in isolation

## Test Organization

### Directory Structure

```
tests/
├── unit/
│   ├── test_contract_engine/
│   ├── test_gateway/
│   ├── test_haystack_pipeline/
│   ├── test_orchestrator/
│   └── test_tool_adapter/
├── integration/
│   ├── test_fsm_integration.py
│   ├── test_pipeline_integration.py
│   ├── test_session_persistence.py
│   └── test_memory_manager.py
├── e2e/
│   ├── test_complete_purchase_flow.py
│   ├── test_rag_query_scenarios.py
│   └── test_error_handling_scenarios.py
├── performance/
│   ├── test_pipeline_performance.py
│   ├── test_memory_performance.py
│   └── test_load_testing.py
└── fixtures/
    ├── sample_contracts.yaml
    ├── test_products.json
    └── mock_responses.json
```

### Naming Conventions

**File Naming**:
- All test files must start with `test_`
- Use descriptive names: `test_product_search_pipeline.py`
- Group related tests in subdirectories

**Test Function Naming**:
- Use descriptive test names: `test_search_component_handles_empty_results`
- Follow pattern: `test_[component]_[scenario]_[expected_outcome]`

## Unit Testing Strategy

### Component Isolation

**FSM State Handler Testing**:
```python
import pytest
from unittest.mock import Mock, AsyncMock
from contract_engine.fsm import ContractStateMachine
from contract_engine.context import SwisperContext

class TestFSMStateHandlers:
    @pytest.fixture
    def mock_context(self):
        return SwisperContext(
            session_id="test_session",
            user_id="test_user",
            product_query="laptop",
            hard_constraints=["price < 2000 CHF"]
        )
    
    @pytest.fixture
    def mock_pipeline(self):
        pipeline = AsyncMock()
        pipeline.run.return_value = {
            "items": [{"name": "Test Laptop", "price": 1500}],
            "attribute_analysis": {"price_range": "1000-2000"}
        }
        return pipeline
    
    async def test_search_products_state_success(self, mock_context, mock_pipeline):
        """Test successful product search state transition"""
        fsm = ContractStateMachine("purchase_item.yaml")
        fsm.product_search_pipeline = mock_pipeline
        
        transition = await fsm.handle_search_products_state(mock_context)
        
        assert transition.from_state == "search_products"
        assert transition.to_state == "match_preferences"
        assert len(mock_context.search_results) == 1
        mock_pipeline.run.assert_called_once()
    
    async def test_search_products_state_too_many_results(self, mock_context, mock_pipeline):
        """Test constraint refinement when too many results"""
        # Mock pipeline to return too many results
        mock_pipeline.run.return_value = {
            "items": [{"name": f"Laptop {i}", "price": 1500} for i in range(60)],
            "attribute_analysis": {"price_range": "1000-3000"}
        }
        
        fsm = ContractStateMachine("purchase_item.yaml")
        fsm.product_search_pipeline = mock_pipeline
        
        transition = await fsm.handle_search_products_state(mock_context)
        
        assert transition.to_state == "refine_constraints"
        assert transition.trigger == "too_many_results"
```

**Pipeline Component Testing**:
```python
import pytest
from haystack_pipeline.components import SearchComponent, AttributeAnalyzer
from unittest.mock import Mock, patch

class TestSearchComponent:
    @pytest.fixture
    def search_component(self):
        return SearchComponent(api_key="test_key")
    
    @patch('haystack_pipeline.components.google_shopping_api')
    def test_search_component_basic_query(self, mock_api, search_component):
        """Test basic product search functionality"""
        # Mock API response
        mock_api.search.return_value = {
            "items": [
                {"title": "Test Laptop", "price": "1500 CHF", "link": "http://example.com"}
            ]
        }
        
        result = search_component.run(query="laptop", max_results=10)
        
        assert "items" in result
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "Test Laptop"
        mock_api.search.assert_called_once_with("laptop", max_results=10)
    
    def test_search_component_empty_query(self, search_component):
        """Test handling of empty search query"""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            search_component.run(query="", max_results=10)
    
    @patch('haystack_pipeline.components.google_shopping_api')
    def test_search_component_api_error(self, mock_api, search_component):
        """Test handling of API errors"""
        mock_api.search.side_effect = Exception("API Error")
        
        result = search_component.run(query="laptop", max_results=10)
        
        assert result["items"] == []
        assert "error" in result
        assert "API Error" in result["error"]
```

### Memory System Testing

**Buffer Store Testing**:
```python
import pytest
from memory_manager.buffer_store import BufferStore
from memory_manager.models import Message
import asyncio

class TestBufferStore:
    @pytest.fixture
    async def buffer_store(self):
        # Use fake Redis for testing
        from fakeredis.aioredis import FakeRedis
        redis_client = FakeRedis()
        return BufferStore(redis_client, max_messages=5, max_tokens=100)
    
    async def test_add_message_within_limits(self, buffer_store):
        """Test adding messages within buffer limits"""
        message = Message(content="Test message", is_user=True)
        
        await buffer_store.add_message("test_session", message)
        
        messages = await buffer_store.get_recent_context("test_session")
        assert len(messages) == 1
        assert messages[0].content == "Test message"
    
    async def test_buffer_overflow_handling(self, buffer_store):
        """Test buffer overflow and automatic trimming"""
        # Add messages beyond limit
        for i in range(10):
            message = Message(content=f"Message {i}", is_user=i % 2 == 0)
            await buffer_store.add_message("test_session", message)
        
        messages = await buffer_store.get_recent_context("test_session")
        assert len(messages) <= 5  # Should be trimmed to max_messages
        
        # Most recent messages should be preserved
        assert "Message 9" in [msg.content for msg in messages]
```

## Integration Testing Strategy

### Pipeline Integration

**Complete Pipeline Flow Testing**:
```python
import pytest
from haystack_pipeline.pipelines import create_product_search_pipeline, create_preference_match_pipeline
from contract_engine.fsm import ContractStateMachine
from contract_engine.context import SwisperContext

class TestPipelineIntegration:
    @pytest.fixture
    async def product_search_pipeline(self):
        return create_product_search_pipeline()
    
    @pytest.fixture
    async def preference_match_pipeline(self):
        return create_preference_match_pipeline()
    
    async def test_complete_search_and_preference_flow(
        self, 
        product_search_pipeline, 
        preference_match_pipeline
    ):
        """Test complete pipeline flow from search to preference matching"""
        # Execute product search
        search_result = await product_search_pipeline.run(
            query="gaming laptop",
            hard_constraints=["price < 3000 CHF", "brand in [ASUS, MSI]"]
        )
        
        assert "items" in search_result
        assert len(search_result["items"]) > 0
        
        # Execute preference matching on search results
        preference_result = await preference_match_pipeline.run(
            items=search_result["items"],
            soft_preferences={
                "brand": "ASUS",
                "gpu": "RTX 4070",
                "ram": "32GB"
            }
        )
        
        assert "ranked_products" in preference_result
        assert len(preference_result["ranked_products"]) > 0
        
        # Verify ranking quality
        top_product = preference_result["ranked_products"][0]
        assert "score" in top_product
        assert top_product["score"] > 0.5  # Should have reasonable confidence
```

### Session Persistence Integration

**Session Lifecycle Testing**:
```python
import pytest
from orchestrator.session_manager import PipelineSessionManager
from contract_engine.context import SwisperContext
from memory_manager.models import PipelineExecution

class TestSessionPersistence:
    @pytest.fixture
    async def session_manager(self):
        # Use test database
        from tests.fixtures.test_db import get_test_session_store
        session_store = get_test_session_store()
        return PipelineSessionManager(session_store)
    
    async def test_session_save_and_restore(self, session_manager):
        """Test complete session save and restore cycle"""
        # Create test context
        context = SwisperContext(
            session_id="test_session_001",
            user_id="test_user",
            product_query="laptop",
            search_results=[{"name": "Test Laptop", "price": 1500}]
        )
        
        # Add pipeline execution
        execution = PipelineExecution(
            pipeline_name="product_search",
            input_data={"query": "laptop"},
            output_data={"items": [{"name": "Test Laptop"}]},
            duration_ms=1250
        )
        context.pipeline_executions.append(execution)
        
        # Save session
        await session_manager.save_session(context.session_id, context)
        
        # Restore session
        restored_context = await session_manager.load_session(context.session_id)
        
        assert restored_context.session_id == context.session_id
        assert restored_context.product_query == context.product_query
        assert len(restored_context.pipeline_executions) == 1
        assert restored_context.pipeline_executions[0].pipeline_name == "product_search"
```

## End-to-End Testing Strategy

### Browser Testing with Playwright

**Complete User Journey Testing**:
```python
import pytest
from playwright.async_api import async_playwright
import asyncio

class TestCompleteUserJourneys:
    @pytest.fixture
    async def browser_context(self):
        """Setup browser context for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Setup console logging
            page.on("console", lambda msg: print(f"Console: {msg.text}"))
            page.on("pageerror", lambda error: print(f"Page Error: {error}"))
            
            yield page
            
            await context.close()
            await browser.close()
    
    async def test_gpu_purchase_flow(self, browser_context):
        """Test complete GPU purchase user journey"""
        page = browser_context
        
        # Navigate to application
        await page.goto("http://localhost:3000")
        
        # Start conversation
        await page.fill('[data-testid="chat-input"]', "I want to buy a graphics card for gaming")
        await page.click('[data-testid="send-button"]')
        
        # Wait for FSM to process and show product search
        await page.wait_for_selector('[data-testid="product-results"]', timeout=10000)
        
        # Verify products are displayed
        products = await page.query_selector_all('[data-testid="product-item"]')
        assert len(products) > 0
        
        # Select preferences
        await page.click('[data-testid="preference-brand-nvidia"]')
        await page.click('[data-testid="preference-memory-16gb"]')
        await page.click('[data-testid="apply-preferences"]')
        
        # Wait for preference matching
        await page.wait_for_selector('[data-testid="ranked-products"]', timeout=15000)
        
        # Verify top recommendations
        top_products = await page.query_selector_all('[data-testid="top-recommendation"]')
        assert len(top_products) <= 3  # Should show top 3
        
        # Select a product
        await page.click('[data-testid="select-product-0"]')
        
        # Verify confirmation dialog
        await page.wait_for_selector('[data-testid="purchase-confirmation"]')
        confirmation_text = await page.text_content('[data-testid="confirmation-message"]')
        assert "graphics card" in confirmation_text.lower()
        
        # Complete purchase
        await page.click('[data-testid="confirm-purchase"]')
        
        # Verify success message
        await page.wait_for_selector('[data-testid="purchase-success"]')
        success_text = await page.text_content('[data-testid="success-message"]')
        assert "order" in success_text.lower()
```

### RAG Query Testing

**Knowledge Retrieval Testing**:
```python
class TestRAGQueryScenarios:
    async def test_rag_query_with_context(self, browser_context):
        """Test RAG query using previous conversation context"""
        page = browser_context
        
        await page.goto("http://localhost:3000")
        
        # First interaction - establish context
        await page.fill('[data-testid="chat-input"]', "I prefer NVIDIA graphics cards")
        await page.click('[data-testid="send-button"]')
        await page.wait_for_response(lambda response: "chat" in response.url)
        
        # Second interaction - query should use context
        await page.fill('[data-testid="chat-input"]', "What graphics card would you recommend for me?")
        await page.click('[data-testid="send-button"]')
        
        # Wait for response
        await page.wait_for_selector('[data-testid="assistant-response"]')
        
        # Verify response uses previous context
        response_text = await page.text_content('[data-testid="assistant-response"]')
        assert "nvidia" in response_text.lower()
        
        # Verify memory retrieval in logs
        logs = await page.evaluate("() => window.memoryLogs || []")
        memory_retrieval_logs = [log for log in logs if "memory_retrieval" in log.get("type", "")]
        assert len(memory_retrieval_logs) > 0
```

### Error Handling Scenarios

**Error Recovery Testing**:
```python
class TestErrorHandlingScenarios:
    async def test_api_failure_graceful_degradation(self, browser_context):
        """Test graceful degradation when external APIs fail"""
        page = browser_context
        
        # Mock API failure
        await page.route("**/api/search", lambda route: route.abort())
        
        await page.goto("http://localhost:3000")
        
        # Attempt search that will fail
        await page.fill('[data-testid="chat-input"]', "Find me a laptop")
        await page.click('[data-testid="send-button"]')
        
        # Wait for error handling
        await page.wait_for_selector('[data-testid="error-message"]', timeout=10000)
        
        # Verify user-friendly error message
        error_text = await page.text_content('[data-testid="error-message"]')
        assert "temporarily unavailable" in error_text.lower()
        assert "try again" in error_text.lower()
        
        # Verify fallback options are provided
        fallback_options = await page.query_selector_all('[data-testid="fallback-option"]')
        assert len(fallback_options) > 0
    
    async def test_session_recovery_after_interruption(self, browser_context):
        """Test session recovery after connection interruption"""
        page = browser_context
        
        await page.goto("http://localhost:3000")
        
        # Start conversation
        await page.fill('[data-testid="chat-input"]', "I want to buy a laptop")
        await page.click('[data-testid="send-button"]')
        await page.wait_for_response(lambda response: "chat" in response.url)
        
        # Simulate connection interruption
        await page.set_offline(True)
        await asyncio.sleep(2)
        await page.set_offline(False)
        
        # Continue conversation
        await page.fill('[data-testid="chat-input"]', "What were we talking about?")
        await page.click('[data-testid="send-button"]')
        
        # Verify session context is recovered
        await page.wait_for_selector('[data-testid="assistant-response"]')
        response_text = await page.text_content('[data-testid="assistant-response"]')
        assert "laptop" in response_text.lower()
```

## Performance Testing Strategy

### Load Testing

**Pipeline Performance Testing**:
```python
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPipelinePerformance:
    async def test_product_search_pipeline_performance(self):
        """Test product search pipeline performance under load"""
        from haystack_pipeline.pipelines import create_product_search_pipeline
        
        pipeline = create_product_search_pipeline()
        
        # Performance requirements
        MAX_RESPONSE_TIME = 5.0  # seconds
        MIN_THROUGHPUT = 10  # requests per second
        
        async def single_search():
            start_time = time.time()
            result = await pipeline.run(
                query="gaming laptop",
                hard_constraints=["price < 2000 CHF"]
            )
            duration = time.time() - start_time
            return duration, len(result.get("items", []))
        
        # Run concurrent searches
        tasks = [single_search() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Analyze performance
        durations = [r[0] for r in results]
        item_counts = [r[1] for r in results]
        
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        throughput = len(results) / sum(durations)
        
        # Assertions
        assert avg_duration < MAX_RESPONSE_TIME, f"Average response time {avg_duration:.2f}s exceeds {MAX_RESPONSE_TIME}s"
        assert max_duration < MAX_RESPONSE_TIME * 2, f"Max response time {max_duration:.2f}s too high"
        assert all(count > 0 for count in item_counts), "Some searches returned no results"
        
        print(f"Performance metrics:")
        print(f"- Average duration: {avg_duration:.2f}s")
        print(f"- Max duration: {max_duration:.2f}s")
        print(f"- Throughput: {throughput:.2f} req/s")
```

### Memory Performance Testing

**Memory System Performance**:
```python
class TestMemoryPerformance:
    async def test_vector_search_performance(self):
        """Test vector search performance with large dataset"""
        from memory_manager.vector_store import VectorMemoryStore
        from memory_manager.embeddings import EmbeddingModelManager
        
        # Setup
        embedding_manager = EmbeddingModelManager({"model_name": "all-MiniLM-L6-v2"})
        vector_store = VectorMemoryStore({"host": "localhost", "port": 19530})
        
        # Insert test data
        test_memories = [
            f"User prefers {brand} laptops with {spec} specifications"
            for brand in ["Dell", "HP", "Lenovo", "ASUS", "MSI"]
            for spec in ["gaming", "business", "ultrabook", "workstation"]
        ]
        
        # Measure insertion performance
        start_time = time.time()
        for i, memory in enumerate(test_memories):
            await vector_store.store_semantic_memory(
                user_id="test_user",
                content=memory,
                metadata={"type": "preference", "index": i}
            )
        insertion_time = time.time() - start_time
        
        # Measure search performance
        search_queries = [
            "What laptop brands does the user like?",
            "What are the user's gaming preferences?",
            "What specifications does the user prefer?"
        ]
        
        search_times = []
        for query in search_queries:
            start_time = time.time()
            results = await vector_store.search_similar_memories(
                user_id="test_user",
                query=query,
                limit=5
            )
            search_time = time.time() - start_time
            search_times.append(search_time)
            
            assert len(results) > 0, f"No results for query: {query}"
        
        avg_search_time = sum(search_times) / len(search_times)
        
        # Performance assertions
        assert insertion_time / len(test_memories) < 0.1, "Insertion too slow"
        assert avg_search_time < 0.5, "Search too slow"
        
        print(f"Memory performance:")
        print(f"- Avg insertion time: {insertion_time/len(test_memories):.3f}s per item")
        print(f"- Avg search time: {avg_search_time:.3f}s")
```

## Test Infrastructure

### Test Configuration

**pytest.ini**:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=contract_engine
    --cov=gateway
    --cov=haystack_pipeline
    --cov=orchestrator
    --cov=tool_adapter
    --cov=memory_manager
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow running tests
asyncio_mode = auto
```

### Test Fixtures and Utilities

**Common Test Fixtures**:
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    client = AsyncMock()
    client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Test response"))]
    )
    return client

@pytest.fixture
def sample_products():
    """Sample product data for testing"""
    return [
        {
            "name": "ASUS ROG Strix RTX 4070",
            "price": 899,
            "brand": "ASUS",
            "memory": "12GB",
            "url": "https://example.com/gpu1"
        },
        {
            "name": "MSI Gaming X RTX 4060 Ti",
            "price": 649,
            "brand": "MSI", 
            "memory": "16GB",
            "url": "https://example.com/gpu2"
        }
    ]

@pytest.fixture
async def test_session_context():
    """Test session context with sample data"""
    from contract_engine.context import SwisperContext
    return SwisperContext(
        session_id="test_session_001",
        user_id="test_user_001",
        product_query="graphics card",
        hard_constraints=["price < 1000 CHF"],
        soft_preferences={"brand": "NVIDIA", "memory": "16GB"}
    )
```

## Continuous Integration

### GitHub Actions Configuration

**.github/workflows/test.yml**:
```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: swisper_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: latest
        virtualenvs-create: true
        virtualenvs-in-project: true
    
    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v3
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}
    
    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      run: poetry install --no-interaction --no-root
    
    - name: Install project
      run: poetry install --no-interaction
    
    - name: Run linting
      run: |
        poetry run pylint contract_engine gateway haystack_pipeline orchestrator tool_adapter
    
    - name: Run unit tests
      run: |
        poetry run pytest tests/unit/ -v --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/swisper_test
        REDIS_URL: redis://localhost:6379
    
    - name: Run integration tests
      run: |
        poetry run pytest tests/integration/ -v
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/swisper_test
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

## Test Scenarios Documentation

### User Journey Test Scenarios

**Scenario 1: Graphics Card Purchase**
```yaml
scenario: "Complete GPU Purchase Flow"
description: "User searches for, evaluates, and purchases a graphics card"
steps:
  1. User initiates conversation: "I want to buy a graphics card for gaming"
  2. System executes product search pipeline
  3. User refines constraints: "Under 1000 CHF, NVIDIA preferred"
  4. System executes preference matching pipeline
  5. User selects from top 3 recommendations
  6. System confirms purchase details
  7. User approves purchase
  8. System completes order
expected_outcomes:
  - Products returned within price constraint
  - NVIDIA products ranked higher
  - Purchase confirmation includes correct details
  - Order ID generated successfully
performance_requirements:
  - Search results within 5 seconds
  - Preference matching within 10 seconds
  - Total flow completion under 2 minutes
```

**Scenario 2: RAG Knowledge Query**
```yaml
scenario: "Context-Aware Knowledge Retrieval"
description: "User asks questions that require previous conversation context"
setup:
  - Previous conversation about laptop preferences
  - User mentioned preference for "business laptops" and "long battery life"
steps:
  1. User asks: "What laptop would you recommend for me?"
  2. System retrieves relevant context from memory
  3. System provides personalized recommendation
  4. User asks follow-up: "What about for travel?"
  5. System refines recommendation based on travel context
expected_outcomes:
  - Recommendations align with stated preferences
  - Context from previous conversations is used
  - Follow-up questions build on established context
  - Memory retrieval logs show relevant context found
```

## Monitoring and Metrics

### Test Metrics Collection

**Test Performance Tracking**:
```python
class TestMetricsCollector:
    def __init__(self):
        self.metrics = {
            "test_durations": {},
            "coverage_percentages": {},
            "failure_rates": {},
            "performance_benchmarks": {}
        }
    
    def record_test_duration(self, test_name: str, duration: float):
        if test_name not in self.metrics["test_durations"]:
            self.metrics["test_durations"][test_name] = []
        self.metrics["test_durations"][test_name].append(duration)
    
    def record_performance_benchmark(self, benchmark_name: str, value: float, unit: str):
        self.metrics["performance_benchmarks"][benchmark_name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.utcnow()
        }
    
    def generate_report(self) -> Dict[str, Any]:
        return {
            "avg_test_duration": self.calculate_avg_test_duration(),
            "slowest_tests": self.get_slowest_tests(5),
            "performance_trends": self.analyze_performance_trends(),
            "coverage_summary": self.get_coverage_summary()
        }
```

For related documentation, see:
- [Architecture Overview](../architecture/overview.md)
- [Local Setup Guide](../deployment/local-setup.md)
- [Production Strategy](../deployment/production-strategy.md)
