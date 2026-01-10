"""Search feature MCP tool definitions."""

from typing import Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.executor import get_supported_languages
from ast_grep_mcp.features.search.docs import PATTERN_CATEGORIES, PATTERN_LANGUAGES, get_docs, get_pattern_examples
from ast_grep_mcp.features.search.service import (
    build_rule_impl,
    debug_pattern_impl,
    develop_pattern_impl,
    dump_syntax_tree_impl,
    find_code_by_rule_impl,
    find_code_impl,
    test_match_code_rule_impl,
)
from ast_grep_mcp.models.base import DumpFormat


def _register_dump_syntax_tree(mcp: FastMCP) -> None:
    """Register dump_syntax_tree tool."""

    @mcp.tool()
    def dump_syntax_tree(
        code: str = Field(description="The code you need"),
        language: str = Field(description=f"The language of the code. Supported: {', '.join(get_supported_languages())}"),
        format: DumpFormat = Field(description="Code dump format. Available values: pattern, ast, cst", default="cst"),
    ) -> str:
        """
        Dump code's syntax structure or dump a query's pattern structure.
        This is useful to discover correct syntax kind and syntax tree structure. Call it when debugging a rule.
        The tool requires three arguments: code, language and format. The first two are self-explanatory.
        `format` is the output format of the syntax tree.
        use `format=cst` to inspect the code's concrete syntax tree structure, useful to debug target code.
        use `format=pattern` to inspect how ast-grep interprets a pattern, useful to debug pattern rule.

        Internally calls: ast-grep run --pattern <code> --lang <language> --debug-query=<format>
        """
        return dump_syntax_tree_impl(code, language, format)


def _register_test_match_code_rule(mcp: FastMCP) -> None:
    """Register test_match_code_rule tool."""

    @mcp.tool()
    def test_match_code_rule(
        code: str = Field(description="The code to test against the rule"),
        yaml_rule: str = Field(description="The ast-grep YAML rule to search. It must have id, language, rule fields."),
    ) -> List[Dict[str, Any]]:
        """
        Test a code against an ast-grep YAML rule.
        This is useful to test a rule before using it in a project.

        Internally calls: ast-grep scan --inline-rules <yaml> --json --stdin
        """
        return test_match_code_rule_impl(code, yaml_rule)


def _register_find_code(mcp: FastMCP) -> None:
    """Register find_code tool."""

    @mcp.tool()
    def find_code(
        project_folder: str = Field(description="The absolute path to the project folder. It must be absolute path."),
        pattern: str = Field(description="The ast-grep pattern to search for. Note, the pattern must have valid AST structure."),
        language: str = Field(
            description=f"The language of the code. Supported: {', '.join(get_supported_languages())}. "
            "If not specified, will be auto-detected based on file extensions.",
            default="",
        ),
        max_results: int = Field(default=0, description="Maximum results to return"),
        output_format: str = Field(default="text", description="'text' or 'json'"),
        max_file_size_mb: int = Field(
            default=0,
            description="Skip files larger than this size in MB. 0 = unlimited (default). "
            "Useful for excluding large generated/minified files.",
        ),
        workers: int = Field(
            default=0,
            description="Number of parallel worker threads. 0 = auto (default, uses ast-grep heuristics). "
            "Higher values can speed up searches on large codebases with multiple CPU cores.",
        ),
    ) -> str | List[Dict[str, Any]]:
        """
        Find code in a project folder that matches the given ast-grep pattern.
        Pattern is good for simple and single-AST node result.
        For more complex usage, please use YAML by `find_code_by_rule`.

        Internally calls: ast-grep run --pattern <pattern> [--json] <project_folder>

        Output formats:
        - text (default): Compact text format with file:line-range headers and complete match text
          Example:
            Found 2 matches:

            path/to/file.py:10-15
            def example_function():
                # function body
                return result

            path/to/file.py:20-22
            def another_function():
                pass

        - json: Full match objects with metadata including ranges, meta-variables, etc.

        The max_results parameter limits the number of complete matches returned (not individual lines).
        When limited, the header shows "Found X matches (showing first Y of Z)".

        Example usage:
          find_code(pattern="class $NAME", max_results=20)  # Returns text format
          find_code(pattern="class $NAME", output_format="json")  # Returns JSON with metadata
        """
        return find_code_impl(
            project_folder,
            pattern,
            language,
            max_results,
            output_format,  # type: ignore[arg-type]
            max_file_size_mb,
            workers,
        )


