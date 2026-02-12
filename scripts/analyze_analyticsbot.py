#!/usr/bin/env python3
"""Comprehensive code analysis for AnalyticsBot project."""

import json
import sys
from pathlib import Path

from ast_grep_mcp.utils.console_logger import console

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool, detect_code_smells_tool  # noqa: E402
from ast_grep_mcp.features.quality.tools import detect_security_issues_tool  # noqa: E402


def analyze_project(project_path: str):
    """Run comprehensive analysis on AnalyticsBot."""

    console.log(f"\n{'=' * 80}")
    console.log("AnalyticsBot Code Analysis")
    console.log(f"{'=' * 80}\n")

    # 1. Complexity Analysis - TypeScript/JavaScript
    console.log("1. Analyzing complexity metrics (TypeScript/JavaScript)...")
    try:
        complexity_result = analyze_complexity_tool(
            project_folder=project_path,
            language="typescript",
            include_patterns=["**/*.ts", "**/*.tsx", "**/*.js", "**/*.mjs"],
            exclude_patterns=["**/node_modules/**", "**/build/**", "**/dist/**"],
            cyclomatic_threshold=10,
            cognitive_threshold=15,
            nesting_threshold=4,
            length_threshold=50,
            store_results=False,
        )

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
            console.log("\n   Top 3 most complex functions:")
            for i, func in enumerate(functions[:3], 1):
                console.log(f"   {i}. {func.get('file', 'unknown').split('/')[-1]} (lines {func.get('lines', '?')})")
                console.log(
                    f"      Cyclomatic: {func.get('cyclomatic', 0)}, Cognitive: {func.get('cognitive', 0)}, Length: {func.get('length', 0)}"
                )

    except Exception as e:
        console.error(f"   Error: {e}")

    # 2. Code Smells Detection
    console.log("\n2. Detecting code smells...")
    try:
        smells_result = detect_code_smells_tool(
            project_folder=project_path,
            language="typescript",
            include_patterns=["**/*.ts", "**/*.tsx", "**/*.js", "**/*.mjs"],
            exclude_patterns=["**/node_modules/**", "**/build/**", "**/dist/**"],
            long_function_lines=50,
            parameter_count=5,
            nesting_depth=4,
            class_lines=300,
            class_methods=20,
            detect_magic_numbers=True,
        )

        if smells_result.get("smells"):
            by_severity = {}
            for smell in smells_result["smells"]:
                sev = smell.get("severity", "unknown")
                by_severity[sev] = by_severity.get(sev, 0) + 1

            console.log(f"   Total code smells: {smells_result.get('total_smells', 0)}")
            for severity in ["high", "medium", "low"]:
                if severity in by_severity:
                    console.log(f"   {severity.capitalize()}: {by_severity[severity]}")
        else:
            console.log("   No code smells detected")

    except Exception as e:
        console.error(f"   Error: {e}")

    # 3. Security Vulnerabilities
    console.log("\n3. Scanning for security vulnerabilities...")
    try:
        security_result = detect_security_issues_tool(
            project_folder=project_path, language="typescript", issue_types=["all"], severity_threshold="low", max_issues=200
        )

        if security_result.get("issues"):
            by_severity = {}
            by_type = {}
            for issue in security_result["issues"]:
                sev = issue.get("severity", "unknown")
                itype = issue.get("issue_type", "unknown")
                by_severity[sev] = by_severity.get(sev, 0) + 1
                by_type[itype] = by_type.get(itype, 0) + 1

            console.log(f"   Total security issues: {security_result.get('total_issues', 0)}")
            console.log("   By severity:")
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    console.log(f"     {severity.capitalize()}: {by_severity[severity]}")

            console.log("   By type:")
            for issue_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]:
                console.log(f"     {issue_type}: {count}")
        else:
            console.log("   No security issues detected")

    except Exception as e:
        console.error(f"   Error: {e}")

    console.log(f"\n{'=' * 80}")
    console.success("Analysis Complete")
    console.log(f"{'=' * 80}\n")

    # Return structured data
    return {
        "complexity": complexity_result if "complexity_result" in locals() else {},
        "smells": smells_result if "smells_result" in locals() else {},
        "security": security_result if "security_result" in locals() else {},
    }


if __name__ == "__main__":
    analyticsbot_path = "/Users/alyshialedlie/code/ISPublicSites/AnalyticsBot"

    results = analyze_project(analyticsbot_path)

    # Save detailed results
    output_file = Path(__file__).parent.parent / "analyticsbot_analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    console.log(f"Detailed results saved to: {output_file}")
