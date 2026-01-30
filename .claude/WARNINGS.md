## Common AI Mistakes in This Project

1. **The SQLAlchemy Trap**:
   AI often puts SQLAlchemy models in `domain/models/`.
   WRONG: Domain models are pure Pydantic.
   RIGHT: SQLAlchemy ORM classes go in `infrastructure/database.py`

2. **The Sync/Await Bug**:
   AI writes `repo.save(task)` without await in async contexts.
   ALWAYS verify async/await propagation through call stack.

3. **The Import Spiral**:
   AI creates circular imports by importing `main.py` into services.
   NEVER import from `api/` into `domain/` or `infrastructure/`.

4. **The "Quick Test Skip"**:
   AI says "I'll add tests later" when under pressure.
   STOP. Write the test first or explicitly mark as `@pytest.mark.skip`.

5. **The WebSocket Business Logic**:
   AI puts task execution logic in WebSocket handlers.
   WebSocket handlers only manage connections. Delegate to TaskService.