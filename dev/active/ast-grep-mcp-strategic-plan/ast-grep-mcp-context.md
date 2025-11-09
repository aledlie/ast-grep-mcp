# AST-Grep MCP Server - Context Documentation

**Last Updated:** 2025-11-08 (Phase 1: 100% COMPLETE - All 5 tasks)

---

## Project Overview

**Name:** ast-grep MCP Server
**Repository:** https://github.com/ast-grep/ast-grep-mcp
**Type:** Model Context Protocol (MCP) Server
**Purpose:** Provide AI assistants with structural code search capabilities using ast-grep
**Status:** Experimental/MVP
**License:** TBD (check repository)

---

## Architecture Overview

### System Design

```
┌─────────────────────┐
│   MCP Client        │
│ (Cursor/Claude)     │
└──────────┬──────────┘
           │ MCP Protocol (stdio)
           ▼
┌─────────────────────┐
│   FastMCP Server    │
│   (Python/main.py)  │
├─────────────────────┤
│ - dump_syntax_tree  │
│ - test_match_code   │
│ - find_code         │
│ - find_code_by_rule │
└──────────┬──────────┘
           │ subprocess.run()
           ▼
┌─────────────────────┐
│   ast-grep CLI      │
│  (External Binary)  │
└─────────────────────┘
```

### Key Design Decisions

1. **Single-File Architecture** (main.py, ~517 lines as of 2025-11-08)
   - Rationale: Simplicity, portability, easy maintenance
   - Trade-off: May need refactoring if complexity grows beyond ~600 lines
   - Current: 166 statements, 96% test coverage

2. **Text Output Format as Default**
   - Rationale: Reduces token usage by ~75% vs JSON
   - Format: `filepath:line-range` headers with match text
   - Trade-off: Less metadata available (use JSON for full details)

3. **Dynamic Tool Registration**
   - Pattern: Tools registered via `register_mcp_tools()` after config parsing
   - Rationale: Allows tools to access global `CONFIG_PATH` variable
   - Complexity: Nested functions for closure over config

4. **Subprocess Execution**
   - Flow: `run_ast_grep()` → `run_command()` → `subprocess.run()`
   - Windows compatibility: `shell=True` for npm-installed ast-grep (batch file)
   - Error handling: Custom exception hierarchy (AstGrepError and subclasses)

5. **Test Mocking Strategy**
   - Approach: `MockFastMCP` class bypasses decorator machinery
   - Pattern: Patch imports, import main, call `register_mcp_tools()`, extract tools
   - Trade-off: Brittle if FastMCP changes, but allows direct tool testing

---

## Key Files and Directories

### Core Implementation
- **`main.py`** (799 lines) - Entire MCP server implementation
  - Lines 1-12: Imports (added time, structlog in Phase 1)
  - Lines 18-63: Logging configuration (configure_logging, get_logger)
  - Lines 66-138: Custom exception classes (6 exception types)
  - Lines 141-181: Pydantic configuration models (validation)
  - Lines 184-225: Config validation function
  - Lines 228-297: Argument parsing, config resolution, logging setup
  - Lines 299-633: Tool implementations (4 tools with comprehensive logging)
  - Lines 636-798: Helper functions (format, languages, execution with logging)
  - Line 799: Entry point

### Documentation
- **`README.md`** - User-facing documentation, installation, usage
- **`CLAUDE.md`** - AI assistant development guide (project instructions)
- **`CONFIGURATION.md`** - sgconfig.yaml configuration guide (350+ lines, created 2025-11-08)
- **`ast-grep.mdc`** - Comprehensive ast-grep rule documentation (for LLMs)
- **`dev/active/ast-grep-mcp-strategic-plan/phase1-session-notes.md`** - Phase 1 implementation notes

### Testing
- **`tests/test_unit.py`** (990 lines, 57 unit tests) - Unit tests with mocked subprocess calls
- **`tests/test_integration.py`** (5 integration tests) - Integration tests with real ast-grep execution
- **`tests/fixtures/`** - Test code samples and config files
  - Code samples: `example.py`, `example.js`, `sample.py`
  - Config samples: `valid_config.yaml`, `invalid_config_*.yaml`, `empty_config.yaml`
