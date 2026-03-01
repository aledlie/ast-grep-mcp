# Backlog

## Medium Priority (P2)

#### M1: Handle JS/TS brace counter edge cases
**Priority**: P2 | **Source**: condense feature session (9e65f55)
Improve brace counter for JavaScript/TypeScript to handle template literals and regex patterns correctly. Currently counts braces inside template strings and regex patterns as structural braces. -- `src/ast_grep_mcp/features/condense/strip.py` (implementation limitation documented in code review)

#### M2: Add tool-layer integration tests for condense tools
**Priority**: P2 | **Source**: condense feature session (9e65f55)
Create integration tests for condense MCP tools that test the full tool interface (tool wrapper + impl + mocking patterns). Current tests only cover impl layer. -- `tests/unit/features/condense/` (test gaps identified)

#### CR1: Commit 565aaea (ast-grep-mcp) — Parser Fixes

  ┌──────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Severity │                                                                        Finding                                                                        │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ High     │ _split_params: > in => arrow-function defaults corrupts depth counter (goes negative). Fix: guard if depth > 0 before decrementing                    │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ High     │ rstrip("?") strips ALL trailing ? chars — could produce empty string on malformed input. Fix: use p.name[:-1] if p.name.endswith("?") else p.name     │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Medium   │ JSDoc nested brace regex only handles 2 levels — 3+ levels ({{ error: { message: string } }}) still fail. Pre-existing limitation partially addressed │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Medium   │ No tests added for new code paths (_split_params, updated regex, rstrip change)                                                                       │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Low      │ _split_params whitespace-only input returns ['   '] — safe due to caller guard but inconsistent contract                                              │
  └──────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘a
