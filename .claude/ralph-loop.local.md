---
active: true
iteration: 1
max_iterations: 20
completion_promise: "DONE"
started_at: "2026-02-13T02:31:09Z"
---

Find all magic numbers in src/ast_grep_mcp/**/*.py (excluding constants.py and __init__.py) and move them into named constants in src/ast_grep_mcp/constants.py. Magic numbers are numeric literals (int or float) used inline that should be named constants. EXCLUDE: 0, 1, -1, 2 (trivially obvious), version strings, and numbers already referencing constants. For each iteration: 1) grep for remaining magic numbers in source files 2) add appropriate constants to constants.py 3) update source files to reference the new constants 4) run uv run pytest to verify no regressions. When ALL magic numbers have been extracted and tests pass, output <promise>DONE</promise>.
