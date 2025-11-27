"""Quality reporting system for code standards enforcement.

This module provides functionality to generate comprehensive quality reports:
- Markdown reports (human-readable)
- JSON reports (machine-readable)
- HTML reports (future)
- Trend tracking with baseline comparison
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.standards import EnforcementResult, RuleViolation

logger = get_logger(__name__)

# =============================================================================
# Markdown Report Generation
# =============================================================================

def generate_markdown_report(
    result: EnforcementResult,
    project_name: str = "Project",
    include_violations: bool = True,
    max_violations_per_rule: int = 10
) -> str:
    """Generate a Markdown-formatted quality report.

    Args:
        result: EnforcementResult from enforce_standards
        project_name: Name of the project for report header
        include_violations: Whether to include violation details
        max_violations_per_rule: Maximum violations to show per rule

    Returns:
        Markdown-formatted report as string
    """
    report_lines = []

    # Header
    report_lines.append(f"# Code Quality Report: {project_name}")
    report_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Execution Time:** {result.execution_time_ms}ms")
    report_lines.append(f"**Files Scanned:** {result.files_scanned}")
    report_lines.append("\n---\n")

    # Summary
    summary = result.summary
    report_lines.append("## Summary\n")
    report_lines.append(f"- **Total Violations:** {summary['total_violations']}")
    report_lines.append(f"- **Error:** {summary['error_count']}")
    report_lines.append(f"- **Warning:** {summary['warning_count']}")
    report_lines.append(f"- **Info:** {summary['info_count']}")
    report_lines.append(f"- **Files with Violations:** {summary['files_with_violations']}")
    report_lines.append(f"- **Rules Executed:** {len(result.rules_executed)}")
    report_lines.append("\n---\n")

    # Violations by Severity
    report_lines.append("## Violations by Severity\n")

    for severity in ["error", "warning", "info"]:
        violations = result.violations_by_severity.get(severity, [])
        if violations:
            report_lines.append(f"### {severity.upper()} ({len(violations)})\n")

            # Group by rule
            by_rule: Dict[str, List[RuleViolation]] = {}
            for v in violations:
                if v.rule_id not in by_rule:
                    by_rule[v.rule_id] = []
                by_rule[v.rule_id].append(v)

            for rule_id, rule_violations in sorted(by_rule.items()):
                report_lines.append(f"#### `{rule_id}` ({len(rule_violations)} occurrences)")

                if include_violations:
                    # Show first N violations
                    shown = min(len(rule_violations), max_violations_per_rule)
                    for v in rule_violations[:shown]:
                        file_name = Path(v.file).name
                        report_lines.append(f"- **{file_name}:{v.line}** - {v.message}")

                    if len(rule_violations) > max_violations_per_rule:
                        remaining = len(rule_violations) - max_violations_per_rule
                        report_lines.append(f"  - *...and {remaining} more*")

                report_lines.append("")

    # Top Issues by Rule
    report_lines.append("\n---\n")
    report_lines.append("## Top Issues by Rule\n")

    # Sort rules by violation count
    rules_sorted = sorted(
        result.violations_by_rule.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]  # Top 10

    report_lines.append("| Rule | Count | Severity |")
    report_lines.append("|------|-------|----------|")

    for rule_id, violations in rules_sorted:
        # Get most common severity for this rule
        severities = [v.severity for v in violations]
        most_common_severity = max(set(severities), key=severities.count)

        report_lines.append(f"| `{rule_id}` | {len(violations)} | {most_common_severity} |")

    # Files with Most Violations
    report_lines.append("\n---\n")
    report_lines.append("## Files with Most Violations\n")

    # Sort files by violation count
    files_sorted = sorted(
        result.violations_by_file.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]  # Top 10

    report_lines.append("| File | Violations | Errors | Warnings | Info |")
    report_lines.append("|------|------------|--------|----------|------|")

    for file_path, violations in files_sorted:
        file_name = Path(file_path).name
        error_count = sum(1 for v in violations if v.severity == "error")
        warning_count = sum(1 for v in violations if v.severity == "warning")
        info_count = sum(1 for v in violations if v.severity == "info")

        report_lines.append(
            f"| `{file_name}` | {len(violations)} | {error_count} | {warning_count} | {info_count} |"
        )

    # Recommendations
    report_lines.append("\n---\n")
    report_lines.append("## Recommendations\n")

    if summary['error_count'] > 0:
        report_lines.append(f"- **🔴 {summary['error_count']} errors** require immediate attention")

    if summary['warning_count'] > 0:
        report_lines.append(f"- **🟡 {summary['warning_count']} warnings** should be addressed")

    if summary['info_count'] > 0:
        report_lines.append(f"- **ℹ️ {summary['info_count']} info items** are suggestions for improvement")

    # Auto-fix suggestion
    fixable_count = sum(
        1 for v in result.violations
        if v.fix_suggestion is not None
    )

    if fixable_count > 0:
        report_lines.append(f"\n**💡 {fixable_count} violations have automatic fixes available.**")
        report_lines.append("Consider using `apply_standards_fixes` to auto-fix safe violations.")

    return "\n".join(report_lines)


# =============================================================================
# JSON Report Generation
# =============================================================================

def generate_json_report(
    result: EnforcementResult,
    project_name: str = "Project",
    include_code_snippets: bool = False
) -> Dict[str, Any]:
    """Generate a JSON-formatted quality report.

    Args:
        result: EnforcementResult from enforce_standards
        project_name: Name of the project
        include_code_snippets: Whether to include code snippets in output

    Returns:
        Dictionary ready for JSON serialization
    """
    report = {
        "project": project_name,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_violations": result.summary["total_violations"],
            "error_count": result.summary["error_count"],
            "warning_count": result.summary["warning_count"],
            "info_count": result.summary["info_count"],
            "files_scanned": result.files_scanned,
            "files_with_violations": result.summary["files_with_violations"],
            "rules_executed": len(result.rules_executed),
            "execution_time_ms": result.execution_time_ms
        },
        "rules_executed": result.rules_executed,
        "violations_by_severity": {
            "error": len(result.violations_by_severity.get("error", [])),
            "warning": len(result.violations_by_severity.get("warning", [])),
            "info": len(result.violations_by_severity.get("info", []))
        },
        "violations_by_rule": {
            rule_id: len(violations)
            for rule_id, violations in result.violations_by_rule.items()
        },
        "violations_by_file": {
            file: len(violations)
            for file, violations in result.violations_by_file.items()
        },
        "violations": []
    }

    # Add violations
    for v in result.violations:
        violation_dict = {
            "file": v.file,
            "line": v.line,
            "column": v.column,
            "end_line": v.end_line,
            "end_column": v.end_column,
            "severity": v.severity,
            "rule_id": v.rule_id,
            "message": v.message,
            "fix_available": v.fix_suggestion is not None
        }

        if include_code_snippets:
            violation_dict["code_snippet"] = v.code_snippet
            violation_dict["fix_suggestion"] = v.fix_suggestion

        report["violations"].append(violation_dict)

    # Add top issues
    top_rules = sorted(
        result.violations_by_rule.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]

    report["top_issues"] = [
        {
            "rule_id": rule_id,
            "count": len(violations),
            "severity": violations[0].severity if violations else "unknown"
        }
        for rule_id, violations in top_rules
    ]

    # Add most problematic files
    top_files = sorted(
        result.violations_by_file.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]

    report["most_violations_files"] = [
        {
            "file": file,
            "violations": len(violations),
            "errors": sum(1 for v in violations if v.severity == "error"),
            "warnings": sum(1 for v in violations if v.severity == "warning"),
            "info": sum(1 for v in violations if v.severity == "info")
        }
        for file, violations in top_files
    ]

    return report


# =============================================================================
# Report Generator (Main Entry Point)
# =============================================================================

def generate_quality_report_impl(
    result: EnforcementResult,
    project_name: str = "Project",
    output_format: str = "markdown",
    include_violations: bool = True,
    include_code_snippets: bool = False,
    save_to_file: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a code quality report in various formats.

    Args:
        result: EnforcementResult from enforce_standards
        project_name: Name of the project
        output_format: Format ('markdown', 'json')
        include_violations: Whether to include violation details
        include_code_snippets: Whether to include code snippets (JSON only)
        save_to_file: Optional file path to save report

    Returns:
        Dictionary with report content and metadata
    """
    if output_format == "markdown":
        report_content = generate_markdown_report(
            result=result,
            project_name=project_name,
            include_violations=include_violations
        )

        response = {
            "format": "markdown",
            "content": report_content,
            "summary": result.summary
        }

        # Save to file if requested
        if save_to_file:
            with open(save_to_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            response["saved_to"] = save_to_file

        return response

    elif output_format == "json":
        report_content = generate_json_report(
            result=result,
            project_name=project_name,
            include_code_snippets=include_code_snippets
        )

        # Save to file if requested
        if save_to_file:
            with open(save_to_file, 'w', encoding='utf-8') as f:
                json.dump(report_content, f, indent=2)

        return {
            "format": "json",
            "content": report_content,
            "summary": result.summary,
            "saved_to": save_to_file if save_to_file else None
        }

    else:
        raise ValueError(f"Unsupported output format: {output_format}")