def _register_find_code_by_rule(mcp: FastMCP) -> None:
    """Register find_code_by_rule tool."""

    @mcp.tool()
    def find_code_by_rule(
        project_folder: str = Field(description="The absolute path to the project folder. It must be absolute path."),
        yaml_rule: str = Field(description="The ast-grep YAML rule to search. It must have id, language, rule fields."),
        max_results: int = Field(default=0, description="Maximum results to return"),
        output_format: str = Field(default="text", description="'text' or 'json'"),
    ) -> str | List[Dict[str, Any]] | Dict[str, Any]:
        """
        Find code in a project folder using a custom YAML rule.
        This is more powerful than find_code as it supports complex rules like:
        - any/all conditions
        - regex/inside/precedes/follows
        - multiple patterns in one rule
        - constraints and relations

        Internally calls: ast-grep scan --inline-rules <yaml> [--json] <project_folder>

        ⚠️  CRITICAL: The stopBy Parameter  ⚠️

        Relational rules (inside, has, follows, precedes) have a `stopBy` parameter:
        - `neighbor` (DEFAULT): Only checks immediate parent/sibling - often NOT what you want!
        - `end`: Searches to tree boundaries - usually what you need
        - Custom rule: Stops when surrounding nodes match

        COMMON MISTAKE - This often fails because it only checks immediate parent:
        ```yaml
        rule:
          pattern: $CALL
          inside:
            kind: function_declaration  # Missing stopBy: end!
        ```

        CORRECT - Add stopBy: end to search the entire tree:
        ```yaml
        rule:
          pattern: $CALL
          inside:
            stopBy: end  # Searches up the entire tree
            kind: function_declaration
        ```

        Minimal Rule Template:
        ```yaml
        id: my-rule
        language: python
        rule:
          pattern: |
            def $NAME($$$PARAMS):
              $$$BODY
        ```

        With Relational Rules:
        ```yaml
        id: my-rule
        language: python
        rule:
          pattern: $CALL
          inside:
            stopBy: end  # Don't forget this!
            kind: function_definition
        ```

        Composite Rules (all/any):
        - `all`: Matches a SINGLE node satisfying ALL sub-rules (not multiple nodes!)
        - `any`: Matches nodes satisfying ANY sub-rule

        ```yaml
        rule:
          any:
            - pattern: console.log($$$)
            - pattern: console.warn($$$)
            - pattern: console.error($$$)
        ```

        Output formats:
        - text (default): Compact text format with file:line-range headers and complete match text
        - json: Full match objects with metadata including ranges, rule ID, matched text etc.

        The max_results parameter limits the number of complete matches returned.

        Example usage:
          find_code_by_rule(project_folder="/path/to/project", yaml_rule=rule_str)
        """
        return find_code_by_rule_impl(
            project_folder,
            yaml_rule,
            max_results,
            output_format,  # type: ignore[arg-type]
        )


