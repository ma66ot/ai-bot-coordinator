# ClawBot Coordinator

A production-ready task orchestration system for managing distributed bot workers with real-time communication and workflow automation.

[![Tests](https://img.shields.io/badge/tests-168%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12+-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

![readme-graphic.jpg](readme-graphic.jpg)

## Overview

ClawBot Coordinator is a scalable microservice that orchestrates task execution across a fleet of bot workers. It provides:

- **Bot Management**: Register, monitor, and manage bot workers
- **Task Orchestration**: Create, assign, and track task execution
- **Workflow Engine**: Chain multiple tasks into coordinated workflows
- **Real-Time Communication**: WebSocket-based bot control and task notifications
- **Automatic Timeout Handling**: Background worker monitors and fails timed-out tasks
- **Database Migrations**: Alembic-based schema version control
- **Production Ready**: Docker deployment with PostgreSQL and Redis

Built with **Clean Architecture** principles, following **Test-Driven Development** with 168 passing tests.

## Features

### 🤖 Bot Management
- Register bots with capabilities (skills they can perform)
- Track bot status: `offline` → `online` → `busy`
- Heartbeat monitoring with staleness detection
- Query bots by capability or availability
- Automatic status management during task lifecycle

### 📋 Task System
- Create tasks with custom payloads
- Assign tasks to capable bots
- Track task lifecycle: `pending` → `assigned` → `in_progress` → `completed`/`failed`
- Configurable timeouts (1-3600 seconds)
- Automatic timeout detection and bot release
- Query tasks by workflow, bot, or status

### 🔄 Workflow Engine
- Create workflows with multiple sequential tasks
- Track workflow status across all tasks
- Bulk task creation with single API call
- Workflow metadata support
- Query workflows with embedded task details

### 🔌 Real-Time WebSocket
- WebSocket endpoint for bot connections (`/ws/control`)
- Server pushes task assignments to connected bots
- Bots report task completion in real-time
- Heartbeat mechanism (30s interval)
- Automatic connection cleanup on disconnect

### ⏰ Background Workers
- Timeout worker runs every 30 seconds
- Automatically fails tasks exceeding timeout
- Frees up bots from timed-out tasks
- Detailed error reporting with timeout information

### 🗄️ Database Management
- Alembic migrations for schema version control
- PostgreSQL with async SQLAlchemy
- Optimized indexes for query performance
- Support for JSON fields (payloads, metadata, results)

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (recommended)
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd bot_connector

# Copy environment file
cp .env.example .env

# Start all services with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

The API will be available at http://localhost:8000

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up database (PostgreSQL must be running)
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/clawbot"
export REDIS_URL="redis://localhost:6379/0"

# Run migrations
alembic upgrade head

# Start the server
uvicorn clawbot_coordinator.main:app --reload
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Usage Examples

### 1. Register a Bot

```bash
curl -X POST http://localhost:8000/api/v1/bots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "build-bot-01",
    "capabilities": ["python", "docker", "build"],
    "metadata": {"version": "1.0", "region": "us-west"}
  }'
```

Response:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "build-bot-01",
  "capabilities": ["python", "docker", "build"],
  "status": "offline",
  "metadata": {"version": "1.0", "region": "us-west"},
  "created_at": "2024-01-30T12:00:00Z"
}
```

### 2. Create a Workflow with Tasks

```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Pipeline",
    "description": "Build, test, and deploy application",
    "task_payloads": [
      {"action": "build", "dockerfile": "Dockerfile", "tag": "v1.2.3"},
      {"action": "test", "suite": "integration", "coverage": true},
      {"action": "deploy", "environment": "staging", "region": "us-west"}
    ],
    "metadata": {"project": "my-app", "branch": "main"}
  }'
```

Response:
```json
{
  "id": "workflow-uuid",
  "name": "CI/CD Pipeline",
  "status": "pending",
  "task_ids": ["task-1-uuid", "task-2-uuid", "task-3-uuid"],
  "created_at": "2024-01-30T12:00:00Z"
}
```

### 3. Assign Task to Bot

```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/assign \
  -H "Content-Type: application/json" \
  -d '{"bot_id": "bot-uuid"}'
```

### 4. Bot Connects via WebSocket

```python
import asyncio
import websockets
import json

async def bot_worker(bot_id):
    uri = f"ws://localhost:8000/api/v1/ws/control?bot_id={bot_id}"
    
    async with websockets.connect(uri) as websocket:
        # Receive connected message
        connected = await websocket.recv()
        print(f"Connected: {connected}")
        
        # Listen for task assignments
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "task_assigned":
                task_id = data["payload"]["task_id"]
                task_payload = data["payload"]["task_payload"]
                
                # Process task...
                result = {"output": "success"}
                
                # Report completion
                completion = {
                    "type": "task_complete",
                    "payload": {
                        "task_id": task_id,
                        "success": True,
                        "result": result
                    }
                }
                await websocket.send(json.dumps(completion))

