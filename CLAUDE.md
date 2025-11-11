# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes ast-grep's structural code search capabilities to AI assistants. It wraps the `ast-grep` CLI tool and provides five main MCP tools:

1. **`dump_syntax_tree`**: Visualize AST structure of code snippets for pattern development
2. **`test_match_code_rule`**: Test YAML rules against code before applying to larger codebases
3. **`find_code`**: Search using simple patterns for straightforward structural matches
4. **`find_code_by_rule`**: Advanced search using complex YAML rules with relational constraints
5. **`find_duplication`**: Detect duplicate code and suggest modularization based on DRY principles

**External dependency**: Requires `ast-grep` CLI to be installed and available in PATH. The server shells out to `ast-grep` via subprocess calls.

## Prerequisites

1. **ast-grep**: Install via [ast-grep installation guide](https://ast-grep.github.io/guide/quick-start.html#installation)
   ```bash
   # macOS
   brew install ast-grep
   # or via cargo
   cargo install ast-grep --locked
   ```
   Verify installation: `ast-grep --version`

2. **uv**: Python package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Python 3.13+**: Required by the project

## MCP Client Configuration

### Cursor
Add to your MCP settings (usually in `.cursor-mcp/settings.json`):
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

### Claude Desktop
Add to your Claude Desktop MCP configuration:
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

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_unit.py          # 57 unit tests
uv run pytest tests/test_integration.py   # 5 integration tests
uv run pytest tests/test_cache.py         # 15 cache tests
uv run pytest tests/test_duplication.py   # 24 duplication detection tests

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing
```

### Linting and Type Checking
```bash
# Run ruff linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Run mypy type checker
uv run mypy main.py
```

### Running the Server
```bash
# Run directly
uv run main.py

# Run with config file
uv run main.py --config /path/to/sgconfig.yaml

# Run with logging options
uv run main.py --log-level DEBUG --log-file /tmp/ast-grep-mcp.log

# Run with caching options
uv run main.py --cache-size 200 --cache-ttl 600

# Run via installed script name
uv run ast-grep-server

# Run directly from GitHub using uvx (no clone required)
uvx --from git+https://github.com/ast-grep/ast-grep-mcp ast-grep-server
```

### Command-Line Scripts

The `scripts/` directory contains standalone utilities for running MCP tools from the command line:

**Find Duplication (Python)**:
```bash
# Analyze Python functions (excludes library code by default)
uv run python scripts/find_duplication.py /path/to/project --language python

# Analyze JavaScript classes with strict similarity
uv run python scripts/find_duplication.py /path/to/project --language javascript \
    --construct-type class_definition --min-similarity 0.9

# Customize exclusion patterns (or disable with empty list)
uv run python scripts/find_duplication.py /path/to/project --language python \
    --exclude-patterns site-packages build dist

# Output as JSON
uv run python scripts/find_duplication.py /path/to/project --language python --json
```

**Find Duplication (Bash wrapper)**:
```bash
# Simple interface with positional arguments (uses default exclusions)
./scripts/find_duplication.sh /path/to/project python
./scripts/find_duplication.sh /path/to/project javascript class_definition 0.9
```

**Default Exclusions**: By default, the tool excludes library code from analysis:
`site-packages`, `node_modules`, `.venv`, `venv`, `vendor`

See `scripts/README.md` for full documentation.

### Logging System

The server uses **structlog** for structured JSON logging. All logs are written to stderr by default, but can be redirected to a file.

**Configuration Options:**
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO
- `--log-file`: Path to log file. Default: stderr
- `LOG_LEVEL` env var: Alternative to --log-level flag
- `LOG_FILE` env var: Alternative to --log-file flag

**Log Format:**
All logs are JSON formatted with the following fields:
- `timestamp`: ISO 8601 timestamp (UTC)
- `level`: Log level (debug, info, warning, error)
- `event`: Event type (e.g., "tool_invoked", "command_completed", "tool_failed")
- Additional context fields specific to each event

**Examples:**
```bash
# Enable debug logging to stderr
uv run main.py --log-level DEBUG

# Log to file with INFO level
uv run main.py --log-file /var/log/ast-grep-mcp.log

# Use environment variables
export LOG_LEVEL=DEBUG
export LOG_FILE=/tmp/ast-grep.log
uv run main.py
```

**Log Events:**
- `tool_invoked`: Tool called with parameters (sanitized)
- `tool_completed`: Tool finished successfully with metrics
- `tool_failed`: Tool execution failed with error details
- `executing_command`: Subprocess command starting
- `command_completed`: Subprocess command finished with timing
- `command_failed`: Subprocess command failed with error
- `command_not_found`: Subprocess binary not found
- `stream_started`: Streaming search initiated with parameters
- `stream_progress`: Progress update during streaming (every N matches)
- `stream_early_termination`: Subprocess terminated after reaching max_results
- `stream_completed`: Streaming search finished with final metrics
- `stream_failed`: Streaming search failed with error details
- `stream_json_parse_error`: Invalid JSON line encountered during streaming

**Performance Metrics:**
All tool invocations and subprocess executions log:
- `execution_time_seconds`: Duration in seconds (rounded to 3 decimals)
- `match_count` / `total_matches`: Number of results found (for search tools)
- `output_length`: Size of output (for dump_syntax_tree)

### Query Result Caching

The server implements an LRU cache with TTL expiration for `find_code` and `find_code_by_rule` query results. Caching avoids redundant ast-grep executions for identical queries, significantly improving response times for repeated searches.

**Configuration Options:**
- `--no-cache`: Disable result caching entirely
- `--cache-size N`: Maximum number of cached entries (default: 100)
- `--cache-ttl SECONDS`: Time-to-live for cache entries in seconds (default: 300)
- `CACHE_DISABLED` env var: Set to any value to disable caching
- `CACHE_SIZE` env var: Alternative to --cache-size flag
- `CACHE_TTL` env var: Alternative to --cache-ttl flag

**Examples:**
```bash
# Run with default caching (100 entries, 300s TTL)
uv run main.py

# Disable caching
uv run main.py --no-cache

# Custom cache size and TTL
uv run main.py --cache-size 200 --cache-ttl 600

# Use environment variables
export CACHE_SIZE=50
export CACHE_TTL=120
uv run main.py
```

**Cache Behavior:**
- Cache keys include: command type (run/scan), all arguments (sorted), and project folder path
- Cache entries expire after TTL seconds (default 300)
- LRU eviction removes oldest entries when cache is full
- Both `text` and `json` output formats use the same cached query results
- Cache statistics are tracked: hits, misses, hit rate, current size

**Cache Log Events:**
- `cache_initialized`: Cache startup with configuration
- `cache_hit`: Query result served from cache
- `cache_miss`: Query not in cache, executing ast-grep
- `cache_stored`: Query result stored in cache after execution

**Implementation Details:**
- Cache class: `QueryCache` (OrderedDict-based LRU with TTL)
- Cache keys: SHA256 hash (first 16 chars) of command + args + project
- Cache storage: Results stored with timestamp for TTL checking
- Thread safety: Not implemented (single-threaded MCP server)

## Architecture

### Single-file Design
The entire MCP server is implemented in `main.py` (~1578 lines). This is intentional for simplicity and portability. The file includes comprehensive logging (~282 lines), streaming result parsing (~156 lines), query result caching (~117 lines), and duplication detection (~382 lines).

### Core Components

**Tool Registration Pattern**: Tools are registered dynamically via `register_mcp_tools()` which is called at startup. This function uses the FastMCP decorator pattern to register the five main tools. Tools are defined as nested functions inside `register_mcp_tools()` to access the global `CONFIG_PATH` variable set during argument parsing.

**Config Path Resolution**: The server supports custom `sgconfig.yaml` via `--config` flag or `AST_GREP_CONFIG` env var. The global `CONFIG_PATH` variable is set by `parse_args_and_get_config()` before tool registration, allowing tools to pass `--config` to ast-grep commands when needed.

**Subprocess Execution Flow**: Tools use two execution paths:
- **Non-streaming** (dump_syntax_tree, test_match_code_rule): `run_ast_grep()` → `run_command()` → `subprocess.run()`
- **Streaming** (find_code, find_code_by_rule): `stream_ast_grep_results()` → `subprocess.Popen()`

Error handling converts `CalledProcessError` and `FileNotFoundError` into user-friendly `RuntimeError` messages.

**Output Format Optimization**: `find_code` and `find_code_by_rule` support two output modes:
- `text` (default): ~75% fewer tokens, formatted as `file:line-range` headers with match text
- `json`: Full metadata including ranges and meta-variables

Both modes internally use JSON from ast-grep for accurate result limiting, then convert to text if requested.

**Streaming Architecture**: `find_code` and `find_code_by_rule` use streaming result parsing via `stream_ast_grep_results()` (main.py:783-937). This function:
- Uses `subprocess.Popen` with `--json=stream` flag to process JSON Lines output
- Parses results line-by-line as they arrive from ast-grep
- Supports early termination: kills the subprocess when `max_results` is reached
- Provides progress logging every N matches (default: 100)
- Performs graceful subprocess cleanup (SIGTERM, then SIGKILL if needed)

The streaming layer sits between the MCP tools and the subprocess execution layer, replacing the traditional `run_ast_grep()` call for search operations. This provides significant performance benefits when searching large codebases with result limits, as ast-grep can be terminated as soon as enough matches are found rather than scanning the entire project.

**Duplication Detection**: The `find_duplication` tool (main.py:880-1077) detects duplicate code and suggests refactoring opportunities based on DRY principles. The detection process:
1. Uses ast-grep streaming to find all instances of a construct type (functions, classes, methods)
2. Normalizes code for comparison (removes whitespace, comments)
3. Calculates pairwise similarity using difflib's SequenceMatcher
4. Groups similar code blocks into duplication clusters (configurable threshold)
5. Generates refactoring suggestions for each cluster

Key algorithms:
- `normalize_code()`: Removes whitespace/comments for fair comparison
- `calculate_similarity()`: Returns 0-1 similarity ratio using SequenceMatcher
- `group_duplicates()`: Clusters similar code with configurable min_similarity and min_lines
- `generate_refactoring_suggestions()`: Creates actionable refactoring advice

The tool returns a structured report with:
- Summary statistics (total constructs, duplicate groups, potential line savings)
- Detailed duplication groups with similarity scores and file locations
- Specific refactoring suggestions (extract function, base class, etc.)

**Usage Example:**
```python
# Find duplicate functions in a Python project
result = find_duplication(
    project_folder="/path/to/project",
    language="python",
    construct_type="function_definition",
    min_similarity=0.8,  # 80% similarity threshold
    min_lines=5          # Ignore functions < 5 lines
)

# Result includes:
# - summary.total_constructs: Total functions found
# - summary.duplicate_groups: Number of duplication clusters
# - summary.potential_line_savings: Lines that could be saved
# - duplication_groups: Details of each cluster
# - refactoring_suggestions: Actionable advice for each cluster
```

### Testing Architecture

Tests use a `MockFastMCP` class to bypass FastMCP's decorator machinery and extract registered tool functions for direct testing. The pattern:
1. Patch `FastMCP` and `pydantic.Field` before importing
2. Import main.py with mocked decorators
3. Call `register_mcp_tools()` to populate `main.mcp.tools` dict
4. Extract tool functions from the dict for testing

Unit tests (`test_unit.py`) mock subprocess calls. Integration tests (`test_integration.py`) run against real fixtures in `tests/fixtures/`.

### Language Support

The `get_supported_languages()` function returns a hardcoded list of ast-grep's built-in languages PLUS any custom languages defined in the `sgconfig.yaml` file (if provided). This list is used in tool parameter descriptions.

## Development Notes

### Windows Compatibility
`run_command()` sets `shell=True` on Windows when calling `ast-grep` because npm-installed ast-grep is a batch file that requires shell execution.

### Config Path Precedence
1. `--config` CLI flag (highest)
2. `AST_GREP_CONFIG` environment variable
3. None (ast-grep uses its defaults)

### Performance Patterns

**Streaming Benefits**: The streaming architecture (main.py:783-937) provides significant performance advantages:
- **Large codebases**: Reduces memory usage by processing results incrementally rather than loading all matches into memory
- **Result limits**: When `max_results` is set, ast-grep is terminated early via SIGTERM, saving CPU and I/O by not scanning the entire project
- **Progress visibility**: Progress logs (every 100 matches by default) help debug long-running searches and provide feedback during development

**Early Termination**: When a search reaches `max_results`, the streaming layer:
1. Stops reading from the subprocess stdout
2. Sends SIGTERM to ast-grep process
3. Waits up to 2 seconds for graceful shutdown
4. Sends SIGKILL if process doesn't terminate
5. Logs `stream_early_termination` event with timing metrics

This can result in substantial time savings on large projects. For example, finding the first 10 matches in a 100,000-file codebase might complete in seconds rather than minutes.

### Common ast-grep Patterns
When testing rules, if no matches are found, the error message suggests adding `stopBy: end` to relational rules (inside/has). This is a common gotcha with ast-grep's traversal behavior.

### Text Format Design
The text output format was designed to minimize token usage for LLMs while maintaining context. Format: `filepath:startline-endline` header followed by complete match text, with matches separated by blank lines.
