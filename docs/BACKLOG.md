# Backlog

## Medium Priority (P2)

#### M1: Handle JS/TS brace counter edge cases
**Priority**: P2 | **Source**: condense feature session (9e65f55)
Improve brace counter for JavaScript/TypeScript to handle template literals and regex patterns correctly. Currently counts braces inside template strings and regex patterns as structural braces. -- `src/ast_grep_mcp/features/condense/strip.py` (implementation limitation documented in code review)

#### M2: Add tool-layer integration tests for condense tools
**Priority**: P2 | **Source**: condense feature session (9e65f55)
Create integration tests for condense MCP tools that test the full tool interface (tool wrapper + impl + mocking patterns). Current tests only cover impl layer. -- `tests/unit/features/condense/` (test gaps identified)
