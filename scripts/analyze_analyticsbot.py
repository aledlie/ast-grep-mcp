#!/usr/bin/env python3
"""Comprehensive code analysis for AnalyticsBot project."""

import json
import sys
from pathlib import Path

from ast_grep_mcp.constants import FormattingDefaults
from ast_grep_mcp.features.deduplication.scoring_scales import AnalyticsBotTopN
from ast_grep_mcp.utils.console_logger import console
from ast_grep_mcp.utils.slicing import take_top_n

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool, detect_code_smells_tool  # noqa: E402
from ast_grep_mcp.features.quality.tools import detect_security_issues_tool  # noqa: E402
from scripts.analysis_output_helpers import count_by_key, log_count_breakdown, print_section_header  # noqa: E402

_TS_PATTERNS = ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.mjs"]
_TS_EXCLUDES = ["**/node_modules/**", "**/build/**", "**/dist/**"]


def _run_complexity_scan(project_path: str) -> dict:  # type: ignore[type-arg]
    """Run TypeScript complexity analysis and log summary."""
    console.log("1. Analyzing complexity metrics (TypeScript/JavaScript)...")
    result = analyze_complexity_tool(
        project_folder=project_path,
        language="typescript",
        include_patterns=_TS_PATTERNS,
        exclude_patterns=_TS_EXCLUDES,
        cyclomatic_threshold=10,
        cognitive_threshold=15,
        nesting_threshold=4,
        length_threshold=50,
        store_results=False,
    )
    return _format_complexity_summary(result)


def _format_complexity_summary(complexity_result: dict) -> dict:  # type: ignore[type-arg]
    """Log complexity summary and return the result dict."""
    summary = complexity_result.get("summary", {})
    functions = complexity_result.get("functions", [])
    console.log(f"   Total functions analyzed: {summary.get('total_functions', 0)}")
    console.log(f"   Total files analyzed: {summary.get('total_files', 0)}")
    console.log(f"   Functions exceeding thresholds: {summary.get('exceeding_threshold', 0)}")
    console.log(f"   Avg cyclomatic complexity: {summary.get('avg_cyclomatic', 0):.1f}")
    console.log(f"   Avg cognitive complexity: {summary.get('avg_cognitive', 0):.1f}")
    console.log(f"   Max cyclomatic complexity: {summary.get('max_cyclomatic', 0)}")
    console.log(f"   Max cognitive complexity: {summary.get('max_cognitive', 0)}")
    if functions:
        console.log(f"\n   Top {AnalyticsBotTopN.TOP_COMPLEX_FUNCTIONS_PREVIEW} most complex functions:")
        for i, func in enumerate(take_top_n(functions, AnalyticsBotTopN.TOP_COMPLEX_FUNCTIONS_PREVIEW), 1):
            console.log(f"   {i}. {func.get('file', 'unknown').split('/')[-1]} (lines {func.get('lines', '?')})")
            cyc, cog, length = func.get("cyclomatic", 0), func.get("cognitive", 0), func.get("length", 0)
            console.log(f"      Cyclomatic: {cyc}, Cognitive: {cog}, Length: {length}")
    return complexity_result


def _run_smell_scan(project_path: str) -> dict:  # type: ignore[type-arg]
    """Run code smell detection and log summary."""
    console.log("\n2. Detecting code smells...")
    result = detect_code_smells_tool(
        project_folder=project_path,
        language="typescript",
        include_patterns=_TS_PATTERNS,
        exclude_patterns=_TS_EXCLUDES,
        long_function_lines=50,
        parameter_count=5,
        nesting_depth=4,
        class_lines=300,
        class_methods=20,
        detect_magic_numbers=True,
    )
    return _format_smell_summary(result)


def _format_smell_summary(smells_result: dict) -> dict:  # type: ignore[type-arg]
    """Log smell summary and return the result dict."""
    if smells_result.get("smells"):
        by_severity = count_by_key(smells_result["smells"], "severity")
        console.log(f"   Total code smells: {smells_result.get('total_smells', 0)}")
        log_count_breakdown(console.log, by_severity, order=["high", "medium", "low"], indent="   ", capitalize_labels=True)
    else:
        console.log("   No code smells detected")
    return smells_result


def _run_security_scan(project_path: str) -> dict:  # type: ignore[type-arg]
    """Run security vulnerability scan and log summary."""
    console.log("\n3. Scanning for security vulnerabilities...")
    result = detect_security_issues_tool(
        project_folder=project_path, language="typescript", issue_types=["all"], severity_threshold="low", max_issues=200
    )
    return _format_security_summary(result)


def _format_security_summary(security_result: dict) -> dict:  # type: ignore[type-arg]
    """Log security summary and return the result dict."""
    if security_result.get("issues"):
        by_severity = count_by_key(security_result["issues"], "severity")
        by_type = count_by_key(security_result["issues"], "issue_type")
        console.log(f"   Total security issues: {security_result.get('total_issues', 0)}")
        console.log("   By severity:")
        log_count_breakdown(console.log, by_severity, order=["critical", "high", "medium", "low"], indent="     ", capitalize_labels=True)
        console.log("   By type:")
        top_types = take_top_n(sorted(by_type.items(), key=lambda x: x[1], reverse=True), AnalyticsBotTopN.TOP_SECURITY_TYPES_PREVIEW)
        for issue_type, count in top_types:
            console.log(f"     {issue_type}: {count}")
    else:
        console.log("   No security issues detected")
    return security_result


def analyze_project(project_path: str) -> dict:  # type: ignore[type-arg]
    """Run comprehensive analysis on AnalyticsBot."""
    print_section_header(console.log, "AnalyticsBot Code Analysis", width=FormattingDefaults.WIDE_SECTION_WIDTH, trailing_newline=True)

    complexity_result: dict = {}  # type: ignore[type-arg]
    smells_result: dict = {}  # type: ignore[type-arg]
    security_result: dict = {}  # type: ignore[type-arg]

    try:
        complexity_result = _run_complexity_scan(project_path)
    except Exception as e:
        console.error(f"   Error: {e}")

    try:
        smells_result = _run_smell_scan(project_path)
    except Exception as e:
        console.error(f"   Error: {e}")

    try:
        security_result = _run_security_scan(project_path)
    except Exception as e:
        console.error(f"   Error: {e}")

    console.log(f"\n{'=' * FormattingDefaults.WIDE_SECTION_WIDTH}")
    console.success("Analysis Complete")
    console.log(f"{'=' * FormattingDefaults.WIDE_SECTION_WIDTH}\n")

    return {"complexity": complexity_result, "smells": smells_result, "security": security_result}


if __name__ == "__main__":
    analyticsbot_path = "/Users/alyshialedlie/code/ISPublicSites/AnalyticsBot"

    results = analyze_project(analyticsbot_path)

    # Save detailed results
    output_file = Path(__file__).parent.parent / "analyticsbot_analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    console.log(f"Detailed results saved to: {output_file}")
