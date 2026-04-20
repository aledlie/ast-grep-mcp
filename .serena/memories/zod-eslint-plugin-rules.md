---
name: zod-eslint-plugin-rules
description: ESLint plugin Zod - 20 lint rules for Zod schema validation
type: reference
---

# ESLint Plugin Zod Rules Reference

## Universal Rules (12 rules for both zod & zod-mini)

| Rule | Purpose | Violation | Fix |
|------|---------|-----------|-----|
| `consistent-import` | Enforce consistent import style | `import { z } from 'zod'` | `import * as z from 'zod'` |
| `consistent-import-source` | Enforce consistent source from Zod imports | Mixed sources | Single source |
| `consistent-object-schema-type` | Enforce consistent schema method usage | Mixed z.object/z.ZodType | Consistent approach |
| `no-any-schema` | Disallow `z.any()` | `z.any()` | `z.unknown().catch({})` |
| `no-empty-custom-schema` | Disallow `z.custom()` without args | `z.custom()` | `z.custom((v) => {...})` |
| `no-unknown-schema` | Disallow `z.unknown()` | `z.unknown()` | `z.any()` or typed schema |
| `prefer-meta` | Enforce `.meta()` over `.describe()` | `.describe("text")` | `.meta({ ... })` |
| `prefer-namespace-import` | Enforce namespace import | `import { z }` | `import * as z` |
| `require-brand-type-parameter` | Require type on `.brand()` | `.brand()` | `.brand<T>()` |
| `require-error-message` | Refine must have error message | `.refine(fn)` | `.refine(fn, { message })` |
| `require-schema-suffix` | Require "Schema" suffix on variables | `const user = z.object(...)` | `const userSchema = z.object(...)` |
| `schema-error-property-style` | Consistent error message style | Mixed styles | Uniform style |

## Zod-Exclusive Rules (9 rules)

| Rule | Purpose | Violation | Fix |
|------|---------|-----------|-----|
| `array-style` | Enforce consistent array style | Mixed z.array/z.ZodArray | Consistent approach |
| `no-number-schema-with-int` | Disallow legacy `.int()` on numbers | `z.number().int()` | `z.number().int()` → use `z.coerce.number()` |
| `no-optional-and-default-together` | Can't use both `.optional()` and `.default()` | `.optional().default(val)` | Use `.default(val)` only |
| `no-string-schema-with-uuid` | Disallow `.uuid()` on strings | `z.string().uuid()` | `z.uuid()` |
| `no-throw-in-refine` | Don't throw in refine callbacks | `refine(() => { throw ... })` | Return false, use { message } |
| `no-transform-in-record-key` | No transforms in record key schemas | `z.record(z.string().transform(...))` | Keep transforms in values |
| `prefer-enum-over-literal-union` | Use `.enum()` for string literals | `z.union([z.literal("a"), z.literal("b")])` | `z.enum(["a", "b"])` |
| `prefer-meta-last` | `.meta()` must be last method | `schema.meta(...).refine(...)` | `schema.refine(...).meta(...)` |
| `prefer-string-schema-with-trim` | Enforce `.trim()` on strings | `z.string()` | `z.string().trim()` |

## Key Detection Patterns for AST-grep Rules

1. **no-any-schema**: Match `z.any()` calls
2. **require-error-message**: Match `.refine()` without second arg with `{ message }`
3. **require-schema-suffix**: Match variable assignments where RHS is `z.object/z.string/z.record` and name doesn't end with "Schema"
4. **prefer-enum-over-literal-union**: Match `z.union([z.literal(...), z.literal(...)])` patterns
5. **no-optional-and-default-together**: Match `.optional().default()` or `.default().optional()` chains