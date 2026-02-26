# Code Condense Prep Review: ast-grep-mcp

> Implementation plan for integrating code condensation pipeline capabilities into ast-grep-mcp, based on the [Repomix-to-Condense Pipeline analysis](~/reports/code-condense-whitepaper/repomix_to_condense_with_additional_integrations.md).

---

## 1. Problem Statement

Feeding entire repositories into AI tools is expensive and slow. The repomix-to-condense whitepaper demonstrates that a `code → semantic extraction → statistical compression` pipeline achieves **90–95% reduction** in token/byte count. ast-grep-mcp already has the core capability (AST-level structural search/rewrite across 27 languages) but lacks explicit condensation tooling. This document outlines how to close that gap.

---

## 2. What ast-grep-mcp Already Provides

| Capability | Whitepaper Role | Current Location |
|---|---|---|
| AST parsing (Tree-sitter) | Semantic extraction engine | `core/executor.py` |
| Structural pattern search | Selective extraction (export surfaces, API boundaries) | `features/search/service.py` |
| Code rewriting | Pre-compression normalization (canonical forms) | `features/rewrite/service.py` |
| Dead code detection | Pre-compression elimination pass | `features/quality/smells.py` |
| Deduplication | Redundancy reduction before packing | `features/deduplication/` |
| Complexity analysis | Prioritize what to keep vs. strip | `features/complexity/` |
| Cross-language support | Polyglot pipeline coverage (27 languages) | `features/cross_language/` |
| Documentation generation | Extract signatures/docstrings (lossy compress equivalent) | `features/documentation/` |

**Key insight:** ast-grep-mcp already performs the most valuable step in the pipeline — the semantic extraction that repomix `--compress` provides via Tree-sitter. The difference is ast-grep-mcp offers *surgical precision* (pattern-based extraction) vs. repomix's *all-or-nothing* structural compression.

---

## 3. Proposed New Feature: `condense` (5 tools)

New feature domain at `src/ast_grep_mcp/features/condense/`.

### 3a. Tool Definitions

| Tool | Purpose | Input | Output |
|---|---|---|---|
| `condense_extract_surface` | Extract public API surface (exports, signatures, types) | `path`, `language`, `include_docstrings` | Condensed source text |
| `condense_normalize` | Rewrite code to canonical forms before compression | `path`, `language`, `normalizations[]` | Normalized source + diff stats |
| `condense_strip` | Remove dead code, debug statements, unused imports | `path`, `language`, `strip_targets[]` | Stripped source + removal count |
| `condense_pack` | Combine extract + normalize + strip into single pipeline | `path`, `language`, `strategy` | Packed output + compression stats |
| `condense_estimate` | Estimate reduction ratio without modifying files | `path`, `language` | Token/byte reduction estimates |

### 3b. Strategies (for `condense_pack`)

Map directly to whitepaper Section 4 use cases:

| Strategy | Behavior | Expected Reduction |
|---|---|---|
| `ai_chat` | Signatures + types + docstrings only (lossy) | ~85% tokens |
| `ai_analysis` | Full source minus dead code and debug stmts (lossless) | ~40% tokens |
| `archival` | Full source, normalized, deduplicated (lossless) | ~30% tokens |
| `polyglot` | Per-language optimal strategy selection | ~60–80% tokens |

### 3c. Module Structure

```
src/ast_grep_mcp/features/condense/
├── __init__.py
├── tools.py              # MCP tool definitions (register_condense_tools)
├── service.py            # Core condensation logic
├── strategies.py         # Strategy implementations (ai_chat, ai_analysis, etc.)
├── normalizer.py         # Code normalization transforms
└── estimator.py          # Reduction estimation without modification
```

---

## 4. Constants Additions

Add to `src/ast_grep_mcp/constants.py`:

```python
class CondenseDefaults:
    """Defaults for code condensation pipeline."""
    # Strategy selection
    DEFAULT_STRATEGY = "ai_analysis"

    # Extraction
    INCLUDE_DOCSTRINGS = True
    INCLUDE_TYPE_ANNOTATIONS = True
    INCLUDE_IMPORTS = True
    MAX_FUNCTION_BODY_LINES = 3  # For ai_chat: inline trivial bodies

    # Normalization
    NORMALIZE_ARROW_FUNCTIONS = True
    NORMALIZE_STRING_QUOTES = True
    NORMALIZE_TRAILING_COMMAS = True

    # Strip targets
    STRIP_CONSOLE_LOG = True
    STRIP_DEBUG_STATEMENTS = True
    STRIP_UNUSED_IMPORTS = True
    STRIP_COMMENTS = False  # Preserve by default; whitepaper shows 10-25% savings
    STRIP_EMPTY_LINES = True

    # Limits
    MAX_FILE_SIZE_BYTES = 1_048_576  # 1 MB; skip larger files
    MAX_FILES_PER_RUN = 500

    # Estimation
    AVG_TOKENS_PER_BYTE = 0.25  # Rough approximation for token counting
```