- **Coverage:** 96% (166 statements, 7 lines uncovered)

### Configuration
- **`pyproject.toml`** - Python project configuration
  - Dependencies: pydantic, mcp[cli], pyyaml, structlog
  - Dev dependencies: pytest, ruff, mypy, pytest-cov
  - Scripts: `ast-grep-server` entry point
  - Tool configs: pytest, coverage (96% target), ruff (line-length=140), mypy (strict=true)

### Other
- **`generate_mcp_docs.py`** - Script to generate MCP server documentation
- **`mcp-docs/`** - Documentation for 29 different MCP servers (reference material)
- **`renovate.json`** - Automated dependency updates configuration

---

## Critical Dependencies

### Runtime Dependencies
1. **ast-grep CLI** (external binary)
   - Purpose: Core structural code search engine
   - Installation: brew/nix/cargo/npm
   - Version compatibility: Monitor for breaking changes
   - Alternative: tree-sitter native integration (future consideration)

2. **FastMCP** (`mcp[cli]>=1.6.0`)
   - Purpose: MCP protocol implementation framework
   - Provides: `@mcp.tool()` decorator, stdio transport
   - Risk: Protocol changes may require adaptation

3. **Pydantic** (`>=2.11.0`)
   - Purpose: Data validation, `Field()` for tool parameters
   - Usage: Parameter descriptions, default values, type hints

4. **PyYAML** (`>=6.0.2`)
   - Purpose: Parse sgconfig.yaml for custom languages
   - Usage: Read custom language configurations

### Development Dependencies
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **ruff** - Linting and formatting
- **mypy** - Static type checking

### Build/Runtime Tools
- **uv** - Fast Python package manager
- **Python 3.13+** - Language runtime

---

## Configuration System

### Config Path Precedence
1. `--config` CLI flag (highest priority)
2. `AST_GREP_CONFIG` environment variable
3. None (ast-grep uses defaults)

### sgconfig.yaml Support
- **Purpose**: Customize ast-grep behavior (language mappings, rule directories)
- **Location**: User-specified via --config or env var
- **Usage**: Passed to ast-grep via `--config` flag
- **Validation**: Full Pydantic validation (structure, field types, extension format)
- **Custom Languages**: Parsed to extend `get_supported_languages()` output
- **Error Handling**: ConfigurationError with helpful messages and documentation links

### Global State
- **`CONFIG_PATH`**: Global variable set by `parse_args_and_get_config()`
- **Rationale**: Shared across all tool functions without passing as parameter
- **Risk**: Global state, but acceptable for single-server-instance design

---

## Data Flow

### Tool Invocation Flow
```
1. MCP Client sends tool request (JSON-RPC over stdio)
   ↓
2. FastMCP deserializes request, calls tool function
   ↓
3. Tool function prepares ast-grep command arguments
   ↓
4. run_ast_grep() adds --config if CONFIG_PATH set
   ↓
5. run_command() executes subprocess.run()
   ↓
6. ast-grep processes code, outputs JSON or text
   ↓
7. Tool function parses output, formats result
   ↓
8. FastMCP serializes response back to client
```

### Text Format Conversion
```
ast-grep JSON output:
{
  "file": "src/app.py",
  "range": {"start": {"line": 10}, "end": {"line": 15}},
  "text": "def example():\n    pass"
}
   ↓
Text format:
src/app.py:11-16
def example():
    pass
```

---

## Testing Strategy

### Unit Tests (`test_unit.py`)
- **Approach**: Mock subprocess calls, test logic in isolation
- **Coverage**: Tool parameter handling, output formatting, error cases
- **Mocking**: Patch `subprocess.run()` to return controlled responses
- **Fixtures**: Mock JSON responses from ast-grep

### Integration Tests (`test_integration.py`)
- **Approach**: Real ast-grep execution against test fixtures
- **Coverage**: End-to-end tool execution, real ast-grep output parsing
- **Fixtures**: `tests/fixtures/` contains sample code in various languages
- **Prerequisites**: Requires ast-grep CLI installed on test system

