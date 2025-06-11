# Redis Configuration Guide

## Production Configuration

### Docker Compose Setup

```yaml
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
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 10s
```

### Memory Management

#### Memory Limits
```bash
# Set maximum memory usage
maxmemory 4gb

# Eviction policy when memory limit reached
maxmemory-policy allkeys-lru
```

#### Eviction Policies
- `allkeys-lru`: Evict least recently used keys (recommended for cache)
- `volatile-lru`: Evict LRU keys with TTL set
- `allkeys-random`: Evict random keys
- `volatile-random`: Evict random keys with TTL set
- `volatile-ttl`: Evict keys with shortest TTL
- `noeviction`: Return errors when memory limit reached

### Persistence Configuration

#### RDB Snapshots (Recommended)
```bash
# Save snapshot if at least 1 key changed in 900 seconds
save 900 1

# Save snapshot if at least 10 keys changed in 300 seconds  
save 300 10

# Save snapshot if at least 10000 keys changed in 60 seconds
save 60 10000
```

#### AOF (Append Only File)
```bash
# Disable AOF for better performance
appendonly no

# If AOF enabled, use everysec for balance of durability/performance
appendfsync everysec
```

### Security Configuration

#### TLS/SSL
```bash
# Enable TLS
tls-port 6380
port 0

# TLS certificate files
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt

# Require TLS for all connections
tls-protocols "TLSv1.2 TLSv1.3"
```

#### Authentication
```bash
# Set password
requirepass your_secure_password

# ACL users (Redis 6+)
user default off
user swisper_app on >app_password ~* &* +@all
```

### Performance Tuning

#### Connection Settings
```bash
# Maximum number of connected clients
maxclients 10000

# TCP keepalive
tcp-keepalive 300

# TCP backlog
tcp-backlog 511
```

#### Memory Optimization
```bash
# Hash optimization
hash-max-ziplist-entries 512
hash-max-ziplist-value 64

# List optimization  
list-max-ziplist-size -2
list-compress-depth 0

# Set optimization
set-max-intset-entries 512

# Sorted set optimization
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
```

## Redis Cluster Configuration

### Cluster Setup (3+ Shards, 3+ Replicas)

#### Master Nodes
```bash
# redis-cluster-node-1.conf
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf
cluster-node-timeout 5000
appendonly yes
maxmemory 4gb
maxmemory-policy allkeys-lru
```

#### Replica Configuration
```bash
# redis-cluster-replica-1.conf
port 7001
cluster-enabled yes
cluster-config-file nodes-7001.conf
cluster-node-timeout 5000
appendonly yes
maxmemory 4gb
maxmemory-policy allkeys-lru
```

#### Cluster Creation
```bash
# Create cluster with 3 masters and 3 replicas
redis-cli --cluster create \
  192.168.1.10:7000 192.168.1.11:7000 192.168.1.12:7000 \
  192.168.1.10:7001 192.168.1.11:7001 192.168.1.12:7001 \
  --cluster-replicas 1
```

### Redis Sentinel (High Availability)

#### Sentinel Configuration
```bash
# sentinel.conf
port 26379
sentinel monitor mymaster 192.168.1.10 6379 2
sentinel auth-pass mymaster your_password
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
```

#### Sentinel Deployment
```bash
# Start sentinel
redis-sentinel /path/to/sentinel.conf
```

## Environment Variables

### Application Configuration
```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password

# Connection pool settings
REDIS_MAX_CONNECTIONS=20
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Circuit breaker settings
REDIS_FAILURE_THRESHOLD=5
REDIS_RECOVERY_TIMEOUT=60
```

### Cluster Configuration
```bash
# Redis Cluster
REDIS_CLUSTER_NODES=node1:7000,node2:7000,node3:7000
REDIS_CLUSTER_PASSWORD=cluster_password
REDIS_CLUSTER_SKIP_FULL_COVERAGE_CHECK=false

# Sentinel Configuration
REDIS_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
REDIS_SENTINEL_SERVICE_NAME=mymaster
REDIS_SENTINEL_PASSWORD=sentinel_password
```

## Monitoring and Alerting

### Key Metrics to Monitor

