"""MCP tool definitions for documentation generation features.

This module registers MCP tools for:
- generate_docstrings: Auto-generate docstrings/JSDoc
- generate_readme_sections: Generate README sections
- generate_api_docs: Generate API documentation
- generate_changelog: Generate changelog from git commits
- sync_documentation: Keep docs synchronized with code
"""

import time
from typing import Any, Dict, List, Optional

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ast_grep_mcp.constants import ConversionFactors, DisplayDefaults, FormattingDefaults
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.documentation.api_docs_generator import generate_api_docs_impl
from ast_grep_mcp.features.documentation.changelog_generator import generate_changelog_impl
from ast_grep_mcp.features.documentation.docstring_generator import generate_docstrings_impl
from ast_grep_mcp.features.documentation.readme_generator import generate_readme_sections_impl
from ast_grep_mcp.features.documentation.sync_checker import sync_documentation_impl
from ast_grep_mcp.models.documentation import ApiRoute


def _log_tool_error(logger: Any, tool: str, execution_time: float, e: Exception) -> None:
    logger.error(
        "tool_failed",
        tool=tool,
        execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
        error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
    )
    sentry_sdk.capture_exception(e)


def _format_docstrings_response(result: Any) -> Dict[str, Any]:
    return {
        "summary": {
            "total_functions": result.total_functions,
            "functions_documented": result.functions_documented,
            "functions_generated": result.functions_generated,
            "functions_skipped": result.functions_skipped,
            "dry_run": result.dry_run,
        },
        "docstrings": [
            {
                "function_name": d.function_name,
                "file_path": d.file_path,
                "line_number": d.line_number,
                "docstring": d.docstring,
                "style": d.style.value,
                "confidence": d.confidence,
            }
            for d in result.docstrings
        ],
        "files_modified": result.files_modified,
        "execution_time_ms": result.execution_time_ms,
    }


def _format_readme_response(result: Any) -> Dict[str, Any]:
    return {
        "project_info": {
            "name": result.project_info.name,
            "version": result.project_info.version,
            "description": result.project_info.description,
            "language": result.project_info.language,
            "package_manager": result.project_info.package_manager,
            "frameworks": result.project_info.frameworks,
            "has_tests": result.project_info.has_tests,
            "has_docs": result.project_info.has_docs,
        },
        "sections": [{"type": s.section_type, "title": s.title, "content": s.content} for s in result.sections],
        "full_readme": result.full_readme,
        "execution_time_ms": result.execution_time_ms,
    }


def _format_changelog_version(v: Any) -> Dict[str, Any]:
    entries_data = {
        change_type.value: [
            {
                "description": e.description,
                "commit_hash": e.commit_hash,
                "scope": e.scope,
                "is_breaking": e.is_breaking,
                "issues": e.issues,
                "prs": e.prs,
            }
            for e in entries
        ]
        for change_type, entries in v.entries.items()
    }
    return {
        "version": v.version,
        "date": v.date,
        "entries": entries_data,
        "is_unreleased": v.is_unreleased,
    }


def _format_sync_doc_coverage(result: Any) -> int | float:
    if result.total_functions > 0:
        return float(round(result.documented_functions / result.total_functions * ConversionFactors.PERCENT_MULTIPLIER, 1))
    return 0


def _format_sync_response(result: Any) -> Dict[str, Any]:
    return {
        "summary": {
            "total_functions": result.total_functions,
            "documented_functions": result.documented_functions,
            "undocumented_functions": result.undocumented_functions,
            "stale_docstrings": result.stale_docstrings,
            "documentation_coverage": _format_sync_doc_coverage(result),
        },
        "issues": [
            {
                "issue_type": i.issue_type,
                "file_path": i.file_path,
                "line_number": i.line_number,
                "function_name": i.function_name,
                "description": i.description,
                "suggested_fix": i.suggested_fix,
                "severity": i.severity,
            }
            for i in result.issues
        ],
        "suggestions": result.suggestions,
        "files_updated": result.files_updated,
        "check_only": result.check_only,
        "execution_time_ms": result.execution_time_ms,
    }