asyncio.run(bot_worker("bot-uuid"))
```

### 5. Query Available Bots

```bash
# Get all online bots with 'python' capability
curl "http://localhost:8000/api/v1/bots/available?capability=python"
```

### 6. Get Workflow with Tasks

```bash
curl http://localhost:8000/api/v1/workflows/{workflow_id}/tasks
```

Response:
```json
{
  "workflow": {
    "id": "workflow-uuid",
    "name": "CI/CD Pipeline",
    "status": "in_progress"
  },
  "tasks": [
    {
      "id": "task-1-uuid",
      "status": "completed",
      "payload": {"action": "build"},
      "result": {"image_id": "sha256:abc123"}
    },
    {
      "id": "task-2-uuid",
      "status": "in_progress",
      "payload": {"action": "test"}
    }
  ]
}
```

## API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### REST Endpoints

#### Bots
- `POST /api/v1/bots` - Register new bot
- `GET /api/v1/bots` - List all bots
- `GET /api/v1/bots/{bot_id}` - Get bot details
- `GET /api/v1/bots/available` - Get available bots
- `POST /api/v1/bots/{bot_id}/heartbeat` - Update bot heartbeat
- `POST /api/v1/bots/{bot_id}/busy` - Mark bot as busy
- `POST /api/v1/bots/{bot_id}/available` - Mark bot as available
- `DELETE /api/v1/bots/{bot_id}` - Delete bot

#### Tasks
- `POST /api/v1/tasks` - Create new task
- `GET /api/v1/tasks` - List all tasks
- `GET /api/v1/tasks/{task_id}` - Get task details
- `GET /api/v1/tasks/pending` - Get pending tasks
- `POST /api/v1/tasks/{task_id}/assign` - Assign task to bot
- `POST /api/v1/tasks/{task_id}/start` - Start task execution
- `POST /api/v1/tasks/{task_id}/complete` - Mark task complete
- `POST /api/v1/tasks/{task_id}/fail` - Mark task failed
- `POST /api/v1/tasks/{task_id}/cancel` - Cancel task
- `DELETE /api/v1/tasks/{task_id}` - Delete task

#### Workflows
- `POST /api/v1/workflows` - Create workflow with tasks
- `GET /api/v1/workflows` - List all workflows
- `GET /api/v1/workflows/{workflow_id}` - Get workflow details
- `GET /api/v1/workflows/{workflow_id}/tasks` - Get workflow with tasks
- `POST /api/v1/workflows/{workflow_id}/start` - Start workflow
- `DELETE /api/v1/workflows/{workflow_id}` - Delete workflow

#### WebSocket
- `WS /api/v1/ws/control?bot_id={uuid}` - Bot control WebSocket
- `GET /api/v1/ws/connections` - List active WebSocket connections
- `POST /api/v1/ws/broadcast/task/{task_id}` - Broadcast task to bot

#### Health
- `GET /` - Root health check
- `GET /health` - Detailed health status

## Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
│  • REST endpoints                   │
│  • WebSocket handlers               │
│  • Request/Response schemas         │
└────────────┬────────────────────────┘
             │ depends on
┌────────────▼────────────────────────┐
│      Domain Layer (Pure Python)     │
│  • Business logic                   │
│  • Domain models (Pydantic)         │
│  • Repository interfaces            │
│  • Services                         │
└────────────┬────────────────────────┘
             │ depends on
┌────────────▼────────────────────────┐
│    Infrastructure Layer (I/O)       │
│  • PostgreSQL repositories          │
│  • Database ORM models              │
│  • Redis client                     │
│  • External integrations            │
└─────────────────────────────────────┘
```

### Technology Stack

- **Framework**: FastAPI 0.110+
- **Python**: 3.12+
- **Database**: PostgreSQL 16 (async via asyncpg)
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Validation**: Pydantic 2.5+
- **Testing**: pytest with pytest-asyncio
- **Deployment**: Docker & Docker Compose

## Development

### Running Tests

```bash
# All tests
pytest tests/

# Unit tests only (fast)
pytest tests/unit/

# Feature tests (with database)
pytest tests/feature/

# With coverage
pytest tests/ --cov=clawbot_coordinator --cov-report=html

# Specific test file
pytest tests/unit/domain/test_bot.py -v
```

### Code Quality

