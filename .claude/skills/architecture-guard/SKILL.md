# Architecture Guardian Skill

Before editing any file, check its path:

1. If path contains `/domain/`:
    - Check imports for `fastapi`, `sqlalchemy`, `redis`
    - If found: REJECT and suggest creating Repository Interface instead

2. If path contains `/infrastructure/repositories/`:
    - Verify it implements corresponding interface from `domain/repositories/`
    - Ensure it converts ORM → Domain model in return statements

3. If path contains `/api/routes/`:
    - Verify no direct database Session usage
    - Ensure dependency injection via `Depends(get_service)`
    - Check HTTP status codes follow REST conventions

4. If path contains `/services/`:
    - Ensure it accepts Repository interfaces in __init__, not concrete classes
    - Verify no FastAPI Request/Response objects imported

Violation Response: "This change violates [Layer] isolation. Move [X] to [Y] instead."