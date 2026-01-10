# ast-grep MCP Improvement Suggestions

Based on the official [ast-grep Prompting Guide](https://ast-grep.github.io/advanced/prompting.html), this document tracks suggestions for improving the ast-grep MCP server.

> **Note:** Completed implementations are documented in [CHANGELOG.md](CHANGELOG.md).

## Implementation Status

| Priority | Suggestion | Status | Commit |
|----------|-----------|--------|--------|
| **P0** | stopBy documentation | ✅ Done | `3ee9ec7` |
| **P0** | Better error messages | ✅ Done | `082fde6` |
| **P1** | Documentation context tool | ✅ Done | `86d5756` |
| **P1** | Rule builder helper | ✅ Done | `86d5756` |
| **P2** | Enhanced tool descriptions | ✅ Done | `3ee9ec7` |
| **P2** | Pattern examples tool | ✅ Done | `86d5756` |
| **P2** | Composite rule guidance | ✅ Done | `3ee9ec7` |
| **P3** | Pre-flight validation | ✅ Done | `082fde6` |
| **P3** | Strictness documentation | Pending | - |
| **P3** | Interactive development | Partial | `a1b4d1a` |

## Remaining Items

### Strictness Mode Documentation (P3)

**Problem:** The guide mentions strictness options (`cst`, `smart`, `ast`, `relaxed`, `signature`) but users may not know when to use each.

**Suggestion:** Add documentation to `get_ast_grep_docs` explaining:
- When to use each strictness mode
- Examples of behavior differences
- Default behavior (`smart`)

### Interactive Rule Development Mode (P3) - Partially Complete

**Problem:** The prompting guide emphasizes trial-and-error refinement.

**Suggestion:** Add a tool that helps iteratively develop rules by:
1. Analyzing sample code's AST structure
2. Suggesting a starting pattern
3. Testing and providing refinement suggestions

**Current Implementation:** The `debug_pattern` tool (`a1b4d1a`) addresses parts 1-3:
- Validates metavariable syntax
- Compares pattern AST with code AST
- Provides prioritized suggestions for fixing issues

**Remaining:** A higher-level workflow tool that guides users through the full pattern development cycle.

## Commit History

| Commit | Date | Description |
|--------|------|-------------|
| `a1b4d1a` | 2026-01-09 | feat(search): add debug_pattern tool for diagnosing pattern matching issues |
| `86d5756` | 2026-01-10 | feat(search): add documentation and rule builder modules |
| `082fde6` | 2026-01-10 | feat(search): add warning detection for YAML rules |
| `3ee9ec7` | 2026-01-10 | feat(search): register new documentation and rule building tools |
| `e844c4e` | 2026-01-10 | docs: update CLAUDE.md with 2026-01-10 changes |

## References

- [ast-grep Prompting Guide](https://ast-grep.github.io/advanced/prompting.html)
- [Pattern Syntax Reference](https://ast-grep.github.io/guide/pattern-syntax.html)
- [Rule Configuration](https://ast-grep.github.io/guide/rule-config.html)
- [Rule Reference](https://ast-grep.github.io/reference/rule.html)
- [Full LLM Documentation](https://ast-grep.github.io/llms-full.txt)

---

**Created:** 2026-01-09
**Updated:** 2026-01-10
**Based on:** ast-grep official prompting documentation