---

## 5. Implementation Details

### 5a. Surface Extraction (`condense_extract_surface`)

Uses existing ast-grep patterns to extract:

```python
# Per-language extraction patterns
SURFACE_PATTERNS = {
    "typescript": [
        "export function $NAME($$$PARAMS): $RET { $$$ }",
        "export class $NAME $$$BODY",
        "export interface $NAME { $$$ }",
        "export type $NAME = $$$",
        "export const $NAME: $TYPE = $$$",
    ],
    "python": [
        "def $NAME($$$PARAMS) -> $RET: $$$",
        "class $NAME($$$BASES): $$$",
        "@$DECORATOR\ndef $NAME($$$): $$$",
    ],
    # ... 27 languages via cross_language/pattern_database.py
}
```

**Reuse:** Leverage `features/search/service.py:find_code_impl()` for pattern matching and `features/cross_language/pattern_database.py` for language-specific patterns.

### 5b. Normalization (`condense_normalize`)

Uses existing rewrite engine for canonical transformations. From the whitepaper (Section 3b):

> ast-grep can rewrite code patterns to canonical forms before compression, increasing redundancy and improving compression ratios.

Normalizations that improve downstream compression:

| Transform | Pattern | Rewrite | Compression Benefit |
|---|---|---|---|
| Arrow function normalization | `function $N($A) { return $E }` | `const $N = ($A) => $E` | Reduces function keyword repetition |
| Consistent string quotes | `"$S"` (where no interpolation) | `'$S'` | Eliminates quote-style entropy |
| Remove trailing semicolons | `$STMT;` (in TS/JS) | `$STMT` | Reduces noise characters |
| Collapse single-line blocks | `if ($C) {\n  $S\n}` | `if ($C) $S` | Reduces brace/whitespace entropy |

**Reuse:** `features/rewrite/service.py:rewrite_code_impl()` for all transformations.

### 5c. Dead Code Strip (`condense_strip`)

Combines existing quality tools:

1. **Unused imports** — `features/quality/smells.py` already detects these
2. **Console/debug stmts** — Pattern: `console.log($$$)`, `print($$$)`, `debugger`
3. **Commented-out code** — Heuristic from quality smells detectors
4. **Empty blocks** — Pattern: `{ }`, `pass`

**Reuse:** `features/quality/smells_detectors.py` for detection, `features/rewrite/service.py` for removal.

### 5d. Pipeline Orchestration (`condense_pack`)

Chains the above in order matching whitepaper Section 3b pipeline:

```
normalize → strip dead code → extract surface → format output
```

Output format options:
- **xml** — Matches repomix XML format for downstream zstd compatibility
- **markdown** — For direct AI consumption
- **plain** — Minimal overhead, best compression ratio

### 5e. Estimation (`condense_estimate`)

Non-destructive analysis that runs extraction patterns in dry-run mode:

```python
# Returns structure like:
{
    "total_files": 109,
    "total_lines": 18500,
    "total_bytes": 620000,
    "estimated_condensed_bytes": {
        "ai_chat": 93000,      # ~85% reduction
        "ai_analysis": 372000,  # ~40% reduction
        "archival": 434000,     # ~30% reduction
    },
    "estimated_tokens": {
        "ai_chat": 23250,
        "ai_analysis": 93000,
        "archival": 108500,
    },
    "top_reduction_candidates": [
        {"file": "utils/formatters.py", "lines": 850, "reducible_pct": 72},
        {"file": "utils/templates.py", "lines": 600, "reducible_pct": 68},
    ]
}
```

---

## 6. Integration with Existing Features

### 6a. Deduplication Pre-Pass

Before condensation, run deduplication to identify clones. From `features/deduplication/`:
- Use `find_duplicates_impl()` to identify redundant code blocks
- Condense keeps one copy, references the rest
- Expected additional reduction: 5–15% on typical codebases

### 6b. Complexity-Guided Extraction

Use `features/complexity/complexity_analyzer.py` to decide extraction depth:
- **High complexity functions:** Keep full body (complex = important)
- **Low complexity functions:** Signature + docstring only
- **Trivial functions (≤3 lines):** Inline the body

### 6c. Cross-Language Pattern Reuse

`features/cross_language/pattern_database.py` already maintains equivalent patterns across languages. Extend with condensation-specific patterns:
- API surface extraction per language
- Debug statement patterns per language
- Import/export patterns per language

---

## 7. Polyglot Pipeline Strategy

From whitepaper Section 3c (Makefile per-type strategies):

