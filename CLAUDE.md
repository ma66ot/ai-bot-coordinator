```markdown
# CLAUDE.md - MANDATORY PROTOCOLS

This file contains ENFORCEMENT RULES, not just guidelines. Violating these rules will break the codebase.

## CRITICAL PROTOCOLS (Never Bypass)

### Protocol 1: TDD Mandate
**BEFORE writing any production code:**
1. Write failing test in appropriate `tests/` directory
2. Run test to confirm it fails for the RIGHT reason (`pytest tests/unit/test_x.py -v`)
3. Write minimal code to pass
4. Run test to confirm green
5. Refactor if needed

**FORBIDDEN**: "I'll add tests later", "Let me implement first then test", skipping red phase.

### Protocol 2: File Creation Order (Hard Stop Points)
You MUST create files in this exact sequence. Do NOT proceed to next step until previous files compile and tests pass:

**Checkpoint 0**: Foundation
- [ ] `config.py` (Pydantic settings)
- [ ] `exceptions.py` (Domain errors)
- [ ] `database.py` (SQLAlchemy base ONLY)
- **STOP**: Run `python -c "from clawbot_coordinator.config import settings"` must succeed

**Checkpoint 1**: Domain Layer (Pure Python)
- [ ] `domain/models/[entity].py` (Pydantic models only)
- [ ] `domain/repositories/[entity]_repo.py` (Abstract classes only)
- **STOP**: Run `python -c "from clawbot_coordinator.domain.models.bot import Bot"` must succeed
- **VALIDATE**: Import check - ensure no SQLAlchemy/FastAPI in domain files

**Checkpoint 2**: Infrastructure Layer
- [ ] `infrastructure/repositories/postgres_[entity]_repo.py`
- [ ] Map ORM to Domain in `_to_domain()` method
- **STOP**: Run `pytest tests/unit/domain/test_[entity].py` must pass

**Checkpoint 3**: Service Layer
- [ ] `domain/services/[entity]_service.py`
- **STOP**: Service must accept Repository interface, not concrete class

**Checkpoint 4**: API Layer
- [ ] `api/schemas/[entity]_schemas.py`
- [ ] `api/routes/[entity]s.py`
- **STOP**: Full feature test passes (`pytest tests/feature/test_[entity]_api.py -v`)

### Protocol 3: Architecture Isolation (Zero Tolerance)

**FORBIDDEN IMPORTS in `domain/`** (Will be caught by pre-commit):
```python
# NEVER ALLOW THESE in domain/:
from fastapi import *          # Domain knows nothing of HTTP
from sqlalchemy import *       # Domain knows nothing of ORM  
from sqlalchemy.orm import *   # Domain models are Pydantic only
from redis import *            # Domain knows nothing of cache
from infrastructure.database import *  # No dependency on infra
from api.routes import *       # Never import upward
```

**ALLOWED in `domain/`**:
```python
from pydantic import BaseModel
from typing import Protocol, Optional
from datetime import datetime
from uuid import UUID
from exceptions import DomainError  # Only exception definitions
```

### Protocol 4: Vertical Slice Isolation
You may ONLY work on ONE slice at a time. Current slices:

1. **Bot Management** (Foundation - NO dependencies)
    - Files: `domain/models/bot.py`, `domain/repositories/bot_repo.py`, `postgres_bot_repo.py`, `bot_service.py`, `routes/bots.py`

2. **Task System** (Depends on Bot Management)
    - Files: `models/task.py`, `repositories/task_repo.py`, `task_service.py`, `routes/tasks.py`, `workers/queue.py`
    - **GATE**: Cannot start until Bot Management tests pass

3. **Workflow Engine** (Depends on Task System)
    - Files: `models/workflow.py`, `workflow_repo.py`, `workflow_service.py`, `routes/workflows.py`

**RULE**: If modifying Task System, you may NOT modify Bot Management files. If you need a Bot field, extend the Bot service, don't modify the repository.

## Pre-Flight Checklist (Run Before Every Implementation)

Before writing code for a feature, you MUST verify:

```bash
# Check 1: Are we in the right virtual environment?
which python  # Should show ./venv/bin/python or similar

# Check 2: Can we import domain layer cleanly?
python -c "from clawbot_coordinator.domain.models.bot import Bot; print('✓ Domain clean')"

# Check 3: Are tests runnable?
pytest tests/unit --collect-only -q  # Should list tests without errors

# Check 4: Is database migration current?
alembic current  # Should show head

