# ClawBot Coordinator - Deployment Guide

This guide covers deploying the ClawBot Coordinator using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM available
- 10GB+ disk space

## Quick Start

### Development

```bash
# Clone the repository
git clone <repository-url>
cd bot_connector

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app

# Access the application
curl http://localhost:8000/health
```

The application will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Production

```bash
# Set environment variables
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export REDIS_PASSWORD=$(openssl rand -base64 32)

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Check health
docker-compose -f docker-compose.prod.yml ps
```

## Development Deployment

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres

# Build and start with latest code
docker-compose up -d --build
```

### Hot Reload

Development mode enables hot reload for the application:

```bash
# Source code is mounted as volume
# Changes to src/ will automatically reload the server
docker-compose logs -f app
```

### Running Commands

```bash
# Run migrations
docker-compose exec app alembic upgrade head

# Run tests
docker-compose exec app pytest tests/

# Check architecture
docker-compose exec app python scripts/check_domain_imports.py

# Access database
docker-compose exec postgres psql -U clawbot -d clawbot_coordinator

# Access Redis CLI
docker-compose exec redis redis-cli
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (data will be lost!)
docker-compose down -v

# Stop without removing containers
docker-compose stop
```

## Production Deployment

### Environment Setup

Create `.env.prod` file:

```bash
# Required variables
POSTGRES_USER=clawbot
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=clawbot_coordinator
REDIS_PASSWORD=<strong-password>

# Optional
APP_NAME="ClawBot Coordinator Production"
ENVIRONMENT=production
DEBUG=false
```

Load environment:

```bash
export $(cat .env.prod | xargs)
```

### Deployment Steps

```bash
# 1. Build production image
docker-compose -f docker-compose.prod.yml build

# 2. Start database and cache first
docker-compose -f docker-compose.prod.yml up -d postgres redis

# 3. Wait for services to be healthy
docker-compose -f docker-compose.prod.yml ps

# 4. Run migrations
docker-compose -f docker-compose.prod.yml run --rm app alembic upgrade head

# 5. Start application
docker-compose -f docker-compose.prod.yml up -d app

# 6. Verify health
curl http://localhost:8000/health
```

### Zero-Downtime Updates

```bash
# 1. Pull latest code
git pull

# 2. Build new image
docker-compose -f docker-compose.prod.yml build app

# 3. Run migrations (if any)
docker-compose -f docker-compose.prod.yml run --rm app alembic upgrade head

# 4. Restart application
docker-compose -f docker-compose.prod.yml up -d app

# 5. Old container will be replaced
docker-compose -f docker-compose.prod.yml ps
```

### Scaling

```bash
# Scale application to 3 instances
docker-compose -f docker-compose.prod.yml up -d --scale app=3

# Behind a load balancer (nginx, traefik, etc.)
# Each instance connects to same database and Redis
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection string |
| `POSTGRES_PASSWORD` | Yes (prod) | - | PostgreSQL password |
| `REDIS_PASSWORD` | Yes (prod) | - | Redis password |
| `ENVIRONMENT` | No | development | Environment mode |
| `DEBUG` | No | false | Enable debug mode |
| `APP_NAME` | No | ClawBot Coordinator | Application name |

### Docker Build Arguments

```bash
# Custom Python version
docker build --build-arg PYTHON_VERSION=3.12 .

# Custom base image
docker build --build-arg BASE_IMAGE=python:3.12-slim .
```

### Volume Management

```bash
# List volumes
docker volume ls | grep clawbot

# Backup PostgreSQL
docker-compose exec postgres pg_dump -U clawbot clawbot_coordinator > backup.sql

# Restore PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U clawbot -d clawbot_coordinator

# Backup volumes
docker run --rm -v clawbot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data
```

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready -U clawbot

# Redis health
docker-compose exec redis redis-cli ping
```

### Logs

```bash
# Follow all logs
docker-compose logs -f

# Application logs only
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Export logs
docker-compose logs app > app.log
```

### Resource Usage

```bash
# Container stats
docker stats

# Specific container
docker stats clawbot-app

# Disk usage
docker system df
```

### Database Monitoring

```bash
# Active connections
docker-compose exec postgres psql -U clawbot -d clawbot_coordinator -c "SELECT count(*) FROM pg_stat_activity;"