### Test Infrastructure
- **MockFastMCP Pattern**: Bypass decorator machinery to extract tool functions
- **Direct Function Testing**: Call tool functions directly without MCP protocol
- **Shared Setup**: `register_mcp_tools()` called in test setup to define tools

---

## Phase 1 Implementation (2025-11-08) - 100% COMPLETE ✅

### Production-Grade Quality Achieved

Phase 1 of the strategic plan focused on establishing production-grade quality standards. **All five tasks completed** in a single session, transforming the codebase from experimental MVP to production-ready quality.

### Completed Enhancements

**1. Custom Exception Hierarchy (Task 1)**
- Created 6 specific exception classes with helpful error messages
- AstGrepError (base), AstGrepNotFoundError, InvalidYAMLError, ConfigurationError, AstGrepExecutionError, NoMatchesError
- Each exception includes installation/resolution guidance
- All error handling migrated from generic exceptions

**2. Comprehensive Logging System (Task 2) - ✅ JUST COMPLETED**
- Structured JSON logging with structlog
- 4 log levels: DEBUG, INFO, WARNING, ERROR
- CLI flags: --log-level, --log-file
- Environment variables: LOG_LEVEL, LOG_FILE
- All 4 tools wrapped with timing and performance metrics
- Subprocess execution logging with sanitization
- Log events: tool_invoked, tool_completed, tool_failed, command_completed, etc.
- Total: +282 lines added to main.py

**3. Test Coverage Expansion (Task 3)**
- Increased coverage from 72% to 96% (target: 90%)
- Added 36 new test cases across 8 new test classes
- Created 7 test fixture files for edge case validation
- Total: 62 tests (unit + integration)

**4. Type Safety with Mypy Strict Mode (Task 4)**
- Enabled mypy strict mode in pyproject.toml
- Added comprehensive type hints throughout codebase
- Used cast() for dynamic JSON parsing
- Removed all type:ignore comments (except get_logger return type)

**5. Configuration Validation with Pydantic (Task 5)**
- Created Pydantic models: CustomLanguageConfig, AstGrepConfig
- Implemented validate_config_file() with comprehensive checks
- File existence, YAML parsing, structure validation, field validation
- Created CONFIGURATION.md documentation (350+ lines)
- Validation integrated into startup sequence

### Final Phase 1 Metrics
- **Test Coverage:** 96% (191 statements, 7 uncovered)
- **Tests:** 62 total (57 unit, 5 integration)
- **Code Quality:** mypy strict mode ✅, ruff linting ✅
- **Lines of Code:** 799 (main.py, +282 from Task 2), 990 (test_unit.py)
- **Documentation:** 6 comprehensive docs (README, CLAUDE with logging, CONFIGURATION, strategic plan, session notes, task checklist)
- **Dependencies:** pydantic, mcp[cli], pyyaml, structlog

### Technical Debt Addressed
- ✅ Generic error messages → Specific, helpful exceptions
- ✅ Minimal test coverage → Comprehensive 96% coverage
- ✅ No type hints → Full mypy strict mode compliance
- ✅ No config validation → Pydantic models with validators
- ✅ No structured logging → structlog with JSON output and performance metrics

### Files Created in Phase 1
- `CONFIGURATION.md` - Configuration guide
- `tests/fixtures/valid_config.yaml` - Valid config example
- `tests/fixtures/invalid_config_*.yaml` - Invalid config examples
- `dev/active/ast-grep-mcp-strategic-plan/phase1-session-notes.md` - Implementation notes

### See Also
- **Phase 1 Session Notes:** `dev/active/ast-grep-mcp-strategic-plan/phase1-session-notes.md`
- **Strategic Plan:** `dev/active/ast-grep-mcp-strategic-plan/ast-grep-mcp-strategic-plan.md`
- **Task Breakdown:** `dev/active/ast-grep-mcp-strategic-plan/ast-grep-mcp-tasks.md`

---

## Known Issues and Limitations

### Current Limitations
1. **No Progress Indication**: Long searches provide no feedback
2. **No Result Streaming**: Wait for all results before returning
3. **No Caching**: Identical queries re-execute every time
4. **Limited Error Context**: Generic error messages, minimal debugging info
5. **No Rewrite Support**: Read-only operations, can't apply ast-grep fixes
6. **Blocking Execution**: Single-threaded, no parallelization
7. **Memory Constraints**: Large result sets load entirely into memory

