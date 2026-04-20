---
name: import-zod-eslint-plugin-rules
description: ESLint plugin for enforcing Zod namespace imports
type: reference
---

# eslint-plugin-import-zod Rules Reference

## Single Rule: prefer-zod-namespace

**Purpose:** Enforce namespace imports for Zod to improve tree-shaking and reduce bundle sizes.

## Violation Patterns

| Pattern | Issue | Fix |
|---------|-------|-----|
| `import { z } from "zod"` | Named import | `import * as z from "zod"` |
| `import z from "zod"` | Default import | `import * as z from "zod"` |
| `import zod from "zod"` | Default import renamed | `import * as zod from "zod"` |
| `import type z from "zod"` | Type default import | `import type * as z from "zod"` |
| `import z, { toJSON } from "zod"` | Mixed imports | Separate into namespace + named |
| `import { z } from "zod/v4"` | Subpath named import | `import * as z from "zod/v4"` |
| `import type { ZodError, z } from "zod"` | Type mixed imports | Namespace for z, separate for others |

## Valid Patterns (No change needed)

- `import * as z from "zod"` ✅
- `import type * as z from "zod"` ✅
- `import { ZodError } from "zod"` ✅ (non-z exports OK)
- `import type { ZodError } from "zod"` ✅

## Generated AST-grep Rules

7 detection rules in `rules/import-zod-rules.yaml`:
1. import-zod-named-to-namespace
2. import-zod-default-to-namespace
3. import-zod-default-renamed-to-namespace
4. import-zod-type-default-to-namespace
5. import-zod-mixed-to-namespace
6. import-zod-subpath-to-namespace
7. import-zod-type-mixed-to-namespace