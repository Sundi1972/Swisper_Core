# Phase 3: Switzerland Deployment Guide

## Overview

This guide provides comprehensive deployment instructions for Phase 3 Haystack Pipeline Integration with T5-based RollingSummariser and semantic memory capabilities, specifically optimized for Switzerland hosting requirements.

## Prerequisites

### System Requirements
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 16GB minimum (32GB recommended)
- **Storage**: 50GB+ SSD for models and vector data
- **Python**: 3.12+ with poetry package manager
- **Docker**: 20.10+ with docker-compose

### Model Storage Requirements
- **T5-small**: ~242MB download + ~500MB runtime memory
- **sentence-transformers**: ~90MB download + ~200MB runtime memory
- **Milvus Lite**: ~50MB + vector data storage
- **Total**: ~1GB+ for models and runtime memory

## Installation Steps

### 1. Environment Setup

#### Clone and Setup Repository
```bash
git clone https://github.com/Sundi1972/Swisper_Core.git
cd Swisper_Core
git checkout devin/1749046679-fsm-debugging-clean

poetry install

poetry run python -c "from transformers import T5Tokenizer; print('T5 available')"
poetry run python -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers available')"
```

#### Environment Configuration
Create `.env` file with Switzerland-specific settings:
```bash
# OpenAI API Key (for fallback only)
OPENAI_API_KEY=your_openai_key_here

# SearchAPI Key
SEARCHAPI_API_KEY=your_searchapi_key_here

# Database Configuration
POSTGRES_DB=swisper_db
POSTGRES_USER=swisper_user
POSTGRES_PASSWORD=secure_password_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=redis_password_here
REDIS_MAX_CONNECTIONS=20

# Memory Manager Configuration
MEMORY_SUMMARY_TRIGGER_TOKENS=3000
MEMORY_MAX_BUFFER_TOKENS=4000
MEMORY_BUFFER_TTL_HOURS=12

# T5 Model Configuration
T5_MODEL_NAME=t5-small
T5_MAX_LENGTH=150
T5_MIN_LENGTH=30
T5_NUM_BEAMS=2

# Sentence Transformers Configuration
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32

# Milvus Configuration
MILVUS_DB_PATH=./milvus_semantic_memory.db
MILVUS_COLLECTION_NAME=semantic_memory
MILVUS_SIMILARITY_THRESHOLD=0.7

# Performance Settings
MAX_CONCURRENT_SUMMARIZATIONS=2
SEMANTIC_SEARCH_TIMEOUT_MS=100
T5_SUMMARIZATION_TIMEOUT_MS=200

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS Configuration for Switzerland
CORS_ALLOWED_ORIGINS=https://your-swiss-domain.ch,https://localhost:5173
```

### 2. Model Pre-loading and Optimization

#### Download Models Locally
```bash
mkdir -p ~/.cache/huggingface/transformers
mkdir -p ~/.cache/sentence-transformers

poetry run python -c "
from transformers import T5Tokenizer, T5ForConditionalGeneration
tokenizer = T5Tokenizer.from_pretrained('t5-small')
model = T5ForConditionalGeneration.from_pretrained('t5-small')
print('T5-small model cached successfully')
"

poetry run python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print('sentence-transformers model cached successfully')
"
```

