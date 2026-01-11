# ast-grep-mcp MCP Tools (47 Total)

> **Auto-generated cache** - Updated when tools are modified via git commits.
> Last updated: 2026-01-10

## Search Tools (9)
| Tool | Description |
|------|-------------|
| `dump_syntax_tree` | Dump code's syntax structure or pattern structure for debugging rules |
| `test_match_code_rule` | Test code against an ast-grep YAML rule before using it in a project |
| `find_code` | Find code matching an ast-grep pattern in a project folder |
| `find_code_by_rule` | Find code using custom YAML rules with complex conditions (any/all, regex, inside, precedes/follows) |
| `debug_pattern` | Debug why a pattern doesn't match code with metavariable validation and AST comparison |
| `develop_pattern` | Interactive pattern development assistant - analyzes code and suggests patterns |
| `get_ast_grep_docs` | Get ast-grep documentation for patterns, rules, relational rules, metavariables, strictness, workflow |
| `build_rule` | Build a properly structured YAML rule from components with automatic stopBy configuration |
| `get_pattern_examples` | Get common ast-grep pattern examples for a language organized by category |

## Rewrite Tools (3)
| Tool | Description |
|------|-------------|
| `rewrite_code` | Apply automated code transformations using ast-grep fix rules with dry-run preview |
| `rollback_rewrite` | Restore files from backup created during rewrite operations |
| `list_backups` | List all available backups in the project |

## Refactoring Tools (2)
| Tool | Description |
|------|-------------|
| `extract_function` | Extract selected code into a new function with automatic parameter/return detection |
| `rename_symbol` | Rename a symbol across codebase with scope awareness and conflict detection |

## Deduplication Tools (4)
| Tool | Description |
|------|-------------|
| `find_duplication` | Find duplicate functions/classes/methods in a codebase |
| `analyze_deduplication_candidates` | Analyze and rank deduplication candidates by refactoring value |
| `apply_deduplication` | Apply automated deduplication refactoring with syntax validation |
| `benchmark_deduplication` | Run performance benchmarks for deduplication functions |

## Complexity Tools (3)
| Tool | Description |
|------|-------------|
| `analyze_complexity` | Analyze code complexity metrics (cyclomatic, cognitive, nesting, length) |
| `detect_code_smells` | Detect code smells and anti-patterns (long functions, parameter bloat, deep nesting, magic numbers) |
| `test_sentry_integration` | Test Sentry integration by triggering different event types |

## Quality Tools (7)
| Tool | Description |
|------|-------------|
| `create_linting_rule` | Create custom linting rules using ast-grep patterns |
| `list_rule_templates` | List available pre-built rule templates (24+ templates) |
| `enforce_standards` | Enforce coding standards by executing linting rules against a project |
| `apply_standards_fixes` | Automatically fix code quality violations with safety classification |
| `generate_quality_report` | Generate comprehensive code quality reports (Markdown/JSON) |
| `detect_security_issues` | Scan for security vulnerabilities (SQL injection, XSS, command injection, secrets, crypto) |
| `detect_orphans` | Find orphan files and functions not imported or called anywhere in the codebase |

## Schema.org Tools (9)
| Tool | Description |
|------|-------------|
| `get_schema_type` | Get detailed information about a schema.org type |
| `search_schemas` | Search for schema.org types by keyword |
| `get_type_hierarchy` | Get inheritance hierarchy for a schema.org type |
| `get_type_properties` | Get all properties available for a schema.org type |
| `generate_schema_example` | Generate example JSON-LD structured data for a schema.org type |
| `generate_entity_id` | Generate proper @id values following Schema.org best practices |
| `validate_entity_id` | Validate @id values against Schema.org best practices |
| `build_entity_graph` | Build knowledge graph of related entities with @id references |
| `enhance_entity_graph` | Analyze existing JSON-LD graphs and suggest enhancements based on Schema.org and Google Rich Results guidelines |

## Documentation Tools (5)
| Tool | Description |
|------|-------------|
| `generate_docstrings` | Auto-generate docstrings/JSDoc with multiple styles (Google, NumPy, Sphinx, JSDoc, Javadoc) |
| `generate_readme_sections` | Generate README.md sections from code structure analysis |
| `generate_api_docs` | Generate API documentation from route definitions (Express, FastAPI, Flask) with OpenAPI 3.0 |
| `generate_changelog` | Generate changelogs from git commits (Keep a Changelog, Conventional formats) |
| `sync_documentation` | Keep documentation synchronized with code, detect stale docs and broken links |

## Cross-Language Tools (5)
| Tool | Description |
|------|-------------|
| `search_multi_language` | Search across multiple programming languages for semantically equivalent patterns |
| `find_language_equivalents` | Find equivalent patterns across programming languages |
| `convert_code_language` | Convert code from one programming language to another |
| `refactor_polyglot` | Refactor across multiple programming languages atomically |
| `generate_language_bindings` | Generate API client bindings for multiple languages from OpenAPI/Swagger specs |

---

## Tool Source Files

| Category | File | Count |
|----------|------|-------|
| Search | `src/ast_grep_mcp/features/search/tools.py` | 9 |
| Rewrite | `src/ast_grep_mcp/features/rewrite/tools.py` | 3 |
| Refactoring | `src/ast_grep_mcp/features/refactoring/tools.py` | 2 |
| Deduplication | `src/ast_grep_mcp/features/deduplication/tools.py` | 4 |
| Complexity | `src/ast_grep_mcp/features/complexity/tools.py` | 3 |
| Quality | `src/ast_grep_mcp/features/quality/tools.py` | 7 |
| Schema | `src/ast_grep_mcp/features/schema/tools.py` | 9 |
| Documentation | `src/ast_grep_mcp/features/documentation/tools.py` | 5 |
| Cross-Language | `src/ast_grep_mcp/features/cross_language/tools.py` | 5 |

**Total: 47 MCP tools** across 9 categories
