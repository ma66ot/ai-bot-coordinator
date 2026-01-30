#!/usr/bin/env python3
"""Prevent AI from accidentally importing FastAPI/SQLAlchemy into domain/"""
import ast
import sys
from pathlib import Path

FORBIDDEN_IMPORTS = ['fastapi', 'sqlalchemy', 'redis', 'starlette']

def check_file(filepath: Path) -> list[str]:
    errors = []
    content = filepath.read_text()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return [f"{filepath}: Syntax error"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name.startswith(f) for f in FORBIDDEN_IMPORTS):
                    errors.append(f"{filepath}:{node.lineno}: Forbidden import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if any(module.startswith(f) for f in FORBIDDEN_IMPORTS):
                errors.append(f"{filepath}:{node.lineno}: Forbidden import from {module}")
    return errors

def main():
    domain_files = Path("src/clawbot_coordinator/domain").rglob("*.py")
    errors = []
    for f in domain_files:
        errors.extend(check_file(f))

    if errors:
        print("ARCHITECTURE VIOLATION DETECTED:")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    print("✅ Domain layer purity check passed")

if __name__ == "__main__":
    main()