# =============================================================================
# Tool Implementations
# =============================================================================


def generate_docstrings_tool(
    project_folder: str,
    file_pattern: str,
    language: str,
    style: str = "auto",
    overwrite_existing: bool = False,
    dry_run: bool = True,
    skip_private: bool = True,
) -> Dict[str, Any]:
    logger = get_logger("tool.generate_docstrings")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="generate_docstrings",
        project_folder=project_folder,
        file_pattern=file_pattern,
        language=language,
        style=style,
        dry_run=dry_run,
    )

    try:
        result = generate_docstrings_impl(
            project_folder=project_folder,
            file_pattern=file_pattern,
            language=language,
            style=style,
            overwrite_existing=overwrite_existing,
            dry_run=dry_run,
            skip_private=skip_private,
        )
        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="generate_docstrings",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            total_functions=result.total_functions,
            functions_generated=result.functions_generated,
        )
        return _format_docstrings_response(result)

    except Exception as e:
        execution_time = time.time() - start_time
        _log_tool_error(logger, "generate_docstrings", execution_time, e)
        raise


def generate_readme_sections_tool(
    project_folder: str,
    language: str = "auto",
    sections: List[str] | None = None,
    include_examples: bool = True,
) -> Dict[str, Any]:
    logger = get_logger("tool.generate_readme_sections")
    start_time = time.time()

    if sections is None:
        sections = ["all"]

    logger.info(
        "tool_invoked",
        tool="generate_readme_sections",
        project_folder=project_folder,
        language=language,
        sections=sections,
    )

    try:
        result = generate_readme_sections_impl(
            project_folder=project_folder,
            language=language,
            sections=sections,
            include_examples=include_examples,
        )
        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="generate_readme_sections",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            sections_generated=len(result.sections),
        )
        return _format_readme_response(result)

    except Exception as e:
        execution_time = time.time() - start_time
        _log_tool_error(logger, "generate_readme_sections", execution_time, e)
        raise


def _format_route_for_output(route: ApiRoute) -> Dict[str, Any]:
    """Format a single route for API output.

    Args:
        route: ApiRoute object

    Returns:
        Dictionary with route details
    """
    return {
        "path": route.path,
        "method": route.method,
        "handler_name": route.handler_name,
        "file_path": route.file_path,
        "line_number": route.line_number,
        "parameters": [{"name": p.name, "location": p.location, "type": p.type_hint, "required": p.required} for p in route.parameters],
    }