### Known Bugs/Quirks
1. **"No matches" Error in test_match_code_rule**: Suggests `stopBy: end` for relational rules
   - Location: main.py:97
   - Rationale: Common gotcha with ast-grep's traversal behavior

2. **Windows Shell Requirement**: ast-grep needs `shell=True` when installed via npm
   - Location: main.py:282
   - Rationale: npm creates batch file wrapper, not executable

3. **Line Number Off-by-One**: ast-grep returns 0-indexed lines, display as 1-indexed
   - Location: main.py:241-242
   - Handles: Conversion for user-friendly output

---

## Common Development Patterns

### Adding a New Tool
```python
@mcp.tool()
def new_tool(
    param: str = Field(description="Parameter description"),
) -> str:
    """Tool description for AI assistant."""
    # Prepare ast-grep args
    args = ["--option", param]

    # Execute
    result = run_ast_grep("command", args)

    # Process and return
    return result.stdout.strip()
```

### Error Handling Pattern
```python
try:
    result = run_ast_grep("scan", args)
except RuntimeError as e:
    # User-friendly error message
    raise ValueError(f"Search failed: {e}")
```

### Output Format Selection
```python
if output_format == "text":
    text_output = format_matches_as_text(matches)
    return header + ":\n\n" + text_output
return matches  # JSON
```

---

## Performance Considerations

### Current Performance Characteristics
- **Small codebases (<1K files)**: <1s response time
- **Medium codebases (1K-10K files)**: 1-5s response time
- **Large codebases (>10K files)**: 5-30s response time (varies by query complexity)

### Bottlenecks
1. **ast-grep Execution**: Subprocess overhead, file I/O
2. **JSON Parsing**: Large result sets require full parsing
3. **No Caching**: Repeated queries re-execute
4. **Single-threaded**: No parallel file processing

### Optimization Opportunities (Future)
- Implement result streaming (don't wait for completion)
- Add LRU cache for frequent queries
- Parallel execution for multi-file searches
- Memory-mapped file handling for large files

---

## Security Considerations

### Current Security Posture
- **Input Validation**: Minimal (relies on ast-grep for YAML validation)
- **Path Traversal**: No explicit protection (relies on ast-grep)
- **Code Injection**: YAML passed to ast-grep could contain shell commands (if ast-grep vulnerable)
- **Resource Limits**: None (queries can consume arbitrary CPU/memory)

### Security Recommendations (Future)
1. Validate all file paths (no `../`, must be within allowed directories)
2. Validate YAML structure before passing to ast-grep
3. Implement timeout limits for long-running queries
4. Add memory limits to prevent OOM
5. Sanitize user input (patterns, file paths)
6. Consider sandboxing ast-grep execution

---

## Development Workflow

### Local Development
```bash
# Setup
uv sync --extra dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing

# Lint
uv run ruff check .
uv run ruff check --fix .

# Type check
uv run mypy main.py

# Run server
uv run main.py --config /path/to/sgconfig.yaml
```

### Testing Workflow
1. Write test case in `test_unit.py` or `test_integration.py`
2. Run specific test: `uv run pytest tests/test_unit.py::test_name -v`
3. Verify coverage: `uv run pytest --cov=main --cov-report=html`
4. Review coverage report in `htmlcov/index.html`

### Debugging
- **Print debugging**: Add print statements (output goes to stderr in MCP context)
- **pytest -s flag**: See print output during tests
- **ast-grep --debug-query**: Use directly to debug AST patterns
- **Mock testing**: Test tool functions directly without MCP protocol

---

## Integration Points

### MCP Client Configuration
**Cursor** (`.cursor-mcp/settings.json`):
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {}
    }
  }
}
```

**Claude Desktop** (similar configuration)

### ast-grep Integration
- **Commands Used**: `ast-grep run`, `ast-grep scan`
- **Flags**: `--pattern`, `--lang`, `--debug-query`, `--json`, `--stdin`, `--inline-rules`, `--config`
- **Input**: Code via stdin for testing, file paths for scanning
- **Output**: JSON for parsing, stderr for debug queries

---

## Future Architecture Considerations

### Potential Refactoring (when >500 lines)
```
ast_grep_mcp/
  __init__.py
  server.py         # FastMCP initialization
  tools.py          # Tool implementations
  executor.py       # ast-grep subprocess handling
  cache.py          # Query result caching
  formatter.py      # Output formatting (text/JSON)
  config.py         # Configuration management
  types.py          # Pydantic models, type definitions
