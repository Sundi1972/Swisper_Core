# Local Development Setup Guide

## Overview

This guide provides step-by-step instructions for setting up a complete Swisper Core development environment on your local machine.

## Prerequisites

### System Requirements

**Operating System**:
- macOS 10.15+ or Ubuntu 20.04+ or Windows 10+ with WSL2
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

**Required Software**:
- Python 3.12+ (managed via pyenv)
- Node.js 18+ (managed via nvm)
- Docker and Docker Compose
- Git
- Poetry (Python dependency management)

### Development Tools

**Recommended IDE**:
- VS Code with Python and TypeScript extensions
- PyCharm Professional (optional)

**Required Extensions** (VS Code):
- Python
- Pylance
- TypeScript and JavaScript Language Features
- Docker
- GitLens

## Installation Steps

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/Sundi1972/Swisper_Core.git
cd Swisper_Core

# Verify repository structure
ls -la
```

### 2. Python Environment Setup

**Install pyenv** (if not already installed):
```bash
# macOS
brew install pyenv

# Ubuntu
curl https://pyenv.run | bash

# Add to shell profile
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
source ~/.bashrc
```

**Install Python and Poetry**:
```bash
# Install Python 3.12
pyenv install 3.12.0
pyenv global 3.12.0

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
python --version  # Should show 3.12.x
poetry --version
```

### 3. Backend Dependencies

**Install Python dependencies**:
```bash
# Install all dependencies
poetry install

# Verify installation
poetry run python -c "import fastapi; print('FastAPI installed successfully')"
poetry run python -c "import haystack; print('Haystack installed successfully')"
```

**Install additional AI model dependencies**:
```bash
# Install sentence transformers and T5 models
poetry run pip install sentence-transformers transformers torch

# Download models locally (for Switzerland hosting compliance)
poetry run python -c "
from sentence_transformers import SentenceTransformer
from transformers import T5Tokenizer, T5ForConditionalGeneration

# Download sentence transformer
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save('./models/sentence-transformers/all-MiniLM-L6-v2')

# Download T5 model
tokenizer = T5Tokenizer.from_pretrained('t5-small')
model = T5ForConditionalGeneration.from_pretrained('t5-small')
tokenizer.save_pretrained('./models/t5-small')
model.save_pretrained('./models/t5-small')

print('Models downloaded successfully')
"
```

### 4. Frontend Dependencies

**Install Node.js and npm**:
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# Install Node.js
nvm install 18
nvm use 18

# Verify installation
node --version  # Should show v18.x.x
npm --version
```

**Install frontend dependencies**:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Verify installation
npm run build

# Return to root directory
cd ..
```

### 5. Database Setup

**Install PostgreSQL**:
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Create database**:
```bash
# Create database and user
sudo -u postgres psql -c "CREATE DATABASE swisper_dev;"
sudo -u postgres psql -c "CREATE USER swisper_user WITH PASSWORD 'dev_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE swisper_dev TO swisper_user;"

# Test connection
psql -h localhost -U swisper_user -d swisper_dev -c "SELECT version();"
```

### 6. Redis Setup

**Install Redis**:
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping  # Should return PONG
```

### 7. Vector Database Setup (Milvus)

**Using Docker Compose**:
```bash
# Create Milvus directory
mkdir -p ./docker/milvus

# Create docker-compose.yml for Milvus
cat > ./docker/milvus/docker-compose.yml << 'EOF'
version: '3.5'

services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - minio:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.0
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - "etcd"
      - "minio"

volumes:
  etcd:
  minio:
  milvus:
EOF

# Start Milvus
cd ./docker/milvus
docker-compose up -d

# Verify Milvus is running
docker-compose ps

# Return to root directory
cd ../..
```

## Environment Configuration

### 1. Environment Variables

**Create .env file**:
```bash
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://swisper_user:dev_password@localhost:5432/swisper_dev

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530

# OpenAI Configuration (for development)
OPENAI_API_KEY=your_openai_api_key_here

# Google Shopping API
GOOGLE_SHOPPING_API_KEY=your_google_shopping_api_key_here

# Local Model Paths
T5_MODEL_PATH=./models/t5-small
SENTENCE_TRANSFORMER_PATH=./models/sentence-transformers/all-MiniLM-L6-v2

# Development Settings
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Security
JWT_SECRET_KEY=your_jwt_secret_key_for_development
ENCRYPTION_KEY=your_encryption_key_for_development
EOF
```

**Load environment variables**:
```bash
# Add to shell profile
echo 'export $(cat .env | xargs)' >> ~/.bashrc
source ~/.bashrc
```

### 2. Database Migration

**Run database migrations**:
```bash
# Create database schema
poetry run python -c "
from contract_engine.database import create_tables
create_tables()
print('Database tables created successfully')
"

# Verify tables
psql -h localhost -U swisper_user -d swisper_dev -c "\dt"
```

### 3. Initialize Vector Database

