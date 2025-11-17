# Configuration Guide

This document describes the `sgconfig.yaml` configuration file format for the ast-grep MCP server.

## Overview

The ast-grep MCP server supports custom configuration via a `sgconfig.yaml` file. This file allows you to customize ast-grep behavior, including:

- Defining custom languages
- Specifying rule directories
- Configuring test directories
- Setting language-to-file extension mappings

## Providing the Configuration File

You can provide the configuration file in two ways (in order of precedence):

1. **Command-line argument**: `--config /path/to/sgconfig.yaml`
2. **Environment variable**: `AST_GREP_CONFIG=/path/to/sgconfig.yaml`

The configuration file is validated on startup. If validation fails, the server will exit with a descriptive error message.

## Configuration Structure

### Top-Level Fields

```yaml
# Optional: Directories containing ast-grep rules
ruleDirs:
  - rules
  - custom-rules

# Optional: Directories containing test files
testDirs:
  - tests

# Optional: Custom language definitions
customLanguages:
  mylang:
    extensions:
      - .ml
      - .mli
    languageId: mylang
    expandoChar: _

# Optional: Language-to-glob mappings
languageGlobs:
  - extensions: [.proto]
    language: protobuf
```

### Field Descriptions

#### `ruleDirs` (optional)

Type: `List[str]`

Directories containing ast-grep rule files (`.yml` or `.yaml` files). Paths are relative to the configuration file location.

**Validation:**
- Must not be an empty list if specified
- Each directory path should exist (not enforced by validation, but recommended)

**Example:**
```yaml
ruleDirs:
  - rules
  - security-rules
  - refactoring-rules
```

#### `testDirs` (optional)

Type: `List[str]`

Directories containing test files for your ast-grep rules. Used by ast-grep's testing framework.

**Validation:**
- Must not be an empty list if specified

**Example:**
```yaml
testDirs:
  - tests
  - rule-tests
```

#### `customLanguages` (optional)

Type: `Dict[str, CustomLanguageConfig]`

Define custom languages with tree-sitter grammars. Each language has:

- **`extensions`** (required): List of file extensions (must start with `.`)
- **`languageId`** (optional): Language identifier
- **`expandoChar`** (optional): Character used for meta-variable expansion

**Validation:**
- Dictionary must not be empty if specified
- Each language must have at least one extension
- All extensions must start with a dot (`.`)

**Example:**
```yaml
customLanguages:
  # Custom language for Protocol Buffers
  protobuf:
    extensions:
      - .proto
    languageId: proto

  # Custom language for Terraform
  terraform:
    extensions:
      - .tf
      - .tfvars
    languageId: hcl
```

#### `languageGlobs` (optional)

Type: `List[Dict[str, Any]]`

Map file extensions to languages. Useful for associating non-standard extensions with existing languages.

**Example:**
```yaml
languageGlobs:
  - extensions: [.proto]
    language: protobuf
  - extensions: [.mjs, .cjs]
    language: javascript
```

## Complete Example

Here's a complete example configuration:

```yaml
# sgconfig.yaml - Complete example

ruleDirs:
  - rules
  - custom-rules
  - security

testDirs:
  - tests
  - rule-tests

customLanguages:
  # Add support for GraphQL
  graphql:
    extensions:
      - .graphql
      - .gql
    languageId: graphql

  # Add support for Solidity
  solidity:
    extensions:
      - .sol
    languageId: solidity

languageGlobs:
  # Map .mjs and .cjs to JavaScript
  - extensions: [.mjs, .cjs]
    language: javascript

  # Map .tsx and .jsx to TypeScript/JavaScript
  - extensions: [.tsx]
    language: tsx
  - extensions: [.jsx]
    language: jsx
```

## Validation

The server validates the configuration file on startup using Pydantic models. Common validation errors include:

### Empty Lists or Dictionaries

**Error:**
```
Configuration error in '/path/to/sgconfig.yaml': Validation failed: Directory list cannot be empty if specified
```

**Fix:**
Remove the empty field or add at least one item:
```yaml
# Wrong
ruleDirs: []

# Right - remove the field
# ruleDirs not specified

# Right - add items
ruleDirs:
  - rules
```

### Invalid File Extensions

**Error:**
```
Configuration error in '/path/to/sgconfig.yaml': Validation failed: Extension 'txt' must start with a dot (e.g., '.myext')
```

**Fix:**
Add a dot prefix to all extensions:
```yaml
# Wrong
customLanguages:
  mylang:
    extensions:
      - txt

# Right
customLanguages:
  mylang:
    extensions:
      - .txt
```

### Empty Extensions List

**Error:**
```
Configuration error in '/path/to/sgconfig.yaml': Validation failed: extensions list cannot be empty
```

**Fix:**
Add at least one extension:
```yaml
# Wrong
customLanguages:
  mylang:
    extensions: []

# Right
customLanguages:
  mylang:
    extensions:
      - .ml
```

### YAML Syntax Errors

**Error:**
```
Configuration error in '/path/to/sgconfig.yaml': YAML parsing failed: ...
```

**Fix:**
Check YAML syntax. Common issues:
- Incorrect indentation (use spaces, not tabs)
- Missing colons or hyphens
- Unclosed quotes or brackets

### File Not Found

**Error:**
```
Configuration error in '/path/to/sgconfig.yaml': File does not exist
```

**Fix:**
- Verify the path is correct
- Use absolute paths or paths relative to your working directory
- Check file permissions

## Testing Your Configuration

You can test your configuration by running the server with the `--config` flag:

```bash
uv run main.py --config /path/to/sgconfig.yaml
```

If validation succeeds, the server will start normally. If validation fails, you'll see a descriptive error message.

## Additional Resources

- [ast-grep Configuration Documentation](https://ast-grep.github.io/guide/project/project-config.html)
- [ast-grep Custom Language Guide](https://ast-grep.github.io/advanced/custom-language.html)
- [tree-sitter Language Support](https://tree-sitter.github.io/tree-sitter/)

## Schema Reference

### CustomLanguageConfig

```python
class CustomLanguageConfig:
    extensions: List[str]         # Required, must start with '.'
    languageId: Optional[str]     # Optional language identifier
    expandoChar: Optional[str]    # Optional expansion character
```

### AstGrepConfig

```python
class AstGrepConfig:
    ruleDirs: Optional[List[str]]                              # Rule directories
    testDirs: Optional[List[str]]                              # Test directories
    customLanguages: Optional[Dict[str, CustomLanguageConfig]] # Custom languages
    languageGlobs: Optional[List[Dict[str, Any]]]             # Language mappings
```

All fields are optional, but if provided, they must follow the validation rules described above.
