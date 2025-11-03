# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that exposes ast-grep's structural code search capabilities to AI assistants. It wraps the `ast-grep` CLI tool and provides four main MCP tools: `dump_syntax_tree`, `test_match_code_rule`, `find_code`, and `find_code_by_rule`.

**External dependency**: Requires `ast-grep` CLI to be installed and available in PATH. The server shells out to `ast-grep` via subprocess calls.

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
uv run pytest tests/test_unit.py
uv run pytest tests/test_integration.py

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

# Run via installed script name
uv run ast-grep-server
```

## Architecture

### Single-file Design
The entire MCP server is implemented in `main.py` (~317 lines). This is intentional for simplicity and portability.

### Core Components

**Tool Registration Pattern**: Tools are registered dynamically via `register_mcp_tools()` which is called at startup. This function uses the FastMCP decorator pattern to register the four main tools. Tools are defined as nested functions inside `register_mcp_tools()` to access the global `CONFIG_PATH` variable set during argument parsing.

**Config Path Resolution**: The server supports custom `sgconfig.yaml` via `--config` flag or `AST_GREP_CONFIG` env var. The global `CONFIG_PATH` variable is set by `parse_args_and_get_config()` before tool registration, allowing tools to pass `--config` to ast-grep commands when needed.

**Subprocess Execution Flow**: All tools ultimately call `run_ast_grep()` → `run_command()` → `subprocess.run()`. Error handling converts `CalledProcessError` and `FileNotFoundError` into user-friendly `RuntimeError` messages.

**Output Format Optimization**: `find_code` and `find_code_by_rule` support two output modes:
- `text` (default): ~75% fewer tokens, formatted as `file:line-range` headers with match text
- `json`: Full metadata including ranges and meta-variables

Both modes internally use JSON from ast-grep for accurate result limiting, then convert to text if requested.

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

### Common ast-grep Patterns
When testing rules, if no matches are found, the error message suggests adding `stopBy: end` to relational rules (inside/has). This is a common gotcha with ast-grep's traversal behavior.

### Text Format Design
The text output format was designed to minimize token usage for LLMs while maintaining context. Format: `filepath:startline-endline` header followed by complete match text, with matches separated by blank lines.