def _register_debug_pattern(mcp: FastMCP) -> None:
    """Register debug_pattern tool."""

    @mcp.tool()
    def debug_pattern(
        pattern: str = Field(description="The ast-grep pattern to debug"),
        code: str = Field(description="The code to match against"),
        language: str = Field(description=f"The programming language. Supported: {', '.join(get_supported_languages())}"),
    ) -> Dict[str, Any]:
        """
        Debug why a pattern doesn't match code.

        This tool provides comprehensive analysis when a pattern fails to match:

        **What it checks:**
        1. **Metavariable validation**: Detects invalid syntax like $name (must be $NAME),
           $123 (can't start with digit), $KEBAB-CASE (no hyphens allowed)
        2. **AST comparison**: Compares the pattern's AST with the code's AST to find
           structural mismatches
        3. **Match attempt**: Actually tries to match and reports results
        4. **Best practices**: Warns about common issues like using $ARG instead of $$$ARGS
           for multiple function arguments

        **Metavariable Quick Reference:**
        | Syntax     | Meaning                          | Example                    |
        |------------|----------------------------------|----------------------------|
        | `$NAME`    | Match single AST node (UPPERCASE)| `function $NAME()`         |
        | `$$$ARGS`  | Match zero or more nodes         | `foo($$$ARGS)`             |
        | `$_NAME`   | Non-capturing (performance)      | `$_FUNC($_ARG)`            |
        | `$$VAR`    | Match unnamed nodes (advanced)   | For tree-sitter internals  |

        **Valid metavariable names:** `$META`, `$META_VAR`, `$META_VAR1`, `$_`, `$_123`
        **Invalid:** `$name` (lowercase), `$123` (digit start), `$KEBAB-CASE` (hyphens)

        **Common Mistakes Detected:**
        - `$name` → Should be `$NAME` (uppercase required)
        - `$123` → Can't start with digit
        - `$KEBAB-CASE` → No hyphens allowed
        - `console.log($GREETING)` → May need `$$$ARGS` for multiple arguments
        - Incomplete code fragments that aren't valid syntax

        **Output includes:**
        - `pattern_valid`: Whether pattern parses correctly
        - `pattern_ast`: How ast-grep interpreted the pattern
        - `code_ast`: How ast-grep parsed the code
        - `ast_comparison`: Side-by-side comparison with differences
        - `metavariables`: All metavars found with validation status
        - `issues`: List of problems found (errors, warnings, tips)
        - `suggestions`: Prioritized list of fixes
        - `match_attempt`: Whether matching succeeded

        **Example usage:**
        ```python
        # Debug why a pattern doesn't match
        result = debug_pattern(
            pattern="console.log($message)",  # Invalid! $message should be $MESSAGE
            code="console.log('hello')",
            language="javascript"
        )
        # Result will show:
        # - issues: [{"severity": "error", "message": "Metavariable must use UPPERCASE..."}]
        # - suggestions: ["[ERROR] Use uppercase letters: $MESSAGE"]
        ```

        **When to use:**
        - Pattern returns no matches when you expect matches
        - You're unsure if your metavariable syntax is correct
        - You want to understand how ast-grep parses your pattern vs code
        - You're learning ast-grep pattern syntax
        """
        result = debug_pattern_impl(pattern, code, language)
        return result.to_dict()


def _register_get_ast_grep_docs(mcp: FastMCP) -> None:
    """Register get_ast_grep_docs tool."""

    @mcp.tool()
    def get_ast_grep_docs(
        topic: Literal["pattern", "rules", "relational", "metavariables", "workflow", "strictness", "all"] = Field(
            description="Documentation topic to retrieve"
        ),
    ) -> str:
        """
        Get ast-grep documentation for the specified topic.

        Use this tool when you need guidance on:
        - Pattern syntax and metavariables
        - YAML rule configuration
        - Relational rules (inside, has, follows, precedes)
        - Strictness modes for matching
        - Best practices and workflows

        This provides accurate, up-to-date documentation to help you write
        correct patterns and rules, reducing trial-and-error.

        **Available Topics:**

        - `pattern`: Pattern syntax, metavariables ($NAME, $$$ARGS), matching rules,
          common patterns by language

        - `rules`: YAML rule structure, required fields (id, language, rule),
          optional fields (message, severity, fix), stopBy configuration

        - `relational`: inside/has/follows/precedes rules, the critical stopBy
          parameter, combining relational rules, common patterns

        - `metavariables`: Complete reference for $NAME, $$$, $_NAME, $$VAR,
          valid/invalid naming, common mistakes

        - `strictness`: Pattern matching modes (cst, smart, ast, relaxed, signature),
          when to use each, behavior differences, best practices

        - `workflow`: Recommended development workflow, tool selection guide,
          troubleshooting checklist

        - `all`: Complete documentation (all topics combined)

        **Example Usage:**
        ```
        # Get help with pattern syntax
        get_ast_grep_docs(topic="pattern")

        # Understand relational rules and stopBy
        get_ast_grep_docs(topic="relational")

        # Get the complete reference
        get_ast_grep_docs(topic="all")
        ```

        **When to Use:**
        - Before writing a complex pattern or rule
        - When a pattern doesn't match as expected
        - To understand metavariable syntax
        - To learn about relational rules and stopBy
        - As a reference while iterating on rules
        """
        return get_docs(topic)


