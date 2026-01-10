"""Search feature MCP tool definitions."""

from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.executor import get_supported_languages
from ast_grep_mcp.features.search.service import (
    debug_pattern_impl,
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
    ) -> str | List[Dict[str, Any]]:
        """
        Find code in a project folder using a custom YAML rule.
        This is more powerful than find_code as it supports complex rules like:
        - any/all conditions
        - regex/inside/precedes/follows
        - multiple patterns in one rule
        - constraints and relations

        Internally calls: ast-grep scan --inline-rules <yaml> [--json] <project_folder>

        Output formats:
        - text (default): Compact text format with file:line-range headers and complete match text
        - json: Full match objects with metadata including ranges, rule ID, matched text etc.

        The max_results parameter limits the number of complete matches returned.

        Example YAML rule:
          id: find-functions
          language: python
          rule:
            pattern: |
              def $NAME($$$):
                $$$BODY
            inside:
              stopBy: end
              kind: module

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
        - `$NAME`: Match single AST node (UPPERCASE only!)
        - `$$$ARGS`: Match zero or more nodes (for function arguments, etc.)
        - `$_NAME`: Non-capturing match (performance optimization)
        - `$$VAR`: Match unnamed tree-sitter nodes (advanced)

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
