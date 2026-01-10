# ast-grep MCP Improvement Suggestions

Based on the official [ast-grep Prompting Guide](https://ast-grep.github.io/advanced/prompting.html), this document tracks suggestions for improving the ast-grep MCP server.

> **Note:** Completed implementations are documented in [CHANGELOG.md](CHANGELOG.md).

## Implementation Status

| Priority | Suggestion | Status | Notes |
|----------|-----------|--------|-------|
| **P0** | stopBy documentation | ✅ Done | See CHANGELOG.md 2026-01-10 |
| **P0** | Better error messages | ✅ Done | Automatic warning detection |
| **P1** | Documentation context tool | ✅ Done | `get_ast_grep_docs` |
| **P1** | Rule builder helper | ✅ Done | `build_rule` |
| **P2** | Enhanced tool descriptions | ✅ Done | All search tools updated |
| **P2** | Pattern examples tool | ✅ Done | `get_pattern_examples` |
| **P2** | Composite rule guidance | ✅ Done | Added to `find_code_by_rule` |
| **P3** | Pre-flight validation | ✅ Done | Warning detection in rules |
| **P3** | Strictness documentation | Pending | Document strictness modes |
| **P3** | Interactive development | Pending | Iterative rule refinement |

## Remaining Items

### Strictness Mode Documentation (P3)

**Problem:** The guide mentions strictness options (`cst`, `smart`, `ast`, `relaxed`, `signature`) but users may not know when to use each.

**Suggestion:** Add documentation to `get_ast_grep_docs` explaining:
- When to use each strictness mode
- Examples of behavior differences
- Default behavior (`smart`)

### Interactive Rule Development Mode (P3)

**Problem:** The prompting guide emphasizes trial-and-error refinement.

**Suggestion:** Add a tool that helps iteratively develop rules by:
1. Analyzing sample code's AST structure
2. Suggesting a starting pattern
3. Testing and providing refinement suggestions

This may be partially addressed by the existing `debug_pattern` tool.

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