def _register_build_rule(mcp: FastMCP) -> None:
    """Register build_rule tool."""

    @mcp.tool()
    def build_rule(
        pattern: str = Field(description="The main pattern to match"),
        language: str = Field(description=f"Target language. Supported: {', '.join(get_supported_languages())}"),
        rule_id: Optional[str] = Field(default=None, description="Unique rule ID (auto-generated if not provided)"),
        inside: Optional[str] = Field(default=None, description="Pattern that must CONTAIN the match (parent)"),
        has: Optional[str] = Field(default=None, description="Pattern that must be INSIDE the match (child)"),
        follows: Optional[str] = Field(default=None, description="Pattern that must PRECEDE the match"),
        precedes: Optional[str] = Field(default=None, description="Pattern that must FOLLOW the match"),
        inside_kind: Optional[str] = Field(
            default=None, description="Node kind that must contain the match (e.g., 'function_declaration')"
        ),
        has_kind: Optional[str] = Field(default=None, description="Node kind that must be inside the match"),
        stop_by: str = Field(
            default="end",
            description="stopBy for relational rules: 'end' (search entire tree, DEFAULT), "
            "'neighbor' (immediate only), or custom pattern",
        ),
        message: Optional[str] = Field(default=None, description="Human-readable message for matches"),
        severity: Optional[str] = Field(default=None, description="Severity: error, warning, info, hint"),
        fix: Optional[str] = Field(default=None, description="Auto-fix template using captured metavariables"),
    ) -> str:
        """
        Build a properly structured YAML rule from components.

        This tool helps you construct valid ast-grep YAML rules without worrying
        about syntax details. It automatically:
        - Adds all required fields (id, language, rule)
        - Sets `stopBy: end` on relational rules (preventing the #1 mistake!)
        - Formats YAML correctly

        **Why Use This Tool?**
        Building YAML rules by hand is error-prone. Common mistakes include:
        - Forgetting `stopBy: end` (causes rules to not match)
        - Missing required fields
        - YAML formatting issues

        This tool eliminates these issues by construction.

        **Relational Rules:**
        - `inside`: Match must be INSIDE this pattern (e.g., inside a function)
        - `has`: Match must CONTAIN this pattern (e.g., has a return statement)
        - `follows`: Match must come AFTER this pattern
        - `precedes`: Match must come BEFORE this pattern

        Use `inside_kind` or `has_kind` for node-type matching instead of patterns.

        **Examples:**

        1. Find console.log inside functions:
        ```
        build_rule(
            pattern="console.log($$$ARGS)",
            language="javascript",
            inside_kind="function_declaration"
        )
        ```

        2. Find functions that have return statements:
        ```
        build_rule(
            pattern="function $NAME($$$) { $$$BODY }",
            language="javascript",
            has="return $VALUE"
        )
        ```

        3. Find variable usage after declaration:
        ```
        build_rule(
            pattern="$VAR",
            language="javascript",
            follows="const $VAR = $VALUE"
        )
        ```

        4. Find and fix console.log calls:
        ```
        build_rule(
            pattern="console.log($$$ARGS)",
            language="javascript",
            message="Remove console.log before production",
            severity="warning",
            fix=""  # Empty string = delete the match
        )
        ```

        **Output:**
        Returns a YAML string ready to use with `find_code_by_rule` or
        `test_match_code_rule`.
        """
        return build_rule_impl(
            pattern=pattern,
            language=language,
            rule_id=rule_id,
            inside=inside,
            has=has,
            follows=follows,
            precedes=precedes,
            inside_kind=inside_kind,
            has_kind=has_kind,
            stop_by=stop_by,
            message=message,
            severity=severity,
            fix=fix,
        )


def _register_get_pattern_examples(mcp: FastMCP) -> None:
    """Register get_pattern_examples tool."""

    @mcp.tool()
    def get_pattern_examples_tool(
        language: str = Field(
            description=f"Target language. Available: {', '.join(PATTERN_LANGUAGES)}"
        ),
        category: Optional[str] = Field(
            default=None,
            description=f"Optional category filter. Available: {', '.join(PATTERN_CATEGORIES)}, all. "
            "If not specified, shows all categories.",
        ),
    ) -> str:
        """
        Get common ast-grep pattern examples for a language.

        Returns ready-to-use patterns organized by category with descriptions.
        Use these as starting points for your searches - patterns are verified
        to work with ast-grep and follow best practices.

        **Categories:**

        - `function`: Function declarations, arrow functions, methods, lambdas
        - `class`: Class definitions, inheritance, constructors, interfaces
        - `import`: Import/require statements, module imports
        - `variable`: Variable declarations, destructuring, type annotations
        - `control_flow`: If/else, loops, switch, ternary expressions
        - `error_handling`: Try/catch, throw, error patterns
        - `async`: Async/await, promises, goroutines, threads

        **Supported Languages:**

        JavaScript, TypeScript, Python, Go, Rust, Java, Ruby, C, C++

        **Example Usage:**

        ```
        # Get all JavaScript patterns
        get_pattern_examples(language="javascript")

        # Get only function patterns for Python
        get_pattern_examples(language="python", category="function")

        # Get error handling patterns for Go
        get_pattern_examples(language="go", category="error_handling")
        ```

        **Output Format:**

        Each pattern includes:
        - Description of what it matches
        - The pattern itself (ready to use with find_code)
        - Optional notes about usage

        **Tips:**

        1. Start with these patterns and customize for your needs
        2. Use $$$PARAMS for function parameters (matches 0+ args)
        3. Use $NAME for single captures, $$$ARGS for multiple
        4. Combine with YAML rules for more complex matching
        """
        return get_pattern_examples(language, category)