| File Type | ast-grep-mcp Strategy | Reason |
|---|---|---|
| Code (.ts, .py, .rs, .go) | `condense_pack` with `ai_chat` | AST extraction removes 70%+ |
| Config (.json, .yaml, .toml) | Pass-through (no AST extraction) | Structure must be preserved |
| Text (.md, .txt) | Strip empty lines only | Natural language, minimal reduction |
| Test files | `condense_extract_surface` | Keep test names/structure, strip bodies |
| Generated files | Exclude entirely | Regenerable from source |

Implementation: `strategies.py` selects per-file strategy based on language and path patterns.

---

## 8. Compression Statistics & Reporting

New model in `src/ast_grep_mcp/models/condense.py`:

```python
@dataclass
class CondenseResult:
    strategy: str
    files_processed: int
    files_skipped: int
    original_bytes: int
    condensed_bytes: int
    reduction_pct: float
    original_tokens_est: int
    condensed_tokens_est: int
    normalizations_applied: int
    dead_code_removed_lines: int
    duplicates_collapsed: int
    per_language_stats: dict[str, LanguageCondenseStats]

@dataclass
class LanguageCondenseStats:
    language: str
    files: int
    original_lines: int
    condensed_lines: int
    patterns_matched: int
```

---

## 9. Test Plan

### Unit Tests (`tests/unit/features/condense/`)

| Test File | Coverage |
|---|---|
| `test_surface_extraction.py` | Per-language pattern extraction accuracy |
| `test_normalizer.py` | Each normalization transform correctness |
| `test_strip.py` | Dead code removal (console.log, unused imports, etc.) |
| `test_strategies.py` | Strategy selection and composition |
| `test_estimator.py` | Estimation accuracy vs. actual condensation |
| `test_pack_pipeline.py` | End-to-end pipeline with all strategies |

### Quality Tests

Add to `tests/quality/test_complexity_regression.py`:
- All condense modules must pass existing complexity gates (cyclomatic ≤20, cognitive ≤30)

### Integration Tests

- Condense the ast-grep-mcp codebase itself (`dogfood test`)
- Verify condensed output is valid, parseable text
- Verify reduction percentages match estimates within ±10%

---

## 10. Implementation Order

| Phase | Work | Dependencies | Est. Files |
|---|---|---|---|
| **P1** | Constants + models + estimator | None | 3 |
| **P2** | Surface extraction (per-language patterns) | P1 | 2 |
| **P3** | Normalizer (rewrite transforms) | P1 | 1 |
| **P4** | Strip (dead code removal) | P1 | 1 |
| **P5** | Pack pipeline (orchestration) | P2, P3, P4 | 1 |
| **P6** | Tool registration + MCP integration | P5 | 2 |
| **P7** | Tests (unit + integration) | P6 | 8 |
| **P8** | Polyglot strategy refinement | P7 | 1 |

Total new files: ~19 (6 source + 1 model + 1 constants update + ~8 test files + 3 supporting)

---

## 11. External Pipeline Integration

ast-grep-mcp handles the **semantic extraction** stage. For the full pipeline described in the whitepaper:

```
ast-grep-mcp (semantic)  →  repomix (packing)  →  zstd (statistical)
     ↓                           ↓                      ↓
  70-85% token reduction    +5-15% overhead         3-4x byte reduction
  (the high-value step)     (structure/metadata)    (on remaining text)
```

### CLI Integration Example

```bash
# 1. ast-grep-mcp condenses via MCP tool call
# 2. Feed output to repomix for structured packing
repomix --style xml -o packed.xml .condense/

# 3. zstd for storage/transfer
zstd -9 packed.xml -o packed.xml.zst
```

### Makefile Target (for ast-grep-mcp itself)

```makefile
condense:
	uv run python -c "from ast_grep_mcp.features.condense.service import condense_pack_impl; \
		print(condense_pack_impl('src/', strategy='ai_chat'))" > .condense/output.xml
	zstd -9 --rm .condense/output.xml
```

---

## 12. Success Criteria

- [ ] 5 new MCP tools registered and functional
- [ ] `condense_estimate` returns within 5s for 109-module codebase
- [ ] `condense_pack` with `ai_chat` achieves ≥80% token reduction on ast-grep-mcp itself
- [ ] `condense_pack` with `ai_analysis` achieves ≥35% token reduction (lossless)
- [ ] All new modules pass complexity regression gates
- [ ] ≥90% unit test coverage on new code
- [ ] Estimation accuracy within ±10% of actual condensation

---

## References

- [Repomix-to-Condense Pipeline Analysis](~/reports/code-condense-whitepaper/repomix_to_condense_with_additional_integrations.md)
- [ast-grep documentation](https://ast-grep.github.io/)
- [Repomix Code Compression Guide](https://repomix.com/guide/code-compress)
- [zstd benchmarks](https://facebook.github.io/zstd/#benchmarks)
- [Large Text Compression Benchmark](https://mattmahoney.net/dc/text.html)
