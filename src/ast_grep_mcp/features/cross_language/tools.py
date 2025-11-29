"""MCP tool definitions for cross-language operations features.

This module registers MCP tools for:
- search_multi_language: Search across multiple programming languages
- find_language_equivalents: Find equivalent patterns across languages
- convert_code_language: Convert code between languages
- refactor_polyglot: Refactor across language boundaries
- generate_language_bindings: Generate API client bindings
"""
import time
from typing import Any, Dict, List, Optional

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.cross_language.binding_generator import generate_language_bindings_impl
from ast_grep_mcp.features.cross_language.language_converter import convert_code_language_impl
from ast_grep_mcp.features.cross_language.multi_language_search import search_multi_language_impl
from ast_grep_mcp.features.cross_language.pattern_equivalence import find_language_equivalents_impl
from ast_grep_mcp.features.cross_language.polyglot_refactoring import refactor_polyglot_impl


# =============================================================================
# Response Formatting Helpers
# =============================================================================

def _format_example(ex) -> Dict[str, Any]:
    """Format a single pattern example."""
    return {
        "language": ex.language,
        "code": ex.code,
        "description": ex.description,
        "notes": ex.notes,
    }


def _format_equivalence(e) -> Dict[str, Any]:
    """Format a single pattern equivalence."""
    return {
        "pattern_id": e.pattern_id,
        "concept": e.concept,
        "category": e.category,
        "description": e.description,
        "examples": [_format_example(ex) for ex in e.examples],
        "related_patterns": e.related_patterns,
        "complexity_comparison": e.complexity_comparison,
    }


def _format_equivalents_result(result) -> Dict[str, Any]:
    """Format find_language_equivalents result."""
    return {
        "pattern_description": result.pattern_description,
        "source_language": result.source_language,
        "target_languages": result.target_languages,
        "equivalences": [_format_equivalence(e) for e in result.equivalences],
        "suggestions": result.suggestions,
        "execution_time_ms": result.execution_time_ms,
    }


def _format_type_mapping(t) -> Dict[str, str]:
    """Format a single type mapping."""
    return {"source": t.source_type, "target": t.target_type}


def _format_warning(w) -> Dict[str, Any]:
    """Format a single conversion warning."""
    return {
        "severity": w.severity,
        "message": w.message,
        "line_number": w.line_number,
        "suggestion": w.suggestion,
    }


def _format_conversion(c) -> Dict[str, Any]:
    """Format a single code conversion."""
    return {
        "source_code": c.source_code,
        "converted_code": c.converted_code,
        "from_language": c.from_language,
        "to_language": c.to_language,
        "style": c.style.value,
        "type_mappings": [_format_type_mapping(t) for t in c.type_mappings],
        "warnings": [_format_warning(w) for w in c.warnings],
        "imports_needed": c.imports_needed,
        "success": c.success,
    }


def _format_conversion_result(result) -> Dict[str, Any]:
    """Format convert_code_language result."""
    return {
        "conversions": [_format_conversion(c) for c in result.conversions],
        "total_functions": result.total_functions,
        "successful_conversions": result.successful_conversions,
        "failed_conversions": result.failed_conversions,
        "execution_time_ms": result.execution_time_ms,
    }


# =============================================================================
# Tool Implementations
# =============================================================================