def _register_develop_pattern(mcp: FastMCP) -> None:
    """Register develop_pattern tool."""

    @mcp.tool()
    def develop_pattern(
        code: str = Field(description="Sample code you want to match"),
        language: str = Field(description=f"The programming language. Supported: {', '.join(get_supported_languages())}"),
        goal: Optional[str] = Field(
            default=None,
            description="Optional: Describe what you're trying to find (e.g., 'console.log calls', 'functions with no return')",
        ),
    ) -> Dict[str, Any]:
        """
        Interactive pattern development assistant.

        This tool helps you develop ast-grep patterns by analyzing your sample code
        and suggesting patterns that will match it. It's the recommended starting
        point when you're not sure how to write a pattern.

        **How It Works:**

        1. **Analyzes your code**: Examines the AST structure, identifies node kinds,
           extracts identifiers and literals

        2. **Suggests patterns**: Generates multiple pattern options:
           - Exact match: The code itself as a pattern
           - Generalized: With metavariables ($NAME) for flexibility
           - Structural: Using node kinds for YAML rules

        3. **Tests patterns**: Verifies if suggested patterns actually match

        4. **Provides guidance**: Gives you next steps and refinement suggestions

        **When to Use:**

        - You have sample code and want to find similar patterns
        - You're new to ast-grep and don't know the pattern syntax
        - You want to quickly bootstrap a pattern without trial-and-error
        - You need to understand the AST structure of your code

        **Example:**

        ```python
        # You want to find all console.log calls
        result = develop_pattern(
            code="console.log('hello')",
            language="javascript",
            goal="Find all console.log calls"
        )

        # Result includes:
        # - code_analysis: root_kind, identifiers, complexity
        # - suggested_patterns: exact, generalized ($ARG), structural
        # - best_pattern: The recommended pattern to use
        # - pattern_matches: True/False - does it work?
        # - yaml_rule_template: Ready-to-use YAML rule
        # - next_steps: What to do next
        ```

        **Output Fields:**

        - `code_analysis`: AST structure analysis
          - `root_kind`: The AST node type (e.g., "call_expression")
          - `identifiers`: Variables and function names found
          - `literals`: String and number literals found
          - `complexity`: "simple", "medium", or "complex"
          - `ast_preview`: First lines of the AST

        - `suggested_patterns`: List of patterns with:
          - `pattern`: The pattern string
          - `description`: What it matches
          - `type`: "exact", "generalized", or "structural"
          - `confidence`: How likely to work (0-1)

        - `best_pattern`: The recommended pattern to start with

        - `pattern_matches`: Whether best_pattern matches the code

        - `yaml_rule_template`: Complete YAML rule ready for find_code_by_rule

        - `next_steps`: Guidance on what to do next

        - `refinement_steps`: If pattern doesn't match, how to fix it

        **Workflow Integration:**

        1. Start here with develop_pattern() to get a working pattern
        2. Use find_code() to search your project
        3. Use build_rule() to add constraints (inside, has)
        4. Use debug_pattern() if matches aren't working
        5. Use test_match_code_rule() to verify edge cases
        """
        result = develop_pattern_impl(code, language, goal)
        return result.to_dict()


def register_search_tools(mcp: FastMCP) -> None:
    """Register search-related MCP tools.

    Args:
        mcp: FastMCP instance to register tools with
    """
    _register_dump_syntax_tree(mcp)
    _register_test_match_code_rule(mcp)
    _register_find_code(mcp)
    _register_find_code_by_rule(mcp)
    _register_debug_pattern(mcp)
    _register_develop_pattern(mcp)
    _register_get_ast_grep_docs(mcp)
    _register_build_rule(mcp)
    _register_get_pattern_examples(mcp)
