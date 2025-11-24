"""MCP tool definitions for code quality and standards features.

This module registers MCP tools for:
- detect_code_smells: Code smell detection
- create_linting_rule: Create custom linting rules
- list_rule_templates: Browse pre-built rule templates
- enforce_standards: Standards enforcement engine
"""

import time
import yaml
from typing import Any, Dict, List, Optional
from pydantic import Field

from mcp.server.fastmcp import FastMCP

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.quality.smells import detect_code_smells_impl
from ast_grep_mcp.features.quality.rules import (
    RULE_TEMPLATES,
    get_available_templates,
    create_rule_from_template,
    save_rule_to_project
)
from ast_grep_mcp.features.quality.validator import validate_rule_definition
from ast_grep_mcp.features.quality.enforcer import (
    enforce_standards_impl,
    format_violation_report
)
from ast_grep_mcp.models.standards import (
    LintingRule,
    RuleValidationError,
    RuleStorageError
)
import sentry_sdk


def register_quality_tools(mcp: FastMCP) -> None:
    """Register all quality feature tools with MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    def detect_code_smells(
        project_folder: str = Field(description="The absolute path to the project folder to analyze"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: ["**/node_modules/**", "**/__pycache__/**", "**/venv/**", "**/.venv/**", "**/site-packages/**", "**/test*/**", "**/*test*"],
            description="Glob patterns for files to exclude"
        ),
        long_function_lines: int = Field(default=50, description="Line count threshold for long function smell (default: 50)"),
        parameter_count: int = Field(default=5, description="Parameter count threshold for parameter bloat (default: 5)"),
        nesting_depth: int = Field(default=4, description="Nesting depth threshold for deep nesting smell (default: 4)"),
        class_lines: int = Field(default=300, description="Line count threshold for large class smell (default: 300)"),
        class_methods: int = Field(default=20, description="Method count threshold for large class smell (default: 20)"),
        detect_magic_numbers: bool = Field(default=True, description="Whether to detect magic number smells"),
        severity_filter: str = Field(default="all", description="Filter by severity: 'all', 'high', 'medium', 'low'"),
        max_threads: int = Field(default=4, description="Number of parallel threads for analysis (default: 4)")
    ) -> Dict[str, Any]:
        """
        Detect common code smells in a project.

        Identifies patterns that indicate potential design or maintainability issues:
        - Long Functions: Functions exceeding line count threshold
        - Parameter Bloat: Functions with too many parameters
        - Deep Nesting: Excessive nesting depth (if/for/while)
        - Large Classes: Classes with too many methods or lines
        - Magic Numbers: Hard-coded numeric/string literals (excludes 0, 1, -1)

        Each smell includes severity (high/medium/low) and actionable suggestions.

        Example usage:
          detect_code_smells(project_folder="/path/to/project", language="python")
          detect_code_smells(project_folder="/path/to/project", language="typescript", severity_filter="high")
        """
        logger = get_logger("tool.detect_code_smells")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="detect_code_smells",
            project_folder=project_folder,
            language=language,
        )

        try:
            result = detect_code_smells_impl(
                project_folder=project_folder,
                language=language,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                long_function_lines=long_function_lines,
                parameter_count=parameter_count,
                nesting_depth=nesting_depth,
                class_lines=class_lines,
                class_methods=class_methods,
                detect_magic_numbers=detect_magic_numbers,
                severity_filter=severity_filter,
                max_threads=max_threads
            )

            execution_time = time.time() - start_time
            result["execution_time_ms"] = round(execution_time * 1000)

            logger.info(
                "tool_completed",
                tool="detect_code_smells",
                files_analyzed=result.get("files_analyzed", 0),
                total_smells=result.get("total_smells", 0),
                execution_time_seconds=round(execution_time, 3)
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="detect_code_smells",
                error=str(e),
                execution_time_seconds=round(execution_time, 3)
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "detect_code_smells",
                "project_folder": project_folder,
                "language": language,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def create_linting_rule(
        rule_name: str = Field(description="Unique rule identifier (e.g., 'no-console-log')"),
        description: str = Field(description="Human-readable description of what the rule checks"),
        pattern: str = Field(description="ast-grep pattern to match (e.g., 'console.log($$$)')"),
        severity: str = Field(description="Severity level: 'error', 'warning', or 'info'"),
        language: str = Field(description="Target language (python, typescript, javascript, java, etc.)"),
        suggested_fix: Optional[str] = Field(default=None, description="Optional replacement pattern or fix suggestion"),
        note: Optional[str] = Field(default=None, description="Additional note or explanation"),
        save_to_project: bool = Field(default=False, description="If True, save rule to project's .ast-grep-rules/"),
        project_folder: Optional[str] = Field(default=None, description="Project folder (required if save_to_project=True)"),
        use_template: Optional[str] = Field(default=None, description="Optional template ID to use as base")
    ) -> Dict[str, Any]:
        """
        Create a custom linting rule using ast-grep patterns.

        This tool allows you to define custom code quality rules that can be enforced
        across your codebase. Rules can detect code smells, anti-patterns, security
        vulnerabilities, or enforce style guidelines.

        **Templates:** Use `use_template` parameter to start from a pre-built template
        (see list_rule_templates tool).

        **Pattern Syntax Examples:**
        - `console.log($$$)` - matches any console.log call
        - `var $NAME = $$$` - matches var declarations
        - `except:` - matches bare except clauses in Python

        Returns:
            Dictionary containing rule definition, validation results, saved path, and YAML
        """
        logger = get_logger("tool.create_linting_rule")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="create_linting_rule",
            rule_name=rule_name,
            language=language,
            severity=severity,
            use_template=use_template,
            save_to_project=save_to_project
        )

        try:
            with sentry_sdk.start_span(op="create_linting_rule", description="Create custom linting rule"):
                # If using a template, create from template
                if use_template:
                    overrides = {
                        'language': language,
                        'severity': severity,
                        'message': description,
                        'pattern': pattern,
                        'note': note,
                        'fix': suggested_fix
                    }
                    # Remove None values
                    overrides = {k: v for k, v in overrides.items() if v is not None}

                    rule = create_rule_from_template(use_template, rule_name, overrides)
                    logger.info("rule_created_from_template", template_id=use_template)
                else:
                    # Create rule from scratch
                    rule = LintingRule(
                        id=rule_name,
                        language=language,
                        severity=severity,
                        message=description,
                        pattern=pattern,
                        note=note,
                        fix=suggested_fix
                    )

                # Validate the rule
                with sentry_sdk.start_span(op="validate_rule", description="Validate rule definition"):
                    validation_result = validate_rule_definition(rule)

                # Save to project if requested
                saved_path: Optional[str] = None
                if save_to_project:
                    if not project_folder:
                        raise ValueError(
                            "project_folder is required when save_to_project=True"
                        )

                    if not validation_result.is_valid:
                        raise RuleValidationError(
                            f"Cannot save invalid rule. Errors: {', '.join(validation_result.errors)}"
                        )

                    with sentry_sdk.start_span(op="save_rule", description="Save rule to project"):
                        saved_path = save_rule_to_project(rule, project_folder)

                # Convert to YAML for output
                rule_dict = rule.to_yaml_dict()
                yaml_str = yaml.dump(rule_dict, default_flow_style=False, sort_keys=False)

                execution_time = time.time() - start_time
                logger.info(
                    "tool_completed",
                    tool="create_linting_rule",
                    execution_time_seconds=round(execution_time, 3),
                    rule_id=rule.id,
                    is_valid=validation_result.is_valid,
                    saved=saved_path is not None
                )

                return {
                    "rule": {
                        "id": rule.id,
                        "language": rule.language,
                        "severity": rule.severity,
                        "message": rule.message,
                        "pattern": rule.pattern,
                        "note": rule.note,
                        "fix": rule.fix,
                        "constraints": rule.constraints
                    },
                    "validation": {
                        "is_valid": validation_result.is_valid,
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings
                    },
                    "saved_to": saved_path,
                    "yaml": yaml_str
                }

        except (RuleValidationError, RuleStorageError, ValueError) as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="create_linting_rule",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200]
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "create_linting_rule",
                "rule_name": rule_name,
                "language": language,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def list_rule_templates(
        language: Optional[str] = Field(default=None, description="Filter by language (python, typescript, javascript, java, etc.)"),
        category: Optional[str] = Field(default=None, description="Filter by category (general, security, performance, style)")
    ) -> Dict[str, Any]:
        """
        List available pre-built rule templates.

        This tool returns a library of pre-built linting rules that can be used
        as-is or customized for your needs. Templates cover common patterns across
        multiple languages including JavaScript/TypeScript, Python, and Java.

        **Template Categories:**
        - `general`: General code quality and best practices
        - `security`: Security vulnerabilities and risks
        - `performance`: Performance anti-patterns
        - `style`: Code style and consistency

        Returns:
            Dictionary with total count, available languages/categories, and template list
        """
        logger = get_logger("tool.list_rule_templates")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="list_rule_templates",
            language=language,
            category=category
        )

        try:
            with sentry_sdk.start_span(op="list_templates", description="Get rule templates"):
                templates = get_available_templates(language=language, category=category)

                # Get unique languages and categories from all templates
                all_templates = list(RULE_TEMPLATES.values())
                all_languages = sorted(set(t.language for t in all_templates))
                all_categories = sorted(set(t.category for t in all_templates))

                # Convert templates to dict format
                template_dicts = [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                        "language": t.language,
                        "severity": t.severity,
                        "pattern": t.pattern,
                        "message": t.message,
                        "note": t.note,
                        "fix": t.fix,
                        "category": t.category
                    }
                    for t in templates
                ]

                execution_time = time.time() - start_time
                logger.info(
                    "tool_completed",
                    tool="list_rule_templates",
                    execution_time_seconds=round(execution_time, 3),
                    total_templates=len(template_dicts),
                    filtered=bool(language or category)
                )

                return {
                    "total_templates": len(template_dicts),
                    "languages": all_languages,
                    "categories": all_categories,
                    "applied_filters": {
                        "language": language,
                        "category": category
                    },
                    "templates": template_dicts
                }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="list_rule_templates",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200]
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "list_rule_templates",
                "language": language,
                "category": category,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def enforce_standards(
        project_folder: str = Field(description="The absolute path to the project folder to scan"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        rule_set: str = Field(
            default="recommended",
            description="Rule set to use: 'recommended', 'security', 'performance', 'style', 'custom', 'all'"
        ),
        custom_rules: List[str] = Field(
            default_factory=list,
            description="List of custom rule IDs from .ast-grep-rules/ (used with rule_set='custom')"
        ),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: [
                "**/node_modules/**", "**/__pycache__/**", "**/venv/**",
                "**/.venv/**", "**/site-packages/**", "**/dist/**",
                "**/build/**", "**/.git/**", "**/coverage/**"
            ],
            description="Glob patterns for files to exclude"
        ),
        severity_threshold: str = Field(
            default="info",
            description="Only report violations >= this severity ('error', 'warning', 'info')"
        ),
        max_violations: int = Field(
            default=100,
            description="Maximum violations to find (0 = unlimited). Stops execution early when reached."
        ),
        max_threads: int = Field(
            default=4,
            description="Number of parallel threads for rule execution (default: 4)"
        ),
        output_format: str = Field(
            default="json",
            description="Output format: 'json' (structured data) or 'text' (human-readable report)"
        )
    ) -> Dict[str, Any]:
        """
        Enforce coding standards by executing linting rules against a project.

        This tool runs a set of linting rules (built-in or custom) against your codebase
        and reports all violations with file locations, severity levels, and fix suggestions.

        **Rule Sets:**
        - `recommended`: General best practices (10 rules)
        - `security`: Security-focused rules (9 rules)
        - `performance`: Performance anti-patterns
        - `style`: Code style and formatting rules (9 rules)
        - `custom`: Load custom rules from .ast-grep-rules/
        - `all`: All built-in rules for the language

        Example usage:
          enforce_standards(project_folder="/path/to/project", language="python")
          enforce_standards(project_folder="/path/to/project", language="typescript", rule_set="security")
        """
        logger = get_logger("tool.enforce_standards")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="enforce_standards",
            project_folder=project_folder,
            language=language,
            rule_set=rule_set,
            custom_rules_count=len(custom_rules),
            max_violations=max_violations,
            max_threads=max_threads
        )

        try:
            # Validate inputs
            if severity_threshold not in ["error", "warning", "info"]:
                raise ValueError(
                    f"Invalid severity_threshold: {severity_threshold}. "
                    "Must be 'error', 'warning', or 'info'."
                )

            if output_format not in ["json", "text"]:
                raise ValueError(
                    f"Invalid output_format: {output_format}. "
                    "Must be 'json' or 'text'."
                )

            # Execute enforcement
            result = enforce_standards_impl(
                project_folder=project_folder,
                language=language,
                rule_set=rule_set,
                custom_rules=custom_rules,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                severity_threshold=severity_threshold,
                max_violations=max_violations,
                max_threads=max_threads
            )

            execution_time = time.time() - start_time

            logger.info(
                "tool_completed",
                tool="enforce_standards",
                execution_time_seconds=round(execution_time, 3),
                total_violations=result.summary["total_violations"],
                files_scanned=result.files_scanned
            )

            # Format output
            if output_format == "text":
                return {
                    "summary": result.summary,
                    "report": format_violation_report(result)
                }
            else:
                # JSON format - return full structured data
                return {
                    "summary": result.summary,
                    "violations": [
                        {
                            "file": v.file,
                            "line": v.line,
                            "column": v.column,
                            "end_line": v.end_line,
                            "end_column": v.end_column,
                            "severity": v.severity,
                            "rule_id": v.rule_id,
                            "message": v.message,
                            "code_snippet": v.code_snippet,
                            "fix_suggestion": v.fix_suggestion,
                            "meta_vars": v.meta_vars
                        }
                        for v in result.violations
                    ],
                    "violations_by_file": {
                        file: [
                            {
                                "line": v.line,
                                "severity": v.severity,
                                "rule_id": v.rule_id,
                                "message": v.message
                            }
                            for v in violations
                        ]
                        for file, violations in result.violations_by_file.items()
                    },
                    "rules_executed": result.rules_executed,
                    "execution_time_ms": result.execution_time_ms
                }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="enforce_standards",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200]
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "enforce_standards",
                "project_folder": project_folder,
                "language": language,
                "rule_set": rule_set,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise
