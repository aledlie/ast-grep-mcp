# Scripts

This directory contains utility scripts for running ast-grep MCP tools from the command line.

## find_duplication.py

Python script to detect duplicate code in a project.

### Usage

```bash
# Basic usage - analyze Python functions
uv run python scripts/find_duplication.py /path/to/project --language python

# Analyze JavaScript classes
uv run python scripts/find_duplication.py /path/to/project --language javascript --construct-type class_definition

# Strict similarity threshold (90%)
uv run python scripts/find_duplication.py /path/to/project --language python --min-similarity 0.9

# Ignore small functions (less than 10 lines)
uv run python scripts/find_duplication.py /path/to/project --language python --min-lines 10

# Output as JSON
uv run python scripts/find_duplication.py /path/to/project --language python --json
```

### Options

- `project_folder` (required): Absolute path to the project to analyze
- `--language, -l` (required): Programming language (python, javascript, typescript, java, go, etc.)
- `--construct-type, -c`: Type of construct to analyze (default: function_definition)
  - `function_definition`: Regular functions
  - `class_definition`: Classes
  - `method_definition`: Methods within classes
- `--min-similarity, -s`: Minimum similarity threshold 0.0-1.0 (default: 0.8)
- `--min-lines, -m`: Minimum lines to consider for duplication (default: 5)
- `--json, -j`: Output results as JSON instead of formatted text

### Examples

**Find duplicate Python functions:**
```bash
uv run python scripts/find_duplication.py /path/to/my-project --language python
```

**Find duplicate JavaScript classes with strict matching:**
```bash
uv run python scripts/find_duplication.py /path/to/my-app \
    --language javascript \
    --construct-type class_definition \
    --min-similarity 0.95
```

**Analyze only larger functions (10+ lines):**
```bash
uv run python scripts/find_duplication.py /path/to/my-project \
    --language python \
    --min-lines 10
```

**Get JSON output for programmatic processing:**
```bash
uv run python scripts/find_duplication.py /path/to/my-project \
    --language python \
    --json > duplication-report.json
```

## find_duplication.sh

Bash wrapper for the Python script (simpler interface).

### Usage

```bash
# Basic usage
./scripts/find_duplication.sh /path/to/project python

# With construct type
./scripts/find_duplication.sh /path/to/project javascript class_definition

# With similarity threshold
./scripts/find_duplication.sh /path/to/project python function_definition 0.9

# With all options
./scripts/find_duplication.sh /path/to/project python function_definition 0.8 10
```

### Arguments (positional)

1. `project_folder` (required): Absolute path to the project
2. `language` (optional, default: python): Programming language
3. `construct_type` (optional, default: function_definition): Type of construct
4. `min_similarity` (optional, default: 0.8): Similarity threshold
5. `min_lines` (optional, default: 5): Minimum lines

### Examples

**Analyze Python project:**
```bash
./scripts/find_duplication.sh /Users/me/myproject python
```

**Analyze JavaScript classes:**
```bash
./scripts/find_duplication.sh /Users/me/webapp javascript class_definition
```

**Strict matching (95% similarity):**
```bash
./scripts/find_duplication.sh /Users/me/myproject python function_definition 0.95
```

## Output Format

The script outputs a formatted report with three sections:

### 1. Summary
- Total constructs analyzed
- Duplicate groups found
- Total duplicated lines
- Potential line savings
- Analysis time

### 2. Duplication Groups
- Group ID and similarity score
- List of duplicate instances with file locations
- Code preview for each instance

### 3. Refactoring Suggestions
- Suggestion type (Extract Function, Base Class, etc.)
- Description and recommendation
- Number of duplicates and lines
- File locations for all duplicates

## Supported Languages

The tool works with all languages supported by ast-grep:

- JavaScript/TypeScript
- Python
- Java
- Go
- Rust
- C/C++
- C#
- Ruby
- PHP
- And many more...

See the [ast-grep language documentation](https://ast-grep.github.io/reference/languages.html) for a complete list.

## Tips

1. **Start with defaults**: Try running with default settings first to get a baseline
2. **Adjust similarity**: Lower threshold (0.7) finds more potential duplicates; higher (0.9) is more strict
3. **Filter small code**: Use `--min-lines 10` to focus on larger duplications
4. **JSON output**: Use `--json` for integration with other tools or CI/CD pipelines
5. **Large projects**: The analysis may take longer on large codebases; be patient

## Troubleshooting

**Error: "Command not found: ast-grep"**
- Install ast-grep: `brew install ast-grep` or see [installation guide](https://ast-grep.github.io/guide/quick-start.html#installation)

**Error: "Project folder must be an absolute path"**
- Use absolute paths: `/Users/me/project` not `./project`
- Use `pwd` to get current directory: `$(pwd)/project`

**No duplicates found when you expect some:**
- Try lowering `--min-similarity` (e.g., 0.7)
- Try lowering `--min-lines` (e.g., 3)
- Check that the correct `--construct-type` is specified
- Verify the `--language` matches your codebase

**Too many false positives:**
- Increase `--min-similarity` (e.g., 0.9)
- Increase `--min-lines` to focus on larger code blocks
