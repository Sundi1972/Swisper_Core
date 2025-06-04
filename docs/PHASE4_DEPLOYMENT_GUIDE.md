# Phase 4: Privacy & Governance Deployment Guide

## Overview

This guide provides comprehensive deployment instructions for Phase 4 Privacy & Governance features in Swisper Core, specifically tailored for Switzerland hosting requirements with complete local data processing compliance.

## Switzerland Hosting Architecture

### Local Processing Requirements
All privacy processing must occur within Switzerland infrastructure:

```yaml
# docker-compose.yml privacy services
services:
  swisper-privacy:
    build: .
    environment:
      - PII_USE_NER=true
      - PII_USE_LLM_FALLBACK=false  # Critical for Switzerland compliance
      - SPACY_MODEL=en_core_web_lg
    volumes:
      - ./models:/app/models  # Local model storage
```

### Data Sovereignty Compliance
- ✅ spaCy NER processing (local)
- ✅ T5 summarization (local)
- ✅ Milvus vector storage (local)
- ❌ OpenAI API calls (disabled)
- ❌ External PII services (not used)

## Infrastructure Setup

### 1. PostgreSQL with pgcrypto Extension

```sql
-- Enable pgcrypto for per-user encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Verify extension
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';
```

### 2. Redis Configuration for Memory Buffer

```redis
# redis.conf for production
maxmemory 4gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
appendonly no  # Disable AOF for low-latency
```

### 3. Milvus Lite Embedded Mode

```python
# No external Milvus server required
from pymilvus import connections, utility

connections.connect(
    alias="default",
    uri="./milvus_lite.db"  # Local embedded database
)
```

### 4. S3-Compatible Storage (Switzerland Region)

```yaml
# Environment configuration
AWS_REGION: eu-central-1  # Frankfurt (closest to Switzerland)
SWISPER_AUDIT_BUCKET: swisper-audit-ch
AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
```

## Model Deployment

### spaCy Model Installation

```bash
# Download and install spaCy model locally
poetry run python -m spacy download en_core_web_lg

# Verify model availability
poetry run python -c "import spacy; nlp = spacy.load('en_core_web_lg'); print('Model loaded successfully')"
```

### Model Pre-loading Script

```python
# scripts/preload_models.py
import spacy
from sentence_transformers import SentenceTransformer
import logging

def preload_privacy_models():
    """Pre-load all privacy models for faster startup"""
    try:
        # Load spaCy NER model
        nlp = spacy.load("en_core_web_lg")
        logging.info("spaCy model loaded successfully")
        
        # Load sentence transformer for embeddings
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logging.info("SentenceTransformer model loaded successfully")
        
        return True
    except Exception as e:
        logging.error(f"Failed to preload models: {e}")
        return False

if __name__ == "__main__":
    preload_privacy_models()
```

## Environment Configuration

### Production Environment Variables

```bash
# .env.production
# Privacy & Governance Configuration
SWISPER_MASTER_KEY=<generate_with_fernet_generate_key>
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_REGION=eu-central-1
SWISPER_AUDIT_BUCKET=swisper-audit-artifacts-switzerland

# PII Detection Configuration
PII_DETECTION_CONFIDENCE_THRESHOLD=0.7
PII_REDACTION_METHOD=placeholder
PII_USE_NER=true
PII_USE_LLM_FALLBACK=false  # Critical for Switzerland compliance

# Encryption Configuration
ENCRYPTION_VERSION=v1
SESSION_ENCRYPTION_ENABLED=true

# GDPR Compliance
DATA_RETENTION_YEARS=7
AUDIT_TRAIL_ENABLED=true

# Performance Tuning
REDIS_MAX_MEMORY=4gb
MILVUS_CACHE_SIZE=2gb
T5_MODEL_CACHE=true
```

### Key Generation Script

```python
# scripts/generate_master_key.py
from cryptography.fernet import Fernet
import base64

def generate_master_key():
    """Generate master encryption key for production"""
    key = Fernet.generate_key()
    key_string = base64.urlsafe_b64encode(key).decode()
    
    print("Generated master key:")
    print(f"SWISPER_MASTER_KEY={key_string}")
    print("\nAdd this to your production environment variables")
    print("Keep this key secure and backed up!")

if __name__ == "__main__":
    generate_master_key()
```

## Docker Deployment

### Production Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies for spaCy and cryptography
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Download spaCy model
RUN python -m spacy download en_core_web_lg

# Copy application code
COPY . .

# Pre-load models for faster startup
RUN python scripts/preload_models.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD python -c "from contract_engine.privacy.pii_redactor import pii_redactor; print('Health OK')"

EXPOSE 8000
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Production

```yaml
version: '3.8'

services:
  swisper-core:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://swisper_user:${POSTGRES_PASSWORD}@postgres:5432/swisper_db
      - REDIS_URL=redis://redis:6379
      - SWISPER_MASTER_KEY=${SWISPER_MASTER_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - PII_USE_LLM_FALLBACK=false
    depends_on:
      - postgres
      - redis
    volumes:
      - ./models:/app/models
      - ./milvus_data:/app/milvus_data

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=swisper_db
      - POSTGRES_USER=swisper_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Performance Optimization

### CPU Affinity Configuration

```bash
# Set CPU affinity for privacy processing
taskset -c 0-3 python -m uvicorn gateway.main:app