```bash
# Architecture validation
python scripts/check_domain_imports.py

# Type checking (if mypy installed)
mypy src/clawbot_coordinator/domain --strict

# Linting (if ruff installed)
ruff check src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# See migration history
alembic history
```

### Project Structure

```
bot_connector/
├── src/clawbot_coordinator/      # Application code
│   ├── domain/                    # Domain layer (pure Python)
│   │   ├── models/                # Domain models (Pydantic)
│   │   ├── repositories/          # Repository interfaces
│   │   └── services/              # Business logic services
│   ├── infrastructure/            # Infrastructure layer
│   │   └── repositories/          # PostgreSQL implementations
│   ├── api/                       # API layer (FastAPI)
│   │   ├── routes/                # REST endpoints
│   │   └── schemas/               # Request/response models
│   ├── workers/                   # Background workers
│   ├── config.py                  # Configuration
│   ├── database.py                # Database setup & ORM
│   ├── dependencies.py            # Dependency injection
│   └── main.py                    # FastAPI application
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests (no I/O)
│   │   ├── domain/                # Domain model tests
│   │   └── workers/               # Worker tests
│   ├── feature/                   # Feature tests (with DB)
│   └── conftest.py                # Test fixtures
├── alembic/                       # Database migrations
│   └── versions/                  # Migration files
├── scripts/                       # Utility scripts
├── docker-compose.yml             # Development environment
├── docker-compose.prod.yml        # Production environment
├── Dockerfile                     # Container image
├── pyproject.toml                 # Project dependencies
└── README.md                      # This file
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | postgresql+asyncpg://... | PostgreSQL connection string |
| `REDIS_URL` | Yes | redis://localhost:6379/0 | Redis connection string |
| `APP_NAME` | No | ClawBot Coordinator | Application name |
| `ENVIRONMENT` | No | development | Environment (development/production) |
| `DEBUG` | No | false | Enable debug logging |

### Creating .env File

```bash
# Copy example file
cp .env.example .env

# Edit with your values
nano .env
```

## Deployment

### Docker Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guide.

Quick production start:

```bash
# Set secure passwords
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export REDIS_PASSWORD=$(openssl rand -base64 32)

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Check health
curl http://localhost:8000/health
```

### Scaling

```bash
# Scale to 3 application instances
docker-compose up -d --scale app=3

# Use with load balancer (nginx, traefik, etc.)
```

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database connection
docker-compose exec postgres pg_isready -U clawbot

# Redis connection
docker-compose exec redis redis-cli ping
```

### Logs

```bash
# Application logs
docker-compose logs -f app

# All services
docker-compose logs -f

# Export logs
docker-compose logs app > app.log
```

### Metrics

The application exposes health endpoints for monitoring:

- `/health` - Returns service status and version
- `/` - Root endpoint with environment info

## Troubleshooting

### Common Issues

**Application won't start**
```bash
# Check logs
docker-compose logs app

# Verify database connection
docker-compose exec app python -c "from clawbot_coordinator.database import engine; print('DB OK')"
```

**Migration failures**
```bash
# Check current version
alembic current

# Manually run migrations
alembic upgrade head

# Rollback and retry
alembic downgrade -1
alembic upgrade head
```

**WebSocket connection refused**
```bash
# Check if bot_id is valid
curl http://localhost:8000/api/v1/bots/{bot_id}

# Check WebSocket connections
curl http://localhost:8000/api/v1/ws/connections
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for more troubleshooting tips.

## Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Write tests first (TDD)
3. Implement feature
4. Run tests: `pytest tests/`
5. Validate architecture: `python scripts/check_domain_imports.py`
6. Create pull request

### Testing Requirements

- All new code must have tests
- Maintain 100% test pass rate
- Follow TDD methodology (RED → GREEN → REFACTOR)
- Unit tests for domain logic
- Feature tests for API endpoints

### Code Standards

- Follow Clean Architecture principles
- Domain layer has no external dependencies
- Type hints required for all functions
- Async/await for all I/O operations
- Pydantic for data validation

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: See `/docs` endpoint when running
- **Issues**: GitHub Issues
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Migration Guide**: [alembic/README.md](alembic/README.md)

## Roadmap

- [ ] Authentication & Authorization
- [ ] Task priority queuing
- [ ] Advanced workflow features (conditionals, loops)
- [ ] Metrics & observability (Prometheus)
- [ ] Rate limiting
- [ ] Bot health scoring
- [ ] Task retry policies
- [ ] Scheduled tasks (cron-like)

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations
- [pytest](https://pytest.org/) - Testing framework

---

**Status**: Production Ready 🚀 | **Tests**: 168 passing ✅ | **Coverage**: Full API coverage
