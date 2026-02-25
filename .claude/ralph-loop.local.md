---
active: true
iteration: 1
max_iterations: 20
completion_promise: "DONE"
started_at: "2026-02-24T00:00:00Z"
---

Use ast-grep (section 3b: structural AST-based code search) to find remaining magic numbers in src/ast_grep_mcp/**/*.py (excluding constants.py and __init__.py) and migrate them to named constants in src/ast_grep_mcp/constants.py.

APPROACH (from section 3b - ast-grep for pre-compression normalization):
- Use `ast-grep run --pattern '$NUM' --lang python src/` to find numeric literals structurally
- Focus on float and int literals that are not 0, 1, -1, 2 (trivially obvious)
- Exclude numbers already referencing constants
- Exclude version strings and __init__.py files

EACH ITERATION:
1. Use ast-grep or grep to find remaining magic numbers in source files (exclude constants.py, __init__.py, tests/)
2. Group related numbers into appropriate constant classes in constants.py
3. Update source files to reference the new constants
4. Run: timeout 60 uv run pytest tests/unit/ -q --tb=short 2>&1 | tail -20
5. Verify tests pass, then commit with: git add -A && git commit -m "(stand) migrate magic numbers batch N"

When ALL magic numbers have been extracted and tests pass, output <promise>DONE</promise>.

KEY: Check what files already import from constants.py vs what files still have raw literals.
