#!/usr/bin/env python3
"""Generate AST-grep rules for eslint-plugin-import-zod patterns."""

from ast_grep_mcp.features.search.service import build_rule_impl

# Rule 1: Named imports of z
print("=" * 60)
print("RULE 1: import-zod-named-to-namespace")
print("=" * 60)
rule1 = build_rule_impl(
    pattern='import { z } from "zod"',
    language="typescript",
    rule_id="import-zod-named-to-namespace",
    message='Use namespace import: import * as z from "zod"',
    severity="warning",
    fix='import * as z from "zod"'
)
print(rule1)

# Rule 2: Default imports of z
print("\n" + "=" * 60)
print("RULE 2: import-zod-default-to-namespace")
print("=" * 60)
rule2 = build_rule_impl(
    pattern='import z from "zod"',
    language="typescript",
    rule_id="import-zod-default-to-namespace",
    message='Use namespace import: import * as z from "zod"',
    severity="warning",
    fix='import * as z from "zod"'
)
print(rule2)

# Rule 3: Default imports with different names
print("\n" + "=" * 60)
print("RULE 3: import-zod-default-renamed-to-namespace")
print("=" * 60)
rule3 = build_rule_impl(
    pattern='import $NAME from "zod"',
    language="typescript",
    rule_id="import-zod-default-renamed-to-namespace",
    message='Use namespace import instead of default import for zod',
    severity="warning"
)
print(rule3)

# Rule 4: Type default imports
print("\n" + "=" * 60)
print("RULE 4: import-zod-type-default-to-namespace")
print("=" * 60)
rule4 = build_rule_impl(
    pattern='import type z from "zod"',
    language="typescript",
    rule_id="import-zod-type-default-to-namespace",
    message='Use namespace type import: import type * as z from "zod"',
    severity="warning",
    fix='import type * as z from "zod"'
)
print(rule4)

# Rule 5: Mixed default and named imports
print("\n" + "=" * 60)
print("RULE 5: import-zod-mixed-to-namespace")
print("=" * 60)
rule5 = build_rule_impl(
    pattern='import z, { $$EXPORTS } from "zod"',
    language="typescript",
    rule_id="import-zod-mixed-to-namespace",
    message='Use namespace import for z and separate import for other exports',
    severity="warning"
)
print(rule5)

# Rule 6: Subpath imports with z
print("\n" + "=" * 60)
print("RULE 6: import-zod-subpath-to-namespace")
print("=" * 60)
rule6 = build_rule_impl(
    pattern='import { z } from "zod/$$SUBPATH"',
    language="typescript",
    rule_id="import-zod-subpath-to-namespace",
    message='Use namespace import for zod subpath: import * as z from "zod/..."',
    severity="warning"
)
print(rule6)

# Rule 7: Type-only mixed imports
print("\n" + "=" * 60)
print("RULE 7: import-zod-type-mixed-to-namespace")
print("=" * 60)
rule7 = build_rule_impl(
    pattern='import type { $$TYPES, z } from "zod"',
    language="typescript",
    rule_id="import-zod-type-mixed-to-namespace",
    message='Use namespace import for z: import type * as z from "zod"',
    severity="warning"
)
print(rule7)

print("\n" + "=" * 60)
print("All import-zod rules generated successfully!")
print("=" * 60)
