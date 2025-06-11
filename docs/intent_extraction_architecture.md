# Intent Extraction Architecture

## Overview

The intent extraction system in Swisper Core uses a contract-aware routing architecture to classify user messages and route them to appropriate handlers. This document describes the current implementation and future plans.

## Current Architecture (June 2025)

### Enhanced Volatility-Based Intent Classification

**Status**: ✅ **IMPLEMENTED AND ACTIVE** (June 2025)

The intent extraction system now includes an enhanced two-step inference process that combines keyword-based volatility classification with LLM confirmation to improve routing accuracy for time-sensitive queries.

#### Key Components

**1. Volatility Classification (`orchestrator/volatility_classifier.py`)**
- **Purpose**: Pre-classify queries based on information volatility
- **Categories**: 
  - `volatile`: Time-sensitive, current information (ministers, prices, breaking news)
  - `semi_static`: Occasionally changing (product specs, company info)
  - `static`: Stable/historical information (biography, geography, definitions)
  - `unknown`: No clear keyword match

**2. Temporal Cue Detection (`orchestrator/prompt_preprocessor.py`)**
- **Purpose**: Identify time-sensitive language patterns
- **Keywords**: "today", "now", "currently", "latest", "new", "as of", "2025", "current"

**3. Two-Step Inference Process**
```python
def extract_user_intent(user_input: str) -> dict:
    # Step 1: Keyword-based volatility pre-classification
    volatility_result = classify_entity_category(user_input)
    temporal_cue = has_temporal_cue(user_input)
    
    # Step 2: LLM classification with volatility context
    enhanced_prompt = f"""
    User query: "{user_input}"
    Volatility classification: {volatility_result["volatility"]}
    Temporal cue detected: {temporal_cue}
    Keyword reasoning: {volatility_result["reason"]}
    
    Determine intent type considering volatility context...
    """
    
    return llm_classify_with_context(enhanced_prompt)
```

#### Enhanced Intent Types

The system now supports five intent types with volatility-aware routing:
- **chat**: General knowledge, historical information (static/semi-static)
- **websearch**: Time-sensitive, current information (volatile + temporal cues)
- **rag**: Document search and knowledge queries
- **contract**: Multi-step workflows and purchases  
- **tool_usage**: External service interactions

#### Volatility Keyword Configuration

**Default Categories**:
```python
VOLATILITY_KEYWORDS = {
    "volatile_keywords": [
        "latest", "current", "recent", "today", "now", "currently", 
        "ministers", "government", "cabinet", "officials", "CEO",
        "president", "price", "stock", "breaking", "news", "2025"
    ],
    "semi_static_keywords": [
        "specs", "specifications", "features", "iPhone", "model", 
        "company", "headquarters", "founded", "employees"
    ],
    "static_keywords": [
        "history", "biography", "born", "died", "capital", "population",
        "definition", "explain", "what is", "who was", "historical"
    ]
}
```

**UI Configuration**: Editable through Settings Modal → "Volatility Indicators" tab

#### Test Results

**Verified Working Examples**:
- ✅ "Who is Angela Merkel" → **chat** (static biographical info)
- ✅ "who is the current german finance minister" → **websearch** (volatile + temporal)
- ✅ "Latest news about German politics" → **websearch** (volatile keywords)
- ✅ "Price of Bitcoin today" → **websearch** (volatile + temporal)
- ✅ "Explain quantum computing" → **chat** (static knowledge)

**Session Consistency**: ✅ Multiple consecutive queries route correctly without interference

#### API Integration

**New Endpoints**:
- `GET /volatility-settings`: Retrieve keyword configuration
- `POST /volatility-settings`: Update keyword categories

**Enhanced Response Format**:
```json
{
  "intent_type": "websearch",
  "confidence": 0.95,
  "reasoning": "Query contains volatile keywords 'current' + 'minister' with temporal context",
  "volatility_level": "volatile",
  "requires_websearch": true
}
```

### Contract-Aware Intent Router

The intent extraction system (`orchestrator/intent_extractor.py`) implements a dynamic routing manifest that includes:

1. **Available Contracts**: Loaded from `contract_templates/` directory
2. **Available Tools**: Loaded from MCP tool registry
3. **Intent Types**: chat, rag, tool_usage, contract

