# Production Deployment Strategy

## Overview

This guide outlines the strategic approach for deploying Swisper Core in production environments, with special emphasis on Switzerland hosting requirements, data sovereignty compliance, and scalable architecture patterns.

## Switzerland Hosting Requirements

### Data Sovereignty Compliance

**Local Processing Requirements**:
- All AI model inference must occur within Swiss borders
- No user data transmission to external cloud AI services
- Local deployment of T5 models for summarization
- Local sentence-transformers for semantic embeddings

**Approved Infrastructure**:
- Swiss-based cloud providers (e.g., Exoscale, cloudscale.ch)
- On-premises deployment in Swiss data centers
- Hybrid cloud with Swiss-resident data processing

**Compliance Framework**:
```yaml
data_residency:
  location: "Switzerland"
  cross_border_transfer: false
  encryption_at_rest: true
  encryption_in_transit: true

processing_requirements:
  ai_models: "local_only"
  user_data: "swiss_resident"
  logs: "swiss_resident"
  backups: "swiss_resident"
```

### Legal and Regulatory Considerations

**Swiss Federal Data Protection Act (FADP)**:
- User consent management for data processing
- Right to data portability and deletion
- Data breach notification requirements
- Privacy by design implementation

**GDPR Compliance** (for EU users):
- Enhanced consent mechanisms
- Data subject rights implementation
- Cross-border data transfer restrictions
- Privacy impact assessments

## Architecture for Production

### High-Level Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                           │
│                     (HAProxy/NGINX)                            │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway Cluster                         │
│                   (FastAPI + Gunicorn)                         │
├─────────────────────────────────────────────────────────────────┤
│  Gateway 1    │  Gateway 2    │  Gateway 3    │  Gateway N     │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Contract Engine  │  Pipeline Manager  │  Memory Manager       │
│  (FSM Processing) │  (Haystack Pipes)  │  (Multi-tier Memory)  │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL      │  Redis Cluster    │  Milvus Vector DB      │
│  (Sessions/Meta) │  (Buffer/Cache)   │  (Semantic Memory)     │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                   Storage & Compliance                         │
├─────────────────────────────────────────────────────────────────┤
│  S3-Compatible   │  Local AI Models  │  Monitoring Stack      │
│  (Artifacts)     │  (T5, Embeddings) │  (Prometheus/Grafana)  │
└─────────────────────────────────────────────────────────────────┘
```

### Containerization Strategy

**Docker Compose for Development**:
```yaml
version: '3.8'
services:
  gateway:
    build: ./gateway
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/swisper
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
      
  contract-engine:
    build: ./contract_engine
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/swisper
    depends_on:
      - postgres
      
  memory-manager:
    build: ./memory_manager
    environment:
      - REDIS_URL=redis://redis:6379
      - MILVUS_HOST=milvus
    depends_on:
      - redis
      - milvus
      
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=swisper
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      
  milvus:
    image: milvusdb/milvus:latest
    environment:
      - ETCD_ENDPOINTS=etcd:2379
      - MINIO_ADDRESS=minio:9000
    depends_on:
      - etcd
      - minio
```

**Kubernetes for Production**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: swisper-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: swisper-gateway
  template:
    metadata:
      labels:
        app: swisper-gateway
    spec:
      containers:
      - name: gateway
        image: swisper/gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: swisper-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## Local AI Model Deployment

### T5 Model Deployment

**Model Configuration**:
```python
# T5 model deployment configuration
T5_CONFIG = {
    "model_name": "t5-small",  # or t5-base for better quality
    "local_path": "/opt/models/t5-small",
    "max_input_length": 512,
    "max_output_length": 150,
    "batch_size": 4,
    "device": "cuda" if torch.cuda.is_available() else "cpu"
}

# Model loading with caching
class T5ModelManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """Load T5 model with local caching"""
        if not os.path.exists(self.config["local_path"]):
            # Download and cache model locally
            self.download_model()
            
        self.tokenizer = T5Tokenizer.from_pretrained(self.config["local_path"])
        self.model = T5ForConditionalGeneration.from_pretrained(self.config["local_path"])
        
        if self.config["device"] == "cuda":
            self.model = self.model.cuda()
