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
| **P3** | Strictness documentation | ✅ Done | `pending` |
| **P3** | Interactive development | ✅ Done | `pending` |

## All Items Complete! 🎉

All suggestions from the ast-grep prompting guide have been implemented.

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