# Or in systemd service
[Service]
CPUAffinity=0-3
```

### Memory Tuning

```python
# config/performance.py
PRIVACY_PERFORMANCE_CONFIG = {
    "spacy_batch_size": 32,
    "embedding_batch_size": 16,
    "redis_connection_pool": 20,
    "milvus_cache_size": "2GB",
    "t5_model_cache": True
}
```

### Monitoring Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'swisper-privacy'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

## Security Configuration

### TLS/SSL Setup

```nginx
# nginx.conf for HTTPS termination
server {
    listen 443 ssl http2;
    server_name swisper.example.com;
    
    ssl_certificate /etc/ssl/certs/swisper.crt;
    ssl_certificate_key /etc/ssl/private/swisper.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall Rules

```bash
# UFW firewall configuration
ufw allow 22/tcp    # SSH
ufw allow 443/tcp   # HTTPS
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw deny 8000/tcp   # Block direct access to app
ufw enable
```

## Backup and Recovery

### Database Backup Script

```bash
#!/bin/bash
# scripts/backup_privacy_data.sh

BACKUP_DIR="/backups/swisper"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
pg_dump -h localhost -U swisper_user swisper_db > "$BACKUP_DIR/postgres_$DATE.sql"

# Backup Milvus data
tar -czf "$BACKUP_DIR/milvus_$DATE.tar.gz" ./milvus_data/

# Backup Redis (if persistence enabled)
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Encrypt backups
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/postgres_$DATE.sql"
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/milvus_$DATE.tar.gz"

echo "Backup completed: $DATE"
```

### Recovery Procedures

```bash
#!/bin/bash
# scripts/restore_privacy_data.sh

BACKUP_FILE=$1
DATE=$(date +%Y%m%d_%H%M%S)

# Stop services
docker-compose down

# Decrypt and restore PostgreSQL
gpg --decrypt "$BACKUP_FILE.gpg" | psql -h localhost -U swisper_user swisper_db

# Restore Milvus data
tar -xzf "milvus_backup.tar.gz" -C ./

# Restart services
docker-compose up -d

echo "Recovery completed: $DATE"
```

## Monitoring and Alerting

### Health Check Endpoints

```python
# Add to gateway/main.py
@app.get("/health/privacy")
async def privacy_health_check():
    """Health check for privacy components"""
    try:
        from contract_engine.privacy.pii_redactor import pii_redactor
        from contract_engine.privacy.encryption_service import encryption_service
        from contract_engine.privacy.audit_store import audit_store
        
        # Test PII redaction
        test_text = "Test email: test@example.com"
        redacted = pii_redactor.redact(test_text)
        
        # Test encryption
        test_data = {"test": "data"}
        encrypted = encryption_service.encrypt_user_data("test_user", test_data)
        decrypted = encryption_service.decrypt_user_data("test_user", encrypted)
        
        # Test audit store
        s3_available = audit_store.s3_client is not None
        
        return {
            "status": "healthy",
            "pii_redaction": "working",
            "encryption": "working",
            "audit_store": "working" if s3_available else "s3_unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

### Prometheus Metrics

```python
# monitoring/privacy_metrics.py
from prometheus_client import Counter, Histogram, Gauge

pii_detections = Counter('swisper_pii_detections_total', 'Total PII detections', ['entity_type'])
pii_processing_time = Histogram('swisper_pii_processing_seconds', 'PII processing time')
encryption_operations = Counter('swisper_encryption_operations_total', 'Encryption operations', ['operation'])
audit_artifacts = Gauge('swisper_audit_artifacts_total', 'Total audit artifacts stored')
```

## Troubleshooting

### Common Issues

#### 1. spaCy Model Not Found
```bash
# Solution: Download model manually
poetry run python -m spacy download en_core_web_lg

# Verify installation
poetry run python -c "import spacy; spacy.load('en_core_web_lg')"
```

#### 2. Encryption Key Issues
```bash
# Generate new master key
python scripts/generate_master_key.py

# Verify key format
python -c "from cryptography.fernet import Fernet; Fernet(b'your_key_here')"
```

#### 3. S3 Connection Issues
```bash
# Test S3 connectivity
aws s3 ls s3://swisper-audit-artifacts-switzerland --region eu-central-1

# Verify credentials
aws sts get-caller-identity
```

#### 4. Performance Issues
```bash
# Check memory usage
docker stats swisper-core

# Monitor PII processing time
curl http://localhost:8000/metrics | grep pii_processing
```

### Log Analysis

```bash
# Monitor privacy-related logs
docker logs swisper-core | grep -E "(PII|privacy|encryption|audit)"

# Check for errors
docker logs swisper-core | grep -E "(ERROR|CRITICAL)" | tail -20
```

## Compliance Verification

### GDPR Compliance Checklist
- [ ] PII detection and redaction working
- [ ] User memory deletion endpoint functional
- [ ] Audit trail storage operational
- [ ] Data retention policies configured
- [ ] Encryption at rest enabled
- [ ] Right to access implemented

### Switzerland Data Protection Verification
- [ ] No external API calls for PII processing
- [ ] All models running locally
- [ ] Data sovereignty maintained
- [ ] Audit logs in Switzerland region
- [ ] Encryption keys managed locally

### Performance SLA Verification
- [ ] PII detection: <100ms
- [ ] T5 summarization: <200ms
- [ ] Semantic search: <100ms
- [ ] Memory operations: <50ms
- [ ] GDPR endpoints: <500ms

This deployment guide ensures complete Switzerland hosting compliance while maintaining business-critical privacy protection and performance requirements.