**Create Milvus collections**:
```bash
poetry run python -c "
from memory_manager.vector_store import VectorMemoryStore
from memory_manager.embeddings import EmbeddingModelManager

# Initialize embedding model
embedding_manager = EmbeddingModelManager({
    'model_name': 'all-MiniLM-L6-v2',
    'local_path': './models/sentence-transformers/all-MiniLM-L6-v2'
})
embedding_manager.load_model()

# Initialize vector store
vector_store = VectorMemoryStore({
    'host': 'localhost',
    'port': 19530
})

# Create collections
vector_store.setup_collections()
print('Milvus collections created successfully')
"
```

## Development Workflow

### 1. Starting Development Services

**Start all services**:
```bash
# Start databases
brew services start postgresql  # macOS
brew services start redis       # macOS

# Or for Ubuntu:
# sudo systemctl start postgresql redis-server

# Start Milvus
cd ./docker/milvus && docker-compose up -d && cd ../..

# Start backend services
poetry run python gateway/main.py &
GATEWAY_PID=$!

# Start frontend development server
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Services started:"
echo "- Gateway: http://localhost:8000"
echo "- Frontend: http://localhost:3000"
echo "- Milvus: http://localhost:19530"
```

**Stop services**:
```bash
# Stop background processes
kill $GATEWAY_PID $FRONTEND_PID

# Stop Docker services
cd ./docker/milvus && docker-compose down && cd ../..

# Stop system services
brew services stop postgresql redis  # macOS
# sudo systemctl stop postgresql redis-server  # Ubuntu
```

### 2. Running Tests

**Backend tests**:
```bash
# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_performance.py          # Performance tests
poetry run pytest tests/test_pipeline_components.py # Pipeline component tests
poetry run pytest tests/test_fsm_integration.py     # FSM integration tests

# Run tests with coverage
poetry run pytest --cov=contract_engine --cov=gateway --cov=haystack_pipeline
```

**Frontend tests**:
```bash
cd frontend

# Run unit tests
npm test

# Run end-to-end tests
npm run test:e2e

cd ..
```

**Playwright tests**:
```bash
# Install Playwright browsers
npx playwright install

# Run end-to-end tests
npx playwright test

# Run specific test
npx playwright test playwright_tests/e2e_gpu_purchase.spec.js
```

### 3. Code Quality

**Linting**:
```bash
# Python linting
poetry run pylint contract_engine gateway haystack_pipeline orchestrator tool_adapter

# Frontend linting
cd frontend && npm run lint && cd ..

# Fix auto-fixable issues
cd frontend && npm run lint:fix && cd ..
```

**Type checking**:
```bash
# Python type checking
poetry run mypy contract_engine gateway haystack_pipeline

# TypeScript checking
cd frontend && npm run type-check && cd ..
```

**Code formatting**:
```bash
# Python formatting
poetry run black contract_engine gateway haystack_pipeline orchestrator tool_adapter

# Frontend formatting
cd frontend && npm run format && cd ..
```

## Troubleshooting

### Common Issues

**1. Poetry installation fails**:
```bash
# Clear Poetry cache
poetry cache clear pypi --all

# Reinstall dependencies
rm poetry.lock
poetry install
```

**2. Database connection errors**:
```bash
# Check PostgreSQL status
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Ubuntu

# Reset database
dropdb -h localhost -U swisper_user swisper_dev
createdb -h localhost -U swisper_user swisper_dev
```

**3. Milvus connection issues**:
```bash
# Check Milvus status
cd ./docker/milvus
docker-compose ps
docker-compose logs milvus

# Restart Milvus
docker-compose down
docker-compose up -d
cd ../..
```

**4. Model download failures**:
```bash
# Manual model download
mkdir -p ./models/sentence-transformers
mkdir -p ./models/t5-small

# Download with specific cache directory
export TRANSFORMERS_CACHE=./models/transformers_cache
poetry run python -c "
from transformers import T5Tokenizer, T5ForConditionalGeneration
tokenizer = T5Tokenizer.from_pretrained('t5-small', cache_dir='./models/transformers_cache')
model = T5ForConditionalGeneration.from_pretrained('t5-small', cache_dir='./models/transformers_cache')
"
```

### Performance Optimization

**1. Enable GPU acceleration** (if available):
```bash
# Install CUDA-enabled PyTorch
poetry run pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU availability
poetry run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

**2. Optimize database performance**:
```bash
# PostgreSQL optimization
psql -h localhost -U swisper_user -d swisper_dev -c "
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
SELECT pg_reload_conf();
"
```

**3. Redis optimization**:
```bash
# Configure Redis for development
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Development Best Practices

### 1. Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature-name
```

### 2. Testing Strategy

- Write unit tests for all new components
- Add integration tests for pipeline changes
- Update end-to-end tests for UI changes
- Run full test suite before committing

### 3. Code Review Checklist

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Performance impact considered
- [ ] Security implications reviewed

## Next Steps

After completing the local setup:

1. **Explore the codebase**: Start with the README and architecture documentation
2. **Run the test suite**: Ensure everything works correctly
3. **Make a small change**: Try modifying a component and running tests
4. **Read the deployment guide**: Understand production deployment strategies

For production deployment, see:
- [Production Strategy](production-strategy.md)
- [Architecture Overview](../architecture/overview.md)
- [Testing Strategy](../testing/strategy.md)
