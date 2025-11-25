"""Search feature MCP tool definitions."""

from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.executor import get_supported_languages
from ast_grep_mcp.features.search.service import (
    dump_syntax_tree_impl,
    find_code_by_rule_impl,
    find_code_impl,
    test_match_code_rule_impl,
)
from ast_grep_mcp.models.base import DumpFormat


def register_search_tools(mcp: FastMCP) -> None:
    """Register search-related MCP tools.

    Args:
        mcp: FastMCP instance to register tools with
    """

    @mcp.tool()
    def dump_syntax_tree(
        code: str = Field(description="The code you need"),
        language: str = Field(
            description=f"The language of the code. Supported: {', '.join(get_supported_languages())}"
        ),
        format: DumpFormat = Field(
            description="Code dump format. Available values: pattern, ast, cst",
            default="cst"
        ),
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

    @mcp.tool()
    def test_match_code_rule(
        code: str = Field(description="The code to test against the rule"),
        yaml_rule: str = Field(
            description="The ast-grep YAML rule to search. It must have id, language, rule fields."
        ),
    ) -> List[Dict[str, Any]]:
        """
        Test a code against an ast-grep YAML rule.
        This is useful to test a rule before using it in a project.

        Internally calls: ast-grep scan --inline-rules <yaml> --json --stdin
        """
        return test_match_code_rule_impl(code, yaml_rule)

    @mcp.tool()
    def find_code(
        project_folder: str = Field(
            description="The absolute path to the project folder. It must be absolute path."
        ),
        pattern: str = Field(
            description="The ast-grep pattern to search for. Note, the pattern must have valid AST structure."
        ),
        language: str = Field(
            description=f"The language of the code. Supported: {', '.join(get_supported_languages())}. "
            "If not specified, will be auto-detected based on file extensions.",
            default=""
        ),
        max_results: int = Field(default=0, description="Maximum results to return"),
        output_format: str = Field(default="text", description="'text' or 'json'"),
        max_file_size_mb: int = Field(
            default=0,
            description="Skip files larger than this size in MB. 0 = unlimited (default). "
            "Useful for excluding large generated/minified files."
        ),
        workers: int = Field(
            default=0,
            description="Number of parallel worker threads. 0 = auto (default, uses ast-grep heuristics). "
            "Higher values can speed up searches on large codebases with multiple CPU cores."
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
            workers
        )

    @mcp.tool()
    def find_code_by_rule(
        project_folder: str = Field(
            description="The absolute path to the project folder. It must be absolute path."
        ),
        yaml_rule: str = Field(
            description="The ast-grep YAML rule to search. It must have id, language, rule fields."
        ),
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
            output_format  # type: ignore[arg-type]
        )