#### Model Optimization for Switzerland Hosting
```bash
cat > optimize_models.py << 'EOF'
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
from sentence_transformers import SentenceTransformer
import time

def optimize_t5_model():
    print("Optimizing T5-small model...")
    
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    model = T5ForConditionalGeneration.from_pretrained('t5-small')
    
    test_text = "This is a test text for summarization performance measurement."
    inputs = tokenizer.encode("summarize: " + test_text, return_tensors="pt", max_length=512, truncation=True)
    
    for _ in range(3):
        with torch.no_grad():
            outputs = model.generate(inputs, max_length=150, min_length=30, num_beams=2, early_stopping=True)
    
    start_time = time.time()
    with torch.no_grad():
        outputs = model.generate(inputs, max_length=150, min_length=30, num_beams=2, early_stopping=True)
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    print(f"T5-small summarization latency: {latency_ms:.2f}ms")
    
    if latency_ms > 200:
        print("WARNING: T5 latency exceeds 200ms SLA")
    else:
        print("✓ T5 latency meets <200ms SLA")

def optimize_embedding_model():
    print("Optimizing sentence-transformers model...")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    test_texts = ["User prefers gaming laptops", "Budget constraint under 1500 CHF", "Needs good battery life"]
    
    for _ in range(3):
        embeddings = model.encode(test_texts)
    
    start_time = time.time()
    embeddings = model.encode(test_texts)
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    print(f"Embedding generation latency: {latency_ms:.2f}ms for {len(test_texts)} texts")
    print(f"Embedding dimensions: {embeddings.shape}")
    
    if latency_ms > 50:
        print("WARNING: Embedding latency exceeds 50ms SLA")
    else:
        print("✓ Embedding latency meets <50ms SLA")

if __name__ == "__main__":
    optimize_t5_model()
    optimize_embedding_model()
    print("Model optimization complete")
EOF

poetry run python optimize_models.py
```

### 3. Infrastructure Deployment

#### Docker Compose for Switzerland
Update docker-compose.yml for production:

```yaml
version: '3.8'

services:
  gateway:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://swisper_user:${POSTGRES_PASSWORD}@postgres:5432/swisper_db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./contract_engine:/app/contract_engine
      - ./orchestrator:/app/orchestrator
      - ./haystack_pipeline:/app/haystack_pipeline
      - ./tool_adapter:/app/tool_adapter
      - ./gateway:/app/gateway
      - model_cache:/root/.cache/huggingface
      - sentence_transformers_cache:/root/.cache/sentence-transformers
      - milvus_data:/app/milvus_data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 4G
          cpus: '2'

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --appendonly no
      --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 10s
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  model_cache:
  sentence_transformers_cache:
  milvus_data:
```

#### Production Deployment Script
```bash
cat > deploy_switzerland.sh << 'EOF'
#!/bin/bash
set -e

echo "🇨🇭 Starting Switzerland deployment for Swisper Core Phase 3..."

command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "Poetry is required but not installed. Aborting." >&2; exit 1; }

if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with Switzerland-specific configuration."
    exit 1
fi

echo "Pre-loading models for offline operation..."
poetry run python optimize_models.py

echo "Initializing database..."
docker-compose up -d postgres redis
sleep 10

echo "Running database migrations..."
poetry run python -c "
from orchestrator.database import init_db
init_db()
print('Database initialized successfully')
"

echo "Starting all services..."
docker-compose up -d

echo "Performing health checks..."
sleep 30

echo "Testing T5 summarization..."
poetry run python -c "
from contract_engine.pipelines.rolling_summariser import summarize_messages
messages = [{'content': 'Test message for Switzerland deployment'}]
summary = summarize_messages(messages)
print(f'✓ T5 summarization working: {summary}')
"

echo "Testing semantic memory..."
poetry run python -c "
from contract_engine.memory.milvus_store import milvus_semantic_store
result = milvus_semantic_store.add_memory('test_user', 'Test preference for deployment', 'preference')
print(f'✓ Semantic memory working: {result}')
"

echo "Testing memory manager integration..."
poetry run python -c "
from contract_engine.memory.memory_manager import MemoryManager
mm = MemoryManager()
context = mm.get_enhanced_context('test_session', 'test_user', 'test query')
print(f'✓ Memory manager integration working: {len(context)} context keys')
"

echo "🎉 Switzerland deployment completed successfully!"
echo "🔗 Application available at: http://localhost:8000"
echo "📊 Health check: http://localhost:8000/health"
echo "📚 API docs: http://localhost:8000/docs"
EOF

chmod +x deploy_switzerland.sh
```

### 4. Performance Optimization