def generate_api_docs_tool(
    project_folder: str,
    language: str,
    framework: Optional[str] = None,
    output_format: str = "markdown",
    include_examples: bool = True,
) -> Dict[str, Any]:
    logger = get_logger("tool.generate_api_docs")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="generate_api_docs",
        project_folder=project_folder,
        language=language,
        framework=framework,
        output_format=output_format,
    )

    try:
        result = generate_api_docs_impl(
            project_folder=project_folder,
            language=language,
            framework=framework,
            output_format=output_format,
            include_examples=include_examples,
        )
        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="generate_api_docs",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            routes_found=len(result.routes),
            framework=result.framework,
        )
        return {
            "routes": [_format_route_for_output(r) for r in result.routes],
            "markdown": result.markdown,
            "openapi_spec": result.openapi_spec,
            "framework": result.framework,
            "execution_time_ms": result.execution_time_ms,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        _log_tool_error(logger, "generate_api_docs", execution_time, e)
        raise


def generate_changelog_tool(
    project_folder: str,
    from_version: Optional[str] = None,
    to_version: str = "HEAD",
    changelog_format: str = "keepachangelog",
    group_by: str = "type",
) -> Dict[str, Any]:
    logger = get_logger("tool.generate_changelog")
    start_time = time.time()

    logger.info(
        "tool_invoked",
        tool="generate_changelog",
        project_folder=project_folder,
        from_version=from_version,
        to_version=to_version,
        format=changelog_format,
    )

    try:
        result = generate_changelog_impl(
            project_folder=project_folder,
            from_version=from_version,
            to_version=to_version,
            changelog_format=changelog_format,
            group_by=group_by,
        )
        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="generate_changelog",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            commits_processed=result.commits_processed,
            versions=len(result.versions),
        )
        return {
            "versions": [_format_changelog_version(v) for v in result.versions],
            "markdown": result.markdown,
            "commits_processed": result.commits_processed,
            "commits_skipped": result.commits_skipped,
            "execution_time_ms": result.execution_time_ms,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        _log_tool_error(logger, "generate_changelog", execution_time, e)
        raise


def sync_documentation_tool(
    project_folder: str,
    language: str,
    doc_types: List[str] | None = None,
    check_only: bool = True,
) -> Dict[str, Any]:
    logger = get_logger("tool.sync_documentation")
    start_time = time.time()

    if doc_types is None:
        doc_types = ["all"]

    logger.info(
        "tool_invoked",
        tool="sync_documentation",
        project_folder=project_folder,
        language=language,
        doc_types=doc_types,
        check_only=check_only,
    )

    try:
        result = sync_documentation_impl(
            project_folder=project_folder,
            language=language,
            doc_types=doc_types,
            check_only=check_only,
        )
        execution_time = time.time() - start_time
        logger.info(
            "tool_completed",
            tool="sync_documentation",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            issues_found=len(result.issues),
        )
        return _format_sync_response(result)

    except Exception as e:
        execution_time = time.time() - start_time
        _log_tool_error(logger, "sync_documentation", execution_time, e)
        raise


# =============================================================================
# MCP Registration
# =============================================================================


def _create_mcp_field_definitions() -> Dict[str, Dict[str, Any]]:
    """Create field definitions for MCP tool registration."""
    return {
        "generate_docstrings": {
            "project_folder": Field(description="Root folder of the project (absolute path)"),
            "file_pattern": Field(description="Glob pattern for files to process (e.g., '**/*.py')"),
            "language": Field(description="Programming language (python, typescript, javascript, java)"),
            "style": Field(default="auto", description="Docstring style (google, numpy, sphinx, jsdoc, javadoc, auto)"),
            "overwrite_existing": Field(default=False, description="If True, replace existing docstrings"),
            "dry_run": Field(default=True, description="If True, only preview changes without applying"),
            "skip_private": Field(default=True, description="If True, skip private functions (starting with _)"),
        },
        "generate_readme_sections": {
            "project_folder": Field(description="Root folder of the project (absolute path)"),
            "language": Field(default="auto", description="Programming language (or 'auto' for detection)"),
            "sections": Field(
                default_factory=lambda: ["all"],
                description="Sections to generate (installation, usage, features, api, structure, contributing, license, or 'all')",
            ),
            "include_examples": Field(default=True, description="Whether to include code examples"),
        },
        "generate_api_docs": {
            "project_folder": Field(description="Root folder of the project (absolute path)"),
            "language": Field(description="Programming language (python, typescript, javascript)"),
            "framework": Field(default=None, description="Framework name (express, fastapi, flask, or None for auto-detect)"),
            "output_format": Field(default="markdown", description="Output format ('markdown', 'openapi', 'both')"),
            "include_examples": Field(default=True, description="Whether to include request/response examples"),
        },
        "generate_changelog": {
            "project_folder": Field(description="Root folder of the project (must be git repository)"),
            "from_version": Field(default=None, description="Starting version/tag (None = last tag or first commit)"),
            "to_version": Field(default="HEAD", description="Ending version/tag (default: HEAD)"),
            "changelog_format": Field(default="keepachangelog", description="Output format ('keepachangelog', 'conventional', 'json')"),
            "group_by": Field(default="type", description="Grouping strategy ('type', 'scope')"),
        },
        "sync_documentation": {
            "project_folder": Field(description="Root folder of the project (absolute path)"),
            "language": Field(description="Programming language (python, typescript, javascript, java)"),
            "doc_types": Field(default_factory=lambda: ["all"], description="Types to check ('docstrings', 'links', 'all')"),
            "check_only": Field(default=True, description="If True, only report issues (no changes)"),
        },
    }


def _register_generation_tools(mcp: FastMCP, fields: Dict[str, Dict[str, Any]]) -> None:
    @mcp.tool()
    def generate_docstrings(
        project_folder: str = fields["generate_docstrings"]["project_folder"],
        file_pattern: str = fields["generate_docstrings"]["file_pattern"],
        language: str = fields["generate_docstrings"]["language"],
        style: str = fields["generate_docstrings"]["style"],
        overwrite_existing: bool = fields["generate_docstrings"]["overwrite_existing"],
        dry_run: bool = fields["generate_docstrings"]["dry_run"],
        skip_private: bool = fields["generate_docstrings"]["skip_private"],
    ) -> Dict[str, Any]:
        """Generate docstrings/JSDoc for undocumented functions."""
        return generate_docstrings_tool(
            project_folder=project_folder,
            file_pattern=file_pattern,
            language=language,
            style=style,
            overwrite_existing=overwrite_existing,
            dry_run=dry_run,
            skip_private=skip_private,
        )

    @mcp.tool()
    def generate_readme_sections(
        project_folder: str = fields["generate_readme_sections"]["project_folder"],
        language: str = fields["generate_readme_sections"]["language"],
        sections: List[str] = fields["generate_readme_sections"]["sections"],
        include_examples: bool = fields["generate_readme_sections"]["include_examples"],
    ) -> Dict[str, Any]:
        """Generate README.md sections from code analysis."""
        return generate_readme_sections_tool(
            project_folder=project_folder,
            language=language,
            sections=sections,
            include_examples=include_examples,
        )


def _register_api_changelog_sync_tools(mcp: FastMCP, fields: Dict[str, Dict[str, Any]]) -> None:
    @mcp.tool()
    def generate_api_docs(
        project_folder: str = fields["generate_api_docs"]["project_folder"],
        language: str = fields["generate_api_docs"]["language"],
        framework: Optional[str] = fields["generate_api_docs"]["framework"],
        output_format: str = fields["generate_api_docs"]["output_format"],
        include_examples: bool = fields["generate_api_docs"]["include_examples"],
    ) -> Dict[str, Any]:
        """Generate API documentation from route definitions."""
        return generate_api_docs_tool(
            project_folder=project_folder,
            language=language,
            framework=framework,
            output_format=output_format,
            include_examples=include_examples,
        )

    @mcp.tool()
    def generate_changelog(
        project_folder: str = fields["generate_changelog"]["project_folder"],
        from_version: Optional[str] = fields["generate_changelog"]["from_version"],
        to_version: str = fields["generate_changelog"]["to_version"],
        changelog_format: str = fields["generate_changelog"]["changelog_format"],
        group_by: str = fields["generate_changelog"]["group_by"],
    ) -> Dict[str, Any]:
        """Generate changelog from git commits."""
        return generate_changelog_tool(
            project_folder=project_folder,
            from_version=from_version,
            to_version=to_version,
            changelog_format=changelog_format,
            group_by=group_by,
        )

    @mcp.tool()
    def sync_documentation(
        project_folder: str = fields["sync_documentation"]["project_folder"],
        language: str = fields["sync_documentation"]["language"],
        doc_types: List[str] = fields["sync_documentation"]["doc_types"],
        check_only: bool = fields["sync_documentation"]["check_only"],
    ) -> Dict[str, Any]:
        """Synchronize documentation with code."""
        return sync_documentation_tool(
            project_folder=project_folder,
            language=language,
            doc_types=doc_types,
            check_only=check_only,
        )


def register_documentation_tools(mcp: FastMCP) -> None:
    """Register all documentation feature tools with MCP server.

    Args:
        mcp: FastMCP server instance
    """
    fields = _create_mcp_field_definitions()
    _register_generation_tools(mcp, fields)
    _register_api_changelog_sync_tools(mcp, fields)
