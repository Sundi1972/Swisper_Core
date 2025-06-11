# Intent Extraction Architecture

## Overview

The intent extraction system in Swisper Core uses a contract-aware routing architecture to classify user messages and route them to appropriate handlers. This document describes the current implementation and future plans.

## Current Architecture (June 2025)

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

### Phase 1 (Current): ChatGPT-based Classification ✅
- Contract-aware routing manifest
- Deterministic template selection
- Confidence-based fallbacks

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
2. **Extensible**: Easy to add new contracts and intent types
3. **Robust**: Graceful fallbacks for edge cases
4. **Observable**: Comprehensive logging and reasoning
5. **Compliant**: Switzerland data sovereignty maintained
6. **Testable**: Isolated testing for each component

This architecture ensures reliable intent classification while providing a clear path for future enhancements and specialized LLM integration.