#### CPU Optimization
```bash
echo "Setting CPU optimization for Switzerland deployment..."

sudo tee /etc/systemd/system/swisper-cpu-optimization.service > /dev/null << 'EOF'
[Unit]
Description=Swisper CPU Optimization for Switzerland
After=docker.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable swisper-cpu-optimization.service
sudo systemctl start swisper-cpu-optimization.service
```

#### Memory Optimization
```bash
echo "Configuring memory optimization..."

sudo tee -a /etc/sysctl.conf > /dev/null << 'EOF'
vm.swappiness=10
vm.dirty_ratio=15
vm.dirty_background_ratio=5
vm.overcommit_memory=1
EOF

sudo sysctl -p
```

### 5. Monitoring and Alerting

#### Health Check Endpoint
Add to gateway/main.py:

```python
@app.get("/health/detailed")
async def detailed_health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    try:
        from contract_engine.pipelines.rolling_summariser import summarize_messages
        test_messages = [{"content": "Health check test message"}]
        start_time = time.time()
        summary = summarize_messages(test_messages)
        t5_latency = (time.time() - start_time) * 1000
        
        health_status["components"]["t5_summarization"] = {
            "status": "healthy" if t5_latency < 200 else "degraded",
            "latency_ms": round(t5_latency, 2),
            "sla_met": t5_latency < 200
        }
    except Exception as e:
        health_status["components"]["t5_summarization"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    try:
        from contract_engine.memory.milvus_store import milvus_semantic_store
        start_time = time.time()
        memories = milvus_semantic_store.search_memories("health_check", "test query", top_k=1)
        semantic_latency = (time.time() - start_time) * 1000
        
        health_status["components"]["semantic_memory"] = {
            "status": "healthy" if semantic_latency < 100 else "degraded",
            "latency_ms": round(semantic_latency, 2),
            "sla_met": semantic_latency < 100
        }
    except Exception as e:
        health_status["components"]["semantic_memory"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    try:
        from contract_engine.memory.memory_manager import MemoryManager
        mm = MemoryManager()
        start_time = time.time()
        context = mm.get_context("health_check_session")
        memory_latency = (time.time() - start_time) * 1000
        
        health_status["components"]["memory_manager"] = {
            "status": "healthy" if memory_latency < 50 else "degraded",
            "latency_ms": round(memory_latency, 2),
            "sla_met": memory_latency < 50
        }
    except Exception as e:
        health_status["components"]["memory_manager"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    component_statuses = [comp["status"] for comp in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        health_status["status"] = "unhealthy"
    elif "degraded" in component_statuses:
        health_status["status"] = "degraded"
    
    return health_status
```

#### Monitoring Script
```bash
cat > monitor_switzerland.sh << 'EOF'
#!/bin/bash

echo "🇨🇭 Swisper Core Switzerland Monitoring Dashboard"
echo "================================================"

echo "📊 System Resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"

echo -e "\n🐳 Docker Containers:"
docker-compose ps

echo -e "\n🏥 Application Health:"
curl -s http://localhost:8000/health/detailed | jq '.'

echo -e "\n⚡ Performance Metrics:"
echo "T5 Model Memory: $(docker stats --no-stream --format 'table {{.Container}}\t{{.MemUsage}}' | grep gateway | awk '{print $2}')"
echo "Redis Memory: $(docker exec -it $(docker-compose ps -q redis) redis-cli --no-auth-warning -a $REDIS_PASSWORD info memory | grep used_memory_human | cut -d: -f2)"

echo -e "\n📝 Recent Logs:"
docker-compose logs --tail=10 gateway
EOF

chmod +x monitor_switzerland.sh
```

### 6. Backup and Recovery