```

### Sentence Transformer Deployment

**Embedding Model Configuration**:
```python
EMBEDDING_CONFIG = {
    "model_name": "all-MiniLM-L6-v2",
    "local_path": "/opt/models/sentence-transformers",
    "dimension": 384,
    "normalize_embeddings": True,
    "device": "cuda" if torch.cuda.is_available() else "cpu"
}

class EmbeddingModelManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        
    def load_model(self):
        """Load sentence transformer with local caching"""
        if not os.path.exists(self.config["local_path"]):
            self.download_model()
            
        self.model = SentenceTransformer(self.config["local_path"])
        
        if self.config["device"] == "cuda":
            self.model = self.model.to("cuda")
```

## Scalability Considerations

### Horizontal Scaling Patterns

**API Gateway Scaling**:
- Multiple FastAPI instances behind load balancer
- Session affinity for stateful operations
- Health checks and automatic failover

**Pipeline Processing Scaling**:
- Async pipeline execution with queue management
- Worker pool for CPU-intensive operations
- Auto-scaling based on queue depth

**Memory System Scaling**:
- Redis cluster for distributed caching
- Milvus cluster for vector database scaling
- PostgreSQL read replicas for query scaling

### Performance Optimization

**Caching Strategy**:
```python
CACHE_CONFIG = {
    "levels": {
        "l1_memory": {
            "type": "in_process",
            "size": "256MB",
            "ttl": 300  # 5 minutes
        },
        "l2_redis": {
            "type": "redis_cluster",
            "size": "2GB",
            "ttl": 3600  # 1 hour
        },
        "l3_persistent": {
            "type": "postgresql",
            "ttl": 86400  # 24 hours
        }
    }
}
```

**Database Optimization**:
```sql
-- Optimized indexes for session queries
CREATE INDEX CONCURRENTLY idx_sessions_user_id_active 
ON sessions(user_id) WHERE expires_at > NOW();

-- Partitioning for large tables
CREATE TABLE pipeline_executions_2024 PARTITION OF pipeline_executions
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Connection pooling configuration
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

## Security Architecture

### Network Security

**Network Segmentation**:
```yaml
network_zones:
  dmz:
    - load_balancer
    - api_gateway
  application:
    - contract_engine
    - pipeline_manager
    - memory_manager
  data:
    - postgresql
    - redis
    - milvus
  management:
    - monitoring
    - logging
    - backup_services
```

**TLS Configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name api.swisper.ch;
    
    ssl_certificate /etc/ssl/certs/swisper.crt;
    ssl_certificate_key /etc/ssl/private/swisper.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://gateway_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Authentication and Authorization

**JWT Configuration**:
```python
JWT_CONFIG = {
    "algorithm": "RS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "issuer": "swisper.ch",
    "audience": "swisper-api"
}

class JWTManager:
    def __init__(self, private_key: str, public_key: str):
        self.private_key = private_key
        self.public_key = public_key
        
    def create_access_token(self, user_id: str, scopes: List[str]) -> str:
        payload = {
            "sub": user_id,
            "scopes": scopes,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=JWT_CONFIG["access_token_expire_minutes"]),
            "iss": JWT_CONFIG["issuer"],
            "aud": JWT_CONFIG["audience"]
        }
        return jwt.encode(payload, self.private_key, algorithm=JWT_CONFIG["algorithm"])
```

## Monitoring and Observability

### Metrics Collection

**Prometheus Configuration**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'swisper-gateway'
    static_configs:
      - targets: ['gateway:8000']
    metrics_path: '/metrics'
    
  - job_name: 'swisper-contract-engine'
    static_configs:
      - targets: ['contract-engine:8001']
      
  - job_name: 'swisper-memory-manager'
    static_configs:
      - targets: ['memory-manager:8002']
```

**Custom Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Pipeline execution metrics
pipeline_executions_total = Counter(
    'swisper_pipeline_executions_total',
    'Total number of pipeline executions',
    ['pipeline_name', 'status']
)

pipeline_duration_seconds = Histogram(
    'swisper_pipeline_duration_seconds',
    'Time spent executing pipelines',
    ['pipeline_name']
)

active_sessions = Gauge(
    'swisper_active_sessions',
    'Number of active user sessions'
)
```