### Routing Manifest Structure

```json
{
  "routing_options": [
    {
      "intent_type": "chat",
      "description": "General open-ended conversation"
    },
    {
      "intent_type": "rag",
      "description": "Ask questions about uploaded or stored documents (prefix with #rag)"
    },
    {
      "intent_type": "tool_usage",
      "description": "Use tools for analysis, comparison, or information gathering",
      "tools": ["search_products", "analyze_product_attributes", ...]
    },
    {
      "intent_type": "contract",
      "description": "Execute structured workflows with specific business logic",
      "contracts": [
        {
          "name": "purchase_item",
          "template": "purchase_item.yaml",
          "description": "Template for executing a product purchase.",
          "trigger_keywords": ["buy", "purchase", "order", "acquire", "shop for", ...]
        }
      ]
    }
  ]
}
```

### LLM Classification Process

1. **Routing Manifest Generation**: Dynamic discovery of available contracts and tools
2. **LLM Classification**: Dedicated system prompt with structured routing options
3. **Deterministic Selection**: LLM must select from exact contract template names provided
4. **Confidence Scoring**: Predictions below 0.6 confidence fall back to chat mode
5. **Validation**: Responses that don't match available contracts are rejected

### System Prompt Design

The LLM receives:
- Complete routing manifest with available options
- Clear classification rules for each intent type
- Confidence scoring guidelines (0.9-1.0 very clear, 0.7-0.9 good match, etc.)
- Strict JSON response format requirements

### Response Validation

- **Required Fields**: intent_type, confidence, reasoning
- **Contract Template Validation**: Must match exactly from available list
- **Fallback Mechanism**: Invalid responses trigger chat mode fallback

## Current Implementation Details

### Key Functions

- `_generate_routing_manifest()`: Creates dynamic routing options
- `extract_user_intent()`: Main classification entry point
- `_classify_intent_with_llm()`: LLM-based classification with validation
- `_create_chat_fallback()`: Fallback for low confidence or errors

### Confidence Thresholds

- **High Confidence (0.8+)**: Clear intent with strong keyword matches
- **Medium Confidence (0.6-0.8)**: Good intent match with supporting context
- **Low Confidence (<0.6)**: Falls back to chat mode

### Enhanced Logging

Intent extraction logs now include:
- User message content (not just session_id)
- Detailed reasoning from LLM
- Confidence scores and decision logic
- Fallback reasons when applicable

## Current Implementation

The intent extraction system is implemented in `orchestrator/intent_extractor.py` using OpenAI's GPT-4o model with structured prompting and response validation. The system maintains a routing manifest that includes:

- Available contract types loaded from `contract_templates/` directory
- Tool registry with MCP (Model Context Protocol) tool descriptions
- Intent classification with four main types: chat, rag, tool, contract
- LLM-based classification with regex fallback for reliability
- Confidence scoring and response validation mechanisms

### Key Components

**Routing Manifest Generation**:
```python
def _generate_routing_manifest() -> Dict[str, Any]:
    contracts = load_available_contracts()
    tools = load_available_tools()
    
    return {
        "intent_types": {
            "chat": "General conversation and questions",
            "rag": "Document search and knowledge queries", 
            "tool": "External service interactions",
            "contract": "Multi-step workflows and purchases"
        },
        "available_contracts": contracts,
        "available_tools": tools,
        "trigger_keywords": {
            "rag": ["#rag", "search documents", "find information"],
            "contract": ["buy", "purchase", "order", "I want to"],
            "tool": ["search", "lookup", "find products"]
        }
    }
```

**Intent Classification Process**:
1. Generate routing manifest with current contracts and tools
2. Use LLM with structured prompt to classify user intent
3. Validate LLM response format and confidence scores
4. Fall back to regex-based classification if LLM fails
5. Return structured intent with routing information

## Current LLM Usage

**Interim Solution**: OpenAI ChatGPT-4.0
- Used during development phase
- Provides reliable intent classification
- Handles complex reasoning and context understanding

**System Prompt Strategy**:
- Conservative confidence scoring
- Explicit routing manifest inclusion
- Deterministic template selection enforcement

## Future Plans

### Specialized Intent Classification Models