#### Automated Backup Script
```bash
cat > backup_switzerland.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/backup/swisper-$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "🇨🇭 Creating Switzerland deployment backup..."

echo "Backing up PostgreSQL database..."
docker exec $(docker-compose ps -q postgres) pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_DIR/postgres_backup.sql

echo "Backing up Redis data..."
docker exec $(docker-compose ps -q redis) redis-cli --no-auth-warning -a $REDIS_PASSWORD BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb $BACKUP_DIR/redis_backup.rdb

echo "Backing up Milvus vector data..."
docker cp $(docker-compose ps -q gateway):/app/milvus_data $BACKUP_DIR/milvus_backup

echo "Backing up configuration..."
cp .env $BACKUP_DIR/env_backup
cp docker-compose.yml $BACKUP_DIR/docker-compose_backup.yml

echo "Backing up model cache..."
docker cp $(docker-compose ps -q gateway):/root/.cache/huggingface $BACKUP_DIR/huggingface_cache
docker cp $(docker-compose ps -q gateway):/root/.cache/sentence-transformers $BACKUP_DIR/sentence_transformers_cache

echo "✅ Backup completed: $BACKUP_DIR"
echo "📦 Backup size: $(du -sh $BACKUP_DIR | cut -f1)"
EOF

chmod +x backup_switzerland.sh
```

### 7. Security Configuration

#### SSL/TLS Setup for Switzerland
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/C=CH/ST=Zurich/L=Zurich/O=Swisper/CN=localhost"
```

#### Firewall Configuration
```bash
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow ssh

sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8443/tcp

sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 172.16.0.0/12 to any port 5432
sudo ufw allow from 192.168.0.0/16 to any port 5432

sudo ufw --force enable
sudo ufw status verbose
```

## Troubleshooting

### Common Issues

#### T5 Model Loading Issues
```bash
poetry run python -c "
from transformers import T5Tokenizer, T5ForConditionalGeneration
try:
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    model = T5ForConditionalGeneration.from_pretrained('t5-small')
    print('✅ T5 model loaded successfully')
except Exception as e:
    print(f'❌ T5 model loading failed: {e}')
"

rm -rf ~/.cache/huggingface/transformers/models--t5-small
```

#### Milvus Connection Issues
```bash
poetry run python -c "
from pymilvus import connections, utility
try:
    connections.connect(uri='./milvus_semantic_memory.db')
    collections = utility.list_collections()
    print(f'✅ Milvus connected, collections: {collections}')
except Exception as e:
    print(f'❌ Milvus connection failed: {e}')
"

rm -rf ./milvus_semantic_memory.db
```

#### Performance Issues
```bash
docker stats

poetry run python -c "
import time
from contract_engine.pipelines.rolling_summariser import summarize_messages
messages = [{'content': 'Performance test message ' * 50}]
start = time.time()
summary = summarize_messages(messages)
latency = (time.time() - start) * 1000
print(f'T5 latency: {latency:.2f}ms (SLA: <200ms)')
"
```

### Log Analysis
```bash
docker-compose logs -f gateway

docker-compose logs -f gateway | grep "T5\|summarization"
docker-compose logs -f gateway | grep "Milvus\|semantic"
docker-compose logs -f gateway | grep "Memory\|buffer"

docker-compose logs gateway > swisper_logs_$(date +%Y%m%d_%H%M%S).log
```

## Production Checklist

### Pre-deployment
- [ ] Environment variables configured for Switzerland
- [ ] Models pre-downloaded and cached locally
- [ ] Database migrations completed
- [ ] SSL certificates generated/configured
- [ ] Firewall rules configured
- [ ] Backup procedures tested

### Post-deployment
- [ ] Health checks passing
- [ ] Performance SLAs verified (<200ms T5, <100ms semantic search)
- [ ] Memory usage within limits
- [ ] Log monitoring configured
- [ ] Backup schedule automated
- [ ] Security scan completed

### Ongoing Maintenance
- [ ] Daily health check monitoring
- [ ] Weekly performance review
- [ ] Monthly backup verification
- [ ] Quarterly security updates
- [ ] Model performance optimization

This deployment guide ensures a robust, secure, and performant Switzerland deployment of Swisper Core Phase 3 with full local model processing and data sovereignty compliance.