def search_multi_language_tool(
    project_folder: str,
    semantic_pattern: str,
    languages: Optional[List[str]] = None,
    group_by: str = "semantic",
    max_results_per_language: int = 100,
) -> Dict[str, Any]:
    """
    Search across multiple programming languages for semantically equivalent patterns.

    This tool enables polyglot search by finding similar code patterns across different
    programming languages simultaneously. It supports semantic grouping to cluster
    related results together.

    **Semantic Patterns:**
    - "async function" - Find async functions across languages
    - "try catch" - Find error handling patterns
    - "class" - Find class definitions
    - "function" - Find function definitions
    - "import" - Find import/require statements
    - "for loop" - Find iteration patterns

    **Supported Languages:**
    Python, TypeScript, JavaScript, Java, Kotlin, Go, Rust, C, C++, C#, Ruby, PHP, Swift

    Args:
        project_folder: Root folder of the project (absolute path)
        semantic_pattern: Semantic pattern to search for (e.g., "async function")
        languages: Languages to search (["auto"] for auto-detection)
        group_by: Grouping strategy ("semantic", "language", "file")
        max_results_per_language: Maximum results per language

    Returns:
        Dictionary containing:
        - query: The semantic query used
        - languages_searched: Languages that were searched
        - matches: List of matches with file, line, code
        - total_matches: Total number of matches
        - matches_by_language: Count per language
        - semantic_groups: Distinct semantic groups found

    Example usage:
        # Search for async functions across all languages
        result = search_multi_language(
            project_folder="/path/to/project",
            semantic_pattern="async function",
            languages=["auto"]
        )

        # Search specific languages
        result = search_multi_language(
            project_folder="/path/to/project",
            semantic_pattern="try catch",
            languages=["python", "typescript", "java"]
        )
    """
    logger = get_logger("tool.search_multi_language")
    start_time = time.time()

    if languages is None:
        languages = ["auto"]

    logger.info(
        "tool_invoked",
        tool="search_multi_language",
        project_folder=project_folder,
        semantic_pattern=semantic_pattern,
        languages=languages,
    )

    try:
        result = search_multi_language_impl(
            project_folder=project_folder,
            semantic_pattern=semantic_pattern,
            languages=languages,
            group_by=group_by,
            max_results_per_language=max_results_per_language,
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="search_multi_language",
            execution_time_seconds=round(execution_time, 3),
            total_matches=result.total_matches,
            languages_searched=result.languages_searched,
        )

        return {
            "query": result.query,
            "languages_searched": result.languages_searched,
            "matches": [
                {
                    "language": m.language,
                    "file_path": m.file_path,
                    "line_number": m.line_number,
                    "code_snippet": m.code_snippet,
                    "semantic_group": m.semantic_group,
                    "confidence": m.confidence,
                }
                for m in result.matches
            ],
            "total_matches": result.total_matches,
            "matches_by_language": result.matches_by_language,
            "semantic_groups": result.semantic_groups,
            "execution_time_ms": result.execution_time_ms,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="search_multi_language",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
        )
        sentry_sdk.capture_exception(e)
        raise


