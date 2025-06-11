# Swisper Core Documentation

This directory contains comprehensive documentation for the Swisper Core project, organized by topic for easy navigation.

## Documentation Structure

### 📐 Architecture
- [System Overview](architecture/overview.md) - High-level architecture and component interactions
- [Intent Extraction](intent_extraction_architecture.md) - LLM-based intent classification system
- [Session Management](architecture/session-management.md) - Session persistence and context management
- [Memory Management](architecture/memory-management.md) - Multi-layered memory architecture
- [Tools and Contracts](architecture/tools-and-contracts.md) - Contract execution and tool integration
- [Use Cases](architecture/use-cases.md) - System use cases and workflows

### 🔌 API Reference
- [API Documentation](api/API_DOCUMENTATION.md) - Core APIs for pipelines, FSM, and session management
- [Memory Manager API](api/MEMORY_MANAGER_API.md) - Memory management service API reference

### ⚙️ Configuration
- [Redis Configuration](configuration/REDIS_CONFIGURATION.md) - Redis setup and optimization guide

### 📚 Guides
- [T5 Usage Guide](guides/T5_USAGE_GUIDE.md) - Local T5 model integration for Swiss compliance
- [T5 API Reference](guides/T5_API_REFERENCE.md) - T5 model API documentation

### 🚀 Deployment
- [Local Setup](deployment/local-setup.md) - Development environment setup
- [Production Strategy](deployment/production-strategy.md) - Production deployment guide
- [Frontend Template Guide](deployment/frontend-template-guide.md) - Frontend deployment templates

### 🧪 Testing
- [Testing Strategy](testing/strategy.md) - Comprehensive testing approach
- [Test Scenarios](testing/scenarios.md) - Specific test cases and scenarios

### 📋 Implementation Plans
- [Overall Refactoring Plan](implementation-plans/overall-refactoring-plan.md)
- [Memory Architecture Plan](implementation-plans/memory-architecture-plan.md)
- [FSM Pipeline Refactoring](implementation-plans/fsm-pipeline-refactoring.md)
- [Phase-specific Plans](implementation-plans/) - Detailed implementation phases

### 🗂️ Temporary Files
- [docs/temp/](temp/) - Handover files, session summaries, and temporary documentation

## Quick Start

1. **New to Swisper Core?** Start with [Architecture Overview](architecture/overview.md)
2. **Setting up development?** See [Local Setup](deployment/local-setup.md)
3. **Working with APIs?** Check [API Documentation](api/API_DOCUMENTATION.md)
4. **Deploying to production?** Follow [Production Strategy](deployment/production-strategy.md)

## Key Concepts

- **SwisperContext**: Central context object managed by swisper_core module
- **Contract Engine**: FSM-based workflow execution system
- **Intent Extraction**: LLM-powered request routing and classification
- **Haystack Pipelines**: Data processing pipelines for search and RAG
- **Privacy-First**: Built-in PII detection, encryption, and Swiss compliance

## Contributing to Documentation

When updating documentation:
1. Follow the topic-based organization structure
2. Update cross-references when moving files
3. Ensure code examples use correct import paths
4. Test all documentation links before committing
5. Update this index when adding new documentation files

For questions about the documentation structure or content, refer to the [Architecture Overview](architecture/overview.md) or the main [README](../README.md).
