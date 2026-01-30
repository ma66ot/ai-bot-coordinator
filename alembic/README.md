# Database Migrations

This directory contains Alembic database migrations for the ClawBot Coordinator.

## Overview

- **Migration Tool**: Alembic
- **Target Database**: PostgreSQL (async via asyncpg)
- **ORM**: SQLAlchemy 2.0 with async support
- **Test Database**: SQLite (in-memory for tests)

## Prerequisites

1. PostgreSQL database running (for production migrations)
2. Database URL configured in environment or `.env` file
3. Virtual environment activated

## Configuration

### Environment Variables

Set the database URL in your `.env` file:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

Or use the default from `config.py`:
```
postgresql+asyncpg://clawbot:clawbot@localhost:5432/clawbot_coordinator
```

## Common Commands

### Create a New Migration

After modifying ORM models in `src/clawbot_coordinator/database.py`:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new field to bots table"

# Create empty migration for manual editing
alembic revision -m "Add custom index"
```

### Apply Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Upgrade to specific revision
alembic upgrade abc123
```

### Rollback Migrations

```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Downgrade to base (remove all)
alembic downgrade base
```

### Check Migration Status

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --verbose
```

## Migration Workflow

### 1. Development

1. Modify ORM models in `src/clawbot_coordinator/database.py`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Edit if necessary (Alembic doesn't catch everything)
5. Test migration: `alembic upgrade head`
6. Run tests: `pytest tests/`
7. If issues, rollback: `alembic downgrade -1`

### 2. Production Deployment

```bash
# Before deploying new code
alembic upgrade head

# Deploy application
# Monitor for issues

# If rollback needed
alembic downgrade -1
```

## Migration Best Practices

### DO

- ✅ Always review auto-generated migrations
- ✅ Test migrations on a copy of production data
- ✅ Make migrations reversible (implement `downgrade()`)
- ✅ Use descriptive migration messages
- ✅ Keep migrations small and focused
- ✅ Add comments for complex migrations

### DON'T

- ❌ Edit existing migrations after they've been applied
- ❌ Skip migrations in sequence
- ❌ Make data-destructive changes without backups
- ❌ Forget to test downgrade path
- ❌ Use production database for testing migrations

## File Structure

```
alembic/
├── versions/           # Migration files
│   └── 9d71a898_initial_schema.py
├── env.py             # Migration environment (async support)
├── script.py.mako     # Migration template
└── README.md          # This file

alembic.ini            # Alembic configuration
```

## Async Support

This project uses **async SQLAlchemy**. The `env.py` file is configured to:

- Import models from `clawbot_coordinator.database`
- Use `async_engine_from_config` for async connections
- Run migrations in async context with `asyncio.run()`

## Initial Migration

The initial migration (`9d71a8985289`) creates:

- **bots table**: Bot registration and status tracking
- **workflows table**: Workflow orchestration
- **tasks table**: Individual task execution (references bots)

All tables include:
- UUID primary keys
- Timestamps (created_at, updated_at)
- Appropriate indexes for query performance

## Troubleshooting

### "Target database is not up to date"

```bash
# Check current version
alembic current

# Check what's pending
alembic history

# Upgrade to head
alembic upgrade head
```

### "Can't locate revision identified by X"

Migration file may have been deleted. Check `alembic_version` table in database:

```sql
SELECT * FROM alembic_version;
```

### "Multiple head revisions present"

Branching detected. Merge with:

```bash
alembic merge -m "merge branches" head1 head2
```

## Testing Migrations

```bash
# Fresh database
alembic downgrade base
alembic upgrade head

# Test specific migration
alembic upgrade 9d71a8985289
alembic downgrade base

# Verify schema
psql -d clawbot_coordinator -c "\dt"  # List tables
psql -d clawbot_coordinator -c "\d bots"  # Describe table
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Run migrations
  run: |
    alembic upgrade head
    
- name: Run tests
  run: |
    pytest tests/
    
- name: Verify migration is reversible
  run: |
    alembic downgrade -1
    alembic upgrade head
```

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