```

### Extension Points
- **Custom Formatters**: Plugin system for output formats
- **Result Processors**: Post-processing hooks (filtering, sorting, grouping)
- **Cache Backends**: Redis, file-based, in-memory
- **Observability**: Pluggable logging, metrics, tracing

---

## Resources and References

### Official Documentation
- **ast-grep**: https://ast-grep.github.io/
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/pydantic/fastmcp
- **MCP Server Registry**: https://github.com/modelcontextprotocol/servers

### Key ast-grep Concepts
- **Pattern Syntax**: AST-based search patterns with metavariables ($VAR)
- **YAML Rules**: Complex multi-condition searches (all/any/not, relational rules)
- **Relational Rules**: inside, has, precedes, follows (with stopBy)
- **Custom Languages**: tree-sitter grammar integration

### Development Resources
- **Python Type Hints**: https://docs.python.org/3/library/typing.html
- **Pydantic**: https://docs.pydantic.dev/
- **pytest**: https://docs.pytest.org/
- **ruff**: https://docs.astral.sh/ruff/

---

## Glossary

- **MCP (Model Context Protocol)**: Protocol for AI assistants to access tools and resources
- **FastMCP**: Python framework for building MCP servers
- **ast-grep**: CLI tool for structural code search using AST pattern matching
- **AST (Abstract Syntax Tree)**: Tree representation of code structure
- **CST (Concrete Syntax Tree)**: Tree including all syntax tokens (whitespace, comments)
- **Pattern**: Simple ast-grep search expression with metavariables
- **YAML Rule**: Complex search configuration with multiple conditions
- **Relational Rule**: Rule matching code based on structural relationships (inside, has, etc.)
- **stopBy**: ast-grep directive to limit traversal depth in relational rules
- **sgconfig.yaml**: ast-grep configuration file for custom languages and settings

---

## Decision Log

### ADR-001: Single-File Architecture
**Date:** Initial implementation
**Decision:** Keep entire server in main.py (~317 lines)
**Rationale:** Simplicity, portability, easy maintenance for experimental project
**Consequences:** May need refactoring if complexity grows beyond ~500 lines

### ADR-002: Text Output Format as Default
**Date:** Initial implementation
**Decision:** Default to text format (~75% fewer tokens than JSON)
**Rationale:** Optimize for LLM token consumption, most users don't need metadata
**Consequences:** Users must explicitly request JSON for full match details

### ADR-003: Global CONFIG_PATH Variable
**Date:** Initial implementation
**Decision:** Use global variable instead of passing config through tool signatures
**Rationale:** Simplifies tool function signatures, config is server-wide setting
**Consequences:** Global state, but acceptable for single-server-instance design

### ADR-004: Dynamic Tool Registration
**Date:** Initial implementation
**Decision:** Register tools via function after config parsing
**Rationale:** Tools need access to CONFIG_PATH, which is set at startup
**Consequences:** Nested functions, slight complexity in tool definition

### ADR-005: Subprocess Execution for ast-grep
**Date:** Initial implementation
**Decision:** Shell out to ast-grep CLI instead of native tree-sitter integration
**Rationale:** Leverage ast-grep's battle-tested implementation, avoid reimplementation
**Consequences:** Dependency on external binary, subprocess overhead
**Future Consideration:** Native tree-sitter integration for performance

---

## Contact and Ownership

**Maintainer:** TBD (check repository)
**Repository:** https://github.com/ast-grep/ast-grep-mcp
**Issues:** https://github.com/ast-grep/ast-grep-mcp/issues
**Discussions:** https://github.com/ast-grep/ast-grep-mcp/discussions

---

*This context document provides the foundational knowledge needed to understand, maintain, and extend the ast-grep MCP server. It should be updated as the project evolves.*
