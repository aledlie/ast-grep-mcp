---
name: zod-ast-grep-rules-generated
description: AST-grep rules generated from eslint-plugin-zod patterns
type: reference
---

# Zod AST-grep Rules Generated

Created 10 AST-grep detection rules in `rules/zod-validation-rules.yaml` based on eslint-plugin-zod patterns.

## Generated Rules

1. **no-any-schema** — Detect `z.any()` usage
2. **require-schema-suffix** — Detect schema variables not ending with "Schema"
3. **require-error-message** — Detect `.refine()` without error messages
4. **prefer-enum-over-literal-union** — Detect union of literals (should use `.enum()`)
5. **no-optional-and-default-together** — Detect `.optional().default()` chains
6. **no-unknown-schema** — Detect `z.unknown()` usage
7. **no-string-schema-with-uuid** — Detect `z.string().uuid()` (use `z.uuid()`)
8. **prefer-string-schema-with-trim** — Suggest `.trim()` on string schemas
9. **no-empty-custom-schema** — Detect `z.custom()` without implementation
10. **prefer-namespace-import** — Detect destructured imports (use namespace)

## Location
- Rules file: `rules/zod-validation-rules.yaml`
- Generator script: `scripts/generate_zod_rules.py`

## Usage
Run with `find_code_by_rule` or `rewrite_code` tools pointing to `rules/zod-validation-rules.yaml`