def find_language_equivalents_tool(
    pattern_description: str,
    source_language: Optional[str] = None,
    target_languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Find equivalent patterns across programming languages.

    This tool provides a knowledge base of equivalent programming patterns
    across different languages. It helps developers understand how to
    express the same concept in different languages.

    **Pattern Categories:**
    - control_flow: if/else, switch, loops
    - functions: function definitions, lambdas, async
    - data_structures: lists, dictionaries, comprehensions
    - error_handling: try/catch, error propagation
    - async: async/await, promises
    - classes: class definitions, interfaces

    **Example Patterns:**
    - "list comprehension" - Array transformation patterns
    - "async await" - Asynchronous programming
    - "try catch" - Exception handling
    - "destructuring" - Value extraction
    - "arrow function" - Lambda expressions

    Args:
        pattern_description: Description of the pattern to find
        source_language: Optional source language to highlight
        target_languages: Languages to include in results

    Returns:
        Dictionary containing:
        - pattern_description: The input query
        - equivalences: List of pattern equivalences
        - suggestions: Related pattern suggestions

    Example usage:
        # Find list comprehension equivalents
        result = find_language_equivalents(
            pattern_description="list comprehension",
            target_languages=["python", "typescript", "java"]
        )

        # Find async patterns from Python perspective
        result = find_language_equivalents(
            pattern_description="async await",
            source_language="python",
            target_languages=["typescript", "javascript", "rust"]
        )
    """
    logger = get_logger("tool.find_language_equivalents")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="find_language_equivalents",
        pattern_description=pattern_description,
        source_language=source_language,
    )

    try:
        result = find_language_equivalents_impl(
            pattern_description=pattern_description,
            source_language=source_language,
            target_languages=target_languages,
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="find_language_equivalents",
            execution_time_seconds=round(execution_time, 3),
            equivalences_found=len(result.equivalences),
        )

        return _format_equivalents_result(result)

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="find_language_equivalents",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
        )
        sentry_sdk.capture_exception(e)
        raise


def convert_code_language_tool(
    code_snippet: str,
    from_language: str,
    to_language: str,
    conversion_style: str = "idiomatic",
    include_comments: bool = True,
) -> Dict[str, Any]:
    """
    Convert code from one programming language to another.

    This tool converts code snippets between supported language pairs,
    handling syntax transformation, type conversion, and idiomatic patterns.

    **Supported Conversions:**
    - Python <-> TypeScript
    - Python <-> JavaScript
    - JavaScript -> TypeScript
    - Java -> Kotlin

    **Conversion Styles:**
    - literal: Direct translation preserving structure
    - idiomatic: Use target language idioms and best practices
    - compatible: Maximum cross-platform compatibility

    **Features:**
    - Syntax transformation (control flow, functions, classes)
    - Type mapping (Python types -> TypeScript types)
    - Idiom conversion (list comprehensions -> map/filter)
    - Warnings for features that don't convert cleanly

    Args:
        code_snippet: Code to convert
        from_language: Source language
        to_language: Target language
        conversion_style: Conversion style (literal, idiomatic, compatible)
        include_comments: Whether to include conversion comments

    Returns:
        Dictionary containing:
        - conversions: List of converted code blocks
        - successful_conversions: Number of successful conversions
        - warnings: Any conversion warnings

    Example usage:
        # Convert Python to TypeScript
        result = convert_code_language(
            code_snippet=\"\"\"
def calculate_total(items: List[float], tax_rate: float = 0.08) -> float:
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)
\"\"\",
            from_language="python",
            to_language="typescript",
            conversion_style="idiomatic"
        )

        # Convert JavaScript to Python
        result = convert_code_language(
            code_snippet=\"\"\"
const fetchData = async (url) => {
    const response = await fetch(url);
    return response.json();
};
\"\"\",
            from_language="javascript",
            to_language="python"
        )
    """
    logger = get_logger("tool.convert_code_language")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="convert_code_language",
        from_language=from_language,
        to_language=to_language,
        conversion_style=conversion_style,
    )

    try:
        result = convert_code_language_impl(
            code_snippet=code_snippet,
            from_language=from_language,
            to_language=to_language,
            conversion_style=conversion_style,
            include_comments=include_comments,
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="convert_code_language",
            execution_time_seconds=round(execution_time, 3),
            successful=result.successful_conversions,
        )

        return _format_conversion_result(result)

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="convert_code_language",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
        )
        sentry_sdk.capture_exception(e)
        raise


def refactor_polyglot_tool(
    project_folder: str,
    refactoring_type: str,
    symbol_name: str,
    new_name: Optional[str] = None,
    affected_languages: Optional[List[str]] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Refactor across multiple programming languages atomically.

    This tool enables refactoring operations that span multiple languages,
    such as renaming an API endpoint that exists in both backend and frontend code.

    **Refactoring Types:**
    - rename_api: Rename API endpoint/symbol across all languages
    - extract_constant: Extract to shared configuration
    - update_contract: Update API contract signature

    **Features:**
    - Cross-language symbol tracking
    - Atomic multi-file changes
    - Risk analysis
    - Manual review identification
    - Validation before applying

    Args:
        project_folder: Root folder of the project
        refactoring_type: Type of refactoring (rename_api, extract_constant, update_contract)
        symbol_name: Symbol being refactored
        new_name: New name (required for rename operations)
        affected_languages: Languages to include (["all"] for all)
        dry_run: If True, only preview changes

    Returns:
        Dictionary containing:
        - plan: The refactoring plan
        - changes: List of changes (made or preview)
        - files_modified: Files that were modified
        - risks: Identified risks
        - requires_manual_review: Files needing manual review

    Example usage:
        # Preview renaming an API endpoint
        result = refactor_polyglot(
            project_folder="/path/to/project",
            refactoring_type="rename_api",
            symbol_name="getUserProfile",
            new_name="fetchUserProfile",
            dry_run=True
        )

        # Apply the rename
        result = refactor_polyglot(
            project_folder="/path/to/project",
            refactoring_type="rename_api",
            symbol_name="getUserProfile",
            new_name="fetchUserProfile",
            affected_languages=["python", "typescript"],
            dry_run=False
        )
    """
    logger = get_logger("tool.refactor_polyglot")
    start_time = time.time()

    if affected_languages is None:
        affected_languages = ["all"]

    logger.info(
        "tool_invoked",
        tool="refactor_polyglot",
        project_folder=project_folder,
        refactoring_type=refactoring_type,
        symbol_name=symbol_name,
        dry_run=dry_run,
    )

    try:
        result = refactor_polyglot_impl(
            project_folder=project_folder,
            refactoring_type=refactoring_type,
            symbol_name=symbol_name,
            new_name=new_name,
            affected_languages=affected_languages,
            dry_run=dry_run,
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="refactor_polyglot",
            execution_time_seconds=round(execution_time, 3),
            changes_count=len(result.plan.changes),
            dry_run=result.dry_run,
        )

        return {
            "plan": {
                "refactoring_type": result.plan.refactoring_type.value,
                "symbol_name": result.plan.symbol_name,
                "new_name": result.plan.new_name,
                "affected_languages": result.plan.affected_languages,
                "changes_count": len(result.plan.changes),
                "risks": result.plan.risks,
                "requires_manual_review": result.plan.requires_manual_review,
            },
            "changes": [
                {
                    "language": c.language,
                    "file_path": c.file_path,
                    "line_number": c.line_number,
                    "original_code": c.original_code,
                    "new_code": c.new_code,
                    "change_type": c.change_type,
                }
                for c in (result.changes_made if not result.dry_run else result.plan.changes)
            ],
            "dry_run": result.dry_run,
            "files_modified": result.files_modified,
            "validation_passed": result.validation_passed,
            "validation_errors": result.validation_errors,
            "execution_time_ms": result.execution_time_ms,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="refactor_polyglot",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
        )
        sentry_sdk.capture_exception(e)
        raise


