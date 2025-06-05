# Swisper Core

An intelligent AI assistant system implementing a sophisticated contract-based interaction framework with local AI model processing for Switzerland data sovereignty compliance.

## Overview

Swisper Core provides a robust, scalable AI assistant platform that combines Finite State Machine (FSM) control with Haystack pipeline data processing. The system is designed for Switzerland hosting requirements with local model processing and comprehensive privacy controls.

### Key Features

- **Contract-Based Interactions**: YAML-defined contracts with explicit state transitions
- **Local AI Processing**: T5 summarization and sentence-transformer embeddings for data sovereignty
- **Multi-Tier Memory System**: Ephemeral buffer, short-term summaries, long-term semantic memory, and auditable artifacts
- **Haystack Pipeline Integration**: Modular data processing with product search and preference matching
- **Switzerland Compliance**: Local model processing, PII extraction, and privacy-by-design architecture
- **Performance Optimization**: Intelligent caching, async processing, and comprehensive monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│  React Frontend │ Authentication │ Voice I/O │ Device Integration│
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway API                                 │
│  FastAPI Gateway │ JWT Validation │ Request Routing │ Security   │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                AI Assistant Core                                │
│  Contract Engine │ Pipeline Manager │ Memory Manager │ Orchestrator│
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                 │
│  PostgreSQL │ Redis Cluster │ Milvus Vector DB │ S3 Storage     │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+ (managed via pyenv)
- Node.js 18+ (managed via nvm)
- Docker and Docker Compose
- Poetry for Python dependency management

### Installation

```bash
# Clone repository
git clone https://github.com/Sundi1972/Swisper_Core.git
cd Swisper_Core

# Install Python dependencies
poetry install

# Install AI models locally (Switzerland compliance)
poetry run python scripts/download_models.py

# Setup databases
docker-compose -f docker/docker-compose.yml up -d

# Install frontend dependencies
cd frontend && npm install && cd ..

# Run development servers
poetry run python gateway/main.py &
cd frontend && npm run dev
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run linting
poetry run pylint contract_engine gateway haystack_pipeline orchestrator tool_adapter

# Run frontend tests
cd frontend && npm test && cd ..

# Run end-to-end tests
npx playwright test
```

## Core Components

### Contract Engine
- **FSM-based contract execution** with explicit state transitions
- **YAML contract definitions** for maintainable conversation flows
- **State persistence and recovery** for session continuity
- **Audit trail** for compliance and debugging

### Haystack Pipeline
- **Product Search Pipeline**: Google Shopping API integration with intelligent caching
- **Preference Match Pipeline**: LLM-based ranking with compatibility checking
- **Modular architecture** for reusable components across contracts

### Memory Manager
- **Ephemeral Buffer** (Redis): Recent messages for immediate context
- **Short-Term Summary** (Redis+Postgres): Rolling T5-based summarization
- **Long-Term Semantic Memory** (Milvus): Vector search for personalization
- **Auditable Artifacts** (S3): Complete logs for compliance

### Gateway
- **FastAPI-based API gateway** with async request handling
- **JWT authentication** with role-based access control
- **Request routing** and validation
- **Rate limiting** and security controls

## Documentation

### Architecture Documentation
- [Overall Architecture](docs/architecture/overview.md) - System architecture and component interaction
- [Tools and Contract Management](docs/architecture/tools-and-contracts.md) - FSM and pipeline integration
- [Session and Context Management](docs/architecture/session-management.md) - State persistence and recovery
- [Memory Management](docs/architecture/memory-management.md) - Multi-tier memory architecture

### Deployment Guides
- [Production Strategy](docs/deployment/production-strategy.md) - Switzerland hosting and scalability
- [Local Setup Guide](docs/deployment/local-setup.md) - Step-by-step development environment
- [Frontend Template Guide](docs/deployment/frontend-template-guide.md) - Reusable frontend template

### Testing Documentation
- [Testing Strategy](docs/testing/strategy.md) - Comprehensive testing approach
- [Test Scenarios](docs/testing/scenarios.md) - End-to-end test definitions

### Implementation History
- [Implementation Plans](docs/implementation-plans/) - Feature development history and checklists

## Development

### Project Structure

```
Swisper_Core/
├── contract_engine/          # FSM-based contract execution
├── gateway/                  # FastAPI API gateway
├── haystack_pipeline/        # Data processing pipelines
├── orchestrator/             # Session and pipeline orchestration
├── tool_adapter/             # External service integrations
├── memory_manager/           # Multi-tier memory system
├── frontend/                 # React application
├── frontend-template/        # Reusable frontend template
├── tests/                    # Comprehensive test suite
└── docs/                     # Documentation
```

### Code Quality

- **Linting**: pylint for Python, ESLint for TypeScript
- **Type Checking**: mypy for Python, TypeScript for frontend
- **Testing**: pytest for backend, Jest for frontend, Playwright for e2e
- **Coverage**: Minimum 80% for critical components

### Contributing

1. **Fork the repository** and create a feature branch
2. **Follow code style guidelines** and add comprehensive tests
3. **Update documentation** for any architectural changes
4. **Run the full test suite** before submitting
5. **Create a pull request** with detailed description

### Branch Naming Convention
- Feature branches: `feature/descriptive-name`
- Bug fixes: `bugfix/issue-description`
- Documentation: `docs/topic-name`

## Performance

### Benchmarks
- **Product Search**: <5 seconds for complex queries
- **Preference Matching**: <10 seconds for 50 products
- **Memory Retrieval**: <500ms for semantic search
- **Session Persistence**: <100ms for context serialization

### Caching Strategy
- **Attribute Analysis**: 60-minute TTL
- **Pipeline Results**: 30-minute TTL
- **Session Data**: 24-hour retention
- **Vector Embeddings**: Persistent with version control

## Security and Privacy

### Switzerland Data Sovereignty
- **Local AI Models**: T5 and sentence-transformers hosted locally
- **No External Data Transmission**: Sensitive data never leaves Swiss borders
- **Compliance**: Swiss Federal Data Protection Act (FADP) and GDPR

### Privacy Features
- **PII Detection and Redaction**: Automatic identification and secure handling
- **Consent Management**: Granular user consent tracking
- **Data Retention**: Configurable policies with automatic cleanup
- **Encryption**: At rest and in transit with Swiss-standard algorithms

## Monitoring and Observability

### Metrics Collection
- **Pipeline Performance**: Execution times and success rates
- **Memory Usage**: Buffer sizes and cache hit ratios
- **API Performance**: Response times and error rates
- **User Behavior**: Interaction patterns and conversion metrics

### Logging
- **Structured Logging**: JSON format with correlation IDs
- **Log Aggregation**: Centralized collection and analysis
- **Error Tracking**: Automatic error detection and alerting
- **Audit Trails**: Complete interaction history for compliance

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or contributions:
- **Issues**: [GitHub Issues](https://github.com/Sundi1972/Swisper_Core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Sundi1972/Swisper_Core/discussions)
- **Documentation**: [docs/](docs/)

## Acknowledgments

- **Haystack**: For the modular pipeline architecture
- **FastAPI**: For the high-performance API framework
- **Milvus**: For vector database capabilities
- **Transformers**: For local AI model processing