We plan to develop specialized models for intent classification to reduce dependency on general-purpose LLMs, in line with Switzerland's data sovereignty requirements:

1. **Local T5-based Classification**: Fine-tuned T5 models for intent detection (see `docs/guides/T5_USAGE_GUIDE.md`)
2. **Embedding-based Routing**: Vector similarity for intent matching using local models
3. **Hybrid Approaches**: Combining LLM classification with local model validation
4. **Swiss-hosted Models**: Deployment of classification models within Swiss data centers

### Implementation Roadmap

**Phase 1**: Enhance current LLM-based system with better fallback mechanisms
**Phase 2**: Implement T5-based local classification for sensitive intents
**Phase 3**: Hybrid system with local models as primary, LLM as fallback
**Phase 4**: Full local processing for compliance-critical workflows

### Specialized Intent Classification LLM

**Target**: Dedicated, smaller, faster model for intent routing
- **Options**: Mistral, Phi, Claude Haiku, or fine-tuned model
- **Benefits**: Lower latency, cost efficiency, specialized performance
- **Training**: Fine-tune on Swisper-specific intent patterns

### Enhanced Routing Capabilities

1. **Multi-Contract Workflows**: Support for complex workflows spanning multiple contracts
2. **Context-Aware Routing**: Consider conversation history for better classification
3. **Dynamic Contract Discovery**: Automatic registration of new contract types
4. **A/B Testing**: Compare different classification approaches

### Quality Assurance

1. **Intent Detection Test Suite**: Comprehensive test cases for all intent types
2. **Analytics Layer**: Log every classification decision for analysis
3. **Confidence Calibration**: Tune confidence thresholds based on real usage
4. **Misclassification Detection**: Automatic flagging of low-confidence predictions

## Contract Registry Evolution

### Current State
- **Mock Registry**: Single contract (purchase_item.yaml)
- **Manual Configuration**: Contract metadata in YAML files
- **Static Discovery**: File-based contract loading

### Future Plans
- **Dynamic Registry**: Database-backed contract management
- **Version Control**: Contract template versioning and rollback
- **Metadata Management**: Rich contract descriptions and capabilities
- **Runtime Registration**: Hot-swappable contract deployment

## Testing Strategy

### Current Testing
- **Essential Test Coverage**: 21 critical tests for core functionality
- **Browser E2E Testing**: Real API integration testing
- **Intent Classification Tests**: Specific test cases for purchase workflows

### Future Testing
- **Intent Classification Benchmarks**: Comprehensive test suite for all intent types
- **Performance Testing**: Latency and accuracy metrics
- **Regression Testing**: Automated detection of classification degradation

## Switzerland Compliance

The intent extraction system maintains Switzerland data sovereignty requirements:
- **Local Processing**: All classification can run locally when needed
- **Fallback Mechanisms**: System works without external LLM dependencies
- **Privacy by Design**: No sensitive data sent to external services without consent

## Migration Path

### Phase 1 (Current): Enhanced Volatility-Based Classification ✅
- Two-step inference process with volatility pre-analysis
- Temporal cue detection for time-sensitive queries
- Contract-aware routing manifest with volatility context
- Deterministic template selection with enhanced LLM prompts
- Confidence-based fallbacks with volatility reasoning

### Phase 2 (Next): Enhanced Validation
- Comprehensive intent test suite
- Analytics and monitoring
- Performance optimization

### Phase 3 (Future): Specialized LLM
- Dedicated intent classification model
- Fine-tuned for Swisper workflows
- Reduced latency and costs

### Phase 4 (Long-term): Advanced Routing
- Multi-contract workflows
- Context-aware classification
- Dynamic contract registry

## Key Design Principles

1. **Deterministic**: LLM must select from predefined options only
2. **Volatility-Aware**: Two-step classification considers information freshness
3. **Extensible**: Easy to add new contracts, intent types, and volatility keywords
4. **Robust**: Graceful fallbacks for edge cases with enhanced reasoning
5. **Observable**: Comprehensive logging including volatility analysis
6. **Compliant**: Switzerland data sovereignty maintained
7. **Testable**: Isolated testing for each component including volatility classification
8. **Configurable**: User-editable volatility keywords through UI

This architecture ensures reliable intent classification while providing a clear path for future enhancements and specialized LLM integration.
