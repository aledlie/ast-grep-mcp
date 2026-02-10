# ast-grep MCP Server

A powerful Model Context Protocol (MCP) server providing structural code search, refactoring, and quality analysis using [ast-grep](https://ast-grep.github.io/).

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package%20manager-green.svg)](https://github.com/astral-sh/uv)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)

## Features

### Code Search & Analysis
- **Pattern-based search** - Find code using ast-grep patterns
- **Rule-based search** - YAML rule definitions for complex queries
- **AST visualization** - Dump syntax trees for any code snippet
- **Complexity analysis** - Cyclomatic, cognitive, nesting metrics
- **Code smell detection** - Long functions, parameter bloat, magic numbers

### Code Transformation
- **Safe rewrites** - Pattern-based code transformations
- **Automatic backups** - Rollback support for all changes
- **Syntax validation** - Prevent syntax errors
- **Dry-run mode** - Preview changes before applying

### Refactoring Assistants
- **Extract function** - Extract code into reusable functions with parameter detection
- **Rename symbol** - Scope-aware renaming with conflict detection
- **Multi-file updates** - Atomic changes across multiple files
- **Import management** - Automatic import/export updates
- **Dry-run mode** - Preview all changes before applying

### Deduplication & Refactoring
- **Duplicate detection** - Find copy-pasted code across projects
- **Intelligent ranking** - Score duplicates by refactoring value
- **Automated refactoring** - Extract functions/classes with one command
- **Impact analysis** - Test coverage + breaking change detection
- **Performance benchmarking** - Track deduplication performance

### Code Quality
- **Linting rules** - 24+ pre-built templates (security, performance, style)
- **Custom rules** - Create project-specific linting rules
- **Pattern validation** - Test rules against code examples
- **Standards enforcement** - Consistent code quality across teams

### Documentation Generation
- **Docstring generation** - Google, NumPy, Sphinx, JSDoc, Javadoc styles
- **README sections** - Automated project analysis and section generation
- **API docs** - OpenAPI 3.0 spec generation
- **Changelog generation** - Keep a Changelog and Conventional formats
- **Doc sync** - Detect stale documentation and broken links

### Cross-Language Operations
- **Multi-language search** - Search across multiple languages simultaneously
- **Language equivalents** - Find equivalent patterns across languages
- **Code conversion** - Convert code patterns between languages
- **Polyglot refactoring** - Refactor across language boundaries
- **Language bindings** - Generate bindings between languages

### Schema.org Integration
- **Type search** - Find Schema.org types by name
- **Property listing** - Get all properties for a type
- **Validation** - Validate JSON-LD structured data
- **Template generation** - Generate Schema.org templates
- **Type comparison** - Compare multiple types
- **Entity graph enhancement** - Analyze and improve JSON-LD graphs

## Architecture

**Modular design** with 64 modules organized for clarity and maintainability:

```
src/ast_grep_mcp/
├── core/           # Core infrastructure (config, cache, executor, logging, sentry)
├── models/         # Data models (refactoring, deduplication, complexity, standards)
├── utils/          # Utilities (templates, formatters, text processing, validation)
├── features/       # Feature modules
│   ├── search/         # Code search (9 tools)
│   ├── rewrite/        # Code transformation (3 tools)
│   ├── refactoring/    # Refactoring assistants (2 tools)
│   ├── schema/         # Schema.org integration (9 tools)
│   ├── deduplication/  # Duplicate detection & refactoring (4 tools)
│   ├── complexity/     # Complexity analysis (3 tools)
│   ├── quality/        # Code quality & linting (7 tools)
│   ├── documentation/  # Documentation generation (5 tools)
│   └── cross_language/ # Cross-language operations (5 tools)
└── server/         # MCP server (registry, runner)
```

**47 MCP Tools (100% Registered):**
- Search: 9 tools (find_code, find_code_by_rule, dump_ast, debug_pattern, get_ast_grep_docs, build_rule, get_pattern_examples, develop_pattern, find_code_by_rule_yaml)
- Rewrite: 3 tools
- Refactoring: 2 tools (extract_function, rename_symbol)
- Schema.org: 9 tools (includes entity graph enhancement)
- Deduplication: 4 tools
- Complexity: 3 tools (includes code smells)
- Quality: 7 tools (linting, security scanner, auto-fix, quality reports)
- Documentation: 5 tools (docstrings, readme, api_docs, changelog, sync)
- Cross-Language: 5 tools (multi-language search, equivalents, conversion, polyglot refactoring, bindings)

## Quick Start

### Prerequisites

- **Python 3.13+** - Latest Python version
- **uv** - Fast Python package manager ([install](https://github.com/astral-sh/uv))
- **ast-grep** - Structural code search tool ([install](https://ast-grep.github.io/guide/quick-start.html))

```bash
# Install ast-grep
cargo install ast-grep

# Or use homebrew (macOS)
brew install ast-grep

# Or use npm
npm install -g @ast-grep/cli
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/ast-grep-mcp.git
cd ast-grep-mcp

# Install dependencies
uv sync

# Verify installation
uv run pytest
```

### Running the Server

**Local development:**
```bash
uv run main.py
```

**With Doppler secrets (recommended for production):**
```bash
doppler run -- uv run main.py
```

### MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

**With Doppler:**
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "bottleneck",
        "--config", "dev",
        "--command",
        "uv --directory /absolute/path/to/ast-grep-mcp run main.py"
      ]
    }
  }
}
```

**Without Doppler:**
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {}
    }
  }
}
```

## Usage Examples

### Code Search

```python
# Find all console.log statements
find_code(
    pattern="console.log($$$)",
    project_folder="/path/to/project",
    language="typescript"
)

# Search with YAML rule
find_code_by_rule(
    rule_yaml="""
    rule:
      pattern: $FUNC($$$)
      constraints:
        FUNC:
          regex: ^(eval|exec)$
    """,
    project_folder="/path/to/project",
    language="python"
)
```

### Code Transformation

```python
# Preview changes (dry run)
rewrite_code(
    pattern="var $VAR = $VALUE",
    replacement="const $VAR = $VALUE",
    project_folder="/path/to/project",
    language="javascript",
    dry_run=True
)

# Apply changes with automatic backup
rewrite_code(
    pattern="var $VAR = $VALUE",
    replacement="const $VAR = $VALUE",
    project_folder="/path/to/project",
    language="javascript",
    dry_run=False
)

# Rollback if needed
rollback_rewrite(backup_id="backup-20251124-103045")
```

### Deduplication

```python
# Find duplicates
duplicates = find_duplication(
    project_folder="/path/to/project",
    language="python",
    min_lines=5
)

# Get ranked candidates
candidates = analyze_deduplication_candidates(
    project_path="/path/to/project",
    language="python",
    max_candidates=10
)

# Apply refactoring
apply_deduplication(
    candidate_id="dup-001",
    refactoring_strategy="extract_function",
    dry_run=True  # Preview first
)
```

### Complexity Analysis

```python
# Analyze complexity
analyze_complexity(
    project_folder="/path/to/project",
    language="python",
    cyclomatic_threshold=10,
    cognitive_threshold=15,
    store_results=True  # Save to SQLite for trends
)
```

### Code Quality

```python
# Detect code smells
detect_code_smells(
    project_folder="/path/to/project",
    language="python",
    severity_filter="high"
)

# Create custom linting rule
create_linting_rule(
    rule_name="no-console-log",
    pattern="console.log($$$)",
    severity="warning",
    language="typescript",
    save_to_project=True
)

# Use pre-built template
create_linting_rule(
    rule_name="no-bare-except",
    use_template="no-bare-except",
    save_to_project=True
)
```

## Configuration

### Environment Variables

```bash
# Optional Sentry error tracking
export SENTRY_DSN="your-dsn"
export SENTRY_ENVIRONMENT="production"

# Optional ast-grep config file
export AST_GREP_CONFIG="/path/to/config.yml"

# Debug logging
export DEBUG=1
```

### Doppler Integration

Recommended for production deployments:

```bash
# Install Doppler CLI
brew install dopplerhq/cli/doppler

# Login
doppler login

# Configure project
doppler setup --project bottleneck --config dev

# Run server
doppler run -- uv run main.py
```

See [docs/DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md) for details.

### Sentry Integration

Optional error tracking and performance monitoring:

```bash
# Set via Doppler
doppler secrets set SENTRY_DSN="your-dsn" --project bottleneck --config dev

# Or set manually
export SENTRY_DSN="your-dsn"
export SENTRY_ENVIRONMENT="production"
```

See [docs/SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) for details.

## Development

### Running Tests

```bash
# All tests (1,600+)
uv run pytest

# Specific test file
uv run pytest tests/unit/test_search.py -v

# With coverage
uv run pytest --cov=src/ast_grep_mcp --cov-report=html

# Integration tests (requires ast-grep binary)
uv run pytest tests/integration/
```

### Linting & Type Checking

```bash
# Lint with ruff
uv run ruff check .

# Type check with mypy
uv run mypy src/

# Format code
uv run ruff format .
```

### Module Structure

See [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md) for comprehensive module documentation.

**Core modules:**
- `core/config.py` - Configuration management
- `core/cache.py` - LRU + TTL caching
- `core/executor.py` - ast-grep subprocess execution
- `core/logging.py` - Structured logging (structlog)
- `core/sentry.py` - Error tracking (optional)

**Feature modules:**
- `features/search/` - Code search tools (9)
- `features/rewrite/` - Code transformation tools (3)
- `features/refactoring/` - Extract function, rename symbol (2)
- `features/schema/` - Schema.org integration (9)
- `features/deduplication/` - Duplicate detection & refactoring (4)
- `features/complexity/` - Complexity analysis (3)
- `features/quality/` - Code quality & linting (7)
- `features/documentation/` - Documentation generation (5)
- `features/cross_language/` - Cross-language operations (5)

### Adding New Features

1. Create feature directory: `src/ast_grep_mcp/features/new_feature/`
2. Add service implementation: `service.py`
3. Add MCP tool wrappers: `tools.py`
4. Register tools in `server/registry.py`
5. Add tests in `tests/unit/test_new_feature.py`

See [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md) for patterns and examples.

## Documentation

### User Guides
- [CLAUDE.md](CLAUDE.md) - Complete user guide (for Claude Code)
- [DEDUPLICATION-GUIDE.md](DEDUPLICATION-GUIDE.md) - Deduplication feature guide
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Configuration options
- [docs/BENCHMARKING.md](docs/BENCHMARKING.md) - Performance benchmarking

### Architecture
- [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md) - Module architecture & patterns
- [docs/MIGRATION-FROM-MONOLITH.md](docs/MIGRATION-FROM-MONOLITH.md) - Refactoring history
- [REMAINING-TASKS-SUMMARY.md](REMAINING-TASKS-SUMMARY.md) - Project status

### Infrastructure
- [docs/SENTRY-INTEGRATION.md](docs/SENTRY-INTEGRATION.md) - Error tracking setup
- [docs/DOPPLER-MIGRATION.md](docs/DOPPLER-MIGRATION.md) - Secret management

## Performance

### Benchmarks

**Search performance:**
- Small project (<1000 files): <1s
- Medium project (1000-10000 files): 1-5s
- Large project (>10000 files): 5-30s

**Deduplication performance:**
- Hash-based bucketing: 83% reduction in comparisons
- 1000 functions analyzed: <10s
- Parallel processing: 50-70% speedup

**Caching:**
- LRU + TTL cache for search results
- ~75% token reduction with text format vs JSON
- Cache hit rate: 60-80% for repeated queries

### Optimization Tips

1. **Use text format** for search results (75% fewer tokens)
2. **Enable parallel processing** (`--threads N`)
3. **Use max_results** to limit output size
4. **Cache frequently used queries** (automatic)
5. **Filter by language** for faster pattern matching

## Troubleshooting

### ast-grep not found

```bash
# Verify installation
ast-grep --version

# Install if missing
cargo install ast-grep

# Or use homebrew
brew install ast-grep
```

### Tests failing

```bash
# Clear coverage artifacts
rm -rf .coverage htmlcov/

# Ensure ast-grep is installed
ast-grep --version

# Run with verbose output
uv run pytest -v
```

### Sentry not working

```bash
# Verify DSN is set
echo $SENTRY_DSN

# Test integration
uv run python -c "from ast_grep_mcp.core.sentry import init_sentry; init_sentry()"
```

### Import errors

If you see import errors:

1. Use modular imports from `ast_grep_mcp.*` (see [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md))
2. Run `uv sync` to update dependencies
3. `main.py` is now only an entry point - all functionality is in the modular architecture

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Follow module structure** (see [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md))
4. **Add tests** for new features
5. **Update documentation** as needed
6. **Run linting** (`uv run ruff check .`)
7. **Run tests** (`uv run pytest`)
8. **Commit changes** with clear messages
9. **Push to branch** (`git push origin feature/amazing-feature`)
10. **Open Pull Request**

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings to public APIs
- Use structured logging (`get_logger(__name__)`)
- Handle errors appropriately (see [docs/MODULE-GUIDE.md](docs/MODULE-GUIDE.md))

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ast-grep](https://ast-grep.github.io/) - Structural code search engine
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) - Python MCP framework
- [Schema.org](https://schema.org/) - Structured data vocabulary

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/ast-grep-mcp/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/ast-grep-mcp/discussions)
- **Documentation:** See [docs/](docs/) directory

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### 2026-02-10: Test Stability & Documentation Improvements

- Added `develop_pattern` tool for iterative pattern development
- Added `matches` rule, pattern objects, lazy metavariables to search docs
- Comprehensive deduplication test coverage across all submodules
- Fixed integration tests, benchmark thresholds, and dev dependencies
- **47 MCP tools total**

### 2026-01-10: Documentation & Rule Builder Tools

- Added `get_ast_grep_docs`, `build_rule`, `get_pattern_examples` tools
- Automatic warning detection for YAML rules (missing stopBy, lowercase metavariables)

### 2026-01-09: Pattern Debugging Tool

- Added `debug_pattern` tool for diagnosing pattern matching issues
- Validates metavariable syntax and compares AST structures

### 2025-11-29: Documentation Generation & Entity Graph Enhancement

- 5 documentation generation tools (docstrings, readme, api_docs, changelog, sync)
- `enhance_entity_graph` tool for Schema.org JSON-LD analysis
- 5 cross-language operation tools

### 2025-11-24: Modular Architecture (v2.0)

- Migrated to 64-module architecture
- 1,600+ tests passing
- Zero complexity violations

---

**Built with ❤️ using ast-grep and MCP**
