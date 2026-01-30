```markdown
# ClawBot Coordinator - Implementation Guide

> **Documentation Structure**: 
> - For **enforcement rules, protocols, and constraints**, see `CLAUDE.md` (MANDATORY)
> - For **detailed architecture, templates, and implementation patterns**, see this file (REFERENCE)

This guide provides comprehensive technical specifications, code templates, and implementation patterns for the ClawBot Coordinator system.

---

## 1. Architecture Overview

### 1.1 System Boundaries

Layer separation diagram:

```mermaid
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER (Pure Python)              │
│  models/  │  repositories/ (abstract)  │  services/        │
│  • No FastAPI imports  • No SQLAlchemy imports in interfaces │
└──────────────────────┬──────────────────────────────────────┘
                       │ depends on
┌──────────────────────▼──────────────────────────────────────┐
│                INFRASTRUCTURE LAYER (I/O)                    │
│  database.py  │  redis_client.py  │  repositories/postgres* │
│  • SQLAlchemy models here only  • Async connections          │
└──────────────────────┬──────────────────────────────────────┘
                       │ depends on
┌──────────────────────▼──────────────────────────────────────┐
│                   API LAYER (FastAPI)                        │
│  routes/  │  websockets/  │  dependencies.py                │
│  • Pydantic DTOs only  • No business logic (delegate to svc) │
└─────────────────────────────────────────────────────────────┘
```

**Note**: See `CLAUDE.md` Protocol 3 for enforcement details on layer isolation.

### 1.2 Vertical Slice Organization

Each feature is self-contained:

| Slice | Entry Point | Test File | Dependencies |
|-------|-------------|-----------|--------------|
| **Bot Management** | `routes/bots.py` | `test_bot_api.py` | None (Foundation) |
| **Task Lifecycle** | `routes/tasks.py` + `workers/queue.py` | `test_task_submission.py` | Bot Management |
| **Workflow Engine** | `routes/workflows.py` | `test_full_workflow.py` | Task System |
| **WebSocket Control** | `websockets/control.py` | `test_websocket_control.py` | Bot Management |

---

## 2. Code Templates

Use these templates when implementing new features. All code must comply with constraints in **CLAUDE.md Protocol 3** (Architecture Isolation).

### Template A: Domain Model

Location: `domain/models/task.py`

```python
"""
Task domain model.
Context: Core business object with state machine behavior.
See CLAUDE.md Gate 4 for state machine enforcement rules.
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    status: TaskStatus = TaskStatus.PENDING
    
    def assign_to(self, bot_id: UUID) -> None:
        """Transition: pending -> assigned"""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot assign task in {self.status} state")
        self.status = TaskStatus.ASSIGNED
        self.bot_id = bot_id
        self.updated_at = datetime.utcnow()
```

### Template B: Repository Interface

Location: `domain/repositories/task_repo.py`

```python
"""
Repository interface (Port).
See CLAUDE.md Protocol 3 for layer isolation rules.
"""
from abc import ABC, abstractmethod
from uuid import UUID
from ..models.task import Task

class TaskRepository(ABC):
    @abstractmethod
    async def get(self, task_id: UUID) -> Task | None:
        """Fetch task by ID. Return None if not found."""
        pass
    
    @abstractmethod
    async def save(self, task: Task) -> None:
        """Upsert task. Must handle both insert and update."""
        pass
```

### Template C: Repository Implementation

Location: `infrastructure/repositories/postgres_task_repo.py`

```python
"""
PostgreSQL implementation.
Requires: TaskORM exists in database.py (Migration must be applied first)
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...domain.models.task import Task, TaskStatus
from ...domain.repositories.task_repo import TaskRepository
from ..database import TaskORM

class PostgresTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, task_id: UUID) -> Task | None:
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.id == task_id)
        )
        orm_obj = result.scalar_one_or_none()
        return self._to_domain(orm_obj) if orm_obj else None