# Check 5: Layer purity (if check_domain_imports.py exists)
python scripts/check_domain_imports.py
```

**IF ANY CHECK FAILS**: Fix foundation before proceeding. Do not build on broken ground.

## Code Quality Gates

### Gate 1: Type Safety
- ALL functions MUST have type hints
- NO `Any` types except in extreme edge cases (document why)
- Use `UUID`, not `str` for IDs
- Domain models use `datetime`, not `int` timestamps

### Gate 2: Async Discipline
- ALL I/O operations MUST be async (database, Redis, HTTP)
- Repository methods: `async def get(...)`
- Service methods: `async def process(...)`
- **FORBIDDEN**: `time.sleep()`, use `asyncio.sleep()`
- **FORBIDDEN**: synchronous SQLAlchemy sessions

### Gate 3: Error Handling
- Domain layer raises: `DomainError`, `InvalidStateTransition`, `ResourceNotFound`
- API layer catches DomainError and converts to HTTPException
- NEVER let domain exceptions leak as 500 errors without handling
- Repository returns `None` for not found, never raises

### Gate 4: State Machine Enforcement
Task states are STRICT. ONLY these transitions allowed:
- `pending → assigned` (via `assign_to()`)
- `assigned → in_progress` (via `start()`)
- `in_progress → completed` (via `complete()`)
- `in_progress → failed` (via `fail()`)
- `any → cancelled` (via `cancel()`)

**FORBIDDEN**: Direct status assignment `task.status = "completed"`
**REQUIRED**: Use methods `task.complete(result)` which validate transition

## Testing Hierarchy (Enforced)

### Unit Tests (`tests/unit/`)
- **Scope**: Single domain model or service
- **Speed**: <50ms
- **Rules**:
    - Mock ALL dependencies (repos, external services)
    - Test state machines exhaustively
    - Test validation edge cases
    - NO database, NO Redis, NO HTTP server

### Feature Tests (`tests/feature/`)
- **Scope**: Full HTTP request/response cycle
- **Speed**: 1-2s
- **Rules**:
    - Use Testcontainers (real PostgreSQL in Docker)
    - Test happy path + common error cases
    - Verify database state after API calls
    - Mark slow tests: `@pytest.mark.slow`

### E2E Tests (`tests/e2e/`)
- **Scope**: Multi-container, WebSocket, full workflows
- **Speed**: 10-30s
- **Rules**:
    - Build Docker image first
    - Test realistic scenarios (bot disconnects, timeouts)
    - Run last, only before major commits

**SEQUENCE**: Implement with Unit → Feature → E2E. If Unit tests pass but Feature fails, your API layer is wrong, not the domain.

## Implementation Workflow (Step-by-Step)

When asked to implement a feature, follow this EXACT workflow:

1. **Analyze**: Which vertical slice? Does it have dependencies?
2. **Validate**: Run Pre-Flight Checklist above
3. **Test-First**: Write failing test in appropriate test directory
4. **Domain**: Create/modify domain model (Pydantic) + repository interface
5. **Infra**: Create PostgreSQL repository implementation
6. **Service**: Create service using dependency injection
7. **API**: Create routes using schemas, delegate to service
8. **Verify**: Run full test suite for that slice
9. **Check**: Run architecture validation (`python scripts/check_domain_imports.py`)

## Common AI Pitfalls (DO NOT DO THESE)

1. **The ORM Leak**: Putting SQLAlchemy models in `domain/models/`
    - **WRONG**: `class Bot(Base):` (SQLAlchemy base)
    - **RIGHT**: `class Bot(BaseModel):` (Pydantic) in domain, `class BotORM(Base):` in infrastructure/database.py

2. **The Sync Trap**: Writing synchronous code in async context
    - **WRONG**: `repo.save(bot)` (forgot await)
    - **RIGHT**: `await repo.save(bot)`

3. **The Import Violation**: Importing FastAPI into domain
    - **WRONG**: `from fastapi import HTTPException` in service layer
    - **RIGHT**: Raise `DomainError` in service, catch and convert to HTTPException in API layer

4. **The Test Skip**: "I'll write tests after I get it working"
    - **CONSEQUENCE**: Untestable code, tight coupling
    - **ENFORCEMENT**: If no test file exists, STOP and create it first

5. **The God Object**: Putting business logic in API routes
    - **WRONG**: Validating task assignment in `@router.post` handler
    - **RIGHT**: Route calls `service.assign_task()`, logic lives in service/domain

6. **The Direct Access**: Repository calling other repositories
    - **WRONG**: TaskRepo fetching Bot directly from DB
    - **RIGHT**: Service layer coordinates TaskRepo and BotRepo

## Command Reference

```bash
# Validate architecture hasn't been violated
python scripts/check_domain_imports.py

# Run only fast unit tests (development feedback loop)
pytest tests/unit -v --tb=short

# Run feature tests for specific slice
pytest tests/feature/test_bot_api.py -v

# Full check before commit (slow but comprehensive)
pytest tests/ -v --cov=clawbot_coordinator

# Check type hints with mypy (if installed)
mypy src/clawbot_coordinator/domain --strict

# Database: Reset and migrate fresh (DESTRUCTIVE)
alembic downgrade base && alembic upgrade head
```

## Emergency Escape Hatches

If you find yourself stuck:
1. **Circular Import**: You're importing upward (domain → api or infra). Fix: Use dependency injection, pass objects as parameters.
2. **Can't Test**: You can't mock the dependency. Fix: Check for missing repository interface or tight coupling.
3. **Type Errors**: mypy complains about async. Fix: Ensure `async def` matches in interface and implementation.

## Success Metrics

Before declaring "done":
- [ ] All new code has type hints
- [ ] Unit tests cover all state transitions (if applicable)
- [ ] Feature tests cover API endpoints
- [ ] `python scripts/check_domain_imports.py` passes
- [ ] No `Any` types without justification comment
- [ ] All repository methods tested with mocks
- [ ] Service layer has no FastAPI imports
```