#### Memory Metrics
```bash
# Redis CLI commands
INFO memory
CONFIG GET maxmemory
CONFIG GET maxmemory-policy

# Key metrics
used_memory
used_memory_human
used_memory_rss
used_memory_peak
maxmemory
evicted_keys
expired_keys
```

#### Performance Metrics
```bash
# Latency monitoring
LATENCY DOCTOR
LATENCY HISTORY command

# Slow log
SLOWLOG GET 10
CONFIG SET slowlog-log-slower-than 10000

# Key metrics
instantaneous_ops_per_sec
total_commands_processed
keyspace_hits
keyspace_misses
```

#### Connection Metrics
```bash
# Connection info
INFO clients
CLIENT LIST

# Key metrics
connected_clients
client_recent_max_input_buffer
client_recent_max_output_buffer
blocked_clients
```

### Alerting Thresholds

#### Memory Alerts
```yaml
# Memory usage > 80% of maxmemory
used_memory_percentage > 80

# High eviction rate
evicted_keys_per_second > 100

# Memory fragmentation
mem_fragmentation_ratio > 1.5
```

#### Performance Alerts
```yaml
# High latency
avg_latency_ms > 10

# Low hit ratio
keyspace_hit_ratio < 0.9

# High slow queries
slow_queries_per_minute > 10
```

#### Availability Alerts
```yaml
# Redis down
redis_up == 0

# High connection usage
connected_clients_percentage > 90

# Replication lag (if using replicas)
master_repl_offset - slave_repl_offset > 1000000
```

## Backup and Recovery

### RDB Backup
```bash
# Manual backup
BGSAVE

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backup/redis"
DATE=$(date +%Y%m%d_%H%M%S)
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/dump_$DATE.rdb
```

### AOF Backup
```bash
# Rewrite AOF
BGREWRITEAOF

# Backup AOF file
cp /var/lib/redis/appendonly.aof /backup/redis/appendonly_$(date +%Y%m%d).aof
```

### Point-in-Time Recovery
```bash
# Stop Redis
systemctl stop redis

# Restore RDB file
cp /backup/redis/dump_20231201_120000.rdb /var/lib/redis/dump.rdb

# Start Redis
systemctl start redis
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage breakdown
INFO memory

# Find large keys
redis-cli --bigkeys

# Analyze memory usage by key pattern
redis-cli --memkeys
```

#### Performance Issues
```bash
# Check slow queries
SLOWLOG GET 100

# Monitor latency
redis-cli --latency
redis-cli --latency-history

# Check hit ratio
INFO stats | grep keyspace
```

#### Connection Issues
```bash
# Check connection limits
CONFIG GET maxclients
INFO clients

# Monitor connections
redis-cli --stat

# Check network connectivity
redis-cli ping
```

### Debug Commands

#### Memory Analysis
```bash
# Memory usage by database
INFO keyspace

# Sample keys
RANDOMKEY
TYPE key_name
MEMORY USAGE key_name

# Memory efficiency
INFO memory | grep mem_fragmentation_ratio
```

#### Performance Analysis
```bash
# Real-time monitoring
redis-cli --stat

# Latency monitoring
redis-cli --latency-dist

# Command statistics
INFO commandstats
```

#### Configuration Verification
```bash
# Current configuration
CONFIG GET "*"

# Specific settings
CONFIG GET maxmemory
CONFIG GET maxmemory-policy
CONFIG GET save
```

## Best Practices

### Development
1. Use Redis CLI for testing and debugging
2. Monitor memory usage during development
3. Test with realistic data volumes
4. Use appropriate data structures for use cases

### Production
1. Enable monitoring and alerting
2. Regular backup and recovery testing
3. Capacity planning based on growth projections
4. Security hardening (TLS, authentication, network isolation)
5. Performance tuning based on workload patterns

### Scaling
1. Start with single instance, scale to cluster when needed
2. Use read replicas for read-heavy workloads
3. Implement proper sharding strategy
4. Monitor and optimize based on usage patterns

### Security
1. Enable authentication and authorization
2. Use TLS for data in transit
3. Network isolation and firewall rules
4. Regular security updates and patches
5. Audit access logs and monitor for suspicious activity