```

### Template D: FastAPI Route

Location: `api/routes/tasks.py`

```python
"""
HTTP API Layer.
See CLAUDE.md Protocol 2 - Only create after Domain/Infra/Services exist.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from ...domain.services.task_service import TaskService
from ...dependencies import get_task_service
from ..schemas.task_schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service)
):
    try:
        task = await service.create_task(
            workflow_id=payload.workflow_id,
            payload=payload.payload
        )
        return TaskResponse.from_domain(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 3. Phase-by-Phase Guide

**Prerequisite**: Review CLAUDE.md Protocol 2 (File Creation Order) before starting.

### Phase 0: Foundation

Files to create first:

1. **`pyproject.toml`**
```toml
[project]
name = "clawbot-coordinator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
    "testcontainers>=3.7.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

2. **`config.py`**, **`exceptions.py`**, **`database.py`** (see CLAUDE.md Checkpoint 0 for validation commands)

### Phase 1: Bot Management

See CLAUDE.md Checkpoint 1 for validation steps.

**Domain Model** (`domain/models/bot.py`):
- Fields: `id`, `name`, `capabilities`, `status`, `last_seen`, `metadata`
- Status enum: `offline`, `online`, `busy`

**Service Methods**:
```python
async def register_bot(self, name: str, capabilities: list[str]) -> Bot
async def heartbeat(self, bot_id: UUID) -> None
async def get_by_capability(self, capability: str) -> list[Bot]
```

### Phase 2: Task System

See CLAUDE.md Checkpoint 2-3.

**State Machine** (enforced in Domain, not DB):
```python
# Valid transitions only via these methods:
task.assign_to(bot_id)      # pending → assigned
task.start()                # assigned → in_progress
task.complete(result)       # in_progress → completed
task.fail(error)            # in_progress → failed
```

**Background Worker** (`workers/queue.py`):
```python
async def process_timeouts():
    """Fail tasks exceeding timeout_seconds"""
    # Query: SELECT * FROM tasks 
    # WHERE status IN ('assigned', 'in_progress') 
    # AND updated_at + timeout_seconds < NOW()
```

### Phase 3: Workflow Engine

**Aggregate Root Pattern**:
```python
class Workflow:
    def on_task_completed(self, task_id: UUID):
        """Triggers next task or workflow completion"""
        # Logic: Find next pending task in sequence
        # If found: assign to capable bot
        # If all done: status = completed
```

---

## 4. Testing Patterns

See CLAUDE.md Section 5 for testing hierarchy enforcement.

### Unit Test Example
```python
# tests/unit/domain/test_task.py
async def test_cannot_claim_already_assigned_task():
    task = Task(workflow_id=uuid4())
    task.assign_to(bot_id=uuid4())
    
    with pytest.raises(ValueError):
        task.assign_to(bot_id=uuid4())  # Should raise
```

### Feature Test Example
```python
# tests/feature/test_task_api.py
async def test_task_lifecycle(client, sample_bot):
    # Create
    create_resp = await client.post("/tasks", json={...})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    
    # Claim
    claim_resp = await client.post(f"/tasks/{task_id}/claim")
    assert claim_resp.json()["status"] == "assigned"
```

---

## 5. Database Migrations

When schema changes are needed (see CLAUDE.md 4.2):

1. Create `migrations/XXX_description.sql`
2. Update ORM in `infrastructure/database.py`
3. Update repository `_to_domain()` methods
4. Run `pytest tests/feature/` to verify

**Template**:
```sql
-- migrations/002_add_task_priority.sql
-- Context: Adding priority for task queuing
-- Safe: Default preserves existing behavior

ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 3;
CREATE INDEX idx_tasks_priority_status ON tasks(priority, status) 
    WHERE status = 'pending';
```

---

## 6. Docker & Deployment

### Single-Container Mode
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y postgresql redis-server supervisor
# ... see full example in original plan
```

### Environment Matrix

| Environment | Database | Redis | Notes |
|-------------|----------|-------|-------|
| **Dev** | External (docker-compose) | External | Hot reload enabled |
| **Test** | TestContainer (auto) | TestContainer (auto) | Fresh per test |
| **Prod** | Embedded (volume) | Embedded (volume) | Single container |

---

## 7. WebSocket Protocol

**Connection**: `/ws/control?token={bot_token}`

**Message Schema**:
```json
{
    "type": "task_assigned|claim_task|task_complete|heartbeat",
    "payload": {},
    "timestamp": "2024-01-01T00:00:00Z"
}
```

**Flow**:
1. Bot connects with auth token
2. Server sends `connected` event
3. Server pushes `task_assigned` when work available
4. Bot sends `task_complete` when done
5. Heartbeat every 30s (configurable)

---

## 8. Documentation Maintenance

When implementing features, update:

- **`CLAUDE.md`**: If adding new architectural constraints or changing protocols
- **`docs/ARCHITECTURE.md`**: For significant design changes
- **Code Comments**: Use tags for AI context:
  ```python
  # NOTE(ai): Uses SELECT FOR UPDATE for race condition prevention
  # TODO(ai): Consider Redis caching for high-frequency reads
  ```

---

## Reference: Quick Commands

```bash
# Validate architecture (from CLAUDE.md)
python scripts/check_domain_imports.py

# Run tests by level (from CLAUDE.md)
pytest tests/unit -v          # Fast feedback
pytest tests/feature -v       # With database
pytest tests/e2e -v           # Full integration

# Database operations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

**For all enforcement rules, mandatory checklists, and AI protocols, see CLAUDE.md.**
```