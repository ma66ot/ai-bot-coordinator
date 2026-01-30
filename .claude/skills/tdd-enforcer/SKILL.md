# TDD Enforcer Skill

When asked to implement a feature:
1. First check if test exists in appropriate `tests/` directory
2. If no test exists:
    - ASK USER: "Should I write the failing test first for [feature name]?"
    - Create test with `@pytest.mark.todo` or explicit `assert False, "Implement [feature]"`
    - Run test to confirm it fails for the right reason
    - Only then proceed to implementation
3. If test exists and fails, fix implementation (not the test)
4. After implementation passes, ask: "Should I refactor before continuing?"

Never write production code without a failing test first.