def generate_language_bindings_tool(
    api_definition_file: str,
    target_languages: Optional[List[str]] = None,
    binding_style: str = "native",
    include_types: bool = True,
) -> Dict[str, Any]:
    """
    Generate API client bindings for multiple languages from specifications.

    This tool parses API specifications (OpenAPI/Swagger) and generates
    client code in multiple programming languages.

    **Supported Input Formats:**
    - OpenAPI 3.0 (JSON or YAML)
    - Swagger 2.0 (JSON or YAML)

    **Supported Output Languages:**
    - Python (using requests)
    - TypeScript (using fetch)
    - JavaScript (using fetch)
    - Java (planned)
    - Go (planned)

    **Binding Styles:**
    - native: Use native language HTTP libraries
    - sdk: Full SDK with utilities and types
    - minimal: Minimal implementation

    **Generated Features:**
    - Type-safe method signatures
    - Request/response type definitions
    - Authentication handling
    - Error handling

    Args:
        api_definition_file: Path to API spec file (OpenAPI/Swagger)
        target_languages: Languages to generate bindings for
        binding_style: Binding style (native, sdk, minimal)
        include_types: Whether to include type definitions

    Returns:
        Dictionary containing:
        - api_name: Name of the API
        - api_version: API version
        - endpoints_count: Number of endpoints
        - bindings: Generated bindings per language
        - warnings: Generation warnings

    Example usage:
        # Generate Python and TypeScript clients
        result = generate_language_bindings(
            api_definition_file="/path/to/openapi.json",
            target_languages=["python", "typescript"],
            binding_style="native"
        )

        # Save generated code
        for binding in result["bindings"]:
            with open(binding["file_name"], "w") as f:
                f.write(binding["code"])
    """
    logger = get_logger("tool.generate_language_bindings")
    start_time = time.time()

    if target_languages is None:
        target_languages = ["python", "typescript", "javascript"]

    logger.info(
        "tool_invoked",
        tool="generate_language_bindings",
        api_definition_file=api_definition_file,
        target_languages=target_languages,
        binding_style=binding_style,
    )

    try:
        result = generate_language_bindings_impl(
            api_definition_file=api_definition_file,
            target_languages=target_languages,
            binding_style=binding_style,
            include_types=include_types,
        )

        execution_time = time.time() - start_time

        logger.info(
            "tool_completed",
            tool="generate_language_bindings",
            execution_time_seconds=round(execution_time, 3),
            bindings_generated=len(result.bindings),
        )

        return {
            "api_name": result.api_name,
            "api_version": result.api_version,
            "base_url": result.base_url,
            "endpoints_count": result.endpoints_count,
            "bindings": [
                {
                    "language": b.language,
                    "file_name": b.file_name,
                    "code": b.code,
                    "imports": b.imports,
                    "dependencies": b.dependencies,
                    "types_generated": b.types_generated,
                }
                for b in result.bindings
            ],
            "warnings": result.warnings,
            "execution_time_ms": result.execution_time_ms,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "tool_failed",
            tool="generate_language_bindings",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
        )
        sentry_sdk.capture_exception(e)
        raise


