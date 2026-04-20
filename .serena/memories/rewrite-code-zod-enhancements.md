---
name: rewrite-code-zod-enhancements
description: Enhancements to rewrite_code tool with Zod-specific rules and templates
type: project
---

# Rewrite Code Tool - Zod Enhancements

## Changes Made

### 1. Enhanced Tool Documentation
**File:** `src/ast_grep_mcp/features/rewrite/tools.py`
- Updated rewrite_code() docstring with comprehensive Zod examples
- Added 5 schema validation patterns (no-any-schema, require-schema-suffix, require-error-message, prefer-enum, no-optional-and-default)
- Added 3 import pattern examples (named→namespace, default→namespace, mixed→namespace)
- Included tips for using metavariables and constraints

### 2. New Zod Templates Module
**File:** `src/ast_grep_mcp/features/rewrite/zod_templates.py`
- Pre-built YAML rules for all 14 Zod patterns
- `get_zod_rule(rule_id)` — retrieve rules by ID
- `list_schema_rules()` — list schema validation rules
- `list_import_rules()` — list import enforcement rules
- `get_rules_by_category(category)` — rules filtered by type

### 3. Comprehensive Rewrite Guide
**File:** `docs/ZOD-REWRITE-GUIDE.md`
- Quick start examples (CLI and Python)
- Detailed guide for each rule with before/after code
- Usage patterns for rewrite_code_impl()
- Rollback examples
- Best practices section

## Available Rules

**Schema Validation (9 rules):**
- no-any-schema
- require-schema-suffix
- require-error-message
- prefer-enum-over-literal-union
- no-optional-and-default-together
- no-unknown-schema
- no-string-schema-with-uuid
- prefer-string-schema-with-trim
- no-empty-custom-schema

**Import Enforcement (5 rules):**
- import-zod-named-to-namespace
- import-zod-default-to-namespace
- import-zod-type-default-to-namespace
- import-zod-mixed-to-namespace
- import-zod-subpath-to-namespace

## Usage

```python
from ast_grep_mcp.features.rewrite.zod_templates import get_zod_rule
from ast_grep_mcp.features.rewrite.service import rewrite_code_impl

rule = get_zod_rule('no-any-schema')
result = rewrite_code_impl('/path/to/project', rule, dry_run=True)
```

## Integration Points

- Integrates with existing rewrite_code_impl() function
- Compatible with find_code_by_rule for validation
- Supports rollback_rewrite() for undo operations
- Works with rule files in rules/ directory