# Table sizes
docker-compose exec postgres psql -U clawbot -d clawbot_coordinator -c "\dt+"

# Query performance
docker-compose exec postgres psql -U clawbot -d clawbot_coordinator -c "SELECT * FROM pg_stat_statements;"
```

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker-compose logs app

# Check environment variables
docker-compose exec app env | grep DATABASE_URL

# Verify database connection
docker-compose exec app python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://clawbot:clawbot@postgres:5432/clawbot_coordinator'); conn = engine.connect(); print('Connected!')"
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection from host
psql -h localhost -U clawbot -d clawbot_coordinator

# Test connection from container
docker-compose exec app psql -h postgres -U clawbot -d clawbot_coordinator
```

### Migration Failures

```bash
# Check current migration version
docker-compose exec app alembic current

# View migration history
docker-compose exec app alembic history

# Manually run migrations
docker-compose exec app alembic upgrade head

# Rollback one migration
docker-compose exec app alembic downgrade -1
```

### Port Conflicts

```bash
# If port 8000 is in use
docker-compose -f docker-compose.yml \
  -e APP_PORT=8001 \
  up -d

# Or edit docker-compose.yml ports section
ports:
  - "8001:8000"
```

### Container Won't Stop

```bash
# Force remove
docker-compose down -t 1

# Kill specific container
docker kill clawbot-app

# Remove all stopped containers
docker container prune
```

### Out of Disk Space

```bash
# Clean up unused images
docker image prune -a

# Clean up volumes (CAUTION: Data loss!)
docker volume prune

# Clean everything
docker system prune -a --volumes
```

## Security Best Practices

### Production Checklist

- [ ] Use strong passwords for PostgreSQL and Redis
- [ ] Don't commit `.env` files to version control
- [ ] Run containers as non-root user (already configured)
- [ ] Use secrets management (Docker secrets, Vault, etc.)
- [ ] Enable TLS for database connections
- [ ] Use reverse proxy (nginx, traefik) with HTTPS
- [ ] Limit container resources (CPU, memory)
- [ ] Regular security updates: `docker-compose pull && docker-compose up -d`
- [ ] Enable Docker content trust: `export DOCKER_CONTENT_TRUST=1`
- [ ] Use read-only root filesystem where possible
- [ ] Implement network segmentation
- [ ] Enable audit logging

### Secrets Management

```bash
# Using Docker secrets (Swarm mode)
echo "my-secret-password" | docker secret create postgres_password -
echo "my-redis-password" | docker secret create redis_password -

# Reference in docker-compose.yml
secrets:
  - postgres_password
  - redis_password
```

## Performance Tuning

### PostgreSQL

Edit `docker-compose.yml` to add PostgreSQL tuning:

```yaml
postgres:
  command:
    - postgres
    - -c
    - max_connections=200
    - -c
    - shared_buffers=256MB
    - -c
    - effective_cache_size=1GB
```

### Application

```yaml
app:
  environment:
    WORKERS: 4  # Number of Uvicorn workers
  command: uvicorn clawbot_coordinator.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Resource Limits

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## Backup and Recovery

### Automated Backups

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U clawbot clawbot_coordinator | gzip > $BACKUP_DIR/postgres.sql.gz

# Backup Redis
docker-compose exec redis redis-cli BGSAVE
docker cp clawbot-redis:/data/dump.rdb $BACKUP_DIR/redis.rdb

# Cleanup old backups (keep 30 days)
find /backups -type d -mtime +30 -exec rm -rf {} \;
```

### Disaster Recovery

```bash
# Stop services
docker-compose down

# Restore PostgreSQL
gunzip -c postgres.sql.gz | docker-compose exec -T postgres psql -U clawbot -d clawbot_coordinator

# Restore Redis
docker cp redis.rdb clawbot-redis:/data/dump.rdb
docker-compose restart redis

# Start services
docker-compose up -d
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t clawbot-coordinator:latest .
      
      - name: Run tests
        run: |
          docker-compose up -d postgres redis
          docker-compose run --rm app pytest tests/
      
      - name: Deploy to production
        run: |
          # Copy files to server
          # Run docker-compose -f docker-compose.prod.yml up -d
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f app`
2. Verify health: `curl http://localhost:8000/health`
3. Review this guide
4. Check GitHub issues