### Logging Strategy

**Structured Logging**:
```python
import structlog

logger = structlog.get_logger()

# Example usage
logger.info(
    "Pipeline execution completed",
    pipeline_name="product_search",
    session_id="sess_123",
    duration_ms=1250,
    result_count=15
)
```

**Log Aggregation**:
```yaml
# Fluentd configuration for log aggregation
<source>
  @type tail
  path /var/log/swisper/*.log
  pos_file /var/log/fluentd/swisper.log.pos
  tag swisper.*
  format json
</source>

<match swisper.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name swisper-logs
  type_name _doc
</match>
```

## Backup and Disaster Recovery

### Backup Strategy

**Database Backups**:
```bash
#!/bin/bash
# PostgreSQL backup script
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -h postgres -U swisper_user swisper_db | gzip > "$BACKUP_DIR/swisper_$DATE.sql.gz"

# Retain last 30 days
find "$BACKUP_DIR" -name "swisper_*.sql.gz" -mtime +30 -delete

# Upload to Swiss S3-compatible storage
aws s3 cp "$BACKUP_DIR/swisper_$DATE.sql.gz" s3://swisper-backups/postgresql/
```

**Vector Database Backups**:
```python
# Milvus backup automation
class MilvusBackupManager:
    def __init__(self, milvus_client: MilvusClient, backup_storage: str):
        self.milvus = milvus_client
        self.backup_storage = backup_storage
        
    async def create_backup(self, collection_name: str):
        """Create backup of Milvus collection"""
        backup_name = f"{collection_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Export collection data
        entities = await self.milvus.query(
            collection_name=collection_name,
            expr="",
            output_fields=["*"]
        )
        
        # Save to backup storage
        backup_path = f"{self.backup_storage}/{backup_name}.json"
        with open(backup_path, 'w') as f:
            json.dump(entities, f)
            
        return backup_path
```

### Disaster Recovery Plan

**Recovery Time Objectives (RTO)**:
- Critical services: 15 minutes
- Full system restoration: 4 hours
- Data loss tolerance (RPO): 1 hour

**Recovery Procedures**:
1. **Service Restoration**: Automated failover to backup infrastructure
2. **Data Recovery**: Restore from latest backups with point-in-time recovery
3. **Validation**: Comprehensive testing of restored services
4. **Monitoring**: Enhanced monitoring during recovery period

## Deployment Automation

### CI/CD Pipeline

**GitLab CI Configuration**:
```yaml
stages:
  - test
  - build
  - deploy-staging
  - deploy-production

test:
  stage: test
  script:
    - poetry install
    - poetry run pytest
    - poetry run pylint contract_engine gateway haystack_pipeline

build:
  stage: build
  script:
    - docker build -t swisper/gateway:$CI_COMMIT_SHA ./gateway
    - docker push swisper/gateway:$CI_COMMIT_SHA

deploy-production:
  stage: deploy-production
  script:
    - kubectl set image deployment/swisper-gateway gateway=swisper/gateway:$CI_COMMIT_SHA
    - kubectl rollout status deployment/swisper-gateway
  only:
    - main
  when: manual
```

### Infrastructure as Code

**Terraform Configuration**:
```hcl
# Swiss cloud provider configuration
provider "exoscale" {
  key    = var.exoscale_api_key
  secret = var.exoscale_secret_key
  region = "ch-gva-2"
}

resource "exoscale_compute_instance" "swisper_app" {
  count           = 3
  name            = "swisper-app-${count.index + 1}"
  template_id     = data.exoscale_compute_template.ubuntu.id
  type            = "standard.large"
  disk_size       = 50
  security_groups = [exoscale_security_group.swisper_app.name]
  
  user_data = templatefile("${path.module}/user_data.sh", {
    docker_image = var.swisper_image
  })
}
```

For implementation details, see:
- [Local Setup Guide](local-setup.md)
- [Architecture Overview](../architecture/overview.md)
- [Testing Strategy](../testing/strategy.md)