# =============================================================================
# MCP Registration
# =============================================================================

def _create_mcp_field_definitions():
    """Create field definitions for MCP tool registration."""
    return {
        'search_multi_language': {
            'project_folder': Field(description="Root folder of the project (absolute path)"),
            'semantic_pattern': Field(description="Semantic pattern to search for (e.g., 'async function', 'try catch')"),
            'languages': Field(default=None, description="Languages to search (['auto'] for auto-detection)"),
            'group_by': Field(default="semantic", description="Grouping strategy ('semantic', 'language', 'file')"),
            'max_results_per_language': Field(default=100, description="Maximum results per language"),
        },
        'find_language_equivalents': {
            'pattern_description': Field(description="Description of the pattern to find (e.g., 'list comprehension')"),
            'source_language': Field(default=None, description="Optional source language to highlight"),
            'target_languages': Field(default=None, description="Languages to include in results"),
        },
        'convert_code_language': {
            'code_snippet': Field(description="Code to convert"),
            'from_language': Field(description="Source language (python, typescript, javascript, java)"),
            'to_language': Field(description="Target language (python, typescript, javascript, kotlin)"),
            'conversion_style': Field(default="idiomatic", description="Conversion style ('literal', 'idiomatic', 'compatible')"),
            'include_comments': Field(default=True, description="Whether to include conversion comments"),
        },
        'refactor_polyglot': {
            'project_folder': Field(description="Root folder of the project"),
            'refactoring_type': Field(description="Type of refactoring ('rename_api', 'extract_constant', 'update_contract')"),
            'symbol_name': Field(description="Symbol being refactored"),
            'new_name': Field(default=None, description="New name (required for rename operations)"),
            'affected_languages': Field(default=None, description="Languages to include (['all'] for all)"),
            'dry_run': Field(default=True, description="If True, only preview changes"),
        },
        'generate_language_bindings': {
            'api_definition_file': Field(description="Path to API spec file (OpenAPI/Swagger JSON or YAML)"),
            'target_languages': Field(default=None, description="Languages to generate bindings for"),
            'binding_style': Field(default="native", description="Binding style ('native', 'sdk', 'minimal')"),
            'include_types': Field(default=True, description="Whether to include type definitions"),
        },
    }


def register_cross_language_tools(mcp: FastMCP) -> None:
    """Register all cross-language feature tools with MCP server.

    Args:
        mcp: FastMCP server instance
    """
    fields = _create_mcp_field_definitions()

    @mcp.tool()
    def search_multi_language(
        project_folder: str = fields['search_multi_language']['project_folder'],
        semantic_pattern: str = fields['search_multi_language']['semantic_pattern'],
        languages: Optional[List[str]] = fields['search_multi_language']['languages'],
        group_by: str = fields['search_multi_language']['group_by'],
        max_results_per_language: int = fields['search_multi_language']['max_results_per_language'],
    ) -> Dict[str, Any]:
        """Search across multiple programming languages for semantically equivalent patterns."""
        return search_multi_language_tool(
            project_folder=project_folder,
            semantic_pattern=semantic_pattern,
            languages=languages,
            group_by=group_by,
            max_results_per_language=max_results_per_language,
        )

    @mcp.tool()
    def find_language_equivalents(
        pattern_description: str = fields['find_language_equivalents']['pattern_description'],
        source_language: Optional[str] = fields['find_language_equivalents']['source_language'],
        target_languages: Optional[List[str]] = fields['find_language_equivalents']['target_languages'],
    ) -> Dict[str, Any]:
        """Find equivalent patterns across programming languages."""
        return find_language_equivalents_tool(
            pattern_description=pattern_description,
            source_language=source_language,
            target_languages=target_languages,
        )

    @mcp.tool()
    def convert_code_language(
        code_snippet: str = fields['convert_code_language']['code_snippet'],
        from_language: str = fields['convert_code_language']['from_language'],
        to_language: str = fields['convert_code_language']['to_language'],
        conversion_style: str = fields['convert_code_language']['conversion_style'],
        include_comments: bool = fields['convert_code_language']['include_comments'],
    ) -> Dict[str, Any]:
        """Convert code from one programming language to another."""
        return convert_code_language_tool(
            code_snippet=code_snippet,
            from_language=from_language,
            to_language=to_language,
            conversion_style=conversion_style,
            include_comments=include_comments,
        )

    @mcp.tool()
    def refactor_polyglot(
        project_folder: str = fields['refactor_polyglot']['project_folder'],
        refactoring_type: str = fields['refactor_polyglot']['refactoring_type'],
        symbol_name: str = fields['refactor_polyglot']['symbol_name'],
        new_name: Optional[str] = fields['refactor_polyglot']['new_name'],
        affected_languages: Optional[List[str]] = fields['refactor_polyglot']['affected_languages'],
        dry_run: bool = fields['refactor_polyglot']['dry_run'],
    ) -> Dict[str, Any]:
        """Refactor across multiple programming languages atomically."""
        return refactor_polyglot_tool(
            project_folder=project_folder,
            refactoring_type=refactoring_type,
            symbol_name=symbol_name,
            new_name=new_name,
            affected_languages=affected_languages,
            dry_run=dry_run,
        )

    @mcp.tool()
    def generate_language_bindings(
        api_definition_file: str = fields['generate_language_bindings']['api_definition_file'],
        target_languages: Optional[List[str]] = fields['generate_language_bindings']['target_languages'],
        binding_style: str = fields['generate_language_bindings']['binding_style'],
        include_types: bool = fields['generate_language_bindings']['include_types'],
    ) -> Dict[str, Any]:
        """Generate API client bindings for multiple languages from specifications."""
        return generate_language_bindings_tool(
            api_definition_file=api_definition_file,
            target_languages=target_languages,
            binding_style=binding_style,
            include_types=include_types,
        )
